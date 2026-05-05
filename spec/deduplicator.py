"""
Deduplication Engine — UAE/GCC-Optimized Multi-Strategy Contact Merging
========================================================================
Strategies:
  1. Exact email match    (normalize → exact)
  2. Exact phone match    (E.164 → exact)
  3. Fuzzy name match     (rapidfuzz ≥ 85 + same company)
  4. Arabic name fuzzy    (normalized Arabic forms)
  5. LinkedIn URL match   (normalized → exact)
  6. WhatsApp cross-ref   (same number → same person)

Merge strategy:
  - Take highest confidence score
  - Union all sources
  - Keep most complete data (prefer verified over unverified)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from rapidfuzz import fuzz


# ---------------------------------------------------------------------------
# Arabic Name Normalization
# ---------------------------------------------------------------------------

# Arabic article/prefix patterns to strip for comparison
ARABIC_PREFIXES: list[str] = [
    "al ", "al-", "el ", "el-",
    "bin ", "bint ", "ibn ",
    "abdul ", "abd ",
    "abdullah ",
]

# Mohammed variants — unify to canonical form for comparison
MOHAMMED_VARIANTS: dict[str, str] = {
    "mohammed": "mohammed",
    "mohammad": "mohammed",
    "muhammad": "mohammed",
    "mohamed": "mohammed",
    "mohamad": "mohammed",
    "muhamed": "mohammed",
    "mahamed": "mohammed",
    "muhammad": "mohammed",
    "mohd": "mohammed",
    "md": "mohammed",
    "muhamad": "mohammed",
    "mohammaed": "mohammed",
    "mohamud": "mohammed",
}

# Additional Arabic name variant maps
ARABIC_NAME_VARIANTS: dict[str, str] = {
    # Ahmed variants
    "ahmed": "ahmed",
    "ahmad": "ahmed",
    "ahmadh": "ahmed",
    "ahamed": "ahmed",
    # Ali variants
    "ali": "ali",
    "aly": "ali",
    # Hassan variants
    "hassan": "hassan",
    "hasan": "hassan",
    "hassaan": "hassan",
    # Hussain variants
    "hussain": "hussain",
    "hussein": "hussain",
    "hussayn": "hussain",
    "husein": "hussain",
    # Abdul variants (already handled in MOHAMMED_VARIANTS + ARABIC_PREFIXES)
    "abdulrahman": "abdulrahman",
    "abdulrahim": "abdulrahim",
    "abdullatif": "abdullatif",
    "abdulsalam": "abdulsalam",
    # Omar variants
    "omar": "omar",
    "umar": "omar",
    "omer": "omar",
    # Youssef variants
    "youssef": "youssef",
    "yousuf": "youssef",
    "yousef": "youssef",
    "yusuf": "youssef",
    "yousif": "youssef",
    # Khalid variants
    "khalid": "khalid",
    "khaled": "khalid",
    "khaleed": "khalid",
    # Nasser variants
    "nasser": "nasser",
    "naser": "nasser",
    "nassir": "nasser",
    # Saeed variants
    "saeed": "saeed",
    "said": "saeed",
    "sayeed": "saeed",
    # Fatima variants
    "fatima": "fatima",
    "fatma": "fatima",
    "fatimah": "fatima",
    # Mariam variants
    "mariam": "mariam",
    "maryam": "mariam",
    "meriam": "mariam",
    # Noor variants
    "noor": "noor",
    "nour": "noor",
    "nur": "noor",
}


def normalize_name_for_matching(name: str) -> str:
    """
    Normalize a name for fuzzy matching.

    Steps:
      1. Lowercase
      2. Strip diacritics (é → e, ñ → n)
      3. Remove Arabic prefixes (al, el, bin, bint)
      4. Unify Mohammed variants
      5. Unify other Arabic name variants
      6. Collapse whitespace
      7. Sort tokens (for token-based comparison)
    """
    if not name:
        return ""

    # Lowercase
    n = name.lower().strip()

    # Strip diacritics
    n = unicodedata.normalize("NFKD", n)
    n = "".join(c for c in n if not unicodedata.combining(c))

    # Remove Arabic prefixes
    for prefix in ARABIC_PREFIXES:
        n = n.replace(prefix, " ")

    # Tokenize
    tokens = n.split()

    # Unify Mohammed variants
    tokens = [MOHAMMED_VARIANTS.get(t, t) for t in tokens]

    # Unify other Arabic variants
    tokens = [ARABIC_NAME_VARIANTS.get(t, t) for t in tokens]

    return " ".join(tokens)


def arabic_name_similarity(name1: str, name2: str) -> float:
    """
    Compare two names with Arabic-aware normalization.

    Uses rapidfuzz token_sort_ratio on normalized forms.
    Returns 0.0-1.0 similarity score.
    """
    n1 = normalize_name_for_matching(name1)
    n2 = normalize_name_for_matching(name2)

    if not n1 or not n2:
        return 0.0

    return fuzz.token_sort_ratio(n1, n2) / 100.0


# ---------------------------------------------------------------------------
# Email Normalization
# ---------------------------------------------------------------------------

def normalize_email(email: str) -> str:
    """
    Normalize email for exact matching.

    Steps:
      1. Lowercase
      2. Strip whitespace
      3. Remove mail tags (+tag in local part is NOT removed — different emails)
    """
    return email.strip().lower()


# ---------------------------------------------------------------------------
# Phone Normalization
# ---------------------------------------------------------------------------

def normalize_phone(phone: str) -> str:
    """
    Normalize phone to E.164 for exact matching.

    Strips all non-digit characters except leading +.
    If no + prefix, assumes UAE (+971) and prepends it.
    """
    import phonenumbers

    # Quick strip
    digits = re.sub(r"[^\d+]", "", phone.strip())

    # Try parsing with UAE default
    try:
        parsed = phonenumbers.parse(digits, "AE")
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
    except phonenumbers.NumberParseException:
        pass

    # Try other GCC defaults
    for region in ["SA", "QA", "KW", "BH", "OM"]:
        try:
            parsed = phonenumbers.parse(digits, region)
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.E164
                )
        except phonenumbers.NumberParseException:
            continue

    # Fallback: strip everything, return digits
    return re.sub(r"[^\d]", "", phone)


# ---------------------------------------------------------------------------
# LinkedIn URL Normalization
# ---------------------------------------------------------------------------

def normalize_linkedin_url(url: str) -> str:
    """
    Normalize LinkedIn URL for exact matching.

    Steps:
      1. Lowercase
      2. Remove trailing slashes
      3. Remove query parameters
      4. Remove www. prefix
      5. Normalize /in/ vs /pub/ paths
      6. Extract username/ID as canonical form

    Examples:
      https://www.linkedin.com/in/ahmed-recruiter/ → linkedin.com/in/ahmed-recruiter
      http://linkedin.com/in/ahmed-recruiter/?trk=foo → linkedin.com/in/ahmed-recruiter
      https://ae.linkedin.com/in/ahmed-recruiter → linkedin.com/in/ahmed-recruiter
    """
    url = url.lower().strip()

    # Remove protocol
    url = re.sub(r"^https?://", "", url)

    # Remove www.
    url = url.replace("www.", "")

    # Remove country subdomains (ae., uk., etc.)
    url = re.sub(r"^[a-z]{2}\.", "", url)

    # Remove query parameters
    url = url.split("?")[0]

    # Remove trailing slash
    url = url.rstrip("/")

    # Remove fragments
    url = url.split("#")[0]

    return url


# ---------------------------------------------------------------------------
# Contact Model
# ---------------------------------------------------------------------------

@dataclass
class Contact:
    """A recruiter contact record to be deduplicated."""
    id: str
    name: str = ""
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    linkedin_url: str = ""
    whatsapp_numbers: list[str] = field(default_factory=list)
    company: str = ""
    title: str = ""
    sources: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    region: str = ""
    # Verification flags
    email_verified: bool = False
    phone_verified: bool = False
    whatsapp_confirmed: bool = False

    @property
    def normalized_emails(self) -> list[str]:
        return [normalize_email(e) for e in self.emails if e]

    @property
    def normalized_phones(self) -> list[str]:
        return [normalize_phone(p) for p in self.phones if p]

    @property
    def normalized_linkedin(self) -> str:
        return normalize_linkedin_url(self.linkedin_url) if self.linkedin_url else ""

    @property
    def normalized_whatsapp(self) -> list[str]:
        return [normalize_phone(p) for p in self.whatsapp_numbers if p]


# ---------------------------------------------------------------------------
# Match Result
# ---------------------------------------------------------------------------

class MatchType(Enum):
    EXACT_EMAIL = auto()
    EXACT_PHONE = auto()
    FUZZY_NAME = auto()
    ARABIC_NAME = auto()
    LINKEDIN_URL = auto()
    WHATSAPP_CROSSREF = auto()


@dataclass
class MatchResult:
    """Result of a deduplication match attempt."""
    is_match: bool
    match_type: Optional[MatchType] = None
    similarity: float = 0.0
    contact_a_id: str = ""
    contact_b_id: str = ""


# ---------------------------------------------------------------------------
# Deduplication Strategies
# ---------------------------------------------------------------------------

def match_exact_email(a: Contact, b: Contact) -> MatchResult:
    """
    Strategy 1: Exact email match.

    Normalize both contacts' emails (lowercase, trim) and check for
    any overlap.
    """
    emails_a = set(a.normalized_emails)
    emails_b = set(b.normalized_emails)

    overlap = emails_a & emails_b
    if overlap:
        return MatchResult(
            is_match=True,
            match_type=MatchType.EXACT_EMAIL,
            similarity=1.0,
            contact_a_id=a.id,
            contact_b_id=b.id,
        )
    return MatchResult(is_match=False, contact_a_id=a.id, contact_b_id=b.id)


def match_exact_phone(a: Contact, b: Contact) -> MatchResult:
    """
    Strategy 2: Exact phone match.

    Normalize both contacts' phones to E.164 and check for overlap.
    """
    phones_a = set(a.normalized_phones)
    phones_b = set(b.normalized_phones)

    overlap = phones_a & phones_b
    if overlap:
        return MatchResult(
            is_match=True,
            match_type=MatchType.EXACT_PHONE,
            similarity=1.0,
            contact_a_id=a.id,
            contact_b_id=b.id,
        )
    return MatchResult(is_match=False, contact_a_id=a.id, contact_b_id=b.id)


# Fuzzy name match threshold
FUZZY_NAME_THRESHOLD: float = 0.85


def match_fuzzy_name(a: Contact, b: Contact) -> MatchResult:
    """
    Strategy 3: Fuzzy name match + same company.

    Uses rapidfuzz token_sort_ratio ≥ 85 AND same company name.
    This prevents merging different people with similar names at
    different companies.
    """
    if not a.name or not b.name:
        return MatchResult(is_match=False, contact_a_id=a.id, contact_b_id=b.id)

    # Must be same company (or at least one has no company)
    company_a = a.company.lower().strip()
    company_b = b.company.lower().strip()

    if company_a and company_b and company_a != company_b:
        return MatchResult(is_match=False, contact_a_id=a.id, contact_b_id=b.id)

    similarity = fuzz.token_sort_ratio(a.name.lower(), b.name.lower()) / 100.0

    if similarity >= FUZZY_NAME_THRESHOLD:
        return MatchResult(
            is_match=True,
            match_type=MatchType.FUZZY_NAME,
            similarity=similarity,
            contact_a_id=a.id,
            contact_b_id=b.id,
        )
    return MatchResult(is_match=False, contact_a_id=a.id, contact_b_id=b.id)


def match_arabic_name(a: Contact, b: Contact) -> MatchResult:
    """
    Strategy 4: Arabic name fuzzy match.

    Compares normalized Arabic forms:
      - Strip Al/El/Bin prefixes
      - Unify Mohammed variants
      - Unify other Arabic name variants
    Then uses token_sort_ratio ≥ 85.
    """
    if not a.name or not b.name:
        return MatchResult(is_match=False, contact_a_id=a.id, contact_b_id=b.id)

    similarity = arabic_name_similarity(a.name, b.name)

    if similarity >= FUZZY_NAME_THRESHOLD:
        return MatchResult(
            is_match=True,
            match_type=MatchType.ARABIC_NAME,
            similarity=similarity,
            contact_a_id=a.id,
            contact_b_id=b.id,
        )
    return MatchResult(is_match=False, contact_a_id=a.id, contact_b_id=b.id)


def match_linkedin_url(a: Contact, b: Contact) -> MatchResult:
    """
    Strategy 5: LinkedIn URL match.

    Normalize LinkedIn URLs and check for exact match.
    """
    url_a = a.normalized_linkedin
    url_b = b.normalized_linkedin

    if url_a and url_b and url_a == url_b:
        return MatchResult(
            is_match=True,
            match_type=MatchType.LINKEDIN_URL,
            similarity=1.0,
            contact_a_id=a.id,
            contact_b_id=b.id,
        )
    return MatchResult(is_match=False, contact_a_id=a.id, contact_b_id=b.id)


def match_whatsapp_crossref(a: Contact, b: Contact) -> MatchResult:
    """
    Strategy 6: WhatsApp cross-reference.

    If two contacts share a WhatsApp number, they are the same person.
    WhatsApp numbers are normalized to E.164 for comparison.
    """
    wa_a = set(a.normalized_whatsapp)
    wa_b = set(b.normalized_whatsapp)

    # Also include regular phones as potential WhatsApp numbers
    wa_a.update(a.normalized_phones)
    wa_b.update(b.normalized_phones)

    overlap = wa_a & wa_b
    if overlap:
        return MatchResult(
            is_match=True,
            match_type=MatchType.WHATSAPP_CROSSREF,
            similarity=1.0,
            contact_a_id=a.id,
            contact_b_id=b.id,
        )
    return MatchResult(is_match=False, contact_a_id=a.id, contact_b_id=b.id)


# All strategies, in order of reliability (most reliable first)
DEDUP_STRATEGIES: list[callable] = [
    match_exact_email,
    match_exact_phone,
    match_linkedin_url,
    match_whatsapp_crossref,
    match_fuzzy_name,
    match_arabic_name,
]


# ---------------------------------------------------------------------------
# Merge Strategy
# ---------------------------------------------------------------------------

def merge_contacts(a: Contact, b: Contact) -> Contact:
    """
    Merge two contacts into one.

    Merge rules:
      1. Confidence: take max(a.confidence, b.confidence)
      2. Sources: union of both source lists
      3. Emails: union of both email lists (deduplicated)
      4. Phones: union of both phone lists (deduplicated by E.164)
      5. WhatsApp: union of both lists
      6. Name: prefer the longer/more complete name
      7. Company: prefer verified or non-empty
      8. Title: prefer the more specific (longer) title
      9. LinkedIn: prefer non-empty
      10. Verification: OR of all verification flags
      11. Region: prefer the more specific
      12. ID: keep the ID of the higher-confidence contact
    """
    # Determine primary (higher confidence)
    primary, secondary = (a, b) if a.confidence_score >= b.confidence_score else (b, a)

    # Union emails (deduplicated)
    all_emails = list(dict.fromkeys(
        primary.emails + secondary.emails
    ))

    # Union phones (deduplicated by normalized form)
    seen_normalized: set[str] = set()
    all_phones: list[str] = []
    for phone in primary.phones + secondary.phones:
        norm = normalize_phone(phone)
        if norm not in seen_normalized:
            seen_normalized.add(norm)
            all_phones.append(phone)

    # Union WhatsApp (deduplicated)
    seen_wa: set[str] = set()
    all_whatsapp: list[str] = []
    for wa in primary.whatsapp_numbers + secondary.whatsapp_numbers:
        norm = normalize_phone(wa)
        if norm not in seen_wa:
            seen_wa.add(norm)
            all_whatsapp.append(wa)

    # Union sources
    all_sources = list(dict.fromkeys(primary.sources + secondary.sources))

    # Name: prefer longer/more complete
    name = primary.name if len(primary.name) >= len(secondary.name) else secondary.name

    # Company: prefer non-empty, then longer
    company = primary.company or secondary.company

    # Title: prefer more specific (longer)
    title = primary.title if len(primary.title) >= len(secondary.title) else secondary.title

    # LinkedIn: prefer non-empty
    linkedin = primary.linkedin_url or secondary.linkedin_url

    return Contact(
        id=primary.id,
        name=name,
        emails=all_emails,
        phones=all_phones,
        linkedin_url=linkedin,
        whatsapp_numbers=all_whatsapp,
        company=company,
        title=title,
        sources=all_sources,
        confidence_score=max(a.confidence_score, b.confidence_score),
        region=primary.region or secondary.region,
        email_verified=a.email_verified or b.email_verified,
        phone_verified=a.phone_verified or b.phone_verified,
        whatsapp_confirmed=a.whatsapp_confirmed or b.whatsapp_confirmed,
    )


# ---------------------------------------------------------------------------
# Deduplication Engine
# ---------------------------------------------------------------------------

class DeduplicationEngine:
    """
    Multi-strategy deduplication engine.

    Uses Union-Find (disjoint set) to efficiently group contacts
    that match on ANY strategy, then merges each group.

    Usage:
        engine = DeduplicationEngine()
        merged = engine.deduplicate(contacts)
    """

    def __init__(
        self,
        strategies: list[callable] | None = None,
        fuzzy_threshold: float = FUZZY_NAME_THRESHOLD,
    ) -> None:
        self.strategies = strategies or DEDUP_STRATEGIES
        self.fuzzy_threshold = fuzzy_threshold

    def deduplicate(self, contacts: list[Contact]) -> list[Contact]:
        """
        Run full deduplication pipeline.

        1. Build match pairs using all strategies
        2. Group matches using Union-Find
        3. Merge each group into a single contact

        Returns deduplicated list of contacts.
        """
        if len(contacts) <= 1:
            return contacts

        # Union-Find data structure
        parent: dict[str, str] = {c.id: c.id for c in contacts}
        rank: dict[str, int] = {c.id: 0 for c in contacts}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]  # Path compression
                x = parent[x]
            return x

        def union(x: str, y: str) -> None:
            rx, ry = find(x), find(y)
            if rx == ry:
                return
            if rank[rx] < rank[ry]:
                rx, ry = ry, rx
            parent[ry] = rx
            if rank[rx] == rank[ry]:
                rank[rx] += 1

        # Check all pairs (O(n²) but n is typically < 10,000 for CLI usage)
        n = len(contacts)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = contacts[i], contacts[j]
                for strategy in self.strategies:
                    result = strategy(a, b)
                    if result.is_match:
                        union(a.id, b.id)
                        break  # No need to check more strategies for this pair

        # Group by root
        groups: dict[str, list[Contact]] = {}
        for c in contacts:
            root = find(c.id)
            groups.setdefault(root, []).append(c)

        # Merge each group
        merged: list[Contact] = []
        for group in groups.values():
            if len(group) == 1:
                merged.append(group[0])
            else:
                # Merge all in group into single contact
                result = group[0]
                for c in group[1:]:
                    result = merge_contacts(result, c)
                merged.append(result)

        return merged

    def find_matches(
        self, contact: Contact, contacts: list[Contact]
    ) -> list[MatchResult]:
        """
        Find all matches for a single contact against a list.
        Returns all match results (both positive and negative).
        """
        results: list[MatchResult] = []
        for other in contacts:
            if other.id == contact.id:
                continue
            for strategy in self.strategies:
                result = strategy(contact, other)
                if result.is_match:
                    results.append(result)
                    break
        return results

    def find_potential_duplicates(
        self, contacts: list[Contact]
    ) -> list[list[Contact]]:
        """
        Find groups of potential duplicates without merging.
        Useful for review before merging.
        """
        parent: dict[str, str] = {c.id: c.id for c in contacts}
        rank: dict[str, int] = {c.id: 0 for c in contacts}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: str, y: str) -> None:
            rx, ry = find(x), find(y)
            if rx == ry:
                return
            if rank[rx] < rank[ry]:
                rx, ry = ry, rx
            parent[ry] = rx
            if rank[rx] == rank[ry]:
                rank[rx] += 1

        n = len(contacts)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = contacts[i], contacts[j]
                for strategy in self.strategies:
                    result = strategy(a, b)
                    if result.is_match:
                        union(a.id, b.id)
                        break

        groups: dict[str, list[Contact]] = {}
        for c in contacts:
            root = find(c.id)
            groups.setdefault(root, []).append(c)

        # Only return groups with > 1 member
        return [g for g in groups.values() if len(g) > 1]
