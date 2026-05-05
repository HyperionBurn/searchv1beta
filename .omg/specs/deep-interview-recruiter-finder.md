# Spec: Recruiter Contact Finder (RCF) — UAE/GCC-Optimized
## Production-Grade Implementation Specification

**Crystallized from Deep Interview** | Ambiguity: 18% | Rounds: 10
**Research-Validated by 25+ Agent Runs Across 4 Research Waves** | May 4, 2026
**Spec Refined by 5-Agent Architecture Team** | May 4, 2026

---

## 1. GOAL

Build **RCF** (Recruiter Contact Finder) — a **local Python CLI tool** that discovers recruiter contact information (emails + phone numbers + WhatsApp) from 30+ sources, with **deep UAE/GCC optimization**. Aggregates, deduplicates, verifies, scores, and exports results. **Personal use only**, optimized for a user based in the UAE.

---

## 2. ARCHITECTURE

### 2.1 Pattern
Plugin-based async pipeline with waterfall enrichment (early exit at confidence threshold).

### 2.2 Pipeline Flow
```
ContactQuery
  → Plugin Registry (filter by region, source_type, config validity)
  → Phase 1: DISCOVERY (waterfall by priority, early exit at 0.80)
      → API Plugins (Google Places, Hunter, Apollo, ...)
      → Scraping Plugins (DMCC, Expatriates, Dubizzle, LinkedIn, ...)
      → Exec Search Plugins (Heidrick, Korn Ferry, ...)
      → Local Plugins (Email Permutator, Google Dork, Arabic Name, ...)
  → Phase 2: DEDUPLICATION (6-strategy merge)
  → Phase 3: ENRICHMENT (parallel, per-contact)
  → Phase 4: VERIFICATION (email 3-tier + phone multi-step + WhatsApp)
  → Phase 5: SCORING (multi-factor confidence)
  → Phase 6: FILTER & SORT (threshold ≥ min_confidence, top N)
  → EXPORT (CSV/JSON/XLSX/HTML)
```

### 2.3 Directory Structure
```
rcf/
├── __init__.py                      # Package root, version
├── cli.py                           # Typer CLI (8 commands)
├── config.py                        # Pydantic config models + YAML loader
│
├── models/
│   ├── __init__.py                  # Re-exports all public symbols
│   ├── enums.py                     # 15 enum definitions
│   ├── validators.py                # UAE/GCC phone, Arabic name, email validators
│   └── models.py                    # 11 Pydantic V2 models
│
├── core/
│   ├── __init__.py
│   ├── base_plugin.py               # SourcePlugin ABC + ALL_PLUGINS registry
│   ├── plugin_registry.py           # Registration, filtering, auto-discovery
│   ├── orchestrator.py              # 6-phase pipeline with waterfall
│   ├── deduplicator.py              # 6-strategy merge (Union-Find)
│   ├── scorer.py                    # Multi-factor confidence scoring
│   └── api_tracker.py               # Free-tier credit tracking
│
├── plugins/
│   ├── __init__.py
│   ├── hunter.py                    # Hunter.io API (50/mo free)
│   ├── apollo.py                    # Apollo.io API (60/mo free)
│   ├── seamless_ai.py              # Seamless.ai (50 lifetime)
│   ├── snov.py                      # Snov.io (50/mo free)
│   ├── rocketreach.py              # RocketReach (5/mo free)
│   ├── zerobounce.py               # ZeroBounce (100/mo free)
│   ├── abstract_api.py             # AbstractAPI (100/mo free)
│   ├── people_data_labs.py         # PDL (100/mo free)
│   ├── google_places.py            # Google Places ($200/mo free credit)
│   ├── greenhouse.py               # Greenhouse JSON API (unlimited)
│   ├── lever.py                    # Lever JSON API (unlimited)
│   ├── linkedin.py                 # LinkedIn via Camoufox+Botasaurus
│   ├── dmcc_directory.py           # DMCC business directory scraper
│   ├── expatriates.py             # Expatriates.com phone scraper
│   ├── dubizzle.py                # Dubizzle phone scraper
│   ├── yellowpages_uae.py         # UAE Yellow Pages scraper
│   ├── bayt.py                    # Bayt.com job board scraper
│   ├── gulf_talent.py             # GulfTalent scraper
│   ├── naukrigulf.py              # Naukrigulf scraper
│   ├── facebook_groups.py         # Facebook Groups (browser)
│   ├── heidrick.py                # Heidrick & Struggles directory
│   ├── korn_ferry.py              # Korn Ferry consultant directory
│   ├── spencer_stuart.py          # Spencer Stuart directory
│   ├── egon_zehnder.py            # Egon Zehnder directory
│   ├── russell_reynolds.py        # Russell Reynolds directory
│   ├── email_permutator.py        # 20+ email pattern generator
│   ├── google_dorking.py          # UAE-specific search queries
│   ├── whatsapp_checker.py        # WhatsApp presence + Business profile
│   ├── uae_phone_detector.py      # UAE carrier/emirate detection
│   └── arabic_name_normalizer.py  # Arabic name → email permutations
│
├── verification/
│   ├── __init__.py
│   ├── email_verifier.py           # 3-tier email pipeline + M365 bypass
│   └── phone_validator.py          # E.164 + UAE carrier + WhatsApp
│
├── uae/
│   ├── __init__.py
│   ├── arabic_name_engine.py       # 8 Mohammed variants, Al/El/Bin, transliteration
│   ├── uae_phone_engine.py         # +971 carrier/emirate, all 6 GCC countries
│   ├── uae_domain_engine.py        # Dual .ae/.com TLD, 15+ employer patterns
│   ├── whatsapp_engine.py          # wa.me checking, Business profile extraction
│   ├── uae_google_dork.py          # 30+ UAE-specific query templates
│   ├── uae_ats.py                  # 10 ATS detection patterns, UAE company→ATS map
│   └── uae_compliance.py           # robots.txt, rate limits, legal disclaimers
│
├── export/
│   ├── __init__.py
│   └── exporter.py                 # CSV/JSON/XLSX/HTML with confidence coloring
│
├── storage/
│   ├── __init__.py
│   └── database.py                 # SQLite WAL, FTS5, 11 tables, 44 indexes
│
├── utils/
│   ├── __init__.py
│   ├── rate_limiter.py             # Per-host async rate control
│   └── logging.py                  # structlog JSON + colored console
│
├── db/
│   └── schema.sql                  # Complete DDL
│
├── config.yml                      # Full config with every key
├── .env.example                    # API key template with signup URLs
└── requirements.txt                # 40+ dependencies
```

---

## 3. DATA MODELS

### 3.1 Enums (models/enums.py)

```python
class Region(str, Enum):
    UAE = "uae"
    SAUDI = "saudi"
    QATAR = "qatar"
    BAHRAIN = "bahrain"
    OMAN = "oman"
    KUWAIT = "kuwait"
    GCC = "gcc"          # all 6 above
    GLOBAL = "global"

class SourceType(str, Enum):
    API = "api"
    SCRAPE = "scrape"
    DIRECTORY = "directory"
    SOCIAL = "social"
    PERMUTATION = "permutation"
    LOCAL = "local"

class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    SYNTAX_VALID = "syntax_valid"
    DNS_VALID = "dns_valid"
    SMTP_VALID = "smtp_valid"
    API_VALID = "api_valid"
    INVALID = "invalid"
    SKIPPED_M365 = "skipped_m365"  # UAE: M365 SMTP unreliable

class PhoneType(str, Enum):
    MOBILE = "mobile"
    LANDLINE = "landline"
    TOLLFREE = "tollfree"
    PREMIUM = "premium"
    VOIP = "voip"
    UNKNOWN = "unknown"

class UAECarrier(str, Enum):
    ETISALAT = "etisalat"
    DU = "du"
    VIRGIN_MOBILE = "virgin_mobile"
    UNKNOWN = "unknown"

class ContactType(str, Enum):
    RECRUITER = "recruiter"
    HR_MANAGER = "hr_manager"
    TALENT_ACQUISITION = "talent_acquisition"
    HEADHUNTER = "headhunter"
    AGENCY = "agency"

class ConfidenceTier(str, Enum):
    UNUSABLE = "unusable"      # 0.00-0.39
    LOW = "low"                # 0.40-0.59
    MEDIUM = "medium"          # 0.60-0.79
    HIGH = "high"              # 0.80-0.89
    VERY_HIGH = "very_high"    # 0.90-1.00

class SessionStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### 3.2 Core Models (models/models.py)

#### ContactQuery — User Input
```python
class ContactQuery(BaseModel):
    query: str                                    # Company name, industry, or recruiter name
    region: Region = Region.UAE                   # Default: UAE
    companies: list[str] = Field(default_factory=list)
    industry: str | None = None
    title_filter: str | None = None              # e.g., "technical recruiter"
    sources: list[SourceType] | None = None      # None = all available
    source_names: list[str] | None = None         # Specific plugin names
    max_results: int = Field(default=50, ge=1, le=1000)
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    check_whatsapp: bool = True
    verify_emails: bool = True
    verify_phones: bool = True
    dry_run: bool = False
    no_cache: bool = False
```

#### RecruiterContact — Core Record
```python
class RecruiterContact(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    name: str
    normalized_name: str | None = None            # Lowercase, stripped
    arabic_name: ArabicName | None = None
    emails: list[EmailRecord] = Field(default_factory=list)
    phones: list[PhoneRecord] = Field(default_factory=list)
    company: str | None = None
    company_profile: CompanyProfile | None = None
    title: str | None = None
    contact_type: ContactType = ContactType.RECRUITER
    linkedin_url: str | None = None
    region: Region = Region.UAE
    sources: list[str] = Field(default_factory=list)
    source_results: list[SourceResult] = Field(default_factory=list)
    confidence: ConfidenceScore = Field(default_factory=ConfidenceScore)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

#### EmailRecord
```python
class EmailRecord(BaseModel):
    email: str
    is_primary: bool = False
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    verification_method: str | None = None       # "dns", "smtp", "api_zerobounce", "hibp"
    verification_date: datetime | None = None
    is_m365_domain: bool = False                  # UAE: M365 SMTP unreliable
    mx_host: str | None = None
```

#### PhoneRecord
```python
class PhoneRecord(BaseModel):
    phone: str                                    # E.164 format: +971XXXXXXXXX
    phone_type: PhoneType = PhoneType.UNKNOWN
    country_code: str = "AE"
    carrier: str | None = None
    is_whatsapp: bool | None = None               # None = unchecked
    whatsapp_business_name: str | None = None
    whatsapp_business_email: str | None = None
    whatsapp_business_website: str | None = None
    validation_status: VerificationStatus = VerificationStatus.UNVERIFIED
    uae_info: UAEPhoneInfo | None = None          # UAE-specific details
```

#### UAEPhoneInfo
```python
class UAEPhoneInfo(BaseModel):
    carrier: UAECarrier = UAECarrier.UNKNOWN
    original_carrier: UAECarrier | None = None    # Before MNP
    emirate: str | None = None                    # From landline area code
    number_type: PhoneType = PhoneType.UNKNOWN
    mnp_active: bool = True                       # MNP since 2019
```

#### ArabicName
```python
class ArabicName(BaseModel):
    original: str                                 # "Mohammed Al Rashid"
    normalized_forms: list[str] = Field(default_factory=list)
    email_permutations: list[str] = Field(default_factory=list)
    al_el_bin_removed: str | None = None          # "Mohammed Rashid"
    mohammed_variant: str | None = None           # "Mohammed", "Mohammad", etc.
    title_stripped: str | None = None             # Without "Eng.", "Dr.", etc.
```

#### CompanyProfile
```python
class CompanyProfile(BaseModel):
    name: str
    domain_ae: str | None = None                  # e.g., "etihad.ae"
    domain_com: str | None = None                 # e.g., "emirates.com"
    industry: str | None = None
    ats_platform: str | None = None               # "taleo", "successfactors", "pageup"
    email_format: str | None = None               # "firstname.lastname"
    is_uae_free_zone: bool = False
    free_zone_name: str | None = None             # "DMCC", "JAFZA", "DIFC"
```

#### ConfidenceScore
```python
class ConfidenceScore(BaseModel):
    value: float = Field(default=0.0, ge=0.0, le=1.0)
    tier: ConfidenceTier = ConfidenceTier.UNUSABLE
    source_count: int = 0
    source_diversity_score: float = 0.0           # Up to 0.40
    email_score: float = 0.0                      # Up to 0.25
    phone_score: float = 0.0                      # Up to 0.20
    profile_score: float = 0.0                    # Up to 0.10
    freshness_penalty: float = 0.0                # Up to -0.15
    regional_bonus: float = 0.0                   # 0.05 for UAE/GCC
    data_age_days: int = 0
```

#### SourceResult
```python
class SourceResult(BaseModel):
    source_name: str
    source_type: SourceType
    raw_data: dict = Field(default_factory=dict)
    extracted_name: str | None = None
    extracted_email: str | None = None
    extracted_phone: str | None = None
    extracted_company: str | None = None
    extracted_title: str | None = None
    extracted_linkedin: str | None = None
    source_url: str | None = None
    confidence_contribution: float = Field(default=0.3, ge=0.0, le=1.0)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

#### SearchSession & APIUsageTracker
```python
class SearchSession(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    query: ContactQuery
    status: SessionStatus = SessionStatus.RUNNING
    results_count: int = 0
    api_usage: dict[str, int] = Field(default_factory=dict)  # source → credits_used
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

class APIUsageTracker(BaseModel):
    source_name: str
    credits_used: int = 0
    credits_limit: int | None = None
    credits_remaining: int | None = None
    reset_date: datetime | None = None
    reset_frequency: str = "monthly"              # "monthly", "daily", "one_time"
    last_used: datetime | None = None
    is_depleted: bool = False
```

---

## 4. PLUGIN SYSTEM

### 4.1 SourcePlugin ABC (core/base_plugin.py)

```python
class SourcePlugin(ABC):
    SPEC: ClassVar[PluginSpec]

    # Properties from SPEC
    @property name -> str
    @property source_type -> SourceType
    @property regions -> list[Region]
    @property data_types -> list[str]
    @property priority -> int                    # 1 (highest) - 10 (lowest)
    @property requires_browser -> bool
    @property api_key_env -> str | None

    # Abstract methods
    async def discover(query: ContactQuery) -> list[SourceResult]
    async def enrich(contact: RecruiterContact) -> RecruiterContact
    async def validate_config() -> bool
    async def get_rate_limit_info() -> RateLimitInfo

    # Built-in features
    self.semaphore: asyncio.Semaphore            # Per-plugin concurrency
    self.http_client: httpx.AsyncClient           # With retry via tenacity
    self.logger: structlog.BoundLogger            # Bound with plugin name
    def _resolve_api_key() -> str | None          # From env var
    def _make_source_result(**kwargs) -> SourceResult
    async def close() -> None                     # Cleanup
```

### 4.2 All 30 Plugins (ALL_PLUGINS Registry)

| # | Plugin Name | Type | Regions | Data Types | Priority | Browser | API Key Env | Rate Limit | Monthly Credits | URL Pattern |
|---|-------------|------|---------|------------|----------|---------|-------------|------------|-----------------|-------------|
| 1 | **google_places** | API | GCC+Global | company, phone, address, website | **1** | No | GOOGLE_PLACES_API_KEY | 20/min | $200/mo free | maps.googleapis.com |
| 2 | **expatriates** | SCRAPE | UAE+GCC | phone, name | **1** | No | — | 6/min | ∞ | expatriates.com |
| 3 | **dubizzle** | SCRAPE | UAE | phone, name | **1** | No | — | 6/min | ∞ | dubai.dubizzle.com |
| 4 | **hunter** | API | GCC+Global | email, email_pattern | **2** | No | HUNTER_API_KEY | 10/min | 50/mo | api.hunter.io/v2 |
| 5 | **apollo** | API | GCC+Global | email, phone, title, company, linkedin | **2** | No | APOLLO_API_KEY | 10/min | 60/mo | api.apollo.io/v1 |
| 6 | **snov** | API | GCC+Global | email, email_pattern | **2** | No | SNOV_API_KEY | 10/min | 50/mo | api.snov.io/v1 |
| 7 | **dmcc_directory** | SCRAPE | UAE | company, name, phone, email | **2** | No | — | 6/min | ∞ | dmcc.ae/business-search |
| 8 | **uae_yellow_pages** | SCRAPE | UAE | company, phone, address, website | **2** | No | — | 6/min | ∞ | yellowpages.ae |
| 9 | **bayt** | SCRAPE | GCC | name, title, company | **2** | No | — | 6/min | ∞ | bayt.com |
| 10 | **gulf_talent** | SCRAPE | GCC | name, title, company, linkedin | **2** | No | — | 6/min | ∞ | gulftalent.com |
| 11 | **naukrigulf** | SCRAPE | GCC | name, title, company, phone | **2** | No | — | 6/min | ∞ | naukrigulf.com |
| 12 | **google_dorking** | SCRAPE | GCC+Global | email, phone, name, linkedin | **2** | No | — | 6/min | ∞ | google.com/search |
| 13 | **rocketreach** | API | GCC+Global | email, phone, linkedin, title | **2** | No | ROCKETREACH_API_KEY | 10/min | 5/mo | api.rocketreach.co |
| 14 | **zerobounce** | API | GCC+Global | email_verification | **2** | No | ZEROBOUNCE_API_KEY | 10/min | 100/mo | api.zerobounce.net |
| 15 | **seamless_ai** | API | GCC+Global | email, phone, title, company | **3** | No | SEAMLESS_AI_KEY | 8/min | 50 lifetime | api.seamless.ai |
| 16 | **abstract_api** | API | GCC+Global | email_verification, phone_validation | **3** | No | ABSTRACT_API_KEY | 8/min | 100/mo | app.abstractapi.com |
| 17 | **people_data_labs** | API | GCC+Global | email, phone, title, company, linkedin | **3** | No | PDL_API_KEY | 10/min | 100/mo | api.peopledatalabs.com/v5 |
| 18 | **greenhouse** | API | GCC+Global | recruiter_name, company, jobs | **3** | No | — | 12/min | ∞ | boards-api.greenhouse.io |
| 19 | **lever** | API | GCC+Global | recruiter_name, company, jobs | **3** | No | — | 12/min | ∞ | api.lever.co |
| 20 | **linkedin** | SCRAPE | GCC+Global | name, title, company, linkedin, email_hint | **3** | **Yes** | — | 4/min | ∞ | linkedin.com |
| 21 | **facebook_groups** | SCRAPE | UAE+Saudi+Qatar | name, phone, post_text | **3** | **Yes** | — | 4/min | ∞ | facebook.com/groups |
| 22 | **heidrick** | SCRAPE | GCC+Global | name, title, email, phone, linkedin | **4** | No | — | 6/min | ∞ | heidrick.com |
| 23 | **korn_ferry** | SCRAPE | GCC+Global | name, title, company, office | **4** | No | — | 6/min | ∞ | kornferry.com |
| 24 | **spencer_stuart** | SCRAPE | GCC+Global | name, title, company, office | **4** | No | — | 6/min | ∞ | spencerstuart.com |
| 25 | **egon_zehnder** | SCRAPE | GCC+Global | name, title, company, office | **4** | No | — | 6/min | ∞ | egonzehnder.com |
| 26 | **russell_reynolds** | SCRAPE | GCC+Global | name, title, company, office | **4** | No | — | 6/min | ∞ | russellreynolds.com |
| 27 | **email_permutator** | PERMUTATION | Global | email, email_pattern | **5** | No | — | 60/min | ∞ | local://permutation |
| 28 | **whatsapp_checker** | SOCIAL | GCC | whatsapp_presence, whatsapp_business | **5** | No | WHATSAPP_API_KEY | 10/min | ∞ | api.whatsapp.com |
| 29 | **uae_phone_detector** | LOCAL | UAE | phone_validation, carrier, emirate | **5** | No | — | 60/min | ∞ | local://uae_phone |
| 30 | **arabic_name_normalizer** | PERMUTATION | GCC+Global | name_variants, email_permutations | **5** | No | — | 60/min | ∞ | local://arabic_name |

### 4.3 PluginRegistry

```python
class PluginRegistry:
    def register(plugin: SourcePlugin) -> None
    def unregister(name: str) -> None
    def get(name: str) -> SourcePlugin
    def get_for_query(query: ContactQuery) -> list[SourcePlugin]  # Filter by region, sorted by priority
    def get_by_priority() -> list[SourcePlugin]
    def get_by_type(source_type: SourceType) -> list[SourcePlugin]
    def get_by_region(region: Region) -> list[SourcePlugin]
    def get_browser_plugins() -> list[SourcePlugin]
    def list_all() -> list[PluginInfo]
    def list_available(region: Region | None) -> list[PluginInfo]
    async def validate_all() -> dict[str, bool]
    async def discover_and_register(package: str) -> int  # Auto-discover from plugins/
    async def close_all() -> None
```

### 4.4 PipelineOrchestrator

```python
class PipelineOrchestrator:
    def __init__(registry, config, dedup, scorer, api_tracker)
    async def run(query: ContactQuery) -> PipelineResult
    async def run_discovery(query) -> list[SourceResult]
    async def run_deduplication(results) -> list[RecruiterContact]
    async def run_enrichment(contacts) -> list[RecruiterContact]
    async def run_verification(contacts) -> list[RecruiterContact]

class PipelineConfig:
    max_concurrent_plugins: int = 5
    confidence_threshold_early_exit: float = 0.80
    enable_enrichment: bool = True
    enable_verification: bool = True
    enable_scoring: bool = True
    waterfall_enabled: bool = True
    plugin_timeout_seconds: float = 120.0

class PipelineResult:
    contacts: list[RecruiterContact]
    total_raw_results: int
    total_after_dedup: int
    total_after_verification: int
    plugins_used: list[str]
    plugins_skipped: list[str]
    plugins_failed: list[str]
    api_usage: dict[str, int]
    duration_seconds: float
    early_exit: bool
```

---

## 5. VERIFICATION & SCORING

### 5.1 Email Verification (3-Tier Waterfall)

| Tier | Method | Speed | Accuracy | UAE Note |
|------|--------|-------|----------|----------|
| **1** | Regex + DNS MX | <1ms | 40% of invalids | Detect M365 → flag as SMTP-unreliable |
| **2** | SMTP RCPT TO | 2-5s | 85-95% | **SKIP for M365 domains** (65-70% UAE = false positives) |
| **3** | API (ZeroBounce → NeverBounce → Kickbox) | 200ms | 99% | Free tier stacking |

**UAE M365 Alternative Verification:**
- HIBP breach lookup (email in breach = confirmed valid)
- Gravatar profile check
- Google exact-match search
- LinkedIn email confirmation

### 5.2 Phone Validation Pipeline

1. libphonenumber format validation → E.164 normalization
2. UAE carrier detection (Etisalat/du/Virgin from prefix)
3. GCC phone validation (all 6 countries)
4. WhatsApp check (wa.me HTTP status)
5. Line type detection (mobile/landline/VoIP)

### 5.3 Confidence Scoring Formula

```
source_diversity = min(0.40, num_distinct_sources × 0.10)
email_score      = syntax(0.05) + dns(0.05) + smtp(0.10) + api(0.15)  # cap 0.25
phone_score      = format(0.05) + carrier(0.05) + whatsapp(0.10)      # cap 0.20
profile_score    = linkedin(0.03) + company(0.03) + title(0.02) + both_email_phone(0.02)  # cap 0.10
freshness        = max(-0.15, -(days_old / 180) × 0.15)
regional_bonus   = 0.05 if UAE/GCC else 0.0

final = min(1.0, source_diversity + email_score + phone_score + profile_score + freshness + regional_bonus)
```

**Confidence Tiers:**
| Tier | Range | Action |
|------|-------|--------|
| UNUSABLE | 0.00-0.39 | Discard |
| LOW | 0.40-0.59 | Include with warning |
| MEDIUM | 0.60-0.79 | Usable |
| HIGH | 0.80-0.89 | Confident |
| VERY HIGH | 0.90-1.00 | Verified |

### 5.4 Deduplication (6 Strategies)

| Strategy | Method | Match Rule |
|----------|--------|------------|
| Exact email | Normalize → lowercase, trim | email == email |
| Exact phone | E.164 normalize | phone == phone |
| Fuzzy name | rapidfuzz token_sort_ratio ≥ 85 + same company | name ~ name |
| Arabic name | Normalized forms (Al/El/Bin stripped, Mohammed unified) | form == form |
| LinkedIn URL | Normalize LinkedIn URL | url == url |
| WhatsApp cross-ref | Same WhatsApp number | whatsapp == whatsapp |

**Merge:** Union-Find algorithm → take highest confidence, union all sources, keep most complete data.

### 5.5 API Usage Tracker

- Per-source: credits_used, credits_limit, reset_date
- Monthly/daily/one-time reset logic
- 80% warning, 100% hard stop
- Graceful degradation: skip depleted sources
- SQLite persistence

---

## 6. UAE/GCC-SPECIFIC ENGINES

### 6.1 ArabicNameEngine (uae/arabic_name_engine.py)

- **8 Mohammed variants:** mohammed, mohammad, muhammad, mohd, mohamed, mhamad, muhamad, md
- **Prefix handling:** Al/El/Al-/El-/Bin/Bint → stripped for email gen
- **ABD compounds:** Abdulrahman ↔ Abdul Rahman ↔ Abd Al Rahman
- **Titles:** Sheikh, Eng., Dr., Mr. → stripped for email gen
- **Transliteration:** 14 Arabic→Latin rules
- **Output:** `normalize()` → list of forms, `generate_email_patterns()` → list of emails

### 6.2 UAEPhoneEngine (uae/uae_phone_engine.py)

| Prefix | Carrier | Note |
|--------|---------|------|
| 50, 54 | Etisalat | MNP since 2019 |
| 55 | du | |
| 52, 56, 58 | Shared | Check actual carrier |

| Area Code | Emirate |
|-----------|---------|
| 02 | Abu Dhabi |
| 03 | Al Ain |
| 04 | Dubai |
| 06 | Sharjah/Ajman/UAQ |
| 07 | RAK |
| 09 | Fujairah |

GCC coverage: Saudi (+966), Qatar (+974), Bahrain (+973), Oman (+968), Kuwait (+965)

### 6.3 UAEDomainEngine (uae/uae_domain_engine.py)

**Dual TLD:** Always try BOTH `.ae` AND `.com` for any UAE company.

| Employer | Domain | Format | MX Provider |
|----------|--------|--------|-------------|
| Emirates Group | emirates.com | firstname.lastname@ | M365 |
| Etihad Airways | etihad.ae | firstname.lastname@ | M365 |
| ADNOC | adnoc.ae | firstname.lastname@ | On-prem |
| DEWA | dewa.gov.ae | firstname.lastname@ | On-prem Exchange |
| Emaar | emaar.ae | firstname.lastname@ | M365 |
| DP World | dpworld.com | firstname.lastname@ | M365 |
| Etisalat | etisalat.ae | f_lastname@ (legacy) | On-prem |
| du | du.ae | firstname.lastname@ | M365 |
| Mubadala | mubadala.com | firstname.lastname@ | M365 |

### 6.4 WhatsAppEngine (uae/whatsapp_engine.py)

- `wa.me/971XXXXXXXXX` → HTTP status check for WhatsApp presence
- Business profile extraction: name, description, email, website, category
- Batch checking with rate limits
- Legal: WhatsApp ToS + UAE Cybercrime Law warnings

### 6.5 UAEATSEngine (uae/uae_ats.py)

**10 ATS detection patterns:** Oracle Taleo (~25-30%), SAP SuccessFactors (~15-20%), PageUp (~10-15%), Lever, Greenhouse, iCIMS, Workday, Jobvite, SmartRecruiters, Bullhorn

**25+ UAE company → ATS mappings** for recruiter metadata extraction from job posting URLs.

### 6.6 UAE Compliance (uae/uae_compliance.py)

- robots.txt checker before every scrape
- Per-domain rate limiting (1 req/5 sec minimum)
- 90-day data retention policy
- Legal disclaimer on startup
- UAE Cybercrime Law (Decree-Law 34/2021) warning

---

## 7. CLI COMMANDS

### `rcf search QUERY`
```bash
rcf search "Emirates Group"                           # Search by company
rcf search "recruiter" --industry tech --region uae    # Search by industry
rcf search "Google" -r global -t 0.7 -m 100           # Global, high confidence
rcf search --companies-file targets.txt -f xlsx        # Batch from file
rcf search "talent acquisition" --dry-run              # Preview only
```

Options: `--region` (default: uae), `--sources`, `--max-results` (50), `--confidence-threshold` (0.5), `--output`, `--format` (csv/json/xlsx/html), `--enrich`, `--verify-emails`, `--verify-phones`, `--check-whatsapp`, `--dry-run`, `--verbose`, `--no-cache`, `--companies-file`, `--industry`, `--title-filter`

### `rcf enrich [CONTACT_ID]`
Enrich existing contacts. Options: `--all`, `--sources`, `--verify-emails`, `--verify-phones`, `--check-whatsapp`

### `rcf export`
Export stored contacts. Options: `--format`, `--output`, `--threshold`, `--region`, `--since`, `--dedup`

### `rcf status`
Show API usage per source (credits used/remaining/reset date), total contacts, last search.

### `rcf sources`
List all 30 sources with type, region, status, free tier remaining.

### `rcf config show|set|init|validate`
Manage configuration. `init` creates .env from template. `validate` checks all API keys.

### `rcf setup`
Interactive first-time setup wizard: check deps, prompt for API keys, validate each.

### `rcf db stats|clean|backup|reset`
SQLite management: row counts, remove old data, backup, full reset.

---

## 8. CONFIGURATION

### config.yml (Complete)
```yaml
general:
  default_region: "uae"
  max_concurrent_requests: 5
  request_delay_seconds: 2.0
  user_agent_rotation: true
  cache_ttl_hours: 168
  data_retention_days: 90
  log_level: "INFO"
  log_file: "rcf.log"

uae:
  check_whatsapp: true
  dual_tld_check: true
  arabic_name_variants: true
  detect_ats: true
  carrier_detection: true
  emirate_detection: true
  preferred_contact_method: "whatsapp"

browser:
  headless: true
  stealth_mode: true
  browser_pool_size: 3
  context_reuse: true
  lightpanda_path: null
  camoufox_profile: null

rate_limits:
  api:
    requests_per_minute: 10
  scrape:
    requests_per_minute: 6
  browser:
    requests_per_minute: 4
  smtp:
    connections_per_minute: 3

verification:
  email:
    enabled: true
    tiers: [syntax, dns, smtp, api]
    skip_smtp_for_m365: true
    use_hibp_fallback: true
  phone:
    enabled: true
    libphonenumber: true
    whatsapp_check: true
    carrier_detection: true

scoring:
  minimum_confidence: 0.5
  prefer_phone_over_email: false
  uae_regional_bonus: 0.05

export:
  default_format: "csv"
  include_confidence: true
  include_sources: true
  include_verification_status: true
  include_timestamps: true
  deduplicate: true
```

### .env.example
```
# Email Discovery APIs
HUNTER_API_KEY=              # hunter.io/signup — 50/mo free
APOLLO_API_KEY=               # app.apollo.io/signup — 60/mo free
SNOV_API_KEY=                 # snov.io/register — 50/mo free
SEAMLESS_AI_KEY=              # seamless.ai/signup — 50 lifetime

# Email Verification APIs
ZEROBOUNCE_API_KEY=           # zerobounce.net/signup — 100/mo free
NEVERBOUNCE_API_KEY=          # neverbounce.com/signup — 1000 one-time
KICKBOX_API_KEY=              # kickbox.com/signup — 100/mo free

# Phone & Location APIs
GOOGLE_PLACES_API_KEY=        # console.cloud.google.com — $200/mo free credit
ABSTRACT_API_KEY=             # abstractapi.com/signup — 100/mo free

# Social & OSINT (Optional)
HIBP_API_KEY=                 # haveibeenpwned.com/API/Key — $3.50/mo
PDL_API_KEY=                  # peopledatalabs.com — 100/mo free
ROCKETREACH_API_KEY=          # rocketreach.co — 5/mo free

# WhatsApp (Optional — for Business API)
WHATSAPP_API_KEY=             # Meta Business Suite
```

---

## 9. DATABASE SCHEMA (SQLite WAL)

### Core Tables
- **contacts** — id, name, normalized_name, title, company, linkedin_url, region, confidence_value, confidence_tier, created_at, updated_at
- **emails** — id, contact_id (FK), email, is_primary, verification_status, verification_method, mx_host, is_m365_domain
- **phones** — id, contact_id (FK), phone (E.164), phone_type, country_code, carrier, is_whatsapp, whatsapp_business_name
- **sources** — id, contact_id (FK), source_name, source_type, source_url, confidence_contribution, extracted_at
- **companies** — id, name, domain_ae, domain_com, industry, ats_platform, email_format, is_free_zone
- **sessions** — id, query_json, status, results_count, api_usage_json, started_at, completed_at
- **api_usage** — id, source_name, credits_used, credits_limit, credits_remaining, reset_date, last_used
- **arabic_name_cache** — id, original, normalized_forms_json, email_permutations_json
- **search_results** — id, session_id (FK), contact_id (FK), source_name, raw_data_json

### Views
- **v_contact_detail** — Denormalized: contact + primary email + primary phone + company + WhatsApp count

### Features
- **WAL mode** with 64MB cache
- **FTS5** full-text search on contacts(name, company, title)
- **44 indexes** for common queries
- **9 triggers** for updated_at and FTS sync

---

## 10. EXPORT FORMATS

### CSV (23 columns)
Name | Email | Email_Verified | Phone | Phone_Carrier | Phone_Type | WhatsApp | WhatsApp_Business | Title | Company | Company_Domain | LinkedIn_URL | Region | Emirate | Sources | Confidence_Score | Confidence_Tier | Created_At | Updated_At

### JSON
Nested structure matching Pydantic models

### XLSX
- Header styling (dark blue)
- Conditional row coloring: green (HIGH/VERY_HIGH), yellow (MEDIUM), red (LOW), grey (UNUSABLE)
- Autofilter, frozen header, auto-width, percentage-formatted confidence

### HTML
- Responsive table with Jinja2 template
- Clickable mailto/LinkedIn links
- WhatsApp emoji indicators
- Client-side sorting
- Print-friendly styles

---

## 11. DEPENDENCIES (requirements.txt)

```txt
# CLI & Config
typer>=0.9.0
pydantic>=2.0.0
pyyaml>=6.0
python-dotenv>=1.0.0

# HTTP & Browser
httpx>=0.27.0
scrapling>=0.4.0
hrequests>=0.9.0
playwright>=1.40.0
camoufox>=0.1.0
botasaurus>=4.0.0
browserforge>=1.0.0

# AI Extraction (Optional)
browser-use>=0.1.0
crawl4ai>=0.8.0
scrapegraphai>=2.0.0

# Parsing & Matching
selectolax>=0.4.0
rapidfuzz>=3.0.0
extruct>=0.16.0

# Verification
dnspython>=2.4.0
email-validator>=2.3.0
phonenumbers>=8.13.0

# Storage & Tasks
aiosqlite>=0.19.0
huey>=2.5.0
diskcache>=5.0.0
duckdb>=1.0.0

# Utilities
tenacity>=8.0.0
structlog>=23.0.0
dedupe>=3.0.0

# Export
openpyxl>=3.1.0
jinja2>=3.1.0
```

---

## 12. SUCCESS CRITERIA

- ✅ At least **1 verified email OR 1 verified phone** per recruiter found
- ✅ Multi-source aggregation > single-source contact discovery rate
- ✅ Clean, deduplicated CSV/JSON with source tracking + confidence scores
- ✅ Free-tier rate limits tracked and respected (auto-stop before limits)
- ✅ Graceful degradation — failed sources don't break the pipeline
- ✅ UAE/GCC phone numbers with carrier/emirate detection
- ✅ Arabic name permutation generates correct email patterns
- ✅ WhatsApp presence checking for discovered mobile numbers
- ✅ Dual `.ae`/`.com` TLD checking for all UAE companies
- ✅ M365 SMTP bypass with alternative verification for UAE
- ✅ Pipeline completes in <60 seconds for single-company search

## 13. NON-GOALS

- ❌ Web UI (CLI + optional Textual TUI only)
- ❌ Multi-platform deployment (local only)
- ❌ Real-time monitoring or scheduling
- ❌ CRM/email tool integration
- ❌ Paid/premium API tiers
- ❌ Automated outreach (finding contacts only)
- ❌ Commercial distribution (personal use — UAE PDPL exemption)

## 14. LEGAL COMPLIANCE

- Display UAE legal disclaimer on first run
- Respect robots.txt and X-Robots-Tag headers
- Never bypass login/authentication
- Rate limit: 1 req/5 sec minimum for UAE sites
- Only scrape publicly visible data
- 90-day data retention with auto-cleanup
- Personal use only — no distribution
- UAE Cybercrime Law (Decree-Law 34/2021) awareness
- UAE PDPL personal use exemption (Article 2(3))
- **API changes:** Free tiers may change or disappear. Tool should handle API failures gracefully.
- **Email permutation false positives:** Guessed emails may pass SMTP but bounce. Confidence scoring helps.
