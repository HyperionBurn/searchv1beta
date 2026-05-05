"""
Tests for enum consolidation (models/enums.py + re-exports in rcf/config.py).

Covers:
  - Region.GCC member exists with correct value
  - ExportFormat has XLSX and HTML
  - SourceType has BROWSER, OSINT, EMAIL
  - rcf.config re-exports enums from models.enums (same class identity)
"""

import pytest

from models.enums import ExportFormat, Region, SourceType


# ===========================================================================
# Region
# ===========================================================================


class TestEnumConsolidation:
    def test_region_gcc_exists(self):
        assert Region.GCC.value == "gcc"

    def test_region_gcc_is_string_enum(self):
        assert isinstance(Region.GCC, str)

    def test_region_from_value_gcc(self):
        assert Region("gcc") == Region.GCC

    def test_region_all_values_lowercase(self):
        for member in Region:
            assert member.value == member.value.lower()


# ===========================================================================
# ExportFormat
# ===========================================================================

    def test_export_format_xlsx_html(self):
        assert ExportFormat.XLSX.value == "xlsx"
        assert ExportFormat.HTML.value == "html"

    def test_export_format_csv(self):
        assert ExportFormat.CSV.value == "csv"

    def test_export_format_all_lowercase(self):
        for member in ExportFormat:
            assert member.value == member.value.lower()


# ===========================================================================
# SourceType
# ===========================================================================

    def test_source_type_new_values(self):
        assert SourceType.BROWSER.value == "browser"
        assert SourceType.OSINT.value == "osint"
        assert SourceType.EMAIL.value == "email"

    def test_source_type_api_scrape(self):
        assert SourceType.API.value == "api"
        assert SourceType.SCRAPE.value == "scrape"


# ===========================================================================
# Re-export identity (rcf.config imports from models.enums)
# ===========================================================================

    def test_config_imports_from_models(self):
        """rcf.config should import enums from models.enums, not define its own."""
        import rcf.config

        # Verify they're the same class object
        assert rcf.config.Region is Region
        assert rcf.config.ExportFormat is ExportFormat
        assert rcf.config.SourceType is SourceType
