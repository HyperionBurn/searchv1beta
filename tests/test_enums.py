"""
Tests for enum definitions (models/enums.py).

Covers:
  - All enums have expected members
  - String values are lowercase
  - JSON serialization produces correct strings
"""

import json

import pytest

from models.enums import (
    APIProvider,
    ContactType,
    ExportFormat,
    GCSCountry,
    PhoneType,
    Region,
    SessionStatus,
    SourceType,
    UAECarrier,
    UAEFreeZone,
    VerificationMethod,
    VerificationStatus,
)


# ===========================================================================
# Region
# ===========================================================================


class TestRegion:
    def test_has_all_members(self):
        expected = {"UAE", "SAUDI", "QATAR", "BAHRAIN", "OMAN", "KUWAIT", "GCC", "GLOBAL"}
        assert set(Region.__members__.keys()) == expected

    def test_values_are_lowercase(self):
        for member in Region:
            assert member.value == member.value.lower()

    def test_json_serialization(self):
        data = {"region": Region.UAE}
        serialized = json.dumps(data, default=str)
        assert '"uae"' in serialized

    def test_from_value(self):
        assert Region("uae") == Region.UAE
        assert Region("saudi") == Region.SAUDI


# ===========================================================================
# GCSCountry
# ===========================================================================


class TestGCSCountry:
    def test_has_all_gcc_members(self):
        expected = {"AE", "SA", "QA", "BH", "OM", "KW"}
        assert set(GCSCountry.__members__.keys()) == expected

    def test_values_lowercase(self):
        for member in GCSCountry:
            assert member.value == member.value.lower()


# ===========================================================================
# ContactType
# ===========================================================================


class TestContactType:
    def test_has_expected_members(self):
        expected = {"RECRUITER", "HR_MANAGER", "TALENT_ACQUISITION", "HEADHUNTER", "AGENCY"}
        assert set(ContactType.__members__.keys()) == expected

    def test_recruiter_value(self):
        assert ContactType.RECRUITER.value == "recruiter"

    def test_json_roundtrip(self):
        data = {"type": ContactType.HEADHUNTER.value}
        assert json.loads(json.dumps(data))["type"] == "headhunter"


# ===========================================================================
# SourceType
# ===========================================================================


class TestSourceType:
    def test_has_expected_members(self):
        expected = {"API", "SCRAPE", "PERMUTATION", "DIRECTORY", "CLASSIFIED", "SOCIAL", "EVENT", "BROWSER", "OSINT", "EMAIL"}
        assert set(SourceType.__members__.keys()) == expected

    def test_values_lowercase(self):
        for member in SourceType:
            assert member.value == member.value.lower()


# ===========================================================================
# APIProvider
# ===========================================================================


class TestAPIProvider:
    def test_has_core_providers(self):
        core = {"HUNTER", "SNOV", "ROCKETREACH", "LINKEDIN", "BAYT"}
        members = set(APIProvider.__members__.keys())
        assert core.issubset(members)

    def test_values_lowercase(self):
        for member in APIProvider:
            assert member.value == member.value.lower()


# ===========================================================================
# VerificationStatus
# ===========================================================================


class TestVerificationStatus:
    def test_has_expected_members(self):
        expected = {
            "UNVERIFIED", "SYNTAX_VALID", "DNS_VALID",
            "SMTP_VALID", "API_VALID", "BOUNCE", "INVALID",
        }
        assert set(VerificationStatus.__members__.keys()) == expected

    def test_values_lowercase(self):
        for member in VerificationStatus:
            assert member.value == member.value.lower()


# ===========================================================================
# VerificationMethod
# ===========================================================================


class TestVerificationMethod:
    def test_has_expected_members(self):
        expected = {"REGEX", "MX_LOOKUP", "SMTP_RCPT", "API_CHECK", "BREACH_DB", "MANUAL", "WEB_CONFIRM"}
        assert set(VerificationMethod.__members__.keys()) == expected


# ===========================================================================
# PhoneType
# ===========================================================================


class TestPhoneType:
    def test_has_expected_members(self):
        expected = {"MOBILE", "LANDLINE", "TOLLFREE", "PREMIUM", "UNKNOWN"}
        assert set(PhoneType.__members__.keys()) == expected


# ===========================================================================
# UAECarrier
# ===========================================================================


class TestUAECarrier:
    def test_has_expected_members(self):
        expected = {"ETISALAT", "DU", "VIRGIN_MOBILE", "UNKNOWN"}
        assert set(UAECarrier.__members__.keys()) == expected

    def test_values_lowercase(self):
        for member in UAECarrier:
            assert member.value == member.value.lower()


# ===========================================================================
# UAEFreeZone
# ===========================================================================


class TestUAEFreeZone:
    def test_has_core_free_zones(self):
        core = {"DMCC", "DIFC", "JAFZA", "ADGM"}
        members = set(UAEFreeZone.__members__.keys())
        assert core.issubset(members)


# ===========================================================================
# SessionStatus
# ===========================================================================


class TestSessionStatus:
    def test_has_expected_members(self):
        expected = {"RUNNING", "COMPLETED", "FAILED", "CANCELLED"}
        assert set(SessionStatus.__members__.keys()) == expected


# ===========================================================================
# ExportFormat
# ===========================================================================


class TestExportFormat:
    def test_has_expected_members(self):
        expected = {"CSV", "JSON", "XLSX", "HTML", "EXCEL", "VCARD", "MARKDOWN"}
        assert set(ExportFormat.__members__.keys()) == expected

    def test_json_serialization(self):
        data = {"format": ExportFormat.CSV.value}
        serialized = json.dumps(data)
        assert '"csv"' in serialized


# ===========================================================================
# Cross-cutting: all enums are str subclasses
# ===========================================================================


class TestEnumStringBehavior:
    """All enums should be str subclasses so they serialize naturally."""

    @pytest.mark.parametrize("enum_cls", [
        Region, GCSCountry, ContactType, SourceType, APIProvider,
        VerificationStatus, VerificationMethod, PhoneType,
        UAECarrier, UAEFreeZone, SessionStatus, ExportFormat,
    ])
    def test_is_str_subclass(self, enum_cls):
        for member in enum_cls:
            assert isinstance(member, str)

    @pytest.mark.parametrize("enum_cls", [
        Region, GCSCountry, ContactType, SourceType,
        VerificationStatus, VerificationMethod, PhoneType,
        UAECarrier, SessionStatus, ExportFormat,
    ])
    def test_all_values_lowercase(self, enum_cls):
        for member in enum_cls:
            assert member.value == member.value.lower(), (
                f"{enum_cls.__name__}.{member.name} value is not lowercase: {member.value!r}"
            )
