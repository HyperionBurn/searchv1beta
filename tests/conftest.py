"""
Shared pytest fixtures for the RCF test suite.
"""

import os
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timezone

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
    ConfidenceScore,
    ContactQuery,
    EmailRecord,
    PhoneRecord,
    RecruiterContact,
    SourceResult,
)


# ---------------------------------------------------------------------------
# Sample ContactQuery
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_contact_query() -> ContactQuery:
    """Returns a ContactQuery scoped to UAE region with a test company name."""
    return ContactQuery(
        company_names=["DMCC"],
        region=Region.UAE,
        contact_types=[ContactType.RECRUITER],
        max_results=50,
        min_confidence=0.4,
    )


# ---------------------------------------------------------------------------
# Sample EmailRecord
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_email_record() -> EmailRecord:
    """Returns a verified EmailRecord."""
    return EmailRecord(
        email="ahmed.recruiter@dmcc.ae",
        verification_status=VerificationStatus.SMTP_VALID,
        verification_method=VerificationMethod.SMTP_RCPT,
        verification_date=datetime(2026, 4, 15, tzinfo=timezone.utc),
        is_primary=True,
        source=SourceType.API,
    )


# ---------------------------------------------------------------------------
# Sample PhoneRecord
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_phone_record() -> PhoneRecord:
    """Returns a UAE mobile PhoneRecord in E.164 format."""
    return PhoneRecord(
        phone="+971501234567",
        validation_status=VerificationStatus.SMTP_VALID,
        country_code="AE",
        line_type=PhoneType.MOBILE,
        is_whatsapp=True,
        is_primary=True,
        source=SourceType.API,
    )


# ---------------------------------------------------------------------------
# Sample SourceResult
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_source_result() -> SourceResult:
    """Returns a SourceResult from a LinkedIn scrape."""
    return SourceResult(
        source_name="linkedin",
        source_type=SourceType.SOCIAL,
        raw_data={"profile_id": "abc123"},
        extracted_name="Ahmed Al-Rashid",
        extracted_email="ahmed.rashid@example.com",
        extracted_phone="+971501234567",
        extracted_company="DMCC",
        extracted_title="Senior Recruiter",
        extracted_linkedin="https://linkedin.com/in/ahmed-rashid",
        confidence_contribution=0.7,
    )


# ---------------------------------------------------------------------------
# Sample RecruiterContact
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_recruiter_contact(
    sample_email_record: EmailRecord,
    sample_phone_record: PhoneRecord,
) -> RecruiterContact:
    """Returns a RecruiterContact with emails and phones."""
    return RecruiterContact(
        name="Ahmed Al-Rashid",
        emails=[sample_email_record],
        phones=[sample_phone_record],
        company="DMCC",
        title="Senior Recruiter",
        linkedin_url="https://linkedin.com/in/ahmed-rashid",
        region=Region.UAE,
        confidence=ConfidenceScore(
            value=0.85,
            source_count=2,
            email_verified=True,
            phone_verified=True,
            linkedin_found=True,
        ),
    )


# ---------------------------------------------------------------------------
# Temporary SQLite database
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_db():
    """
    Creates a temporary SQLite database with the full schema from db/schema.sql.

    Yields the connection object. The temporary file is cleaned up after the test.
    """
    schema_path = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    # Create a temp file-based DB
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(db_path)
    conn.executescript(schema_sql)
    conn.commit()

    yield conn

    conn.close()
    os.unlink(db_path)
