-- ============================================================================
-- UAE/GCC Recruiter Contact Finder — SQLite Schema
-- Optimised for WAL mode, async access, and GCC-specific queries.
-- ============================================================================

-- ============================================================================
-- PRAGMA CONFIGURATION (run once at connection open)
-- ============================================================================

PRAGMA journal_mode = WAL;           -- Write-Ahead Logging for concurrent reads
PRAGMA synchronous = NORMAL;         -- Balance safety vs performance
PRAGMA cache_size = -64000;          -- 64 MB cache
PRAGMA foreign_keys = ON;            -- Enforce FK constraints
PRAGMA busy_timeout = 5000;          -- Wait up to 5s for locked DB
PRAGMA temp_store = MEMORY;          -- In-memory temp tables
PRAGMA mmap_size = 268435456;        -- 256 MB memory-mapped I/O

-- ============================================================================
-- TABLE: companies
-- ============================================================================

CREATE TABLE IF NOT EXISTS companies (
    id              TEXT        NOT NULL PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    name            TEXT        NOT NULL,
    domain_ae       TEXT,
    domain_com      TEXT,
    industry        TEXT,
    ats_platform    TEXT,                -- e.g. 'taleo', 'sap_successfactors', 'pageup'
    email_format_pattern TEXT,           -- e.g. 'firstname.lastname'
    is_uae_free_zone INTEGER    NOT NULL DEFAULT 0,
    free_zone_name  TEXT,                -- e.g. 'DMCC', 'DIFC', 'JAFZA'
    linkedin_url    TEXT,
    country         TEXT        NOT NULL DEFAULT 'AE',
    region          TEXT        NOT NULL DEFAULT 'uae',
    employee_count_range TEXT,
    created_at      TEXT        NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT        NOT NULL DEFAULT (datetime('now')),

    CHECK (length(name) BETWEEN 1 AND 300),
    CHECK (country = upper(country) AND length(country) = 2),
    CHECK (is_uae_free_zone IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_companies_name       ON companies (name);
CREATE INDEX IF NOT EXISTS idx_companies_domain_ae  ON companies (domain_ae);
CREATE INDEX IF NOT EXISTS idx_companies_domain_com ON companies (domain_com);
CREATE INDEX IF NOT EXISTS idx_companies_region     ON companies (region);
CREATE INDEX IF NOT EXISTS idx_companies_industry   ON companies (industry);

-- Trigger: auto-update updated_at
CREATE TRIGGER IF NOT EXISTS trg_companies_updated_at
    AFTER UPDATE ON companies
    FOR EACH ROW
BEGIN
    UPDATE companies SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- ============================================================================
-- TABLE: contacts (THE CORE RECORD)
-- ============================================================================

CREATE TABLE IF NOT EXISTS contacts (
    id              TEXT        NOT NULL PRIMARY KEY,   -- UUID v4
    name            TEXT        NOT NULL,
    first_name      TEXT        NOT NULL DEFAULT '',
    last_name       TEXT        NOT NULL DEFAULT '',
    middle_name     TEXT,
    normalized_name TEXT        NOT NULL DEFAULT '',    -- lowercase canonical
    company_id      TEXT        REFERENCES companies(id) ON DELETE SET NULL,
    company_name    TEXT,                               -- denormalised for fast reads
    title           TEXT,
    contact_type    TEXT        NOT NULL DEFAULT 'recruiter'
                                CHECK (contact_type IN (
                                    'recruiter', 'hr_manager', 'talent_acquisition',
                                    'headhunter', 'agency'
                                )),
    linkedin_url    TEXT,
    whatsapp_number TEXT,                               -- E.164 if different from primary phone
    region          TEXT        NOT NULL DEFAULT 'uae'
                                CHECK (region IN (
                                    'uae', 'saudi', 'qatar', 'bahrain',
                                    'oman', 'kuwait', 'gcc', 'global'
                                )),
    country         TEXT        NOT NULL DEFAULT 'AE',
    confidence_score REAL       NOT NULL DEFAULT 0.0
                                CHECK (confidence_score BETWEEN 0.0 AND 1.0),
    source_count    INTEGER     NOT NULL DEFAULT 0,
    email_verified  INTEGER     NOT NULL DEFAULT 0,     -- boolean
    phone_verified  INTEGER     NOT NULL DEFAULT 0,     -- boolean
    linkedin_found  INTEGER     NOT NULL DEFAULT 0,     -- boolean
    whatsapp_found  INTEGER     NOT NULL DEFAULT 0,     -- boolean
    is_active       INTEGER     NOT NULL DEFAULT 1,     -- boolean
    notes           TEXT,
    created_at      TEXT        NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT        NOT NULL DEFAULT (datetime('now')),

    CHECK (length(name) BETWEEN 1 AND 300),
    CHECK (country = upper(country) AND length(country) = 2)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_contacts_name            ON contacts (name);
CREATE INDEX IF NOT EXISTS idx_contacts_normalized_name ON contacts (normalized_name);
CREATE INDEX IF NOT EXISTS idx_contacts_company_name    ON contacts (company_name);
CREATE INDEX IF NOT EXISTS idx_contacts_company_id      ON contacts (company_id);
CREATE INDEX IF NOT EXISTS idx_contacts_region          ON contacts (region);
CREATE INDEX IF NOT EXISTS idx_contacts_contact_type    ON contacts (contact_type);
CREATE INDEX IF NOT EXISTS idx_contacts_confidence      ON contacts (confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_contacts_active          ON contacts (is_active, confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_contacts_created         ON contacts (created_at DESC);

-- Composite index for the most common search: active + region + confidence
CREATE INDEX IF NOT EXISTS idx_contacts_search
    ON contacts (is_active, region, confidence_score DESC);

-- Full-text search index for name/company queries
-- NOTE: FTS5 uses the unicode61 tokenizer which doesn't handle Arabic name variants.
-- Arabic normalization (e.g. محمد → mohammed) must happen at the application layer
-- BEFORE inserting into the contacts table. See uae_engine_spec/arabic_name_engine.py
CREATE VIRTUAL TABLE IF NOT EXISTS contacts_fts USING fts5 (
    name,
    company_name,
    title,
    content=contacts,
    content_rowid=rowid
);

-- Trigger: auto-update updated_at
CREATE TRIGGER IF NOT EXISTS trg_contacts_updated_at
    AFTER UPDATE ON contacts
    FOR EACH ROW
BEGIN
    UPDATE contacts SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- Triggers: keep FTS in sync
CREATE TRIGGER IF NOT EXISTS trg_contacts_fts_insert AFTER INSERT ON contacts BEGIN
    INSERT INTO contacts_fts (rowid, name, company_name, title)
    VALUES (NEW.rowid, NEW.name, NEW.company_name, NEW.title);
END;

CREATE TRIGGER IF NOT EXISTS trg_contacts_fts_delete AFTER DELETE ON contacts BEGIN
    INSERT INTO contacts_fts (contacts_fts, rowid, name, company_name, title)
    VALUES ('delete', OLD.rowid, OLD.name, OLD.company_name, OLD.title);
END;

CREATE TRIGGER IF NOT EXISTS trg_contacts_fts_update AFTER UPDATE ON contacts BEGIN
    INSERT INTO contacts_fts (contacts_fts, rowid, name, company_name, title)
    VALUES ('delete', OLD.rowid, OLD.name, OLD.company_name, OLD.title);
    INSERT INTO contacts_fts (rowid, name, company_name, title)
    VALUES (NEW.rowid, NEW.name, NEW.company_name, NEW.title);
END;

-- ============================================================================
-- TABLE: emails
-- ============================================================================

CREATE TABLE IF NOT EXISTS emails (
    id                  TEXT    NOT NULL PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    contact_id          TEXT    NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    email               TEXT    NOT NULL,
    verification_status TEXT    NOT NULL DEFAULT 'unverified'
                                CHECK (verification_status IN (
                                    'unverified', 'syntax_valid', 'dns_valid',
                                    'smtp_valid', 'api_valid', 'bounce', 'invalid'
                                )),
    verification_method TEXT
                                CHECK (verification_method IS NULL OR verification_method IN (
                                    'regex', 'mx_lookup', 'smtp_rcpt', 'api_check',
                                    'breach_db', 'manual', 'web_confirm'
                                )),
    verification_date   TEXT,           -- ISO 8601 datetime
    is_primary          INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
    source_type         TEXT,
    bounce_count        INTEGER NOT NULL DEFAULT 0 CHECK (bounce_count >= 0),
    last_bounce_date    TEXT,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now')),

    CHECK (length(email) BETWEEN 3 AND 254),
    UNIQUE (contact_id, email)
);

CREATE INDEX IF NOT EXISTS idx_emails_contact_id   ON emails (contact_id);
CREATE INDEX IF NOT EXISTS idx_emails_email         ON emails (email);
CREATE INDEX IF NOT EXISTS idx_emails_verification  ON emails (verification_status);
CREATE INDEX IF NOT EXISTS idx_emails_primary       ON emails (contact_id, is_primary);

-- Trigger: auto-update updated_at
CREATE TRIGGER IF NOT EXISTS trg_emails_updated_at
    AFTER UPDATE ON emails
    FOR EACH ROW
BEGIN
    UPDATE emails SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- ============================================================================
-- TABLE: phones
-- ============================================================================

CREATE TABLE IF NOT EXISTS phones (
    id                  TEXT    NOT NULL PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    contact_id          TEXT    NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    phone               TEXT    NOT NULL,                       -- E.164 format
    validation_status   TEXT    NOT NULL DEFAULT 'unverified'
                                CHECK (validation_status IN (
                                    'unverified', 'syntax_valid', 'dns_valid',
                                    'smtp_valid', 'api_valid', 'bounce', 'invalid'
                                )),
    country_code        TEXT    NOT NULL DEFAULT 'AE',
    carrier             TEXT,                                   -- e.g. 'etisalat', 'du', 'virgin_mobile'
    line_type           TEXT    NOT NULL DEFAULT 'unknown'
                                CHECK (line_type IN (
                                    'mobile', 'landline', 'tollfree', 'premium', 'unknown'
                                )),
    is_whatsapp         INTEGER NOT NULL DEFAULT 0 CHECK (is_whatsapp IN (0, 1)),
    whatsapp_business   INTEGER NOT NULL DEFAULT 0 CHECK (whatsapp_business IN (0, 1)),
    is_primary          INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
    source_type         TEXT,
    emirate             TEXT,           -- UAE landline only
    mnp_note            TEXT,           -- Mobile Number Portability caveat
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now')),

    CHECK (phone LIKE '+%'),
    CHECK (length(country_code) = 2),
    UNIQUE (contact_id, phone)
);

CREATE INDEX IF NOT EXISTS idx_phones_contact_id   ON phones (contact_id);
CREATE INDEX IF NOT EXISTS idx_phones_phone         ON phones (phone);
CREATE INDEX IF NOT EXISTS idx_phones_country       ON phones (country_code);
CREATE INDEX IF NOT EXISTS idx_phones_carrier       ON phones (carrier);
CREATE INDEX IF NOT EXISTS idx_phones_whatsapp      ON phones (is_whatsapp);
CREATE INDEX IF NOT EXISTS idx_phones_primary       ON phones (contact_id, is_primary);
CREATE INDEX IF NOT EXISTS idx_phones_line_type     ON phones (line_type);

-- Trigger: auto-update updated_at
CREATE TRIGGER IF NOT EXISTS trg_phones_updated_at
    AFTER UPDATE ON phones
    FOR EACH ROW
BEGIN
    UPDATE phones SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- ============================================================================
-- TABLE: sources (raw extraction results per contact)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sources (
    id                      TEXT    NOT NULL PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    contact_id              TEXT    NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    source_name             TEXT    NOT NULL,                       -- e.g. 'linkedin', 'google_maps'
    source_type             TEXT    NOT NULL
                                    CHECK (source_type IN (
                                        'api', 'scrape', 'permutation', 'directory',
                                        'classified', 'social', 'event'
                                    )),
    raw_data                TEXT,                                   -- JSON blob
    extracted_name          TEXT,
    extracted_email         TEXT,
    extracted_phone         TEXT,
    extracted_company       TEXT,
    extracted_title         TEXT,
    extracted_linkedin      TEXT,
    source_url              TEXT,
    confidence_contribution REAL    NOT NULL DEFAULT 0.3
                                    CHECK (confidence_contribution BETWEEN 0.0 AND 1.0),
    extracted_at            TEXT    NOT NULL DEFAULT (datetime('now')),
    request_id              TEXT,                                   -- API trace ID

    CHECK (length(source_name) BETWEEN 1 AND 100)
);

CREATE INDEX IF NOT EXISTS idx_sources_contact_id    ON sources (contact_id);
CREATE INDEX IF NOT EXISTS idx_sources_source_name   ON sources (source_name);
CREATE INDEX IF NOT EXISTS idx_sources_source_type   ON sources (source_type);
CREATE INDEX IF NOT EXISTS idx_sources_extracted_at  ON sources (extracted_at DESC);

-- ============================================================================
-- TABLE: arabic_name_cache
-- ============================================================================

CREATE TABLE IF NOT EXISTS arabic_name_cache (
    id                  TEXT    NOT NULL PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    original_name       TEXT    NOT NULL,
    normalized_form     TEXT    NOT NULL,
    al_el_bin_removed   TEXT    NOT NULL DEFAULT '',
    first_name          TEXT    NOT NULL DEFAULT '',
    last_name           TEXT    NOT NULL DEFAULT '',
    middle_name         TEXT,
    variants_json       TEXT    NOT NULL DEFAULT '[]',        -- JSON array of strings
    mohammed_variants_json TEXT  NOT NULL DEFAULT '[]',       -- JSON array of strings
    email_permutations_json TEXT NOT NULL DEFAULT '[]',       -- JSON array of strings
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),

    CHECK (length(original_name) BETWEEN 1 AND 300),
    UNIQUE (original_name)
);

CREATE INDEX IF NOT EXISTS idx_arabic_name_original   ON arabic_name_cache (original_name);
CREATE INDEX IF NOT EXISTS idx_arabic_name_normalized ON arabic_name_cache (normalized_form);
CREATE INDEX IF NOT EXISTS idx_arabic_name_first_last ON arabic_name_cache (first_name, last_name);

-- ============================================================================
-- TABLE: sessions
-- ============================================================================

CREATE TABLE IF NOT EXISTS sessions (
    session_id          TEXT    NOT NULL PRIMARY KEY,
    queries_json        TEXT    NOT NULL DEFAULT '[]',        -- JSON array of ContactQuery
    results_count       INTEGER NOT NULL DEFAULT 0 CHECK (results_count >= 0),
    api_usage_json      TEXT    NOT NULL DEFAULT '{}',        -- JSON: {source: credits}
    errors_json         TEXT    NOT NULL DEFAULT '[]',        -- JSON array of error strings
    started_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    completed_at        TEXT,
    status              TEXT    NOT NULL DEFAULT 'running'
                                CHECK (status IN (
                                    'running', 'completed', 'failed', 'cancelled'
                                )),
    total_duration_seconds REAL  CHECK (total_duration_seconds IS NULL OR total_duration_seconds >= 0)
);

CREATE INDEX IF NOT EXISTS idx_sessions_status     ON sessions (status);
CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions (started_at DESC);

-- ============================================================================
-- TABLE: search_results (junction: session → contacts with ranking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS search_results (
    id          TEXT    NOT NULL PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    session_id  TEXT    NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    contact_id  TEXT    NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    rank        INTEGER NOT NULL DEFAULT 0,                     -- result rank in this session
    relevance   REAL    NOT NULL DEFAULT 0.0,                   -- relevance score for this query

    UNIQUE (session_id, contact_id)
);

CREATE INDEX IF NOT EXISTS idx_search_results_session ON search_results (session_id);
CREATE INDEX IF NOT EXISTS idx_search_results_contact ON search_results (contact_id);

-- ============================================================================
-- TABLE: api_usage
-- ============================================================================

CREATE TABLE IF NOT EXISTS api_usage (
    id                  TEXT    NOT NULL PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    source_name         TEXT    NOT NULL,
    source_type         TEXT    NOT NULL DEFAULT 'api',
    credits_used        INTEGER NOT NULL DEFAULT 0 CHECK (credits_used >= 0),
    credits_limit       INTEGER CHECK (credits_limit IS NULL OR credits_limit >= 0),
    credits_remaining   INTEGER CHECK (credits_remaining IS NULL OR credits_remaining >= 0),
    reset_date          TEXT,                                   -- ISO 8601 date
    last_used           TEXT,                                   -- ISO 8601 datetime
    api_key_env_var     TEXT,                                   -- env var name (not the key itself!)
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now')),

    CHECK (length(source_name) BETWEEN 1 AND 100),
    UNIQUE (source_name)
);

CREATE INDEX IF NOT EXISTS idx_api_usage_source ON api_usage (source_name);

-- Trigger: auto-update updated_at
CREATE TRIGGER IF NOT EXISTS trg_api_usage_updated_at
    AFTER UPDATE ON api_usage
    FOR EACH ROW
BEGIN
    UPDATE api_usage SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- ============================================================================
-- TABLE: tags (for contact tagging)
-- ============================================================================

CREATE TABLE IF NOT EXISTS tags (
    id          TEXT    NOT NULL PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    contact_id  TEXT    NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    tag         TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),

    CHECK (length(tag) BETWEEN 1 AND 50),
    UNIQUE (contact_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_tags_contact ON tags (contact_id);
CREATE INDEX IF NOT EXISTS idx_tags_tag     ON tags (tag);

-- ============================================================================
-- TABLE: exports
-- ============================================================================

CREATE TABLE IF NOT EXISTS exports (
    id                      TEXT    NOT NULL PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    format                  TEXT    NOT NULL CHECK (format IN (
                                        'csv', 'json', 'excel', 'vcard', 'markdown'
                                    )),
    filename                TEXT    NOT NULL,
    row_count               INTEGER NOT NULL DEFAULT 0 CHECK (row_count >= 0),
    filters_applied_json    TEXT    NOT NULL DEFAULT '{}',
    deduped_count           INTEGER NOT NULL DEFAULT 0 CHECK (deduped_count >= 0),
    confidence_threshold    REAL    NOT NULL DEFAULT 0.0
                                    CHECK (confidence_threshold BETWEEN 0.0 AND 1.0),
    export_date             TEXT    NOT NULL DEFAULT (datetime('now')),
    file_size_bytes         INTEGER CHECK (file_size_bytes IS NULL OR file_size_bytes >= 0),
    session_id              TEXT    REFERENCES sessions(session_id) ON DELETE SET NULL,

    CHECK (length(filename) BETWEEN 1 AND 500)
);

CREATE INDEX IF NOT EXISTS idx_exports_date     ON exports (export_date DESC);
CREATE INDEX IF NOT EXISTS idx_exports_format   ON exports (format);
CREATE INDEX IF NOT EXISTS idx_exports_session  ON exports (session_id);

-- ============================================================================
-- TABLE: known_email_patterns (per-domain email format cache)
-- ============================================================================

CREATE TABLE IF NOT EXISTS known_email_patterns (
    id          TEXT    NOT NULL PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    domain      TEXT    NOT NULL,
    pattern     TEXT    NOT NULL,           -- e.g. 'firstname.lastname'
    sample_emails_json TEXT NOT NULL DEFAULT '[]',
    confidence  REAL    NOT NULL DEFAULT 0.5 CHECK (confidence BETWEEN 0.0 AND 1.0),
    source      TEXT,                       -- where this pattern was observed
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),

    UNIQUE (domain, pattern)
);

CREATE INDEX IF NOT EXISTS idx_email_patterns_domain ON known_email_patterns (domain);

-- Trigger: auto-update updated_at
CREATE TRIGGER IF NOT EXISTS trg_email_patterns_updated_at
    AFTER UPDATE ON known_email_patterns
    FOR EACH ROW
BEGIN
    UPDATE known_email_patterns SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- ============================================================================
-- VIEW: contact_detail (denormalised view for fast reads)
-- ============================================================================

CREATE VIEW IF NOT EXISTS v_contact_detail AS
SELECT
    c.id,
    c.name,
    c.first_name,
    c.last_name,
    c.normalized_name,
    c.company_name,
    c.title,
    c.contact_type,
    c.linkedin_url,
    c.whatsapp_number,
    c.region,
    c.country,
    c.confidence_score,
    c.source_count,
    c.email_verified,
    c.phone_verified,
    c.linkedin_found,
    c.whatsapp_found,
    c.is_active,
    c.created_at,
    c.updated_at,
    -- Primary email
    (SELECT e.email FROM emails e WHERE e.contact_id = c.id AND e.is_primary = 1 LIMIT 1)
        AS primary_email,
    -- Email count
    (SELECT COUNT(*) FROM emails e WHERE e.contact_id = c.id)
        AS email_count,
    -- Primary phone
    (SELECT p.phone FROM phones p WHERE p.contact_id = c.id AND p.is_primary = 1 LIMIT 1)
        AS primary_phone,
    -- Phone count
    (SELECT COUNT(*) FROM phones p WHERE p.contact_id = c.id)
        AS phone_count,
    -- Has WhatsApp
    (SELECT COUNT(*) FROM phones p WHERE p.contact_id = c.id AND p.is_whatsapp = 1)
        AS whatsapp_count,
    -- Company domain
    co.domain_com,
    co.domain_ae,
    co.email_format_pattern,
    co.ats_platform,
    co.is_uae_free_zone,
    co.free_zone_name
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.id;

-- ============================================================================
-- VIEW: api_usage_summary
-- ============================================================================

CREATE VIEW IF NOT EXISTS v_api_usage_summary AS
SELECT
    source_name,
    source_type,
    credits_used,
    credits_limit,
    credits_remaining,
    CASE
        WHEN credits_limit IS NOT NULL AND credits_limit > 0
        THEN round(CAST(credits_used AS REAL) / credits_limit * 100, 1)
        ELSE NULL
    END AS usage_percentage,
    reset_date,
    last_used
FROM api_usage
ORDER BY source_name;
