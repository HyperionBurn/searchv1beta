"""
SourcePlugin — Abstract Base Class for all data source plugins.

Every data source (API, scraper, directory, local utility) implements this ABC.
The plugin system provides:
  - Uniform async discover/enrich/validate interface
  - Built-in rate limiting via asyncio.Semaphore
  - Automatic retry via tenacity
  - Pydantic return types (SourceResult, RecruiterContact)
  - Per-plugin configuration validation
  - Region & source-type filtering

Plugin Lifecycle:
  1. __init__() — Load config, create HTTP client, init semaphore
  2. validate_config() — Check API keys, connectivity
  3. discover(query) → list[SourceResult] — Find raw contacts
  4. enrich(contact) → RecruiterContact — Fill in missing data
  5. get_rate_limit_info() → RateLimitInfo — Report usage

Usage:
    class HunterPlugin(SourcePlugin):
        async def discover(self, query: ContactQuery) -> list[SourceResult]:
            ...
"""

from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)
import httpx
import structlog

from models.enums import Region, SourceType
from models.models import ContactQuery, RecruiterContact, SourceResult


# ---------------------------------------------------------------------------
# Supporting types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RateLimitInfo:
    """Snapshot of a plugin's current rate-limit / credit status."""

    requests_per_minute: int
    requests_per_month: int | None = None
    credits_used: int = 0
    credits_limit: int | None = None
    credits_remaining: int | None = None
    reset_date: datetime | None = None
    is_depleted: bool = False


@dataclass(frozen=True)
class PluginSpec:
    """
    Static metadata about a plugin — one per source.
    Loaded from the ALL_PLUGINS registry dict and used for filtering,
    sorting, and configuration validation.
    """

    name: str
    source_type: SourceType
    regions: list[Region]
    data_types: list[str]
    priority: int                     # 1 (highest) – 10 (lowest)
    requires_browser: bool
    api_key_env: str | None
    rate_limit_rpm: int               # requests per minute
    rate_limit_monthly: int | None    # credits per month (None = unlimited)
    url_pattern: str                  # base URL or URL regex
    extraction_method: str            # "rest_api", "graphql", "html_scrape",
                                      # "browser_scrape", "permutation",
                                      # "local_computation", "whatsapp_api"


@dataclass
class PluginInfo:
    """Public-facing plugin metadata for listing / display."""

    name: str
    source_type: SourceType
    regions: list[Region]
    data_types: list[str]
    priority: int
    requires_browser: bool
    api_key_env: str | None
    is_configured: bool
    rate_limit_rpm: int
    rate_limit_monthly: int | None


# ---------------------------------------------------------------------------
# Tenacity retry decorator — shared across all plugins
# ---------------------------------------------------------------------------

def _default_retry():
    """Common retry policy for all plugin HTTP calls."""
    return retry(
        retry=retry_if_exception_type((
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.RemoteProtocolError,
        )),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        before_sleep=before_sleep_log(
            structlog.get_logger(),  # type: ignore[arg-type]
            level=30,  # WARNING
        ),
        reraise=True,
    )


# ---------------------------------------------------------------------------
# SourcePlugin ABC
# ---------------------------------------------------------------------------

class SourcePlugin(ABC):
    """
    Abstract base class for every data-source plugin.

    Subclasses MUST implement:
        - discover()    → find raw contacts from a source
        - enrich()      → fill in missing data for a contact
        - validate_config() → check API keys, connectivity
        - get_rate_limit_info() → report credit usage

    Subclasses SHOULD override (optional):
        - close()       → clean up resources (HTTP clients, browsers)

    Subclasses get for free:
        - self.semaphore          → asyncio.Semaphore for concurrency control
        - self.http_client        → httpx.AsyncClient with retry
        - self.logger             → structlog bound with plugin name
        - self._resolve_api_key() → read API key from env
    """

    # Class-level spec — each concrete plugin MUST override this
    SPEC: ClassVar[PluginSpec]

    def __init__(self, max_concurrency: int = 5) -> None:
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrency)
        self.http_client: httpx.AsyncClient = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
            headers={"User-Agent": "RCF/1.0"},
        )
        self.logger = structlog.get_logger().bind(plugin=self.name)

    # ── Properties (derived from SPEC) ───────────────────────────────

    @property
    def name(self) -> str:
        return self.SPEC.name

    @property
    def source_type(self) -> SourceType:
        return self.SPEC.source_type

    @property
    def regions(self) -> list[Region]:
        return self.SPEC.regions

    @property
    def data_types(self) -> list[str]:
        return self.SPEC.data_types

    @property
    def priority(self) -> int:
        return self.SPEC.priority

    @property
    def requires_browser(self) -> bool:
        return self.SPEC.requires_browser

    @property
    def api_key_env(self) -> str | None:
        return self.SPEC.api_key_env

    # ── Abstract Methods ─────────────────────────────────────────────

    @abstractmethod
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """
        Query this source for raw contact data.

        Args:
            query: User search parameters (company, industry, region, etc.)

        Returns:
            List of raw SourceResult objects. Each contains extracted name,
            email, phone, company, title, etc. from this single source.

        Raises:
            PluginError: On unrecoverable source failure (after retries).
        """
        ...

    @abstractmethod
    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """
        Enrich an existing contact with additional data from this source.

        Called after discovery and initial merge. Use this to:
          - Add missing email/phone data
          - Verify existing data against this source
          - Add LinkedIn URL, job title, etc.

        Args:
            contact: Existing merged contact to enrich.

        Returns:
            Updated contact (may be the same object, modified in-place).
        """
        ...

    @abstractmethod
    async def validate_config(self) -> bool:
        """
        Verify that this plugin is correctly configured and operational.

        Checks:
          - Required API keys are set in environment
          - API endpoint is reachable (lightweight ping)
          - Required browser dependencies are available
          - Rate-limit credits are not depleted

        Returns:
            True if plugin is ready to use, False otherwise.
        """
        ...

    @abstractmethod
    async def get_rate_limit_info(self) -> RateLimitInfo:
        """
        Return current rate-limit and credit usage for this plugin.

        Called by the orchestrator to decide whether to skip a depleted
        source or throttle requests.
        """
        ...

    # ── Built-in helpers ─────────────────────────────────────────────

    async def close(self) -> None:
        """Clean up HTTP client and any browser resources."""
        await self.http_client.aclose()

    def _resolve_api_key(self) -> str | None:
        """Read the API key from the environment variable specified in SPEC."""
        if self.SPEC.api_key_env is None:
            return None
        return os.environ.get(self.SPEC.api_key_env)

    def _make_source_result(
        self,
        *,
        raw_data: dict[str, Any] | None = None,
        extracted_name: str | None = None,
        extracted_email: str | None = None,
        extracted_phone: str | None = None,
        extracted_company: str | None = None,
        extracted_title: str | None = None,
        extracted_linkedin: str | None = None,
        source_url: str | None = None,
        confidence_contribution: float = 0.3,
        request_id: str | None = None,
    ) -> SourceResult:
        """Factory helper to build a SourceResult with plugin metadata filled in."""
        return SourceResult(
            source_name=self.name,
            source_type=self.source_type,
            raw_data=raw_data or {},
            extracted_name=extracted_name,
            extracted_email=extracted_email,
            extracted_phone=extracted_phone,
            extracted_company=extracted_company,
            extracted_title=extracted_title,
            extracted_linkedin=extracted_linkedin,
            source_url=source_url,
            confidence_contribution=confidence_contribution,
            request_id=request_id,
        )


# ---------------------------------------------------------------------------
# Plugin Error types
# ---------------------------------------------------------------------------

class PluginError(Exception):
    """Base exception for plugin failures."""

    def __init__(self, plugin_name: str, message: str, *, original: Exception | None = None) -> None:
        self.plugin_name = plugin_name
        self.original = original
        super().__init__(f"[{plugin_name}] {message}")


class PluginConfigError(PluginError):
    """Plugin is misconfigured (missing API key, bad URL, etc.)."""


class PluginRateLimitError(PluginError):
    """Plugin has exceeded its rate limit or credit quota."""

    def __init__(self, plugin_name: str, retry_after: int | None = None) -> None:
        self.retry_after = retry_after
        super().__init__(plugin_name, f"Rate limit exceeded (retry_after={retry_after}s)")


class PluginValidationError(PluginError):
    """Plugin data validation failed."""


# ---------------------------------------------------------------------------
# ALL_PLUGINS — Complete specification for all 30 sources
# ---------------------------------------------------------------------------

ALL_PLUGINS: dict[str, PluginSpec] = {
    # ==================================================================
    # API PLUGINS (11)
    # ==================================================================

    "hunter": PluginSpec(
        name="hunter",
        source_type=SourceType.API,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["email", "email_pattern", "company_domain"],
        priority=2,
        requires_browser=False,
        api_key_env="HUNTER_API_KEY",
        rate_limit_rpm=10,
        rate_limit_monthly=50,
        url_pattern="https://api.hunter.io/v2",
        extraction_method="rest_api",
    ),

    "apollo": PluginSpec(
        name="apollo",
        source_type=SourceType.API,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["email", "phone", "title", "company", "linkedin"],
        priority=2,
        requires_browser=False,
        api_key_env="APOLLO_API_KEY",
        rate_limit_rpm=10,
        rate_limit_monthly=60,
        url_pattern="https://api.apollo.io/v1",
        extraction_method="rest_api",
    ),

    "seamless_ai": PluginSpec(
        name="seamless_ai",
        source_type=SourceType.API,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["email", "phone", "title", "company"],
        priority=3,
        requires_browser=False,
        api_key_env="SEAMLESS_AI_KEY",
        rate_limit_rpm=8,
        rate_limit_monthly=50,
        url_pattern="https://api.seamless.ai",
        extraction_method="rest_api",
    ),

    "snov": PluginSpec(
        name="snov",
        source_type=SourceType.API,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["email", "email_pattern", "company_domain"],
        priority=2,
        requires_browser=False,
        api_key_env="SNOV_API_KEY",
        rate_limit_rpm=10,
        rate_limit_monthly=50,
        url_pattern="https://api.snov.io/v1",
        extraction_method="rest_api",
    ),

    "rocketreach": PluginSpec(
        name="rocketreach",
        source_type=SourceType.API,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["email", "phone", "linkedin", "title"],
        priority=2,
        requires_browser=False,
        api_key_env="ROCKETREACH_API_KEY",
        rate_limit_rpm=10,
        rate_limit_monthly=25,
        url_pattern="https://api.rocketreach.co/v2",
        extraction_method="rest_api",
    ),

    "zerobounce": PluginSpec(
        name="zerobounce",
        source_type=SourceType.API,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["email_verification"],
        priority=2,
        requires_browser=False,
        api_key_env="ZEROBOUNCE_API_KEY",
        rate_limit_rpm=10,
        rate_limit_monthly=100,
        url_pattern="https://api.zerobounce.net/v2",
        extraction_method="rest_api",
    ),

    "abstract_api": PluginSpec(
        name="abstract_api",
        source_type=SourceType.API,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["email_verification", "phone_validation"],
        priority=3,
        requires_browser=False,
        api_key_env="ABSTRACT_API_KEY",
        rate_limit_rpm=8,
        rate_limit_monthly=100,
        url_pattern="https://app.abstractapi.com/api",
        extraction_method="rest_api",
    ),

    "people_data_labs": PluginSpec(
        name="people_data_labs",
        source_type=SourceType.API,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["email", "phone", "title", "company", "linkedin", "education"],
        priority=3,
        requires_browser=False,
        api_key_env="PDL_API_KEY",
        rate_limit_rpm=10,
        rate_limit_monthly=100,
        url_pattern="https://api.peopledatalabs.com/v5",
        extraction_method="rest_api",
    ),

    "google_places": PluginSpec(
        name="google_places",
        source_type=SourceType.API,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["company", "phone", "address", "website"],
        priority=1,
        requires_browser=False,
        api_key_env="GOOGLE_PLACES_API_KEY",
        rate_limit_rpm=20,
        rate_limit_monthly=None,
        url_pattern="https://maps.googleapis.com/maps/api",
        extraction_method="rest_api",
    ),

    "greenhouse": PluginSpec(
        name="greenhouse",
        source_type=SourceType.API,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["recruiter_name", "company", "job_listings"],
        priority=3,
        requires_browser=False,
        api_key_env=None,
        rate_limit_rpm=12,
        rate_limit_monthly=None,
        url_pattern="https://boards-api.greenhouse.io/v1/boards/{company}",
        extraction_method="rest_api",
    ),

    "lever": PluginSpec(
        name="lever",
        source_type=SourceType.API,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["recruiter_name", "company", "job_listings"],
        priority=3,
        requires_browser=False,
        api_key_env=None,
        rate_limit_rpm=12,
        rate_limit_monthly=None,
        url_pattern="https://api.lever.co/v1/postings/{company}",
        extraction_method="rest_api",
    ),

    # ==================================================================
    # SCRAPING PLUGINS (9)
    # ==================================================================

    "linkedin": PluginSpec(
        name="linkedin",
        source_type=SourceType.SCRAPE,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["name", "title", "company", "linkedin", "email_hint"],
        priority=3,
        requires_browser=True,
        api_key_env=None,
        rate_limit_rpm=4,
        rate_limit_monthly=None,
        url_pattern="https://www.linkedin.com/search/results/people/?keywords={query}",
        extraction_method="browser_scrape",
    ),

    "dmcc_directory": PluginSpec(
        name="dmcc_directory",
        source_type=SourceType.SCRAPE,
        regions=[Region.UAE],
        data_types=["company", "name", "phone", "email", "freezone"],
        priority=2,
        requires_browser=False,
        api_key_env=None,
        rate_limit_rpm=6,
        rate_limit_monthly=None,
        url_pattern="https://www.dmcc.ae/business-search?q={query}",
        extraction_method="html_scrape",
    ),

    "expatriates": PluginSpec(
        name="expatriates",
        source_type=SourceType.SCRAPE,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.KUWAIT, Region.BAHRAIN, Region.OMAN],
        data_types=["phone", "name", "classified_text"],
        priority=1,
        requires_browser=False,
        api_key_env=None,
        rate_limit_rpm=6,
        rate_limit_monthly=None,
        url_pattern="https://www.expatriates.com/classifieds/{region}/index.html",
        extraction_method="html_scrape",
    ),

    "dubizzle": PluginSpec(
        name="dubizzle",
        source_type=SourceType.SCRAPE,
        regions=[Region.UAE],
        data_types=["phone", "name", "classified_text"],
        priority=1,
        requires_browser=False,
        api_key_env=None,
        rate_limit_rpm=6,
        rate_limit_monthly=None,
        url_pattern="https://dubai.dubizzle.com/search/?q={query}",
        extraction_method="html_scrape",
    ),

    "uae_yellow_pages": PluginSpec(
        name="uae_yellow_pages",
        source_type=SourceType.SCRAPE,
        regions=[Region.UAE],
        data_types=["company", "phone", "address", "website"],
        priority=2,
        requires_browser=False,
        api_key_env=None,
        rate_limit_rpm=6,
        rate_limit_monthly=None,
        url_pattern="https://www.yellowpages.ae/search?q={query}",
        extraction_method="html_scrape",
    ),

    "bayt": PluginSpec(
        name="bayt",
        source_type=SourceType.SCRAPE,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT],
        data_types=["name", "title", "company", "nationality"],
        priority=2,
        requires_browser=False,
        api_key_env=None,
        rate_limit_rpm=6,
        rate_limit_monthly=None,
        url_pattern="https://www.bayt.com/en/uae/jobs/{query}",
        extraction_method="html_scrape",
    ),

    "gulf_talent": PluginSpec(
        name="gulf_talent",
        source_type=SourceType.SCRAPE,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT],
        data_types=["name", "title", "company", "linkedin"],
        priority=2,
        requires_browser=False,
        api_key_env=None,
        rate_limit_rpm=6,
        rate_limit_monthly=None,
        url_pattern="https://www.gulftalent.com/jobs/search?keywords={query}",
        extraction_method="html_scrape",
    ),

    "naukrigulf": PluginSpec(
        name="naukrigulf",
        source_type=SourceType.SCRAPE,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT],
        data_types=["name", "title", "company", "phone"],
        priority=2,
        requires_browser=False,
        api_key_env=None,
        rate_limit_rpm=6,
        rate_limit_monthly=None,
        url_pattern="https://www.naukrigulf.com/{query}-jobs",
        extraction_method="html_scrape",
    ),

    "facebook_groups": PluginSpec(
        name="facebook_groups",
        source_type=SourceType.SCRAPE,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR],
        data_types=["name", "phone", "post_text"],
        priority=3,
        requires_browser=True,
        api_key_env=None,
        rate_limit_rpm=4,
        rate_limit_monthly=None,
        url_pattern="https://www.facebook.com/groups/{group_id}/search/?q={query}",
        extraction_method="browser_scrape",
    ),

    # ==================================================================
    # EXECUTIVE SEARCH PLUGINS (5)
    # ==================================================================

    "heidrick_and_struggles": PluginSpec(
        name="heidrick_and_struggles",
        source_type=SourceType.SCRAPE,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["name", "title", "company", "linkedin", "office"],
        priority=4,
        requires_browser=False,
        api_key_env=None,
        rate_limit_rpm=6,
        rate_limit_monthly=None,
        url_pattern="https://www.heidrick.com/people-search?query={query}",
        extraction_method="html_scrape",
    ),

    "korn_ferry": PluginSpec(
        name="korn_ferry",
        source_type=SourceType.SCRAPE,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["name", "title", "company", "office"],
        priority=4,
        requires_browser=False,
        api_key_env=None,
        rate_limit_rpm=6,
        rate_limit_monthly=None,
        url_pattern="https://www.kornferry.com/consultants?query={query}",
        extraction_method="html_scrape",
    ),

    "spencer_stuart": PluginSpec(
        name="spencer_stuart",
        source_type=SourceType.SCRAPE,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["name", "title", "company", "office"],
        priority=4,
        requires_browser=False,
        api_key_env=None,
        rate_limit_rpm=6,
        rate_limit_monthly=None,
        url_pattern="https://www.spencerstuart.com/consultants?query={query}",
        extraction_method="html_scrape",
    ),

    "egon_zehnder": PluginSpec(
        name="egon_zehnder",
        source_type=SourceType.SCRAPE,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["name", "title", "company", "office"],
        priority=4,
        requires_browser=False,
        api_key_env=None,
        rate_limit_rpm=6,
        rate_limit_monthly=None,
        url_pattern="https://www.egonzehnder.com/consultants?query={query}",
        extraction_method="html_scrape",
    ),

    "russell_reynolds": PluginSpec(
        name="russell_reynolds",
        source_type=SourceType.SCRAPE,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["name", "title", "company", "office"],
        priority=4,
        requires_browser=False,
        api_key_env=None,
        rate_limit_rpm=6,
        rate_limit_monthly=None,
        url_pattern="https://www.russellreynolds.com/consultants?query={query}",
        extraction_method="html_scrape",
    ),

    # ==================================================================
    # LOCAL / UTILITY PLUGINS (5)
    # ==================================================================

    "email_permutator": PluginSpec(
        name="email_permutator",
        source_type=SourceType.PERMUTATION,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["email", "email_pattern"],
        priority=5,
        requires_browser=False,
        api_key_env=None,
        rate_limit_rpm=60,
        rate_limit_monthly=None,
        url_pattern="local://permutation",
        extraction_method="local_computation",
    ),

    "google_dorking": PluginSpec(
        name="google_dorking",
        source_type=SourceType.SCRAPE,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["email", "phone", "name", "linkedin"],
        priority=2,
        requires_browser=False,
        api_key_env=None,
        rate_limit_rpm=6,
        rate_limit_monthly=None,
        url_pattern='https://www.google.com/search?q="{query}"+email+recruiter',
        extraction_method="html_scrape",
    ),

    "whatsapp_checker": PluginSpec(
        name="whatsapp_checker",
        source_type=SourceType.SOCIAL,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT],
        data_types=["whatsapp_presence", "whatsapp_business"],
        priority=5,
        requires_browser=False,
        api_key_env="WHATSAPP_API_KEY",
        rate_limit_rpm=10,
        rate_limit_monthly=None,
        url_pattern="https://api.whatsapp.com/check",
        extraction_method="whatsapp_api",
    ),

    "uae_phone_detector": PluginSpec(
        name="uae_phone_detector",
        source_type=SourceType.API,
        regions=[Region.UAE],
        data_types=["phone_validation", "carrier_detection", "emirate_detection"],
        priority=5,
        requires_browser=False,
        api_key_env=None,
        rate_limit_rpm=60,
        rate_limit_monthly=None,
        url_pattern="local://uae_phone",
        extraction_method="local_computation",
    ),

    "arabic_name_normalizer": PluginSpec(
        name="arabic_name_normalizer",
        source_type=SourceType.PERMUTATION,
        regions=[Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT, Region.GLOBAL],
        data_types=["name_variants", "email_permutations"],
        priority=5,
        requires_browser=False,
        api_key_env=None,
        rate_limit_rpm=60,
        rate_limit_monthly=None,
        url_pattern="local://arabic_name",
        extraction_method="local_computation",
    ),
}
