# RCF — Recruiter Contact Finder

**UAE/GCC-optimized CLI tool for discovering recruiter contact information from 30+ data sources.**

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Status: Active](https://img.shields.io/badge/status-active-brightgreen.svg)

---

## What is RCF?

RCF (Recruiter Contact Finder) is a local command-line tool that discovers recruiter contact information — emails, phone numbers, LinkedIn profiles — from **30+ data sources** simultaneously. Built with a plugin architecture and async pipeline, it's specifically optimized for the **UAE and GCC recruitment market**, with native Arabic name handling, UAE carrier detection, and WhatsApp verification.

Whether you're sourcing recruiters at a specific company, mapping an entire industry's talent acquisition team, or building a recruiter database for outreach, RCF automates the discovery, verification, and scoring workflow end-to-end.

---

## Features

### 🔌 30+ Data Sources
| Category | Count | Examples |
|----------|-------|---------|
| **Email Discovery APIs** | 11 | Hunter, Apollo, Snov.io, Seamless.ai, RocketReach |
| **Web Scraping** | 9 | LinkedIn, Google Dorking, Bayt, GulfTalent, Dubizzle |
| **Executive Search** | 5 | Spencer Stuart, Korn Ferry, Heidrick & Struggles, Egon Zehnder, Russell Reynolds |
| **Local / UAE-Specific** | 5 | DMCC Directory, UAE Yellow Pages, Expatriates, WhatsApp Checker, UAE Phone Detector |

### ⚙️ 6-Phase Pipeline
```
Discovery → Deduplication → Enrichment → Verification → Scoring → Export
```
Each phase runs automatically, with configurable thresholds and early-exit logic to minimize API usage.

### ✉️ 3-Tier Email Verification
| Tier | Method | Description |
|------|--------|-------------|
| 1 — Syntax | Regex | RFC 5322 compliance check |
| 2 — DNS | MX Lookup | Verifies domain accepts mail |
| 3 — SMTP | RCPT TO | Confirms mailbox exists |
| 4 — API | ZeroBounce / HIBP | Third-party validation + breach DB |

**M365 Bypass**: Automatically skips SMTP verification for Microsoft 365 domains (which accept all RCPT TO commands, causing false positives).

### 🇦🇪 UAE/GCC Optimization
- **Arabic name normalization** — Handles Al/Bin/Mohammed variants, transliteration differences
- **UAE carrier detection** — Identifies Etisalat, du, Virgin Mobile from phone prefix
- **Emirate inference** — Maps phone area codes and addresses to specific emirates
- **WhatsApp verification** — Pings numbers to confirm WhatsApp presence + Business accounts
- **Dual TLD check** — Tries both `.ae` and `.com` for company domain resolution
- **ATS detection** — Identifies Taleo, SAP SuccessFactors, PageUp career pages

### 📊 Multi-Factor Confidence Scoring
| Factor | Weight | Description |
|--------|--------|-------------|
| Source diversity | up to 0.40 | Multiple independent sources corroborating |
| Email verification | up to 0.25 | Verified email (syntax → DNS → SMTP → API) |
| Phone verification | up to 0.20 | Validated + carrier-detected phone number |
| Profile richness | up to 0.10 | LinkedIn, title, company, industry present |
| Freshness penalty | up to -0.15 | Decay for stale data |
| UAE regional bonus | +0.05 | Bonus for UAE-sourced data |

**Confidence Tiers**:
| Tier | Score Range | Meaning |
|------|-------------|---------|
| 🟢 High | 0.80 – 1.00 | Verified across multiple sources |
| 🟡 Medium | 0.50 – 0.79 | Partially verified, good confidence |
| 🟠 Low | 0.01 – 0.49 | Found but unverified |
| 🔴 Unverified | 0.00 | No verification signals |

### 📤 4 Export Formats
- **CSV** — Standard comma-separated with fixed column order
- **JSON** — Nested structure matching Pydantic models
- **XLSX** — Styled spreadsheet with conditional coloring, autofilter, frozen headers
- **HTML** — Responsive table with confidence color-coding

---

## Quick Start

```bash
# Install
pip install -e .

# First-time setup (creates config.yml + .env)
rcf setup

# Search for recruiters
rcf search "Google Dubai" --region uae

# Export high-confidence results
rcf search "recruitment agency" --region gcc --format xlsx --threshold 0.7
```

---

## Installation

### Prerequisites
- **Python 3.11+**
- **pip** (Python package manager)
- **Playwright** (optional — needed for LinkedIn and browser-based sources)

### Install

```bash
# Clone the repository
git clone https://github.com/your-org/rcf.git
cd rcf

# Install in development mode
pip install -e .

# (Optional) Install Playwright for browser-based sources
pip install playwright
playwright install chromium
```

### API Keys

RCF uses API keys stored in a `.env` file (or environment variables). Run the setup wizard to configure them:

```bash
rcf setup
```

Or manually create a `.env` file:

```env
# Email Discovery
HUNTER_API_KEY=your_key_here
APOLLO_API_KEY=your_key_here
SNOV_API_KEY=your_key_here
SEAMLESS_AI_KEY=your_key_here
ROCKETREACH_API_KEY=your_key_here

# Email Verification
ZEROBOUNCE_API_KEY=your_key_here

# Phone & Location
GOOGLE_PLACES_API_KEY=your_key_here

# People Data
PDL_API_KEY=your_key_here
```

> **Note**: Most sources offer free tiers (see [Sources Table](#30-sources-table) below). You only need keys for the sources you want to use.

---

## Configuration

RCF uses `config.yml` for all settings, with `.env` for secrets. Run `rcf config init` to generate defaults.

### Key Configuration Sections

```yaml
# General settings
general:
  default_region: "uae"
  max_concurrent_requests: 5
  request_delay_seconds: 2.0
  cache_ttl_hours: 168          # 1 week
  database_path: "rcf_data.db"

# UAE/GCC-specific settings
uae:
  check_whatsapp: true
  dual_tld_check: true
  arabic_name_variants: true
  detect_ats: true
  carrier_detection: true
  preferred_contact_method: "whatsapp"

# Email verification pipeline
verification:
  email:
    tiers: [syntax, dns, smtp, api]
    skip_smtp_for_m365: true
  phone:
    libphonenumber: true
    whatsapp_check: true
    carrier_detection: true

# Confidence scoring
scoring:
  minimum_confidence: 0.5
  prefer_phone_over_email: false
  uae_regional_bonus: 0.05
```

### Viewing & Editing Configuration

```bash
# Show full configuration
rcf config show

# Show a specific key
rcf config show general.default_region

# Validate config and check API keys
rcf config validate
```

---

## CLI Reference

### `rcf search` — Search for recruiter contacts

The primary command. Searches across all configured sources, deduplicates, verifies, scores, and exports results.

```bash
# Basic search
rcf search "Google Dubai" --region uae

# Search with specific format and confidence threshold
rcf search "recruitment agency" --region gcc --format xlsx --threshold 0.7

# Batch search from a file
rcf search --companies-file companies.txt --industry technology

# Search with title filter
rcf search "technical recruiter" --title-filter "senior" --dry-run

# Full options
rcf search QUERY [OPTIONS]
  --region, -r          Target region (uae, saudi, qatar, bahrain, oman, kuwait, gcc, global)
  --sources, -s         Specific source names to use (repeatable)
  --max-results, -m     Maximum contacts to return (1–10000, default: 50)
  --threshold, -t       Minimum confidence score (0.0–1.0, default: 0.5)
  --output, -o          Output file path (auto-generated if omitted)
  --format, -f          Output format: csv, json, xlsx, html
  --no-enrich           Skip enrichment waterfall
  --no-verify-emails    Skip email verification
  --no-verify-phones    Skip phone verification
  --no-check-whatsapp   Skip WhatsApp presence check
  --dry-run             Show what would be searched without executing
  --no-cache            Ignore cached results
  --industry, -i        Filter by industry
  --title-filter        Filter by recruiter title
  --companies-file      Read company names from file (one per line)
```

### `rcf enrich` — Enrich existing contacts

Re-runs the enrichment waterfall for contacts already in the database.

```bash
# Enrich a specific contact
rcf enrich abc123

# Enrich all contacts
rcf enrich --all

# Enrich with specific sources
rcf enrich --all --sources hunter apollo --verify-emails
```

### `rcf export` — Export stored contacts

Export contacts from the local database with filtering and deduplication.

```bash
# Export all as XLSX
rcf export --format xlsx --output recruiters.xlsx

# Export high-confidence UAE contacts as JSON
rcf export --format json --threshold 0.8 --region uae

# Export recent contacts as HTML
rcf export --format html --since 2026-01-01 --dedup
```

### `rcf status` — Show system status

Displays total contacts, last search date, database size, and per-source API credit usage.

```bash
rcf status
rcf status --source hunter --verbose
```

### `rcf sources` — List all data sources

Shows all 30+ sources with configuration status, type, free tier info, and region support.

```bash
rcf sources
rcf sources --type api
rcf sources --region uae
```

### `rcf config` — Manage configuration

| Command | Description |
|---------|-------------|
| `rcf config show [KEY]` | Display full or specific config value |
| `rcf config set KEY VALUE` | Set a configuration value |
| `rcf config init [--force]` | Create config.yml and .env from templates |
| `rcf config validate` | Validate config and check all API keys |

### `rcf setup` — First-time setup wizard

Interactive wizard that checks dependencies, creates config files, prompts for API keys, and validates the setup.

```bash
rcf setup
```

### `rcf db` — Database management

| Command | Description |
|---------|-------------|
| `rcf db stats` | Show row counts and database size |
| `rcf db clean --older-than 30` | Remove old contacts and expired cache |
| `rcf db backup -o backup.db` | Create a consistent SQLite backup |
| `rcf db reset --yes` | ⚠️ Delete all data and recreate tables |

---

## Architecture

### Plugin System

RCF uses a plugin architecture where every data source implements the `SourcePlugin` abstract base class:

```
SourcePlugin (ABC)
├── discover(query) → list[SourceResult]    # Find raw contacts
├── enrich(contact) → RecruiterContact      # Fill missing data
├── validate_config() → bool                # Check API keys
└── get_rate_limit_info() → RateLimitInfo   # Report usage
```

Each plugin declares a `PluginSpec` with metadata:
- **Source type** (API, scrape, directory, social, browser, OSINT, email)
- **Regions** (UAE, Saudi, Qatar, GCC, global)
- **Priority** (1–10, used for waterfall ordering)
- **Rate limits** (requests per minute, monthly credits)
- **Extraction method** (REST API, GraphQL, HTML scrape, browser automation, local computation)

### Pipeline Orchestrator

The orchestrator runs the 6-phase pipeline:

```
ContactQuery
  → Filter plugins by region & type
  → Discovery waterfall (priority order, early exit at confidence threshold)
  → Deduplication (6 strategies: exact email, exact phone, fuzzy name, Arabic name, LinkedIn URL, WhatsApp cross-ref)
  → Enrichment (parallel across contacts, highest-priority source wins)
  → Verification (email: syntax → DNS → SMTP → API; phone: libphonenumber → WhatsApp)
  → Confidence scoring (multi-factor formula)
  → Export (CSV / JSON / XLSX / HTML)
```

### Async & Rate Limiting

- **Global semaphore** limits total concurrent HTTP requests
- **Per-plugin semaphore** limits calls to each source
- **Rate limiter** enforces per-minute quotas per source type
- **Tenacity retry** with exponential backoff for transient failures
- **Automatic caching** with configurable TTL

### Deduplication Strategies

Results from multiple sources are merged using 6 strategies:
1. **Exact email match**
2. **Exact phone match** (E.164 normalized)
3. **Fuzzy name match** (rapidfuzz ≥ 85 + same company)
4. **Arabic name fuzzy match** (normalized transliteration forms)
5. **LinkedIn URL match** (normalized)
6. **WhatsApp cross-reference** (same number → same person)

---

## 30 Sources Table

| # | Source | Type | Free Tier | Regions |
|---|--------|------|-----------|---------|
| 1 | **Hunter** | API | 25 searches/mo | Global |
| 2 | **Apollo** | API | 50 credits/mo | Global |
| 3 | **Snov.io** | API | 50 credits/mo | Global |
| 4 | **Seamless.ai** | API | 50 credits/mo | Global |
| 5 | **RocketReach** | API | 5 lookups/mo | Global |
| 6 | **People Data Labs** | API | 100 records/mo | Global |
| 7 | **Google Places** | API | $200 credit/mo | GCC |
| 8 | **Abstract API** | API | 100 requests/mo | Global |
| 9 | **ZeroBounce** | API | 100 emails/mo | Global |
| 10 | **Email Permutator** | Local | Unlimited | Global |
| 11 | **WhatsApp Checker** | API | Rate-limited | GCC |
| 12 | **LinkedIn** | Scrape | Requires browser | Global |
| 13 | **Google Dorking** | Scrape | Unlimited | GCC |
| 14 | **Bayt** | Scrape | Free | UAE, Saudi, GCC |
| 15 | **NaukriGulf** | Scrape | Free | UAE, Saudi, GCC |
| 16 | **GulfTalent** | Scrape | Free | UAE, Qatar, GCC |
| 17 | **Expatriates** | Scrape | Free | UAE |
| 18 | **Dubizzle** | Scrape | Free | UAE |
| 19 | **Facebook Groups** | Scrape | Requires browser | UAE |
| 20 | **DMCC Directory** | Directory | Free | UAE |
| 21 | **UAE Yellow Pages** | Directory | Free | UAE |
| 22 | **Greenhouse** | Directory | Free | Global |
| 23 | **Lever** | Directory | Free | Global |
| 24 | **Spencer Stuart** | Exec Search | Free | Global |
| 25 | **Korn Ferry** | Exec Search | Free | Global |
| 26 | **Heidrick & Struggles** | Exec Search | Free | Global |
| 27 | **Egon Zehnder** | Exec Search | Free | Global |
| 28 | **Russell Reynolds** | Exec Search | Free | Global |
| 29 | **Arabic Name Normalizer** | Local | Unlimited | GCC |
| 30 | **UAE Phone Detector** | Local | Unlimited | UAE |

---

## Development

### Project Structure

```
rcf/
├── cli.py                  # Typer CLI with all commands
├── config.py               # Pydantic config models + YAML loader
├── export.py               # Multi-format export engine
├── logging.py              # Structured logging setup
├── core/
│   ├── base_plugin.py      # SourcePlugin ABC + PluginSpec
│   ├── orchestrator.py     # 6-phase async pipeline
│   ├── deduplicator.py     # 6-strategy dedup engine
│   ├── scorer.py           # Multi-factor confidence scoring
│   ├── plugin_registry.py  # Auto-discovery & registration
│   └── api_tracker.py      # Per-source credit tracking
├── plugins/                # 30 data source implementations
│   ├── hunter.py
│   ├── apollo.py
│   ├── linkedin.py
│   └── ...
├── storage/                # SQLite persistence layer
├── utils/
│   └── rate_limiter.py     # Token-bucket rate limiter
└── verification/           # Email + phone verification
models/
├── models.py               # Pydantic V2 data models
├── enums.py                # All enumerations
└── validators.py           # Field validation helpers
spec/
├── SPECIFICATION.md        # Detailed technical spec
├── scorer.py               # Scoring formula implementation
├── deduplicator.py         # Dedup algorithm implementation
├── email_verifier.py       # Verification tier logic
└── phone_validator.py      # Phone validation logic
db/
├── schema.sql              # SQLite schema
└── validate_schema.py      # Schema validation
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run MCP server tests
cd mcp-server && node test/run-tests.mjs
```

### Adding a New Plugin

1. Create a new file in `rcf/plugins/` (e.g., `my_source.py`)
2. Extend `SourcePlugin` and define a `PluginSpec`:

```python
from rcf.core.base_plugin import SourcePlugin, PluginSpec
from models.enums import Region, SourceType

class MySourcePlugin(SourcePlugin):
    SPEC = PluginSpec(
        name="my_source",
        source_type=SourceType.API,
        regions=[Region.UAE, Region.GCC],
        data_types=["email", "phone"],
        priority=3,
        requires_browser=False,
        api_key_env="MY_SOURCE_API_KEY",
        rate_limit_rpm=10,
        rate_limit_monthly=1000,
        url_pattern="https://api.mysource.com/v1/",
        extraction_method="rest_api",
    )

    async def discover(self, query):
        # Implement discovery logic
        ...

    async def enrich(self, contact):
        # Implement enrichment logic
        ...

    async def validate_config(self):
        # Check API key / connectivity
        ...

    async def get_rate_limit_info(self):
        # Return current rate limit status
        ...
```

3. Register in `rcf/plugins/__init__.py`
4. Add configuration defaults in `rcf/config.py`
5. Add the API key to `.env` and `config.yml`

---

## Regions

RCF supports the following regions:

| Region | Code | Countries |
|--------|------|-----------|
| 🇦🇪 UAE | `uae` | United Arab Emirates |
| 🇸🇦 Saudi Arabia | `saudi` | Kingdom of Saudi Arabia |
| 🇶🇦 Qatar | `qatar` | State of Qatar |
| 🇧🇭 Bahrain | `bahrain` | Kingdom of Bahrain |
| 🇴🇲 Oman | `oman` | Sultanate of Oman |
| 🇰🇼 Kuwait | `kuwait` | State of Kuwait |
| 🌐 GCC | `gcc` | All GCC countries |
| 🌍 Global | `global` | Worldwide |

---

## License

This project is licensed under the **MIT License**.

---

<p align="center">
  Built for the UAE/GCC recruitment market 🇦🇪
</p>
