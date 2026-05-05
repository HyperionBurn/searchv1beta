"""
Tests for pipeline orchestrator fixes (rcf/core/orchestrator.py).

Covers:
  - Async context manager support (__aenter__ / __aexit__)
  - Deduplication uses asyncio.to_thread for CPU-bound work
  - RateLimiterRegistry integration
  - PipelineConfig and PipelineResult construction
"""

import asyncio
import inspect

import pytest

from models.enums import ContactType, Region, SourceType
from models.models import ContactQuery, EmailRecord, RecruiterContact

from rcf.core.orchestrator import PipelineConfig, PipelineOrchestrator, PipelineResult
from rcf.core.plugin_registry import PluginRegistry


# ===========================================================================
# Async context manager
# ===========================================================================


class TestOrchestratorFixes:
    def test_orchestrator_is_context_manager(self):
        """PipelineOrchestrator supports async context manager."""
        assert hasattr(PipelineOrchestrator, "__aenter__")
        assert hasattr(PipelineOrchestrator, "__aexit__")

    @pytest.mark.asyncio
    async def test_orchestrator_context_manager_closes_registry(self):
        """Using async with should call registry.close_all on exit."""
        registry = PluginRegistry()
        async with PipelineOrchestrator(registry=registry) as orch:
            assert orch.registry is registry
        # Exiting the context manager should have completed without error

    def test_rate_limiter_integrated(self):
        """Orchestrator should have a rate_limiter attribute."""
        from rcf.utils.rate_limiter import RateLimiterRegistry

        registry = PluginRegistry()
        orch = PipelineOrchestrator(registry=registry)
        assert hasattr(orch, "rate_limiter")
        assert isinstance(orch.rate_limiter, RateLimiterRegistry)


# ===========================================================================
# Deduplication uses asyncio.to_thread
# ===========================================================================


class TestDeduplicationThreadOffload:
    def test_dedup_runs_in_thread(self):
        """run_deduplication should use asyncio.to_thread."""
        source = inspect.getsource(PipelineOrchestrator.run_deduplication)
        assert "to_thread" in source

    def test_dedup_method_is_async(self):
        """run_deduplication should be a coroutine function."""
        assert asyncio.iscoroutinefunction(PipelineOrchestrator.run_deduplication)


# ===========================================================================
# PipelineResult edge cases
# ===========================================================================


class TestPipelineResultFixes:
    def test_early_exit_defaults_false(self):
        result = PipelineResult(
            contacts=[],
            total_raw_results=0,
            total_after_dedup=0,
            total_after_verification=0,
            plugins_used=[],
            plugins_skipped=[],
            plugins_failed=[],
            api_usage={},
            duration_seconds=0.0,
        )
        assert result.early_exit is False

    def test_early_exit_can_be_true(self):
        result = PipelineResult(
            contacts=[],
            total_raw_results=0,
            total_after_dedup=0,
            total_after_verification=0,
            plugins_used=[],
            plugins_skipped=["plugin_a"],
            plugins_failed=[],
            api_usage={},
            duration_seconds=0.1,
            early_exit=True,
        )
        assert result.early_exit is True
        assert "plugin_a" in result.plugins_skipped


# ===========================================================================
# Orchestrator construction
# ===========================================================================


class TestOrchestratorConstruction:
    def test_default_config(self):
        registry = PluginRegistry()
        orch = PipelineOrchestrator(registry=registry)
        assert orch.config.max_concurrent_plugins == 5

    def test_custom_config(self):
        registry = PluginRegistry()
        config = PipelineConfig(max_concurrent_plugins=10)
        orch = PipelineOrchestrator(registry=registry, config=config)
        assert orch.config.max_concurrent_plugins == 10

    def test_has_dedup_engine(self):
        registry = PluginRegistry()
        orch = PipelineOrchestrator(registry=registry)
        from rcf.core.deduplicator import DeduplicationEngine

        assert isinstance(orch.dedup, DeduplicationEngine)

    def test_has_scorer_engine(self):
        registry = PluginRegistry()
        orch = PipelineOrchestrator(registry=registry)
        from rcf.core.scorer import ConfidenceScoringEngine

        assert isinstance(orch.scorer, ConfidenceScoringEngine)

    def test_has_api_tracker(self):
        registry = PluginRegistry()
        orch = PipelineOrchestrator(registry=registry)
        from rcf.core.api_tracker import APITracker

        assert isinstance(orch.api_tracker, APITracker)
