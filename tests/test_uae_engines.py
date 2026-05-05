"""
Tests for UAE engine modules (uae_engine_spec/).

Covers:
  - UAE phone engine: landline area code mapping (Dubai fix)
  - Arabic name engine: Mohammed variants (distinct names excluded)
  - UAE domain engine: employer database completeness
"""

import pytest


# ===========================================================================
# UAE Phone Engine — Landline area codes
# ===========================================================================


class TestUAEPhoneEngine:
    def test_dubai_landline_area_code(self):
        """04 is Dubai, not Fujairah."""
        from uae_engine_spec.uae_phone_engine import UAE_LANDLINE_AREA_MAP, Emirate

        assert UAE_LANDLINE_AREA_MAP["04"] == Emirate.DUBAI

    def test_fujairah_area_code(self):
        """Fujairah uses 09."""
        from uae_engine_spec.uae_phone_engine import UAE_LANDLINE_AREA_MAP, Emirate

        assert UAE_LANDLINE_AREA_MAP["09"] == Emirate.FUJAIRAH

    def test_abu_dhabi_area_code(self):
        """Abu Dhabi uses 02."""
        from uae_engine_spec.uae_phone_engine import UAE_LANDLINE_AREA_MAP, Emirate

        assert UAE_LANDLINE_AREA_MAP["02"] == Emirate.ABU_DHABI

    def test_sharjah_area_code(self):
        """Sharjah uses 06."""
        from uae_engine_spec.uae_phone_engine import UAE_LANDLINE_AREA_MAP, Emirate

        assert UAE_LANDLINE_AREA_MAP["06"] == Emirate.SHARJAH

    def test_ras_al_khaimah_area_code(self):
        """Ras Al Khaimah uses 07."""
        from uae_engine_spec.uae_phone_engine import UAE_LANDLINE_AREA_MAP, Emirate

        assert UAE_LANDLINE_AREA_MAP["07"] == Emirate.RAS_AL_KHAIMAH

    def test_al_ain_area_code(self):
        """Al Ain uses 03 and maps to Abu Dhabi emirate."""
        from uae_engine_spec.uae_phone_engine import UAE_LANDLINE_AREA_MAP, Emirate

        assert UAE_LANDLINE_AREA_MAP["03"] == Emirate.ABU_DHABI

    def test_all_area_codes_mapped(self):
        """All 6 UAE area codes are mapped."""
        from uae_engine_spec.uae_phone_engine import UAE_LANDLINE_AREA_MAP

        assert len(UAE_LANDLINE_AREA_MAP) >= 6

    def test_no_none_or_unknown_values(self):
        """No area code should map to UNKNOWN emirate."""
        from uae_engine_spec.uae_phone_engine import UAE_LANDLINE_AREA_MAP, Emirate

        for code, emirate in UAE_LANDLINE_AREA_MAP.items():
            assert emirate != Emirate.UNKNOWN, f"Area code {code} maps to UNKNOWN"


# ===========================================================================
# Arabic Name Engine — Mohammed variants
# ===========================================================================


class TestArabicNameEngine:
    def test_mohammed_variants_exclude_distinct_names(self):
        """Ahmed, Mahmoud, Hamid should NOT be in Mohammed variants."""
        from uae_engine_spec.arabic_name_engine import MOHAMMED_VARIANTS

        assert "ahmed" not in MOHAMMED_VARIANTS
        assert "ahmad" not in MOHAMMED_VARIANTS
        assert "mahmoud" not in MOHAMMED_VARIANTS
        assert "mahmud" not in MOHAMMED_VARIANTS
        assert "hamid" not in MOHAMMED_VARIANTS

    def test_mohammed_variants_include_core(self):
        """Core Mohammed transliterations must be present."""
        from uae_engine_spec.arabic_name_engine import MOHAMMED_VARIANTS

        assert "mohammed" in MOHAMMED_VARIANTS
        assert "muhammad" in MOHAMMED_VARIANTS
        assert "mohamed" in MOHAMMED_VARIANTS
        assert "mohd" in MOHAMMED_VARIANTS

    def test_mohammed_variants_include_new_entries(self):
        """Newly added variants should be present."""
        from uae_engine_spec.arabic_name_engine import MOHAMMED_VARIANTS

        assert "mohamet" in MOHAMMED_VARIANTS
        assert "mohummad" in MOHAMMED_VARIANTS

    def test_mohammed_variants_all_lowercase(self):
        """All variants should be lowercase for consistent matching."""
        from uae_engine_spec.arabic_name_engine import MOHAMMED_VARIANTS

        for variant in MOHAMMED_VARIANTS:
            assert variant == variant.lower(), f"Variant '{variant}' is not lowercase"


# ===========================================================================
# UAE Domain Engine — Employer database
# ===========================================================================


class TestUAEDomainEngine:
    def test_employer_database_has_major_companies(self):
        """Verify recently added employers exist."""
        from uae_engine_spec.uae_domain_engine import EMPLOYER_DATABASE

        names = [e.company_name.lower() for e in EMPLOYER_DATABASE]
        assert any("emirates" in n for n in names)
        assert any("mashreq" in n for n in names)

    def test_employer_database_has_emirates_group(self):
        """Emirates Group must be in the database."""
        from uae_engine_spec.uae_domain_engine import EMPLOYER_DATABASE

        names = [e.company_name for e in EMPLOYER_DATABASE]
        assert any("Emirates Group" in n for n in names)

    def test_employer_database_has_etihad(self):
        """Etihad Airways must be in the database."""
        from uae_engine_spec.uae_domain_engine import EMPLOYER_DATABASE

        names = [e.company_name for e in EMPLOYER_DATABASE]
        assert any("Etihad" in n for n in names)

    def test_employer_entries_have_primary_domain(self):
        """Every employer must have a non-empty primary_domain."""
        from uae_engine_spec.uae_domain_engine import EMPLOYER_DATABASE

        for emp in EMPLOYER_DATABASE:
            assert emp.primary_domain, f"{emp.company_name} has empty primary_domain"
            assert "." in emp.primary_domain, f"{emp.company_name}: invalid domain '{emp.primary_domain}'"

    def test_employer_entries_have_known_aliases(self):
        """Every employer must have at least one known alias."""
        from uae_engine_spec.uae_domain_engine import EMPLOYER_DATABASE

        for emp in EMPLOYER_DATABASE:
            assert len(emp.known_aliases) >= 1, f"{emp.company_name} has no known_aliases"

    def test_employer_database_minimum_count(self):
        """Employer database should have at least 20 entries."""
        from uae_engine_spec.uae_domain_engine import EMPLOYER_DATABASE

        assert len(EMPLOYER_DATABASE) >= 20
