"""Tests for _contact_to_export_model mapping function.

Bugs fixed:
1. Non-Arabic names resulted in empty first_name/last_name (no fallback).
   Fix: split contact.name when arabic_name is None.
2. Missing company_profile caused AttributeError.
   Fix: use safe attribute access with None checks.
3. Emirate was not populated from phone number.
   Fix: infer emirate from landline area code via infer_uae_emirate().
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from models.enums import (
    ContactType,
    PhoneType,
    Region,
    SourceType,
    UAECarrier,
    VerificationMethod,
    VerificationStatus,
)
from models.models import (
    ArabicName,
    CompanyProfile,
    ConfidenceScore,
    EmailRecord,
    PhoneRecord,
    RecruiterContact,
    SourceResult,
)


def _make_contact(
    name: str = "John Smith",
    arabic_name: ArabicName | None = None,
    emails: list | None = None,
    phones: list | None = None,
    company: str | None = None,
    company_profile: CompanyProfile | None = None,
    title: str | None = None,
    region: Region = Region.UAE,
) -> RecruiterContact:
    """Helper to build a RecruiterContact for testing."""
    return RecruiterContact(
        name=name,
        arabic_name=arabic_name,
        emails=emails or [],
        phones=phones or [],
        company=company,
        company_profile=company_profile,
        title=title,
        region=region,
        confidence=ConfidenceScore(value=0.7),
        sources=[
            SourceResult(
                source_name="test",
                source_type=SourceType.API,
            )
        ],
    )


def _make_email(
    email: str = "test@example.com",
    is_primary: bool = True,
    verification_status: VerificationStatus = VerificationStatus.SMTP_VALID,
    verification_method: VerificationMethod = VerificationMethod.SMTP_RCPT,
    source: SourceType = SourceType.API,
) -> EmailRecord:
    return EmailRecord(
        email=email,
        is_primary=is_primary,
        verification_status=verification_status,
        verification_method=verification_method,
        source=source,
    )


def _make_phone(
    phone: str = "+971501234567",
    is_primary: bool = True,
    line_type: PhoneType = PhoneType.MOBILE,
    is_whatsapp: bool = False,
    carrier: str | None = None,
    validation_status: VerificationStatus = VerificationStatus.UNVERIFIED,
) -> PhoneRecord:
    return PhoneRecord(
        phone=phone,
        is_primary=is_primary,
        line_type=line_type,
        is_whatsapp=is_whatsapp,
        carrier=carrier,
        validation_status=validation_status,
        country_code="AE",
        source=SourceType.API,
    )


class TestExportNonArabicName:
    """Non-Arabic names should populate first_name/last_name via name split."""

    def test_non_arabic_name_exports_first_last(self):
        from rcf.cli import _contact_to_export_model

        contact = _make_contact(name="John Smith")
        result = _contact_to_export_model(contact)
        assert result.first_name == "John"
        assert result.last_name == "Smith"

    def test_single_name_fallback(self):
        from rcf.cli import _contact_to_export_model

        contact = _make_contact(name="Madonna")
        result = _contact_to_export_model(contact)
        assert result.first_name == "Madonna"
        assert result.last_name == ""

    def test_multi_part_name_split(self):
        """name.split(None, 1) splits into at most 2 parts."""
        from rcf.cli import _contact_to_export_model

        contact = _make_contact(name="Mary Jane Watson")
        result = _contact_to_export_model(contact)
        assert result.first_name == "Mary"
        # split(None, 1) gives ["Mary", "Jane Watson"]
        assert result.last_name == "Jane Watson"


class TestExportArabicName:
    """Arabic names should use ArabicName.first_name / last_name."""

    def test_arabic_name_used(self):
        from rcf.cli import _contact_to_export_model

        arabic = ArabicName(original_name="Mohammed Al Rashid")
        contact = _make_contact(name="Mohammed Al Rashid", arabic_name=arabic)
        result = _contact_to_export_model(contact)
        assert result.first_name == "mohammed"
        assert result.last_name == "rashid"

    def test_arabic_name_overrides_name_split(self):
        from rcf.cli import _contact_to_export_model

        arabic = ArabicName(original_name="Ahmed Bin Sulaiman")
        contact = _make_contact(name="Ahmed Bin Sulaiman", arabic_name=arabic)
        result = _contact_to_export_model(contact)
        # ArabicName auto-populates first/last from normalized form
        assert result.first_name != ""
        assert result.last_name != ""


class TestExportCompanyProfileNone:
    """Exporting contact without company_profile should not crash."""

    def test_no_company_profile_no_crash(self):
        from rcf.cli import _contact_to_export_model

        contact = _make_contact(company="Acme Corp", company_profile=None)
        result = _contact_to_export_model(contact)
        assert result.company == "Acme Corp"
        assert result.company_domain == ""
        assert result.industry == ""

    def test_with_company_profile(self):
        from rcf.cli import _contact_to_export_model

        profile = CompanyProfile(
            name="Acme Corp",
            domain_com="acme.com",
            industry="technology",
        )
        contact = _make_contact(company="Acme Corp", company_profile=profile)
        result = _contact_to_export_model(contact)
        assert result.company_domain == "acme.com"
        assert result.industry == "technology"

    def test_company_profile_with_none_fields(self):
        from rcf.cli import _contact_to_export_model

        profile = CompanyProfile(name="Acme Corp")
        contact = _make_contact(company="Acme Corp", company_profile=profile)
        result = _contact_to_export_model(contact)
        assert result.company_domain == ""
        assert result.industry == ""


class TestExportEmirateFromPhone:
    """Emirate should be inferred from landline phone number."""

    def test_dubai_landline_emirate(self):
        from rcf.cli import _contact_to_export_model

        phone = _make_phone(phone="+97141234567", line_type=PhoneType.LANDLINE)
        contact = _make_contact(phones=[phone])
        result = _contact_to_export_model(contact)
        assert result.emirate == "Dubai"

    def test_abu_dhabi_landline_emirate(self):
        from rcf.cli import _contact_to_export_model

        phone = _make_phone(phone="+97121234567", line_type=PhoneType.LANDLINE)
        contact = _make_contact(phones=[phone])
        result = _contact_to_export_model(contact)
        assert result.emirate == "Abu Dhabi"

    def test_mobile_number_no_emirate(self):
        """Mobile numbers don't map to an emirate — should be empty."""
        from rcf.cli import _contact_to_export_model

        phone = _make_phone(phone="+971501234567", line_type=PhoneType.MOBILE)
        contact = _make_contact(phones=[phone])
        result = _contact_to_export_model(contact)
        assert result.emirate == ""

    def test_no_phone_no_crash(self):
        from rcf.cli import _contact_to_export_model

        contact = _make_contact(phones=[])
        result = _contact_to_export_model(contact)
        assert result.emirate == ""


class TestExportEmailPhone:
    """Email and phone export edge cases."""

    def test_no_email_no_phone(self):
        from rcf.cli import _contact_to_export_model

        contact = _make_contact(emails=[], phones=[])
        result = _contact_to_export_model(contact)
        assert result.email == ""
        assert result.phone == ""
        assert result.email_verified is None
        assert result.phone_verified is None

    def test_primary_email_selected(self):
        from rcf.cli import _contact_to_export_model

        primary = _make_email(email="primary@test.com", is_primary=True)
        secondary = _make_email(email="secondary@test.com", is_primary=False)
        contact = _make_contact(emails=[secondary, primary])
        result = _contact_to_export_model(contact)
        assert result.email == "primary@test.com"

    def test_first_email_fallback_when_no_primary(self):
        from rcf.cli import _contact_to_export_model

        email1 = _make_email(email="first@test.com", is_primary=False)
        email2 = _make_email(email="second@test.com", is_primary=False)
        contact = _make_contact(emails=[email1, email2])
        result = _contact_to_export_model(contact)
        assert result.email == "first@test.com"

    def test_confidence_tiers(self):
        from rcf.cli import _contact_to_export_model

        for score, expected_tier in [
            (0.9, "high"),
            (0.7, "medium"),
            (0.3, "low"),
            (0.0, "unverified"),
        ]:
            contact = _make_contact()
            contact.confidence = ConfidenceScore(value=score)
            result = _contact_to_export_model(contact)
            assert result.confidence_tier == expected_tier
