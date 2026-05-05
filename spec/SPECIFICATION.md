# Verification & Scoring Engine — Complete Specification

## UAE/GCC-Optimized Recruiter Contact Finder CLI

**Version**: 1.0  
**Date**: May 4, 2026  
**Status**: Production-ready specification

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Orchestrator                          │
│  (30+ sources → raw contacts → verification pipeline)       │
└──────────┬──────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│              DeduplicationEngine                             │
│  6 strategies: email, phone, fuzzy, Arabic, LinkedIn, WA    │
│  Union-Find grouping → merge → unique contacts              │
└──────────┬──────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────┐  ┌──────────────────────┐
│ EmailVerificationPipe│  │ PhoneValidationPipe  │
│ Tier 1: Syntax + DNS │  │ Tier 1: Format + E164│
│ Tier 2: SMTP Probe   │  │ Tier 2: WhatsApp Chk │
│ Tier 3: API Verify   │  │ Tier 3: Twilio/Abstr │
│ Tier 3-alt: M365 Alt │  │                      │
└──────────┬───────────┘  └──────────┬───────────┘
           │                         │
           ▼                         ▼
┌─────────────────────────────────────────────────────────────┐
│              ConfidenceScoringEngine                         │
│  source_diversity + email + phone + profile + freshness     │
│  + regional_bonus → 0.00-1.00 → tier classification        │
└──────────┬──────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│              FreeTierTracker (SQLite)                        │
│  Per-provider credit tracking, reset logic, degradation     │
└─────────────────────────────────────────────────────────────┘
```

---

## File Map

| File | Module | Responsibility |
|------|--------|---------------|
| `email_verifier.py` | `EmailVerificationPipeline` | 3-tier email verification |
| `phone_validator.py` | `PhoneValidationPipeline` | Multi-step phone validation |
| `scorer.py` | `ConfidenceScoringEngine` | Contact quality scoring |
| `deduplicator.py` | `DeduplicationEngine` | Multi-strategy dedup |
| `api_tracker.py` | `FreeTierTracker` | API credit management |

---

## 1. Email Verification Pipeline

### 1.1 Tier 1: Syntax + DNS (instant, ~50ms)

| Step | Method | Output |
|------|--------|--------|
| Regex | RFC 5322 compliant regex | `SYNTAX_VALID` / `INVALID` |
| DNS MX | `dnspython` resolver, 5s timeout | `DNS_VALID` / `INVALID` |
| MX fingerprint | Check MX hostname suffixes | `MXProvider` enum |

**MX Provider Fingerprints:**

| MX Suffix | Provider | Action |
|-----------|----------|--------|
| `.mail.protection.outlook.com` | M365 | Skip SMTP, use Tier 3-alt |
| `.googlemail.com` / `.google.com` | Google Workspace | Normal SMTP probe |
| Customer's own domain | On-prem Exchange | Normal SMTP probe |

**UAE M365 Domain Cache** (`UAE_M365_DOMAINS`): Pre-seeded with 50+ UAE employer domains. Grows via MX detection. Domains include:
- Banks: emiratesnbd.com, adcb.com, fab.ae, dib.ae, mashreqbank.com
- Telcos: etisalat.ae, du.ae
- Airlines: emirates.com, etihad.ae, flydubai.com
- Government: adnoc.ae, mubadala.com
- Recruitment: michaelpage.ae, hays.ae

### 1.2 Tier 2: SMTP Probe (2-5s)

**Single probe flow:**
```
CONNECT → HELO → MAIL FROM → RCPT TO → QUIT
```

**Timing side-channel:**
| RCPT TO response time | Interpretation |
|----------------------|----------------|
| < 50ms | Catch-all (accepts everything) |
| 50-500ms | Likely valid user |
| > 500ms | Genuine verification |
| Fast rejection (< 100ms) | User definitely not found |

**Rate limiting:** Max 1 SMTP connection per domain per 10 seconds.

**UAE Critical Rule:** Skip SMTP entirely for M365 domains (65-70% of UAE). M365 accepts RCPT TO for ALL addresses → 100% false positive rate.

**Batch verification:** SMTP pipelining (RFC 2920) sends multiple RCPT TO commands in single TCP send → 10-50x faster for batch.

**Greylisting:** Detect 450/451 responses containing "greylist" or "try again". Flag for retry after 5 minutes.

### 1.3 Tier 3: API Verification (~200ms)

**Free tier waterfall (try in order, stop on definitive result):**

| Priority | Provider | Free Limit | Accuracy |
|----------|----------|-----------|----------|
| 1 | ZeroBounce | 100/mo | ~99% |
| 2 | NeverBounce | 1000 one-time | ~98% |
| 3 | Kickbox | 100/mo | ~97% |

**Behavior:**
- Try ZeroBounce first → if VALID or INVALID, stop
- If indeterminate (catch-all/unknown) → try NeverBounce
- If still indeterminate → try Kickbox
- If all fail → `API_RATE_LIMITED`

### 1.4 Tier 3-alt: UAE M365 Alternative Verification

**Only triggered for M365 domains where SMTP was skipped.**

Four checks run in parallel:

| Method | Endpoint | Signal |
|--------|----------|--------|
| HIBP breach lookup | `haveibeenpwned.com/api/v3/breachedaccount/{email}` | Email in breach = confirmed valid |
| Gravatar profile | `en.gravatar.com/{md5_hash}.json` | Profile exists = real person |
| Google search | `google.com/search?q="{email}"` | Email indexed = likely valid |
| LinkedIn crossref | Google site search for domain + name | Confirms person-company link |

**Any positive result = email confirmed valid (confidence 0.80).**

---

## 2. Phone Validation Pipeline

### 2.1 GCC Number Format Reference

| Country | Code | Mobile Prefixes | Example |
|---------|------|----------------|---------|
| UAE | +971 | 50, 52, 54, 55, 56, 58 | +971501234567 |
| Saudi Arabia | +966 | 50, 53, 54, 55, 59 | +966501234567 |
| Qatar | +974 | 3, 5, 6, 7 | +97455123456 |
| Kuwait | +965 | 5, 6, 9 | +96555123456 |
| Bahrain | +973 | 3 | +97333123456 |
| Oman | +968 | 7, 9 | +96892123456 |

### 2.2 UAE Carrier Detection

| Prefix | Carrier | Type |
|--------|---------|------|
| 50 | Etisalat | Mobile |
| 52 | du | Mobile |
| 54 | Etisalat | Mobile |
| 55 | du | Mobile |
| 56 | Etisalat | Mobile |
| 58 | Virgin Mobile (du MVNO) | Mobile |
| 2 (area) | Abu Dhabi | Landline |
| 4 (area) | Dubai | Landline |
| 6 (area) | Sharjah/Ajman | Landline |

### 2.3 Tier 1: Format + E.164 Normalization (instant)

Uses `libphonenumbers` with UAE-first, then GCC fallback parsing.

Handles all common GCC formats:
- `+971501234567` (international)
- `00971501234567` (double-zero international)
- `0501234567` (UAE local)
- `+971 50 123 4567` (formatted)
- `(+971) 50 123 4567` (parenthesized)

### 2.4 Tier 2: WhatsApp Verification (2-5s)

**Method:** HTTP GET to `https://wa.me/{phone}` (no redirects).

| Response | Interpretation |
|----------|---------------|
| 302 → `web.whatsapp.com` | Number has WhatsApp ✅ |
| 302 → `wa.me` | Number may not have WhatsApp |
| 200 with "Chat with" | Number has WhatsApp ✅ |

**Only checked for mobile numbers** (WhatsApp requires mobile).

### 2.5 Tier 3: External API Validation (~200ms)

| Priority | Provider | Cost | UAE Support |
|----------|----------|------|-------------|
| 1 | Twilio Lookup v2 | $0.01/query | Yes |
| 2 | Abstract API | 100/mo free | Yes |

Twilio returns: carrier name, line type, caller name.  
Abstract API returns: valid/invalid, carrier, line type, location.

---

## 3. Confidence Scoring Engine

### 3.1 Scoring Formula

```
final_score = min(1.0,
    source_diversity      # up to 0.40
  + email_score           # up to 0.25
  + phone_score           # up to 0.20
  + profile_score         # up to 0.10
  + freshness_penalty     # up to -0.15
  + regional_bonus        # +0.05
)
```

### 3.2 Component Formulas

**Source Diversity (up to 0.40):**
```
source_diversity = min(0.40, num_distinct_sources × 0.10)
```
| Sources | Score |
|---------|-------|
| 1 | 0.10 |
| 2 | 0.20 |
| 3 | 0.30 |
| 4+ | 0.40 |

**Email Verification (up to 0.25):**
```
email_score = 0
if syntax_valid:     email_score += 0.05
if dns_valid:        email_score += 0.05
if smtp_verified:    email_score += 0.10
if api_verified:     email_score += 0.15
email_score = min(email_score, 0.25)
```
*UAE M365: `alt_verified` substitutes for `smtp_verified` (+0.10)*

**Phone Verification (up to 0.20):**
```
phone_score = 0
if format_valid:        phone_score += 0.05
if carrier_detected:    phone_score += 0.05
if whatsapp_confirmed:  phone_score += 0.10
phone_score = min(phone_score, 0.20)
```

**Profile Richness (up to 0.10):**
```
profile_score = 0
if linkedin_found:          profile_score += 0.03
if company_verified:        profile_score += 0.03
if title_matched:           profile_score += 0.02
if has_both_email_and_phone: profile_score += 0.02
profile_score = min(profile_score, 0.10)
```

**Freshness Penalty (up to -0.15):**
```
penalty = max(-0.15, -(days_old / 180) × 0.15)
```
| Age | Penalty |
|-----|---------|
| 0 days | 0.00 |
| 30 days | -0.025 |
| 60 days | -0.050 |
| 90 days | -0.075 |
| 180+ days | -0.150 |

**Regional Bonus:**
```
bonus = 0.05 if (is_uae or is_gcc) else 0.0
```

### 3.3 Threshold Tiers

| Score Range | Tier | Action |
|-------------|------|--------|
| 0.00 – 0.39 | UNUSABLE | Discard |
| 0.40 – 0.59 | LOW | Include with warning |
| 0.60 – 0.79 | MEDIUM | Usable |
| 0.80 – 0.89 | HIGH | Confident |
| 0.90 – 1.00 | VERY HIGH | Verified |

### 3.4 Example Scores

| Scenario | Email | Phone | Sources | Score | Tier |
|----------|-------|-------|---------|-------|------|
| Perfect UAE contact | API+alt verified | WhatsApp confirmed | 3 | ~0.95 | VERY HIGH |
| Good GCC contact | SMTP verified | Carrier detected | 2 | ~0.70 | MEDIUM |
| Phone-only, WhatsApp | None | WhatsApp confirmed | 2 | ~0.50 | LOW |
| Single source, email only | Syntax+DNS valid | None | 1 | ~0.15 | UNUSABLE |

---

## 4. Deduplication Engine

### 4.1 Match Strategies (ordered by reliability)

| # | Strategy | Match Type | Threshold |
|---|----------|-----------|-----------|
| 1 | Exact email | `normalize_email()` → exact match | 100% |
| 2 | Exact phone | `normalize_phone()` → E.164 exact | 100% |
| 3 | LinkedIn URL | `normalize_linkedin_url()` → exact | 100% |
| 4 | WhatsApp cross-ref | Same E.164 number | 100% |
| 5 | Fuzzy name | `rapidfuzz token_sort_ratio` | ≥ 85% + same company |
| 6 | Arabic name fuzzy | Normalized Arabic forms | ≥ 85% |

### 4.2 Arabic Name Normalization

**Prefix stripping:** Al, El, Bin, Bint, Ibn, Abdul, Abd  
**Mohammed variants (15+):** mohammed, mohammad, muhammad, mohamed, mohd, md, etc. → unified to `mohammed`  
**Other variants (30+):** ahmed/ahmad, hassan/hasan, omar/umar, youssef/yousuf, etc.

### 4.3 Merge Rules

When two contacts match:
1. **ID**: Keep ID of higher-confidence contact
2. **Confidence**: `max(a, b)`
3. **Sources**: Union (deduplicated)
4. **Emails**: Union (deduplicated by normalized form)
5. **Phones**: Union (deduplicated by E.164)
6. **WhatsApp**: Union (deduplicated by E.164)
7. **Name**: Prefer longer/more complete
8. **Company**: Prefer non-empty
9. **Title**: Prefer more specific (longer)
10. **Verification**: OR of all flags

### 4.4 Algorithm

Union-Find (disjoint set) with path compression and union by rank.

1. Initialize: each contact is its own set
2. For each pair (i, j), try each strategy in order
3. First match found → `union(i, j)`, skip remaining strategies
4. After all pairs processed, group by root
5. Merge each group into single contact

Complexity: O(n² × s) where n = contacts, s = strategies.  
For typical CLI usage (n < 10,000), this completes in < 5 seconds.

---

## 5. Free Tier Tracker

### 5.1 Provider Configuration

| Provider | Free Limit | Reset | Notes |
|----------|-----------|-------|-------|
| ZeroBounce | 100/mo | Monthly (1st) | Best accuracy |
| NeverBounce | 1000 | One-time | Good backup |
| Kickbox | 100/mo | Monthly (1st) | Decent accuracy |
| Twilio Lookup | Pay-per-use | N/A | $0.01/query |
| Abstract API | 100/mo | Monthly (1st) | Phone validation |
| HIBP | Rate-limited | N/A | 1 req/1.5s |

### 5.2 Thresholds

| Threshold | Percentage | Action |
|-----------|-----------|--------|
| Warning | 80% | Log warning, continue |
| Hard stop | 100% | Skip provider, fall through |

### 5.3 Graceful Degradation

```
email_verify priority:  zerobounce → neverbounce → kickbox
phone_verify priority:  twilio_lookup → abstract_api
alt_verify priority:    hibp
```

When a provider is depleted, it's automatically skipped. The system continues with remaining providers.

### 5.4 Persistence

SQLite database at `~/.gcc-recruiter/api_usage.db` with two tables:
- `api_usage`: Current state per provider
- `usage_log`: Append-only audit log

### 5.5 Reset Logic

| Reset Type | Logic |
|-----------|-------|
| Monthly | Reset on 1st of each month |
| Daily | Reset at midnight UTC |
| One-time | Never reset |
| Unlimited | No credits to track |

---

## Dependencies

```
# requirements.txt
dnspython>=2.4.0        # DNS MX lookup
phonenumbers>=8.13.0    # Phone format/validation
rapidfuzz>=3.3.0        # Fuzzy string matching
aiohttp>=3.9.0          # Async HTTP client
```

---

## Data Flow (End-to-End)

```
1. Scrape 30+ sources → raw contacts (name, email, phone, company, source)
                          │
2. DeduplicationEngine ──┤  6 strategies, Union-Find
                          │
3. EmailVerificationPipe ─┤  3-tier waterfall + M365 alt
   PhoneValidationPipe ───┤  3-tier validation + WhatsApp
                          │
4. ConfidenceScoringEngine┤  6-component formula → 0.00-1.00
                          │
5. Filter by tier ────────┤  Discard UNUSABLE, warn LOW
                          │
6. Output ────────────────┘  JSON/CSV/TSV results
```

---

## Key UAE/GCC-Specific Design Decisions

1. **M365 SMTP skip**: 65-70% of UAE corporate email is on M365. SMTP RCPT TO always returns 250 OK → useless. Skip SMTP, use HIBP/Gravatar/Google instead.

2. **WhatsApp as primary signal**: WhatsApp is THE primary recruiter communication channel in GCC. WhatsApp confirmation = strong signal for both phone validity and contact quality.

3. **Arabic name fuzzy matching**: Mohammed has 15+ romanization variants. Al/El/Bin prefixes must be stripped. Name matching without this would miss 30%+ of duplicates.

4. **Regional bonus**: UAE/GCC contacts get +0.05 because the tool targets this region. International recruiters are less valuable.

5. **`.com` vs `.ae` domains**: ~60/40 split in UAE. Always try both when generating email permutations.

6. **E.164 normalization critical**: GCC numbers come in wildly varying formats. All phone matching depends on consistent E.164 normalization.
