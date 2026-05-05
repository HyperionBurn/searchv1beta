"""
UAE/GCC-specific validators for phone numbers, emails, Arabic names, and domains.

Key design decisions driven by research:
- M365 dominates UAE corporate email (~65-70%); SMTP RCPT TO is useless there,
  so we classify verification methods and avoid relying on SMTP alone.
- WhatsApp (+971-5X) is the PRIMARY recruiter communication channel in GCC.
- Arabic name permutation is the #1 challenge for email guessing.
- `.com` is more common than `.ae` for UAE companies (~60/40 split).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

from pydantic import field_validator

# =====================================================================
# CONSTANTS
# =====================================================================

# UAE mobile prefixes (after country code +971, before subscriber number)
# Post-MNP (2019) these are *original assignment* hints only.
UAE_MOBILE_PREFIXES: set[str] = {"50", "52", "53", "54", "55", "56", "58"}

# UAE landline area codes (single digit after +971)
UAE_LANDLINE_AREA_CODES: set[str] = {"2", "3", "4", "6", "7", "9"}
# 2 = Abu Dhabi, 3 = Al Ain, 4 = Dubai, 6 = Sharjah/Ajman/Umm Al Quwain,
# 7 = Ras Al Khaimah, 9 = Fujairah

# UAE toll-free / premium prefixes
UAE_TOLLFREE_PREFIXES: set[str] = {"800", "900"}
UAE_PREMIUM_PREFIX: str = "700"

# UAE emirate mapping from landline area code
UAE_AREA_CODE_TO_EMIRATE: dict[str, str] = {
    "2": "Abu Dhabi",
    "3": "Al Ain",
    "4": "Dubai",
    "6": "Sharjah",
    "7": "Ras Al Khaimah",
    "9": "Fujairah",
}

# Etisalat original assignment prefixes (pre-MNP)
# 50 = Etisalat, 54 = Etisalat
ETISALAT_MOBILE_PREFIXES: set[str] = {"50", "54"}
# Du original assignment prefixes (pre-MNP)
# 55 = Du
DU_MOBILE_PREFIXES: set[str] = {"55"}
# Shared / MVNO prefixes (could be either carrier post-MNP)
# 52, 56, 58 = originally mixed, now uncertain
SHARED_MOBILE_PREFIXES: set[str] = {"52", "56", "58"}

# Saudi Arabia mobile prefixes (after +966)
SAUDI_MOBILE_PREFIXES: set[str] = {"50", "53", "54", "55", "56", "58", "59"}

# GCC country codes
GCC_COUNTRY_CODES: dict[str, str] = {
    "971": "AE",   # UAE
    "966": "SA",   # Saudi Arabia
    "974": "QA",   # Qatar
    "973": "BH",   # Bahrain
    "968": "OM",   # Oman
    "965": "KW",   # Kuwait
}

# Qatar mobile prefixes (after +974)
QATAR_MOBILE_PREFIXES: set[str] = {"3", "5", "6", "7"}

# Bahrain mobile prefixes (after +973)
BAHRAIN_MOBILE_PREFIXES: set[str] = {"3"}

# Oman mobile prefixes (after +968)
OMAN_MOBILE_PREFIXES: set[str] = {"9"}

# Kuwait mobile prefixes (after +965)
KUWAIT_MOBILE_PREFIXES: set[str] = {"5", "6", "8", "9"}

# Common email pattern templates for UAE companies
EMAIL_PATTERN_TEMPLATES: dict[str, str] = {
    "firstname_lastname": "{first}.{last}",
    "firstlast": "{first}{last}",
    "first_last": "{first}_{last}",
    "flast": "{f}{last}",
    "firstl": "{first}{l}",
    "firstname": "{first}",
    "first.lastname": "{first}.{last}",
    "last_first": "{last}.{first}",
    "firstlast_digit": "{first}{last}{d}",
}

# UAE TLD patterns
UAE_DOMAIN_PATTERN = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+"
    r"(?:ae|co\.ae|com\.ae|gov\.ae|ac\.ae|org\.ae|net\.ae|sch\.ae)$",
    re.IGNORECASE,
)

# General email regex (RFC 5322 simplified)
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)

# M365 MX record fingerprints — domains hosted on Microsoft 365 / Exchange Online
MX_M365_FINGERPRINTS: set[str] = {
    ".mail.protection.outlook.com",
    ".eurprd05.prod.outlook.com",
    ".apcprd05.prod.outlook.com",
    ".mail.eo.outlook.com",
    ".messaging.microsoft.com",
}

# LinkedIn URL pattern
LINKEDIN_URL_PATTERN = re.compile(
    r"^https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+/?$",
    re.IGNORECASE,
)


# =====================================================================
# PHONE VALIDATORS
# =====================================================================


def _strip_phone(raw: str) -> str:
    """Strip spaces, dashes, parentheses, dots from a phone string."""
    return re.sub(r"[\s\-\(\)\.\u200c\u200d]", "", raw)


def _extract_country_code(number: str) -> tuple[str, str]:
    """Return (country_code_digits, remaining_number) from a phone string.

    Handles +XXX, 00XXX, and bare-number forms.
    """
    digits = re.sub(r"[^\d]", "", number)
    if digits.startswith("00"):
        digits = digits[2:]
    # GCC codes are all 3 digits except 965 (Kuwait, also 3) and 966 (Saudi, 3)
    # All GCC codes: 971, 966, 974, 973, 968, 965 → all 3 digits
    for cc in sorted(GCC_COUNTRY_CODES.keys(), key=len, reverse=True):
        if digits.startswith(cc):
            return cc, digits[len(cc):]
    return "", digits


def validate_uae_phone(value: str) -> str:
    """Validate and normalise a UAE phone number.

    Accepts:
      - +971-5X-XXX-XXXX  (mobile)
      - +971-X-XXX-XXXX   (landline)
      - 800-XXX-XXXX       (toll-free)
      - 05X-XXX-XXXX       (local format, converts to +971)

    Returns the number in E.164 format: +971XXXXXXXXX
    """
    if not value:
        raise ValueError("Phone number cannot be empty")

    stripped = _strip_phone(value)
    digits = re.sub(r"[^\d+]", "", stripped)

    # Handle local format 05XXXXXXXX
    if digits.startswith("05") and len(digits) == 10:
        digits = "+971" + digits[1:]
    # Handle +971
    elif digits.startswith("+971") or digits.startswith("971"):
        if not digits.startswith("+"):
            digits = "+" + digits
    # Handle 800 toll-free (local)
    elif digits.startswith("800") and len(digits) == 9:
        digits = "+971" + digits
    else:
        raise ValueError(
            f"Invalid UAE phone format: '{value}'. "
            f"Expected +971-5X-XXX-XXXX (mobile), "
            f"+971-X-XXX-XXXX (landline), or 800-XXX-XXXX (toll-free)"
        )

    digit_part = digits[1:]  # strip +

    if digit_part.startswith("9715") and len(digit_part) == 12:
        # Mobile: +971 5X XXX XXXX
        prefix = digit_part[3:5]  # 50, 52, 54, 55, 56, 58
        if prefix not in UAE_MOBILE_PREFIXES:
            raise ValueError(
                f"Invalid UAE mobile prefix '{prefix}'. "
                f"Valid prefixes: {sorted(UAE_MOBILE_PREFIXES)}"
            )
    elif digit_part.startswith("971") and len(digit_part) == 11:
        # Landline: +971 X XXX XXXX
        area = digit_part[3]
        if area not in UAE_LANDLINE_AREA_CODES:
            raise ValueError(
                f"Invalid UAE landline area code '{area}'. "
                f"Valid codes: {sorted(UAE_LANDLINE_AREA_CODES)}"
            )
    elif digit_part.startswith("971800") and len(digit_part) == 12:
        # Toll-free: +971 800 XXX XXXX
        pass
    elif digit_part.startswith("971700") and len(digit_part) == 12:
        # Premium: +971 700 XXX XXXX
        pass
    else:
        raise ValueError(
            f"Invalid UAE phone number length/format: '{value}'. "
            f"Mobile=12 digits (+9715XXXXXXXX), "
            f"Landline=11 digits (+971XXXXXXXXX), "
            f"Toll-free=12 digits (+971800XXXXXX)"
        )

    return digits


def validate_saudi_phone(value: str) -> str:
    """Validate and normalise a Saudi phone number.

    Accepts: +966-5X-XXX-XXXX, 05X-XXX-XXXX (local)
    Returns E.164: +9665XXXXXXXX
    """
    if not value:
        raise ValueError("Phone number cannot be empty")

    stripped = _strip_phone(value)
    digits = re.sub(r"[^\d+]", "", stripped)

    if digits.startswith("05") and len(digits) == 10:
        digits = "+966" + digits[1:]
    elif digits.startswith("+966") or digits.startswith("966"):
        if not digits.startswith("+"):
            digits = "+" + digits
    else:
        raise ValueError(
            f"Invalid Saudi phone format: '{value}'. "
            f"Expected +966-5X-XXX-XXXX"
        )

    digit_part = digits[1:]
    if digit_part.startswith("9665") and len(digit_part) == 12:
        prefix = digit_part[3:5]
        if prefix not in SAUDI_MOBILE_PREFIXES:
            raise ValueError(
                f"Invalid Saudi mobile prefix '{prefix}'. "
                f"Valid prefixes: {sorted(SAUDI_MOBILE_PREFIXES)}"
            )
    elif digit_part.startswith("966") and len(digit_part) == 12:
        # Saudi landline: +966 XX XXX XXXX (area code 2 digits: 11, 12, 13, etc.)
        pass
    else:
        raise ValueError(f"Invalid Saudi phone number: '{value}'")

    return digits


def validate_gcc_phone(value: str) -> str:
    """Validate any GCC phone number and return E.164 format.

    Dispatches to country-specific validators.  Accepts all 6 GCC countries.
    """
    if not value:
        raise ValueError("Phone number cannot be empty")

    stripped = _strip_phone(value)
    digits = re.sub(r"[^\d+]", "", stripped)

    # Handle local format: leading 0
    if digits.startswith("0") and not digits.startswith("00"):
        local_digits = digits[1:]
        # Need country context; try to infer from length
        # UAE: 05XXXXXXXX (9 digits after 0) → +9715XXXXXXXX
        if local_digits.startswith("5") and len(local_digits) == 9:
            return validate_uae_phone("+971" + local_digits)
        # Note: Saudi also uses 05XXXXXXXX format (9 digits after 0).
        # Without explicit country context, we default to UAE as it's the
        # primary use-case. Callers needing Saudi should pass +966 prefix.

    cc, remaining = _extract_country_code(digits)

    if cc == "971":
        return validate_uae_phone(value)
    elif cc == "966":
        return validate_saudi_phone(value)
    elif cc == "974":
        # Qatar: +974 XXXX XXXX (mobile starts with 3/5/6/7)
        if len(remaining) in (8, 9):
            return "+" + cc + remaining
        raise ValueError(f"Invalid Qatar phone: '{value}'")
    elif cc == "973":
        # Bahrain: +973 XXXX XXXX (mobile starts with 3)
        if len(remaining) == 8:
            return "+" + cc + remaining
        raise ValueError(f"Invalid Bahrain phone: '{value}'")
    elif cc == "968":
        # Oman: +968 9XXX XXXX (mobile starts with 9)
        if len(remaining) == 8:
            return "+" + cc + remaining
        raise ValueError(f"Invalid Oman phone: '{value}'")
    elif cc == "965":
        # Kuwait: +965 XXXX XXXX (mobile starts with 5/6/8/9)
        if len(remaining) == 8:
            return "+" + cc + remaining
        raise ValueError(f"Invalid Kuwait phone: '{value}'")
    else:
        raise ValueError(
            f"Unrecognised GCC country code in phone: '{value}'. "
            f"Supported: +971 (UAE), +966 (SA), +974 (QA), "
            f"+973 (BH), +968 (OM), +965 (KW)"
        )


def infer_uae_carrier(e164: str) -> str:
    """Best-effort UAE carrier inference from E.164 number.

    Post-MNP (2019) this is a HINT only.  Use a carrier lookup API
    for authoritative results.
    """
    digit_part = e164.lstrip("+")
    if not digit_part.startswith("971"):
        return "unknown"

    subscriber = digit_part[3:]  # everything after 971

    if subscriber.startswith("5"):
        prefix = subscriber[0:2]  # e.g. "50", "55" — the mobile prefix after "5"
        if prefix in ETISALAT_MOBILE_PREFIXES:
            return "etisalat"
        elif prefix in DU_MOBILE_PREFIXES:
            return "du"
        elif prefix in SHARED_MOBILE_PREFIXES:
            return "unknown"  # shared prefix — cannot determine without API
        else:
            return "unknown"
    elif subscriber.startswith("800") or subscriber.startswith("900"):
        return "tollfree"
    elif subscriber.startswith("700"):
        return "premium"
    elif subscriber[0] in UAE_LANDLINE_AREA_CODES:
        return "etisalat"  # Etisalat has landline monopoly
    return "unknown"


def infer_uae_emirate(e164: str) -> str | None:
    """Infer emirate from a UAE landline number. Returns None for mobile."""
    digit_part = e164.lstrip("+")
    if not digit_part.startswith("971"):
        return None
    subscriber = digit_part[3:]
    if subscriber.startswith("5") or subscriber.startswith("800"):
        return None  # mobile / toll-free — no emirate mapping
    area_code = subscriber[0]
    return UAE_AREA_CODE_TO_EMIRATE.get(area_code)


def is_uae_mobile(e164: str) -> bool:
    """Check if a UAE E.164 number is mobile."""
    digit_part = e164.lstrip("+")
    return digit_part.startswith("9715")


def is_uae_whatsapp_likely(e164: str) -> bool:
    """Heuristic: UAE mobile numbers are very likely to have WhatsApp.

    WhatsApp is THE primary recruiter communication channel in GCC.
    """
    return is_uae_mobile(e164)


# =====================================================================
# EMAIL VALIDATORS
# =====================================================================


def validate_email(value: str) -> str:
    """Basic email syntax validation. Returns lowercased email."""
    if not value:
        raise ValueError("Email cannot be empty")
    value = value.strip().lower()
    if not EMAIL_REGEX.match(value):
        raise ValueError(f"Invalid email format: '{value}'")
    return value


def is_uae_domain(domain: str) -> bool:
    """Check if a domain uses a UAE TLD."""
    domain = domain.lower().strip()
    return bool(UAE_DOMAIN_PATTERN.match(domain))


def is_m365_domain(domain: str) -> bool:
    """Check if a domain's MX records point to Microsoft 365.

    M365 MX records contain patterns like:
    - *.mail.protection.outlook.com
    - *.eurprd05.prod.outlook.com
    - *.apcprd05.prod.outlook.com

    Returns False if MX lookup fails (network error, no MX records, etc.)
    """
    try:
        import dns.resolver

        mx_records = dns.resolver.resolve(domain, "MX")
        for record in mx_records:
            exchange = str(record.exchange).lower()
            for fingerprint in MX_M365_FINGERPRINTS:
                if fingerprint in exchange:
                    return True
        return False
    except Exception:
        return False


# =====================================================================
# LINKEDIN VALIDATOR
# =====================================================================


def validate_linkedin_url(value: str) -> str:
    """Validate and normalise a LinkedIn profile URL."""
    if not value:
        raise ValueError("LinkedIn URL cannot be empty")
    value = value.strip()
    if not LINKEDIN_URL_PATTERN.match(value):
        raise ValueError(
            f"Invalid LinkedIn URL: '{value}'. "
            f"Expected format: https://linkedin.com/in/username"
        )
    # Normalise: ensure no trailing slash
    return value.rstrip("/")


# =====================================================================
# ARABIC NAME NORMALISER
# =====================================================================

# Prefixes to handle in Arabic names
ARABIC_PREFIXES: list[str] = [
    "al ", "al-", "el ", "el-",
    "bin ", "bin-", "bint ", "bint-",
    "ibn ", "ibn-",
    "abdul ", "abdul-",
    "abd ", "abd-",
]

# Mohammed variant spellings
MOHAMMED_VARIANTS: set[str] = {
    "mohammed", "mohammad", "muhammad", "mohamed",
    "mohamad", "muhamed", "mohd", "mhmd", "mhd",
    "muhmmad", "mohammd", "muhamad",
}

# Prefixes to strip for "al_el_bin_removed" form
PREFIXES_TO_STRIP: list[str] = [
    "al ", "al-", "el ", "el-",
    "bin ", "bin-", "bint ", "bint-",
    "ibn ", "ibn-",
]

# Common transliteration variants map (char → possible replacements)
TRANSLITERATION_MAP: dict[str, list[str]] = {
    "kh": ["kh", "ch", "h"],
    "sh": ["sh", "ch"],
    "gh": ["gh", "g"],
    "ou": ["ou", "u", "oo"],
    "aa": ["aa", "a"],
    "ie": ["ie", "i", "y"],
    "q": ["q", "k", "c"],
    "j": ["j", "g"],
    "y": ["y", "i", "j"],
    "h": ["h", "hh"],
}


def _strip_diacritics(text: str) -> str:
    """Remove Arabic diacritics and normalise Unicode."""
    # NFD decomposition then strip combining marks
    normalised = unicodedata.normalize("NFD", text)
    return "".join(
        ch for ch in normalised
        if unicodedata.category(ch) != "Mn"
    )


def normalize_arabic_name(name: str) -> str:
    """Normalise an Arabic/Romanised Arabic name to canonical lowercase form."""
    name = name.strip().lower()
    name = _strip_diacritics(name)
    # Collapse multiple spaces
    name = re.sub(r"\s+", " ", name)
    return name


def generate_name_variants(name: str) -> list[str]:
    """Generate common spelling variants of an Arabic name."""
    name = normalize_arabic_name(name)
    variants: set[str] = {name}

    parts = name.split()
    if not parts:
        return [name]

    # Mohammed compression: replace first occurrence of any Mohammed variant with "m"
    for variant in MOHAMMED_VARIANTS:
        if parts[0] == variant:
            variants.add("m " + " ".join(parts[1:]))
            variants.add("mohd " + " ".join(parts[1:]))
            break
        elif len(parts) > 1 and parts[1] == variant:
            first = parts[0]
            variants.add(first + " m " + " ".join(parts[2:]))
            variants.add(first + " mohd " + " ".join(parts[2:]))
            break

    # Prefix-stripped form
    # Try stripping Al/El/Bin/Bint from ALL parts, not just the start
    # Normalise hyphens to spaces for consistent matching
    normalised_for_strip = name.replace("-", " ")
    stripped = normalised_for_strip
    for prefix in PREFIXES_TO_STRIP:
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix):]
            break
    if stripped != normalised_for_strip and stripped.strip():
        variants.add(stripped.strip())
    # Also try removing Al/El from middle of name
    parts = normalised_for_strip.split()
    filtered_parts = []
    for p in parts:
        if p.lower() not in ("al", "el", "bin", "bint", "ibn"):
            filtered_parts.append(p)
    if filtered_parts != parts:
        variants.add(" ".join(filtered_parts))

    return sorted(variants)


def generate_email_permutations(
    first_name: str,
    last_name: str,
    domain: str,
    middle_name: str | None = None,
) -> list[str]:
    """Generate likely email permutations for an Arabic name at a given domain.

    Uses the dominant firstname.lastname pattern plus common alternatives.
    Returns deduplicated list.
    """
    first = normalize_arabic_name(first_name).replace(" ", "")
    last = normalize_arabic_name(last_name).replace(" ", "")
    middle = normalize_arabic_name(middle_name).replace(" ", "") if middle_name else ""
    domain = domain.lower().strip().lstrip("@")

    # Also generate with Mohammed compressed
    first_variants: set[str] = {first}
    for variant in MOHAMMED_VARIANTS:
        if first.startswith(variant):
            first_variants.add("m" + first[len(variant):])
            first_variants.add("mohd" + first[len(variant):])

    emails: set[str] = set()

    for f in first_variants:
        emails.add(f"{f}.{last}@{domain}")
        emails.add(f"{f}{last}@{domain}")
        emails.add(f"{f}_{last}@{domain}")
        emails.add(f"{f[0]}{last}@{domain}")         # flast
        emails.add(f"{f}{last[0]}@{domain}")          # firstl
        emails.add(f"{f}@{domain}")                    # firstname only
        emails.add(f"{last}.{f}@{domain}")             # last.first
        if middle:
            emails.add(f"{f}.{middle[0]}.{last}@{domain}")
            emails.add(f"{f}{middle[0]}{last}@{domain}")

    return sorted(emails)


# =====================================================================
# UAE DOMAIN VALIDATOR
# =====================================================================


class UAEDomainValidator:
    """Validates and categorises UAE domain names."""

    UAE_TLDS: tuple[str, ...] = (
        ".ae", ".co.ae", ".com.ae", ".gov.ae", ".ac.ae",
        ".org.ae", ".net.ae", ".sch.ae",
    )

    @classmethod
    def is_uae_domain(cls, domain: str) -> bool:
        d = domain.lower().strip()
        return any(d.endswith(tld) for tld in cls.UAE_TLDS)

    @classmethod
    def categorise(cls, domain: str) -> str:
        d = domain.lower().strip()
        if d.endswith(".gov.ae"):
            return "government"
        elif d.endswith(".ac.ae"):
            return "education"
        elif d.endswith(".sch.ae"):
            return "school"
        elif d.endswith(".org.ae"):
            return "nonprofit"
        elif d.endswith((".co.ae", ".com.ae")):
            return "commercial"
        elif d.endswith(".net.ae"):
            return "network"
        elif d.endswith(".ae"):
            return "generic_ae"
        return "non_uae"


# =====================================================================
# ARABIC NAME NORMALISER (stateless utility)
# =====================================================================


class ArabicNameNormalizer:
    """Stateless helper that encapsulates Arabic name processing logic."""

    @staticmethod
    def normalize(name: str) -> str:
        return normalize_arabic_name(name)

    @staticmethod
    def variants(name: str) -> list[str]:
        return generate_name_variants(name)

    @staticmethod
    def email_permutations(
        first_name: str,
        last_name: str,
        domain: str,
        middle_name: str | None = None,
    ) -> list[str]:
        return generate_email_permutations(first_name, last_name, domain, middle_name)

    @staticmethod
    def strip_prefixes(name: str) -> str:
        stripped = normalize_arabic_name(name).replace("-", " ")
        for prefix in PREFIXES_TO_STRIP:
            if stripped.startswith(prefix):
                stripped = stripped[len(prefix):]
                break
        # Also remove Al/El/Bin from anywhere in the name
        parts = stripped.split()
        filtered = [p for p in parts if p.lower() not in ("al", "el", "bin", "bint", "ibn")]
        return " ".join(filtered) if filtered else stripped.strip()


# =====================================================================
# GCC TELECOM DB (carrier prefix lookup)
# =====================================================================


@dataclass(frozen=True)
class CarrierInfo:
    carrier: str
    country: str
    number_type: str
    emirate: str | None = None
    mnp_note: str | None = None


class GCCTelecomDB:
    """Lookup utility for GCC carrier information based on number prefix."""

    @staticmethod
    def lookup(e164: str) -> CarrierInfo:
        digit_part = e164.lstrip("+")
        cc, remaining = _extract_country_code(digit_part)

        if cc == "971":
            return GCCTelecomDB._lookup_uae(cc, remaining)
        elif cc == "966":
            return CarrierInfo(carrier="unknown", country="SA", number_type="mobile")
        else:
            return CarrierInfo(
                carrier="unknown",
                country=GCC_COUNTRY_CODES.get(cc, "XX"),
                number_type="unknown",
            )

    @staticmethod
    def _lookup_uae(cc: str, remaining: str) -> CarrierInfo:
        if remaining.startswith("5"):
            prefix = remaining[0:3]  # e.g. "50X"
            carrier = infer_uae_carrier("+" + cc + remaining)
            return CarrierInfo(
                carrier=carrier,
                country="AE",
                number_type="mobile",
                emirate=None,
                mnp_note="Post-MNP (2019): carrier is hint only, use API for accuracy",
            )
        elif remaining.startswith("800") or remaining.startswith("900"):
            return CarrierInfo(carrier="tollfree", country="AE", number_type="tollfree")
        elif remaining.startswith("700"):
            return CarrierInfo(carrier="premium", country="AE", number_type="premium")
        else:
            emirate = UAE_AREA_CODE_TO_EMIRATE.get(remaining[0])
            return CarrierInfo(
                carrier="etisalat",
                country="AE",
                number_type="landline",
                emirate=emirate,
            )


# =====================================================================
# UAE EMAIL PATTERN INFERENCE
# =====================================================================


def infer_email_pattern(sample_emails: list[str]) -> str | None:
    """Given sample emails from the same domain, infer the pattern.

    Returns one of the keys from EMAIL_PATTERN_TEMPLATES, or None.
    """
    if not sample_emails:
        return None

    patterns_seen: dict[str, int] = {}
    for email in sample_emails:
        local = email.split("@")[0].lower()
        if "." in local and "_" not in local:
            parts = local.split(".")
            if len(parts) == 2:
                patterns_seen["firstname_lastname"] = patterns_seen.get("firstname_lastname", 0) + 1
            elif len(parts) == 3:
                patterns_seen["first_m_last"] = patterns_seen.get("first_m_last", 0) + 1
        elif "_" in local:
            patterns_seen["first_last"] = patterns_seen.get("first_last", 0) + 1
        elif len(local) <= 8 and local.isalpha():
            patterns_seen["firstname"] = patterns_seen.get("firstname", 0) + 1
        else:
            patterns_seen["other"] = patterns_seen.get("other", 0) + 1

    if not patterns_seen:
        return None

    # Return the most common pattern
    return max(patterns_seen, key=patterns_seen.get)  # type: ignore[arg-type]
