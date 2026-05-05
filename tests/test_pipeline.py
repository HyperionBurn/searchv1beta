"""
Tests for the pipeline orchestration (rcf/core/orchestrator.py).

Covers:
  - PipelineConfig defaults
  - PipelineResult creation
  - Plugin registry discovery
  - Empty query returns empty results
"""

import pytest

from models.enums import ContactType, Region, SourceType
from models.models import ContactQuery, EmailRecord, PhoneRecord, RecruiterContact, SourceResult

from rcf.core.orchestrator import PipelineConfig, PipelineResult
from rcf.core.plugin_registry import PluginRegistry


# ===========================================================================
# PipelineConfig
# ===========================================================================


class TestPipelineConfig:
    def test_defaults(self):
        config = PipelineConfig()
        assert config.max_concurrent_plugins == 5
        assert config.confidence_threshold_early_exit == 0.80
        assert config.enable_enrichment is True
        assert config.enable_verification is True
        assert config.enable_scoring is True
        assert config.waterfall_enabled is True
        assert config.plugin_timeout_seconds == 120.0

    def test_custom_values(self):
        config = PipelineConfig(
            max_concurrent_plugins=10,
            confidence_threshold_early_exit=0.90,
            enable_enrichment=False,
        )
        assert config.max_concurrent_plugins == 10
        assert config.confidence_threshold_early_exit == 0.90
        assert config.enable_enrichment is False


# ===========================================================================
# PipelineResult
# ===========================================================================


class TestPipelineResult:
    def test_creation(self):
        result = PipelineResult(
            contacts=[],
            total_raw_results=0,
            total_after_dedup=0,
            total_after_verification=0,
            plugins_used=[],
            plugins_skipped=[],
            plugins_failed=[],
            api_usage={},
            duration_seconds=0.5,
        )
        assert result.contacts == []
        assert result.total_raw_results == 0
        assert result.early_exit is False

    def test_with_contacts(self):
        contact = RecruiterContact(
            name="Test Person",
            emails=[EmailRecord(email="test@example.com")],
        )
        result = PipelineResult(
            contacts=[contact],
            total_raw_results=1,
            total_after_dedup=1,
            total_after_verification=1,
            plugins_used=["test_plugin"],
            plugins_skipped=[],
            plugins_failed=[],
            api_usage={"test_plugin": 1},
            duration_seconds=1.2,
        )
        assert len(result.contacts) == 1
        assert result.contacts[0].name == "Test Person"
        assert "test_plugin" in result.plugins_used

    def test_early_exit_flag(self):
        result = PipelineResult(
            contacts=[],
            total_raw_results=0,
            total_after_dedup=0,
            total_after_verification=0,
            plugins_used=[],
            plugins_skipped=["remaining"],
            plugins_failed=[],
            api_usage={},
            duration_seconds=0.1,
            early_exit=True,
        )
        assert result.early_exit is True


# ===========================================================================
# PluginRegistry
# ===========================================================================


class TestPluginRegistry:
    def test_empty_registry(self):
        registry = PluginRegistry()
        assert registry.list_all() == []

    def test_register_and_get(self):
        """Register a mock plugin and retrieve it."""
        from unittest.mock import MagicMock

        registry = PluginRegistry()
        mock_plugin = MagicMock()
        mock_plugin.name = "test_plugin"
        mock_plugin.source_type = SourceType.API
        mock_plugin.priority = 1

        registry.register(mock_plugin)
        assert registry.get("test_plugin") == mock_plugin

    def test_get_nonexistent_raises(self):
        registry = PluginRegistry()
        with pytest.raises(KeyError, match="not found"):
            registry.get("nonexistent")

    def test_duplicate_register_raises(self):
        from unittest.mock import MagicMock

        registry = PluginRegistry()
        mock_plugin = MagicMock()
        mock_plugin.name = "test_plugin"
        mock_plugin.source_type = SourceType.API
        mock_plugin.priority = 1

        registry.register(mock_plugin)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(mock_plugin)

    def test_unregister(self):
        from unittest.mock import MagicMock

        registry = PluginRegistry()
        mock_plugin = MagicMock()
        mock_plugin.name = "test_plugin"
        mock_plugin.source_type = SourceType.API
        mock_plugin.priority = 1

        registry.register(mock_plugin)
        registry.unregister("test_plugin")
        assert registry.list_all() == []

    def test_get_by_priority(self):
        from unittest.mock import MagicMock

        registry = PluginRegistry()

        for name, priority in [("low", 10), ("high", 1), ("mid", 5)]:
            p = MagicMock()
            p.name = name
            p.priority = priority
            registry.register(p)

        ordered = registry.get_by_priority()
        assert [p.name for p in ordered] == ["high", "mid", "low"]

    def test_get_for_query_empty_registry(self):
        """With no plugins registered, get_for_query returns empty list."""
        registry = PluginRegistry()
        query = ContactQuery(
            company_names=["Test"],
            region=Region.UAE,
        )
        plugins = registry.get_for_query(query)
        assert plugins == []


# ===========================================================================
# PipelineOrchestrator — basic integration
# ===========================================================================


class TestPipelineOrchestratorBasic:
    def test_instantiation_with_defaults(self):
        from rcf.core.orchestrator import PipelineOrchestrator

        registry = PluginRegistry()
        orchestrator = PipelineOrchestrator(registry)
        assert orchestrator.config.max_concurrent_plugins == 5

    def test_custom_config(self):
        from rcf.core.orchestrator import PipelineOrchestrator

        registry = PluginRegistry()
        config = PipelineConfig(max_concurrent_plugins=3)
        orchestrator = PipelineOrchestrator(registry, config=config)
        assert orchestrator.config.max_concurrent_plugins == 3
