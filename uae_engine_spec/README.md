# UAE/GCC Recruiter Contact Finder — Engine Specification

Complete, production-grade specification for all UAE/GCC-specific modules.

## Architecture Overview

```
uae_engine_spec/
├── __init__.py                # Package init with all exports
├── arabic_name_engine.py      # Arabic name handling & email permutations
├── uae_phone_engine.py        # UAE/GCC phone validation & carrier detection
├── uae_domain_engine.py       # UAE employer domain resolution
├── whatsapp_engine.py         # WhatsApp number detection & enrichment
├── uae_google_dork.py         # UAE-specific Google dork query builder
├── uae_ats.py                 # ATS detection & recruiter metadata
└── uae_compliance.py          # Legal compliance, rate limiting, data retention
```

## Module Summary

### 1. ArabicNameEngine (`arabic_name_engine.py`)

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `normalize(name)` | `"Mohammed Al Rashid"` | `NormalizedName` | All normalized forms |
| `generate_email_patterns(name, domain)` | `"Mohammed Al Rashid", "emirates.com"` | `list[str]` | All email candidates |
| `handle_prefixes(name)` | `"Khalid Al Maktoum"` | `list[str]` | Al/El/Bin/Bint variants |
| `handle_mohammed(name)` | `"Mohammed Al Rashid"` | `list[str]` | 8+ Mohammed variant expansions |
| `transliterate(name)` | `"Yousuf Al Qassim"` | `list[str]` | Arabic→Latin transliteration |

**Key data**: 8 Mohammed variants, 8 Abd compound patterns, 17 ABD transliterations, title stripping for Sheikh/Eng./Dr./Prof., 25+ example inputs with expected email outputs.

### 2. UAEPhoneEngine (`uae_phone_engine.py`)

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `classify(number)` | `"+971501234567"` | `UAEPhoneInfo` | Full classification |
| `detect_carrier(number)` | `"+971501234567"` | `"etisalat"` | Carrier (with MNP caveat) |
| `detect_emirate(number)` | `"+97121234567"` | `"abu_dhabi"` | Emirate from area code |
| `format_e164(number)` | `"0501234567"` | `"+971501234567"` | E.164 normalization |
| `is_whatsapp_number(number)` | `"+971501234567"` | `bool` | WhatsApp check via wa.me |
| `validate_uae(number)` | `"+971501234567"` | `bool` | Full UAE validation |
| `validate_gcc(number, country)` | `"+966501234567", "saudi"` | `bool` | GCC-wide validation |

**Key data**: Carrier prefix map (50/52/53/54/55/56/58 → Etisalat/Du/Virgin), landline area codes (02-09 → 6 emirates), regex for all 6 GCC countries.

### 3. UAEDomainEngine (`uae_domain_engine.py`)

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `resolve_domains(company)` | `"Emirates Group"` | `["emirates.com", ...]` | Dual TLD (.com + .ae) |
| `get_email_format(company)` | `"Etisalat"` | `"{first}_{last}"` | Known email pattern |
| `get_employer_info(company)` | `"ADNOC"` | `EmployerEmailInfo` | Full employer record |
| `is_government_domain(domain)` | `"mohre.gov.ae"` | `True` | Government check |
| `detect_free_zone(company)` | `"DMCC company"` | `"DMCC"` | Free zone detection |

**Key data**: 15 employer records (Emirates, Etihad, ADNOC, DEWA, Emaar, Meraas, DP World, Etisalat, du, Mubadala, Dubai Properties, Emirates NBD, FAB, Careem, Noon), 12 free zone patterns, government domain regex.

### 4. WhatsAppEngine (`whatsapp_engine.py`)

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `check_whatsapp(number)` | `"+971501234567"` | `WhatsAppInfo` | Account detection |
| `get_business_profile(number)` | `"+971501234567"` | `WhatsAppBusinessProfile` | Business info extraction |
| `generate_wa_link(number, message)` | `"+971501234567"` | `"https://wa.me/971501234567"` | Click-to-chat link |
| `batch_check(numbers)` | `["...", "..."]` | `dict[str, WhatsAppInfo]` | Batch check (rate-limited) |

**Key data**: Legal disclaimer, UAE cybercrime law text, rate limits (5 sec/check, max 50/batch), confidence scoring.

### 5. UAEGoogleDorkEngine (`uae_google_dork.py`)

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `build_email_query(company)` | `"ADNOC"` | query string | Email dorks |
| `build_phone_query(company)` | `"ABC Recruitment"` | query string | Phone dorks |
| `build_whatsapp_query(company)` | `"ABC Recruitment"` | query string | WhatsApp dorks |
| `build_walkin_query(location)` | `"Dubai"` | query string | Walk-in interview dorks |
| `build_recruiter_query(name, company)` | `"Ahmed", "ADNOC"` | query string | Recruiter-specific dorks |
| `build_custom_query(template, **kwargs)` | template name | query string | Any of 30+ templates |

**Key data**: 30+ query templates, 25+ UAE locations, 14 recruiter title keywords, 16 recruitment keywords.

### 6. UAEATSEngine (`uae_ats.py`)

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `detect_ats(url)` | careers URL | `ATSInfo` | ATS from URL pattern |
| `detect_ats_for_company(company)` | `"Emirates Group"` | `dict` | Known company→ATS mapping |
| `extract_recruiter_metadata(url)` | job URL | `RecruiterMetadata` | Job ID, ATS, company from URL |

**Key data**: 10 ATS detection patterns (Oracle Taleo, SAP SF, PageUp, Lever, Greenhouse, iCIMS, Workday, Jobvite, SmartRecruiters, Bullhorn), 25+ UAE company→ATS mappings.

### 7. UAEComplianceEngine (`uae_compliance.py`)

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `display_startup_disclaimer()` | — | formatted text | Legal disclaimer |
| `check_robots_txt(url)` | URL | `bool` | robots.txt compliance |
| `enforce_rate_limit(url)` | URL | `float` (waited) | Rate limit enforcement |
| `check_data_retention()` | — | `list[Path]` | Find expired data files |
| `enforce_data_retention()` | — | `int` | Delete expired data |
| `get_compliance_report()` | — | `ComplianceReport` | Session audit report |
| `should_proceed(url)` | URL | `(bool, str)` | Full compliance gate |

**Key data**: Rate limits per domain category (2-10 sec), 90-day retention, UAE cybercrime law text, audit logging.

## Quick Start

```python
from uae_engine_spec import (
    ArabicNameEngine,
    UAEPhoneEngine,
    UAEDomainEngine,
    WhatsAppEngine,
    UAEGoogleDorkEngine,
    UAEATSEngine,
    UAEComplianceEngine,
)

# 1. Startup compliance
compliance = UAEComplianceEngine(data_dir=Path("./data"))
print(compliance.display_startup_disclaimer())

# 2. Find email for a recruiter at ADNOC
name_eng = ArabicNameEngine()
domain_eng = UAEDomainEngine()
emails = name_eng.generate_email_patterns("Mohammed Al Rashid", "adnoc.ae")

# 3. Validate a UAE phone number
phone_eng = UAEPhoneEngine()
info = phone_eng.classify("+971501234567")
print(f"Type: {info.phone_type}, Carrier: {info.carrier}")

# 4. Build Google dorks
dork_eng = UAEGoogleDorkEngine()
query = dork_eng.build_email_query("ADNOC")

# 5. Check ATS
ats_eng = UAEATSEngine()
ats = ats_eng.detect_ats("https://emiratesgroupcareers.com/hcmUI/...")
print(f"ATS: {ats.ats_name}")
```

## Key Design Decisions

1. **No external dependencies** — All modules use only Python stdlib (plus optional `requests` for HTTP)
2. **M365 awareness** — Email verification bypasses SMTP RCPT TO since M365 accepts all addresses (~65-70% of UAE corporate email)
3. **MNP caveat** — Carrier detection always includes Mobile Number Portability disclaimer
4. **Dual TLD** — Every UAE company check tries both `.com` and `.ae`
5. **Rate limiting** — Built into every module that makes HTTP requests
6. **Legal compliance** — `UAEComplianceEngine` wraps all HTTP operations
7. **WhatsApp primary** — WhatsApp is treated as the primary recruiter communication channel in GCC (not email)
