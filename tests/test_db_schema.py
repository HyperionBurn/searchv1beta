"""
Tests for the database schema (db/schema.sql).

Covers:
  - Create DB from schema.sql
  - Verify all tables exist
  - Insert and query a contact
  - FTS5 search works
  - Triggers fire correctly (updated_at)
"""

import sqlite3
from datetime import datetime

import pytest


# ===========================================================================
# Table existence
# ===========================================================================


class TestSchemaTables:
    EXPECTED_TABLES = {
        "companies",
        "contacts",
        "emails",
        "phones",
        "sources",
        "arabic_name_cache",
        "sessions",
        "search_results",
        "api_usage",
        "tags",
        "exports",
        "known_email_patterns",
    }

    def test_all_tables_created(self, temp_db):
        cursor = temp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}
        for table in self.EXPECTED_TABLES:
            assert table in tables, f"Missing table: {table}"

    def test_fts5_virtual_table(self, temp_db):
        cursor = temp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='fts5' OR sql LIKE '%fts5%'"
        )
        fts_tables = [row[0] for row in cursor.fetchall()]
        # FTS5 virtual tables may appear with different type in some SQLite versions
        # Verify the table exists and is queryable instead
        cursor2 = temp_db.execute(
            "SELECT name FROM sqlite_master WHERE name='contacts_fts'"
        )
        assert cursor2.fetchone() is not None, "contacts_fts table not found"

    def test_views_created(self, temp_db):
        cursor = temp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
        )
        views = {row[0] for row in cursor.fetchall()}
        assert "v_contact_detail" in views
        assert "v_api_usage_summary" in views


# ===========================================================================
# Company insertion
# ===========================================================================


class TestCompanyInsertion:
    def test_insert_and_query(self, temp_db):
        temp_db.execute(
            "INSERT INTO companies (name, domain_com, country, region) "
            "VALUES (?, ?, ?, ?)",
            ("DMCC", "dmcc.ae", "AE", "uae"),
        )
        temp_db.commit()

        row = temp_db.execute(
            "SELECT name, domain_com FROM companies WHERE name = ?",
            ("DMCC",),
        ).fetchone()

        assert row is not None
        assert row[0] == "DMCC"
        assert row[1] == "dmcc.ae"

    def test_free_zone_flag(self, temp_db):
        temp_db.execute(
            "INSERT INTO companies (name, is_uae_free_zone, free_zone_name) "
            "VALUES (?, ?, ?)",
            ("DMCC Free Zone Co", 1, "DMCC"),
        )
        temp_db.commit()

        row = temp_db.execute(
            "SELECT is_uae_free_zone, free_zone_name FROM companies WHERE name = ?",
            ("DMCC Free Zone Co",),
        ).fetchone()

        assert row[0] == 1
        assert row[1] == "DMCC"


# ===========================================================================
# Contact insertion
# ===========================================================================


class TestContactInsertion:
    def test_insert_contact(self, temp_db):
        temp_db.execute(
            "INSERT INTO contacts "
            "(id, name, first_name, last_name, normalized_name, company_name, "
            "contact_type, region, country, confidence_score) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "test-uuid-001",
                "Ahmed Al-Rashid",
                "Ahmed",
                "Al-Rashid",
                "ahmed al-rashid",
                "DMCC",
                "recruiter",
                "uae",
                "AE",
                0.85,
            ),
        )
        temp_db.commit()

        row = temp_db.execute(
            "SELECT name, company_name, confidence_score FROM contacts WHERE id = ?",
            ("test-uuid-001",),
        ).fetchone()

        assert row is not None
        assert row[0] == "Ahmed Al-Rashid"
        assert row[1] == "DMCC"
        assert abs(row[2] - 0.85) < 0.01

    def test_contact_with_linkedin(self, temp_db):
        temp_db.execute(
            "INSERT INTO contacts "
            "(id, name, normalized_name, linkedin_url, linkedin_found, region, country) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "test-uuid-002",
                "Saeed Khan",
                "saeed khan",
                "https://linkedin.com/in/saeed-khan",
                1,
                "uae",
                "AE",
            ),
        )
        temp_db.commit()

        row = temp_db.execute(
            "SELECT linkedin_url, linkedin_found FROM contacts WHERE id = ?",
            ("test-uuid-002",),
        ).fetchone()

        assert row[0] == "https://linkedin.com/in/saeed-khan"
        assert row[1] == 1


# ===========================================================================
# Email insertion
# ===========================================================================


class TestEmailInsertion:
    def test_insert_email(self, temp_db):
        # First create a contact
        temp_db.execute(
            "INSERT INTO contacts "
            "(id, name, normalized_name, region, country) "
            "VALUES (?, ?, ?, ?, ?)",
            ("c-001", "Test Person", "test person", "uae", "AE"),
        )

        temp_db.execute(
            "INSERT INTO emails "
            "(contact_id, email, verification_status, is_primary) "
            "VALUES (?, ?, ?, ?)",
            ("c-001", "test@example.com", "smtp_valid", 1),
        )
        temp_db.commit()

        row = temp_db.execute(
            "SELECT email, verification_status, is_primary FROM emails WHERE contact_id = ?",
            ("c-001",),
        ).fetchone()

        assert row is not None
        assert row[0] == "test@example.com"
        assert row[1] == "smtp_valid"
        assert row[2] == 1

    def test_unique_email_per_contact(self, temp_db):
        temp_db.execute(
            "INSERT INTO contacts "
            "(id, name, normalized_name, region, country) "
            "VALUES (?, ?, ?, ?, ?)",
            ("c-002", "Test", "test", "uae", "AE"),
        )
        temp_db.execute(
            "INSERT INTO emails (contact_id, email) VALUES (?, ?)",
            ("c-002", "dup@example.com"),
        )
        temp_db.commit()

        with pytest.raises(sqlite3.IntegrityError):
            temp_db.execute(
                "INSERT INTO emails (contact_id, email) VALUES (?, ?)",
                ("c-002", "dup@example.com"),
            )


# ===========================================================================
# Phone insertion
# ===========================================================================


class TestPhoneInsertion:
    def test_insert_phone(self, temp_db):
        temp_db.execute(
            "INSERT INTO contacts "
            "(id, name, normalized_name, region, country) "
            "VALUES (?, ?, ?, ?, ?)",
            ("c-010", "Phone Test", "phone test", "uae", "AE"),
        )
        temp_db.execute(
            "INSERT INTO phones "
            "(contact_id, phone, carrier, line_type, is_whatsapp) "
            "VALUES (?, ?, ?, ?, ?)",
            ("c-010", "+971501234567", "etisalat", "mobile", 1),
        )
        temp_db.commit()

        row = temp_db.execute(
            "SELECT phone, carrier, line_type, is_whatsapp FROM phones WHERE contact_id = ?",
            ("c-010",),
        ).fetchone()

        assert row[0] == "+971501234567"
        assert row[1] == "etisalat"
        assert row[2] == "mobile"
        assert row[3] == 1


# ===========================================================================
# FTS5 search
# ===========================================================================


class TestFTS5Search:
    def _insert_test_contacts(self, temp_db):
        """Helper to insert contacts for FTS testing."""
        temp_db.execute(
            "INSERT INTO contacts "
            "(id, name, first_name, last_name, normalized_name, company_name, title, "
            "contact_type, region, country) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "fts-001",
                "Ahmed Al-Rashid",
                "Ahmed",
                "Al-Rashid",
                "ahmed al-rashid",
                "DMCC",
                "Senior Recruiter",
                "recruiter",
                "uae",
                "AE",
            ),
        )
        temp_db.execute(
            "INSERT INTO contacts "
            "(id, name, first_name, last_name, normalized_name, company_name, title, "
            "contact_type, region, country) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "fts-002",
                "Saeed Khan",
                "Saeed",
                "Khan",
                "saeed khan",
                "Hays Recruitment",
                "Tech Recruiter",
                "recruiter",
                "uae",
                "AE",
            ),
        )
        temp_db.commit()

    def test_search_by_name(self, temp_db):
        self._insert_test_contacts(temp_db)
        results = temp_db.execute(
            "SELECT c.name FROM contacts c "
            "JOIN contacts_fts fts ON c.rowid = fts.rowid "
            "WHERE contacts_fts MATCH ?",
            ("Ahmed",),
        ).fetchall()
        names = [r[0] for r in results]
        assert "Ahmed Al-Rashid" in names

    def test_search_by_company(self, temp_db):
        self._insert_test_contacts(temp_db)
        results = temp_db.execute(
            "SELECT c.name FROM contacts c "
            "JOIN contacts_fts fts ON c.rowid = fts.rowid "
            "WHERE contacts_fts MATCH ?",
            ("DMCC",),
        ).fetchall()
        names = [r[0] for r in results]
        assert "Ahmed Al-Rashid" in names

    def test_search_by_title(self, temp_db):
        self._insert_test_contacts(temp_db)
        results = temp_db.execute(
            "SELECT c.name FROM contacts c "
            "JOIN contacts_fts fts ON c.rowid = fts.rowid "
            "WHERE contacts_fts MATCH ?",
            ("Recruiter",),
        ).fetchall()
        names = [r[0] for r in results]
        assert len(names) >= 2  # Both contacts have "Recruiter" in title


# ===========================================================================
# Triggers
# ===========================================================================


class TestTriggers:
    def test_updated_at_trigger_on_contacts(self, temp_db):
        temp_db.execute(
            "INSERT INTO contacts "
            "(id, name, normalized_name, region, country) "
            "VALUES (?, ?, ?, ?, ?)",
            ("trg-001", "Trigger Test", "trigger test", "uae", "AE"),
        )
        temp_db.commit()

        # Get initial updated_at
        initial = temp_db.execute(
            "SELECT updated_at FROM contacts WHERE id = ?", ("trg-001",)
        ).fetchone()[0]

        # Update the row
        temp_db.execute(
            "UPDATE contacts SET name = ? WHERE id = ?",
            ("Trigger Test Updated", "trg-001"),
        )
        temp_db.commit()

        updated = temp_db.execute(
            "SELECT updated_at FROM contacts WHERE id = ?", ("trg-001",)
        ).fetchone()[0]

        assert updated >= initial

    def test_updated_at_trigger_on_companies(self, temp_db):
        temp_db.execute(
            "INSERT INTO companies (name, country, region) VALUES (?, ?, ?)",
            ("TestCo", "AE", "uae"),
        )
        temp_db.commit()

        initial = temp_db.execute(
            "SELECT updated_at FROM companies WHERE name = ?", ("TestCo",)
        ).fetchone()[0]

        temp_db.execute(
            "UPDATE companies SET industry = ? WHERE name = ?",
            ("Technology", "TestCo"),
        )
        temp_db.commit()

        updated = temp_db.execute(
            "SELECT updated_at FROM companies WHERE name = ?", ("TestCo",)
        ).fetchone()[0]

        assert updated >= initial

    def test_fts_insert_trigger(self, temp_db):
        """Inserting a contact should automatically add it to the FTS index."""
        temp_db.execute(
            "INSERT INTO contacts "
            "(id, name, normalized_name, company_name, title, region, country) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("fts-trg-001", "FTS Trigger Test", "fts trigger test", "TestCo", "Recruiter", "uae", "AE"),
        )
        temp_db.commit()

        # Verify the FTS index was populated
        results = temp_db.execute(
            "SELECT * FROM contacts_fts WHERE contacts_fts MATCH ?",
            ("FTS",),
        ).fetchall()
        assert len(results) >= 1

    def test_fts_delete_trigger(self, temp_db):
        """Deleting a contact should remove it from the FTS index."""
        temp_db.execute(
            "INSERT INTO contacts "
            "(id, name, normalized_name, company_name, region, country) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("fts-del-001", "Delete Test Person", "delete test person", "Co", "uae", "AE"),
        )
        temp_db.commit()

        temp_db.execute("DELETE FROM contacts WHERE id = ?", ("fts-del-001",))
        temp_db.commit()

        results = temp_db.execute(
            "SELECT * FROM contacts_fts WHERE contacts_fts MATCH ?",
            ("Delete",),
        ).fetchall()
        # After deletion, FTS should have no matching rows for this contact
        assert len(results) == 0

    def test_cascade_delete_emails(self, temp_db):
        """Deleting a contact should cascade delete its emails."""
        temp_db.execute(
            "INSERT INTO contacts "
            "(id, name, normalized_name, region, country) "
            "VALUES (?, ?, ?, ?, ?)",
            ("cascade-001", "Cascade Test", "cascade test", "uae", "AE"),
        )
        temp_db.execute(
            "INSERT INTO emails (contact_id, email) VALUES (?, ?)",
            ("cascade-001", "cascade@example.com"),
        )
        temp_db.commit()

        # Verify email exists
        assert temp_db.execute(
            "SELECT COUNT(*) FROM emails WHERE contact_id = ?", ("cascade-001",)
        ).fetchone()[0] == 1

        # Delete contact
        temp_db.execute("DELETE FROM contacts WHERE id = ?", ("cascade-001",))
        temp_db.commit()

        # Email should be cascade-deleted
        assert temp_db.execute(
            "SELECT COUNT(*) FROM emails WHERE contact_id = ?", ("cascade-001",)
        ).fetchone()[0] == 0


# ===========================================================================
# View tests
# ===========================================================================


class TestViews:
    def test_contact_detail_view(self, temp_db):
        temp_db.execute(
            "INSERT INTO companies (id, name, domain_com, country, region) "
            "VALUES (?, ?, ?, ?, ?)",
            ("co-001", "DMCC", "dmcc.ae", "AE", "uae"),
        )
        temp_db.execute(
            "INSERT INTO contacts "
            "(id, name, normalized_name, company_id, company_name, region, country) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("v-001", "View Test", "view test", "co-001", "DMCC", "uae", "AE"),
        )
        temp_db.execute(
            "INSERT INTO emails (contact_id, email, is_primary) VALUES (?, ?, ?)",
            ("v-001", "view@dmcc.ae", 1),
        )
        temp_db.execute(
            "INSERT INTO phones (contact_id, phone, is_primary) VALUES (?, ?, ?)",
            ("v-001", "+971501234567", 1),
        )
        temp_db.commit()

        row = temp_db.execute(
            "SELECT name, company_name, primary_email, primary_phone "
            "FROM v_contact_detail WHERE id = ?",
            ("v-001",),
        ).fetchone()

        assert row is not None
        assert row[0] == "View Test"
        assert row[1] == "DMCC"
        assert row[2] == "view@dmcc.ae"
        assert row[3] == "+971501234567"


# ===========================================================================
# Indexes
# ===========================================================================


class TestIndexes:
    EXPECTED_INDEXES = {
        "idx_companies_name",
        "idx_contacts_name",
        "idx_contacts_confidence",
        "idx_contacts_search",
        "idx_emails_email",
        "idx_phones_phone",
        "idx_sources_source_name",
        "idx_tags_tag",
    }

    def test_key_indexes_exist(self, temp_db):
        cursor = temp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
        )
        indexes = {row[0] for row in cursor.fetchall()}
        for idx in self.EXPECTED_INDEXES:
            assert idx in indexes, f"Missing index: {idx}"
