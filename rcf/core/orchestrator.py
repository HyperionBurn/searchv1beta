"""
Pipeline Orchestrator — Main async pipeline for contact discovery, enrichment,
and verification.

Pipeline Flow:
  ContactQuery
    → filter plugins by region/type
    → run discovery waterfall (priority order, early exit at confidence threshold)
    → deduplicate results
    → run enrichment (parallel across contacts)
    → run verification (email + phone)
    → score confidence
    → return sorted RecruiterContact list

Waterfall Pattern:
  1. Sort plugins by priority (1 = highest)
  2. Run highest-priority plugin's discover()
  3. After each plugin, check if any merged contact exceeds min_confidence
  4. If threshold met for all target contacts, skip remaining plugins
  5. Continue until all plugins exhausted or threshold met

Concurrency:
  - Global asyncio.Semaphore limits total concurrent plugin calls
  - Per-plugin asyncio.Semaphore limits calls to each source
  - RateLimiterRegistry enforces per-minute quotas
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from models.enums import Region, SourceType, VerificationStatus
from models.models import (
    ContactQuery,
    ConfidenceScore,
    EmailRecord,
    PhoneRecord,
    RecruiterContact,
    SourceResult,
)

from .base_plugin import (
    PluginError,
    PluginRateLimitError,
    RateLimitInfo,
    SourcePlugin,
)
from .plugin_registry import PluginRegistry
from .deduplicator import DeduplicationEngine
from .scorer import ConfidenceScoringEngine
from .api_tracker import APITracker
from rcf.utils.rate_limiter import RateLimiterRegistry

logger = structlog.get_logger().bind(component="orchestrator")


# ---------------------------------------------------------------------------
# Pipeline configuration
# ---------------------------------------------------------------------------

@dataclass
class PipelineConfig:
    """Orchestrator-level configuration."""

    max_concurrent_plugins: int = 5
    confidence_threshold_early_exit: float = 0.80
    enable_enrichment: bool = True
    enable_verification: bool = True
    enable_scoring: bool = True
    waterfall_enabled: bool = True
    plugin_timeout_seconds: float = 120.0
    check_whatsapp: bool = False


@dataclass
class PipelineResult:
    """Result of a complete pipeline run."""

    contacts: list[RecruiterContact]
    total_raw_results: int
    total_after_dedup: int
    total_after_verification: int
    plugins_used: list[str]
    plugins_skipped: list[str]
    plugins_failed: list[str]
    api_usage: dict[str, int]
    duration_seconds: float
    early_exit: bool = False


# ---------------------------------------------------------------------------
# PipelineOrchestrator
# ---------------------------------------------------------------------------

class PipelineOrchestrator:
    """
    Main orchestrator that drives the full contact-finding pipeline.

    Usage:
        registry = PluginRegistry()
        await registry.discover_and_register()

        orchestrator = PipelineOrchestrator(registry)
        result = await orchestrator.run(query)
        for contact in result.contacts:
            print(contact.name, contact.confidence.value)
    """

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.registry.close_all()
        return False

    def __init__(
        self,
        registry: PluginRegistry,
        config: PipelineConfig | None = None,
        dedup_engine: DeduplicationEngine | None = None,
        scorer_engine: ConfidenceScoringEngine | None = None,
        api_tracker: APITracker | None = None,
    ) -> None:
        self.registry = registry
        self.config = config or PipelineConfig()
        self.dedup = dedup_engine or DeduplicationEngine()
        self.scorer = scorer_engine or ConfidenceScoringEngine()
        self.api_tracker = api_tracker or APITracker()
        self._global_semaphore = asyncio.Semaphore(
            self.config.max_concurrent_plugins
        )
        self.rate_limiter = RateLimiterRegistry()
        self.logger = logger

    # ── Main Pipeline ────────────────────────────────────────────────

    async def run(self, query: ContactQuery) -> PipelineResult:
        """
        Execute the complete pipeline: discover → dedup → enrich → verify → score.

        This is the primary entry point for the CLI and programmatic API.

        Args:
            query: User search parameters.

        Returns:
            PipelineResult with final contacts and execution metadata.
        """
        start = time.monotonic()

        self.logger.info(
            "pipeline_start",
            region=query.region.value,
            max_results=query.max_results,
            min_confidence=query.min_confidence,
        )

        plugins_used: list[str] = []
        plugins_skipped: list[str] = []
        plugins_failed: list[str] = []
        api_usage: dict[str, int] = {}
        early_exit = False

        # ── Phase 1: Discovery ──────────────────────────────────────
        all_raw_results: list[SourceResult] = []
        target_plugins = self.registry.get_for_query(query)

        self.logger.info(
            "discovery_start",
            plugin_count=len(target_plugins),
            plugins=[p.name for p in target_plugins],
        )

        if self.config.waterfall_enabled:
            # Waterfall: run plugins in priority order, check threshold after each
            for plugin in target_plugins:
                try:
                    results = await self._run_plugin_discovery(plugin, query)
                    all_raw_results.extend(results)
                    plugins_used.append(plugin.name)
                    api_usage[plugin.name] = len(results)

                    # Check early exit: do merged contacts meet threshold?
                    if self._check_early_exit(
                        all_raw_results, query.min_confidence
                    ):
                        early_exit = True
                        remaining = [
                            p.name for p in target_plugins
                            if p.name not in plugins_used
                        ]
                        plugins_skipped.extend(remaining)
                        self.logger.info(
                            "waterfall_early_exit",
                            confidence_met=True,
                            skipped_count=len(remaining),
                        )
                        break

                except PluginError as exc:
                    plugins_failed.append(plugin.name)
                    self.logger.warning(
                        "plugin_discovery_failed",
                        plugin=plugin.name,
                        error=str(exc),
                    )
                except asyncio.TimeoutError:
                    plugins_failed.append(plugin.name)
                    self.logger.warning(
                        "plugin_discovery_timeout",
                        plugin=plugin.name,
                        timeout=self.config.plugin_timeout_seconds,
                    )
        else:
            # Parallel: run all plugins concurrently
            tasks = [
                self._run_plugin_discovery(plugin, query)
                for plugin in target_plugins
            ]
            task_results = await asyncio.gather(*tasks, return_exceptions=True)

            for plugin, result in zip(target_plugins, task_results):
                if isinstance(result, Exception):
                    plugins_failed.append(plugin.name)
                    self.logger.warning(
                        "plugin_discovery_failed",
                        plugin=plugin.name,
                        error=str(result),
                    )
                else:
                    all_raw_results.extend(result)
                    plugins_used.append(plugin.name)
                    api_usage[plugin.name] = len(result)

        total_raw = len(all_raw_results)

        # ── Phase 2: Deduplication ──────────────────────────────────
        merged_contacts = await self.run_deduplication(all_raw_results)
        total_after_dedup = len(merged_contacts)

        self.logger.info(
            "dedup_complete",
            raw=total_raw,
            merged=total_after_dedup,
        )

        # ── Phase 3: Enrichment ─────────────────────────────────────
        if self.config.enable_enrichment and merged_contacts:
            merged_contacts = await self.run_enrichment(merged_contacts)

        # ── Phase 4: Verification ───────────────────────────────────
        if self.config.enable_verification and merged_contacts:
            merged_contacts = await self.run_verification(merged_contacts)

        # ── Phase 5: Scoring ────────────────────────────────────────
        if self.config.enable_scoring:
            merged_contacts = [
                self.scorer.score(contact)
                for contact in merged_contacts
            ]

        # ── Phase 6: Filter & Sort ──────────────────────────────────
        final_contacts = [
            c for c in merged_contacts
            if c.confidence.value >= query.min_confidence
        ]
        final_contacts.sort(
            key=lambda c: c.confidence.value,
            reverse=True,
        )
        final_contacts = final_contacts[:query.max_results]

        # ── Build result ────────────────────────────────────────────
        duration = time.monotonic() - start

        result = PipelineResult(
            contacts=final_contacts,
            total_raw_results=total_raw,
            total_after_dedup=total_after_dedup,
            total_after_verification=len(final_contacts),
            plugins_used=plugins_used,
            plugins_skipped=plugins_skipped,
            plugins_failed=plugins_failed,
            api_usage=api_usage,
            duration_seconds=round(duration, 3),
            early_exit=early_exit,
        )

        self.logger.info(
            "pipeline_complete",
            total_contacts=len(final_contacts),
            duration_seconds=result.duration_seconds,
            early_exit=early_exit,
        )

        return result

    # ── Individual Pipeline Phases ───────────────────────────────────

    async def run_discovery(self, query: ContactQuery) -> list[SourceResult]:
        """
        Run ONLY the discovery phase across all matching plugins.

        Returns raw SourceResult list (no dedup, enrichment, or scoring).
        """
        target_plugins = self.registry.get_for_query(query)
        all_results: list[SourceResult] = []

        for plugin in target_plugins:
            try:
                results = await self._run_plugin_discovery(plugin, query)
                all_results.extend(results)
            except PluginError:
                continue

        return all_results

    async def run_deduplication(
        self, results: list[SourceResult]
    ) -> list[RecruiterContact]:
        """
        Merge raw source results into deduplicated RecruiterContacts.

        Uses the DeduplicationEngine with 6 strategies:
          email, phone, fuzzy name, Arabic name, LinkedIn, WhatsApp.
        """
        return await asyncio.to_thread(self.dedup.merge, results)

    async def run_enrichment(
        self, contacts: list[RecruiterContact]
    ) -> list[RecruiterContact]:
        """
        Run enrichment plugins on all contacts concurrently.

        Enrichment adds missing data from secondary sources:
          - Email patterns from company domain
          - Phone numbers from directories
          - LinkedIn URLs from social sources
          - Arabic name variants
        """
        enriched: list[RecruiterContact] = []

        async def _enrich_one(contact: RecruiterContact) -> RecruiterContact:
            for plugin in self.registry.get_by_priority():
                if plugin.source_type in (SourceType.API, SourceType.SCRAPE):
                    try:
                        contact = await asyncio.wait_for(
                            plugin.enrich(contact),
                            timeout=30.0,
                        )
                    except (PluginError, asyncio.TimeoutError):
                        continue
            return contact

        tasks = [_enrich_one(c) for c in contacts]
        enriched = await asyncio.gather(*tasks)
        return list(enriched)

    async def run_verification(
        self, contacts: list[RecruiterContact]
    ) -> list[RecruiterContact]:
        """
        Run email and phone verification on all contacts.

        Uses the verification pipeline:
          - Email: syntax → DNS → SMTP → API (tiered, stop on definitive)
          - Phone: format → WhatsApp check → carrier detection
        """
        from spec.email_verifier import EmailVerificationPipeline
        from spec.phone_validator import PhoneValidationPipeline

        email_pipeline = EmailVerificationPipeline()
        phone_pipeline = PhoneValidationPipeline()

        verified: list[RecruiterContact] = []

        for contact in contacts:
            # Verify emails
            if contact.emails:
                verified_emails: list[EmailRecord] = []
                for email_rec in contact.emails:
                    try:
                        verified_rec = await email_pipeline.verify_record(email_rec)
                        verified_emails.append(verified_rec)
                    except Exception:
                        verified_emails.append(email_rec)
                contact.emails = verified_emails

            # Verify phones
            if contact.phones:
                verified_phones: list[PhoneRecord] = []
                for phone_rec in contact.phones:
                    try:
                        verified_rec = await phone_pipeline.verify_record(phone_rec)
                        verified_phones.append(verified_rec)
                    except Exception:
                        verified_phones.append(phone_rec)
                contact.phones = verified_phones

            verified.append(contact)

        return verified

    # ── Internal helpers ─────────────────────────────────────────────

    async def _run_plugin_discovery(
        self,
        plugin: SourcePlugin,
        query: ContactQuery,
    ) -> list[SourceResult]:
        """Execute a single plugin's discover() with semaphore and timeout."""
        async with self._global_semaphore:
            await self.rate_limiter.acquire(plugin.name)
            async with plugin.semaphore:
                results = await asyncio.wait_for(
                    plugin.discover(query),
                    timeout=self.config.plugin_timeout_seconds,
                )
                self.logger.debug(
                    "plugin_discovery_complete",
                    plugin=plugin.name,
                    results=len(results),
                )
                return results

    def _check_early_exit(
        self,
        results: list[SourceResult],
        min_confidence: float,
    ) -> bool:
        """
        Check if the waterfall can exit early.

        Heuristic: if the top merged contact would have confidence >=
        confidence_threshold_early_exit (default 0.80) based on the
        raw source results collected so far, skip remaining plugins.
        """
        if not results:
            return False

        # Quick heuristic: count unique names and source diversity
        name_groups: dict[str, list[SourceResult]] = {}
        for r in results:
            key = (r.extracted_name or "").lower().strip()
            if key:
                name_groups.setdefault(key, []).append(r)

        # If any name has 3+ corroborating sources, likely high confidence
        for group in name_groups.values():
            if len(group) >= 3:
                source_types = {r.source_type for r in group}
                if len(source_types) >= 2:
                    return True

        return False
