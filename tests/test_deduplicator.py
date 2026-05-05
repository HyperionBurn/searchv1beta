"""
Tests for the deduplication engine (rcf/core/deduplicator.py + spec/deduplicator.py).

Covers:
  - Merge two results with same email
  - Merge two results with same phone
  - Different names should NOT merge
  - Arabic name variants should merge (Mohammed/Muhammad/Mohd)
  - Empty input returns empty
"""

import pytest

from models.enums import Region, SourceType
from models.models import SourceResult
from rcf.core.deduplicator import DeduplicationEngine


def _make_source(
    name: str = "Test Person",
    email: str | None = None,
    phone: str | None = None,
    company: str | None = None,
    linkedin: str | None = None,
    title: str | None = None,
    source_name: str = "test_source",
) -> SourceResult:
    """Helper to create a SourceResult for dedup tests."""
    return SourceResult(
        source_name=source_name,
        source_type=SourceType.API,
        extracted_name=name,
        extracted_email=email,
        extracted_phone=phone,
        extracted_company=company,
        extracted_linkedin=linkedin,
        extracted_title=title,
    )


class TestDeduplicationEngine:
    """Tests for the DeduplicationEngine.merge() method."""

    def setup_method(self):
        self.engine = DeduplicationEngine()

    def test_empty_input_returns_empty(self):
        result = self.engine.merge([])
        assert result == []

    def test_single_result_returns_one_contact(self):
        results = [_make_source(name="Ahmed Ali", email="ahmed@example.com")]
        contacts = self.engine.merge(results)
        assert len(contacts) == 1
        assert contacts[0].name == "Ahmed Ali"

    # ---- Email-based merge ----

    def test_merge_same_email(self):
        results = [
            _make_source(name="Ahmed Ali", email="ahmed@example.com", company="DMCC", source_name="linkedin"),
            _make_source(name="Ahmed Ali", email="ahmed@example.com", company="DMCC", source_name="bayt"),
        ]
        contacts = self.engine.merge(results)
        assert len(contacts) == 1
        assert contacts[0].emails[0].email == "ahmed@example.com"

    # ---- Phone-based merge ----

    def test_merge_same_phone(self):
        results = [
            _make_source(name="Saeed Khan", phone="+971501234567", source_name="linkedin"),
            _make_source(name="Saeed Khan", phone="+971501234567", source_name="google_maps"),
        ]
        contacts = self.engine.merge(results)
        assert len(contacts) == 1
        assert contacts[0].phones[0].phone == "+971501234567"

    # ---- LinkedIn-based merge ----

    def test_merge_same_linkedin(self):
        results = [
            _make_source(
                name="Fatima Hassan",
                linkedin="https://linkedin.com/in/fatima-hassan",
                source_name="linkedin",
            ),
            _make_source(
                name="Fatima Hassan",
                linkedin="https://linkedin.com/in/fatima-hassan",
                source_name="bayt",
            ),
        ]
        contacts = self.engine.merge(results)
        assert len(contacts) == 1

    # ---- Different people should NOT merge ----

    def test_different_names_do_not_merge(self):
        results = [
            _make_source(name="Ahmed Ali", email="ahmed@example.com", source_name="src_a"),
            _make_source(name="Saeed Khan", email="saeed@example.com", source_name="src_b"),
        ]
        contacts = self.engine.merge(results)
        assert len(contacts) == 2

    def test_different_companies_no_overlap(self):
        results = [
            _make_source(name="Ahmed Ali", company="DMCC", source_name="src_a"),
            _make_source(name="Ahmed Ali", company="DIFC", source_name="src_b"),
        ]
        # Without email/phone/linkedin overlap, fuzzy name + different company = no merge
        contacts = self.engine.merge(results)
        assert len(contacts) == 2

    # ---- Arabic name variants should merge ----

    def test_arabic_mohammed_variants_merge(self):
        """Mohammed/Muhammad should be treated as the same name."""
        results = [
            _make_source(
                name="Mohammed Ahmed",
                email="m.ahmed@company.com",
                company="TestCo",
                source_name="linkedin",
            ),
            _make_source(
                name="Muhammad Ahmed",
                email="m.ahmed@company.com",
                company="TestCo",
                source_name="bayt",
            ),
        ]
        contacts = self.engine.merge(results)
        # Same email → merge regardless of name spelling
        assert len(contacts) == 1

    def test_fuzzy_name_with_same_company(self):
        """Fuzzy name match + same company should merge."""
        results = [
            _make_source(
                name="Mohammed Ali",
                company="DMCC",
                source_name="linkedin",
            ),
            _make_source(
                name="Muhammad Ali",
                company="DMCC",
                source_name="google_maps",
            ),
        ]
        contacts = self.engine.merge(results)
        # Arabic name fuzzy match + same company should merge
        assert len(contacts) == 1

    # ---- Merge picks best data ----

    def test_merge_prefers_non_none_fields(self):
        results = [
            _make_source(
                name="Ahmed Ali",
                email="ahmed@example.com",
                source_name="src_a",
                company=None,
                title="Recruiter",
            ),
            _make_source(
                name="Ahmed Ali",
                email="ahmed@example.com",
                source_name="src_b",
                company="DMCC",
                title=None,
            ),
        ]
        contacts = self.engine.merge(results)
        assert len(contacts) == 1
        # Should have merged data from both sources
        assert contacts[0].emails[0].email == "ahmed@example.com"
        # Best company and title should be picked
        assert contacts[0].company == "DMCC"
        assert contacts[0].title == "Recruiter"

    # ---- Multiple distinct results ----

    def test_three_distinct_people(self):
        results = [
            _make_source(name="Ahmed Ali", email="ahmed@example.com", source_name="a"),
            _make_source(name="Saeed Khan", email="saeed@example.com", source_name="b"),
            _make_source(name="Omar Hassan", email="omar@example.com", source_name="c"),
        ]
        contacts = self.engine.merge(results)
        assert len(contacts) == 3

    # ---- Source tracking ----

    def test_merged_contact_has_all_sources(self):
        results = [
            _make_source(name="Ahmed Ali", email="ahmed@example.com", source_name="linkedin"),
            _make_source(name="Ahmed Ali", email="ahmed@example.com", source_name="bayt"),
        ]
        contacts = self.engine.merge(results)
        assert len(contacts) == 1
        assert len(contacts[0].sources) == 2
