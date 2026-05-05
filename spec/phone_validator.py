"""
Phone Validation Pipeline — UAE/GCC-Optimized
==============================================
Multi-step phone validation with:
  - E.164 normalization
  - UAE/GCC carrier detection
  - WhatsApp number verification
  - Line type detection (mobile/landline/VoIP)
  - Twilio Lookup v2 + Abstract API backup

GCC Country Codes & Prefixes:
  UAE:       +971  (mobile: 50, 52, 54, 55, 56, 58)
  Saudi:     +966  (mobile: 50, 53, 54, 55, 59)
  Qatar:     +974  (mobile: 3, 5, 6, 7)
  Kuwait:    +965  (mobile: 5, 6, 9)
  Bahrain:   +973  (mobile: 3)
  Oman:      +968  (mobile: 7, 9)
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import phonenumbers
from phonenumbers import PhoneNumberFormat, PhoneNumberType


# ---------------------------------------------------------------------------
# Constants & Lookup Tables
# ---------------------------------------------------------------------------

class GCCCountry(Enum):
    UAE = "AE"
    SAUDI_ARABIA = "SA"
    QATAR = "QA"
    KUWAIT = "KW"
    BAHRAIN = "BH"
    OMAN = "OM"


# GCC country code → calling code
GCC_CALLING_CODES: dict[GCCCountry, int] = {
    GCCCountry.UAE: 971,
    GCCCountry.SAUDI_ARABIA: 966,
    GCCCountry.QATAR: 974,
    GCCCountry.KUWAIT: 965,
    GCCCountry.BAHRAIN: 973,
    GCCCountry.OMAN: 968,
}

# Reverse lookup: calling code → GCC country
CALLING_CODE_TO_COUNTRY: dict[int, GCCCountry] = {
    v: k for k, v in GCC_CALLING_CODES.items()
}

# UAE mobile number prefixes (after +971)
UAE_MOBILE_PREFIXES: set[str] = {"50", "52", "54", "55", "56", "58"}

# UAE carrier → prefix mapping (best-effort, number portability exists)
UAE_CARRIER_MAP: dict[str, str] = {
    "50": "Etisalat",
    "52": "du",
    "54": "Etisalat",
    "55": "du",
    "56": "Etisalat",
    "58": "Virgin Mobile (du MVNO)",
}

# UAE landline area codes
UAE_LANDLINE_PREFIXES: dict[str, str] = {
    "2": "Abu Dhabi",
    "3": "Al Ain",
    "4": "Dubai",
    "6": "Sharjah/Ajman/Umm Al Quwain",
    "7": "Ras Al Khaimah/Fujairah",
    "9": "Fujairah",
}

# Saudi mobile prefixes (after +966)
SAUDI_MOBILE_PREFIXES: set[str] = {"50", "53", "54", "55", "59"}

# Qatar mobile prefixes (after +974, single digit)
QATAR_MOBILE_PREFIXES: set[str] = {"3", "5", "6", "7"}

# Kuwait mobile prefixes (after +965, single digit)
KUWAIT_MOBILE_PREFIXES: set[str] = {"5", "6", "9"}

# Bahrain mobile prefixes (after +973)
BAHRAIN_MOBILE_PREFIXES: set[str] = {"3"}

# Oman mobile prefixes (after +968)
OMAN_MOBILE_PREFIXES: set[str] = {"7", "9"}

# Aggregated: country → mobile prefixes
GCC_MOBILE_PREFIXES: dict[GCCCountry, set[str]] = {
    GCCCountry.UAE: UAE_MOBILE_PREFIXES,
    GCCCountry.SAUDI_ARABIA: SAUDI_MOBILE_PREFIXES,
    GCCCountry.QATAR: QATAR_MOBILE_PREFIXES,
    GCCCountry.KUWAIT: KUWAIT_MOBILE_PREFIXES,
    GCCCountry.BAHRAIN: BAHRAIN_MOBILE_PREFIXES,
    GCCCountry.OMAN: OMAN_MOBILE_PREFIXES,
}


class LineType(Enum):
    MOBILE = "mobile"
    LANDLINE = "landline"
    VOIP = "voip"
    TOLL_FREE = "toll_free"
    PREMIUM = "premium"
    UNKNOWN = "unknown"


class PhoneStatus(Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    FORMAT_INVALID = "FORMAT_INVALID"
    POSSIBLE = "POSSIBLE"  # Valid format but not verified
    WHATSAPP_CONFIRMED = "WHATSAPP_CONFIRMED"
    WHATSAPP_NOT_FOUND = "WHATSAPP_NOT_FOUND"
    GCC_OUTSIDE_REGION = "GCC_OUTSIDE_REGION"


class GCCRegion(Enum):
    UAE = "UAE"
    SAUDI_ARABIA = "SAUDI_ARABIA"
    QATAR = "QATAR"
    KUWAIT = "KUWAIT"
    BAHRAIN = "BAHRAIN"
    OMAN = "OMAN"
    NON_GCC = "NON_GCC"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class PhoneValidationResult:
    """Complete phone validation result."""
    raw_input: str
    e164: str = ""
    national_format: str = ""
    international_format: str = ""
    country_code: int = 0
    region: GCCRegion = GCCRegion.NON_GCC
    status: PhoneStatus = PhoneStatus.INVALID
    line_type: LineType = LineType.UNKNOWN
    carrier: str = ""
    is_gcc: bool = False
    is_uae: bool = False
    is_mobile: bool = False
    whatsapp_confirmed: bool = False
    whatsapp_checked: bool = False
    twilio_lookup_done: bool = False
    twilio_carrier: str = ""
    twilio_line_type: str = ""
    abstract_verified: bool = False
    confidence: float = 0.0
    validated_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Tier 1: Format Validation + E.164 Normalization
# ---------------------------------------------------------------------------

def normalize_phone(raw: str) -> Optional[phonenumbers.PhoneNumber]:
    """
    Parse and normalize a phone number using libphonenumbers.

    Handles:
      - +971501234567
      - 00971501234567
      - 0501234567 (UAE local)
      - +971 50 123 4567
      - +971-50-123-4567
      - (+971) 50 123 4567
    """
    # Strip common non-numeric prefixes
    cleaned = re.sub(r"[^\d+]", "", raw)

    # Handle 00 prefix (international)
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]

    # UAE local format: 050/052/054/055/056/058 followed by 7 digits
    if re.match(r"^0(50|52|54|55|56|58)\d{7}$", cleaned):
        cleaned = "+971" + cleaned[1:]

    # GCC local formats (leading 0)
    gcc_local_patterns = [
        (r"^05\d{8}$", "+966"),  # Saudi
        (r"^\d{8}$", "+974"),     # Qatar (no leading 0)
        (r"^\d{8}$", "+965"),     # Kuwait (no leading 0)
        (r"^\d{8}$", "+973"),     # Bahrain
        (r"^9\d{7}$", "+968"),    # Oman
    ]

    try:
        # Try parsing as international first
        parsed = phonenumbers.parse(cleaned, None)
        if phonenumbers.is_valid_number(parsed):
            return parsed
    except phonenumbers.NumberParseException:
        pass

    # Try parsing with UAE default region
    try:
        parsed = phonenumbers.parse(raw, "AE")
        if phonenumbers.is_valid_number(parsed):
            return parsed
    except phonenumbers.NumberParseException:
        pass

    # Try other GCC regions
    for country in GCCCountry:
        try:
            parsed = phonenumbers.parse(raw, country.value)
            if phonenumbers.is_valid_number(parsed):
                return parsed
        except phonenumbers.NumberParseException:
            continue

    return None


def detect_line_type(parsed: phonenumbers.PhoneNumber) -> LineType:
    """Detect line type from parsed phone number."""
    number_type = phonenumbers.number_type(parsed)
    type_map = {
        PhoneNumberType.MOBILE: LineType.MOBILE,
        PhoneNumberType.FIXED_LINE: LineType.LANDLINE,
        PhoneNumberType.FIXED_LINE_OR_MOBILE: LineType.MOBILE,  # Default to mobile for GCC
        PhoneNumberType.TOLL_FREE: LineType.TOLL_FREE,
        PhoneNumberType.PREMIUM_RATE: LineType.PREMIUM,
        PhoneNumberType.VOIP: LineType.VOIP,
    }
    return type_map.get(number_type, LineType.UNKNOWN)


def detect_gcc_carrier(parsed: phonenumbers.PhoneNumber) -> tuple[str, GCCRegion]:
    """
    Detect carrier and GCC region from phone number.

    Returns (carrier_name, gcc_region).
    For UAE: Etisalat/du/Virgin Mobile.
    For other GCC: returns generic carrier or empty string.
    """
    calling_code = parsed.country_code
    national = str(parsed.national_number)

    # Determine region
    region_enum = CALLING_CODE_TO_COUNTRY.get(calling_code, None)
    if region_enum is None:
        return "", GCCRegion.NON_GCC

    gcc_region = GCCRegion[region_enum.name]

    # UAE carrier detection
    if region_enum == GCCCountry.UAE:
        prefix = national[:2]
        # Check mobile prefixes
        if prefix in UAE_CARRIER_MAP:
            return UAE_CARRIER_MAP[prefix], gcc_region
        # Check landline
        area = national[:1]
        if area in UAE_LANDLINE_PREFIXES:
            return f"Landline ({UAE_LANDLINE_PREFIXES[area]})", gcc_region
        return "Unknown UAE carrier", gcc_region

    # Other GCC: generic carrier detection
    mobile_prefixes = GCC_MOBILE_PREFIXES.get(region_enum, set())
    if mobile_prefixes:
        for prefix_len in [2, 1]:
            if national[:prefix_len] in mobile_prefixes:
                return f"Mobile ({region_enum.name})", gcc_region

    return f"Unknown ({region_enum.name})", gcc_region


def run_tier1(raw_phone: str) -> PhoneValidationResult:
    """
    Execute Tier 1: Format validation + E.164 normalization.

    Uses libphonenumbers for robust parsing across all GCC formats.
    """
    result = PhoneValidationResult(raw_input=raw_phone)

    parsed = normalize_phone(raw_phone)
    if parsed is None:
        result.status = PhoneStatus.FORMAT_INVALID
        return result

    # Format outputs
    result.e164 = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
    result.national_format = phonenumbers.format_number(
        parsed, PhoneNumberFormat.NATIONAL
    )
    result.international_format = phonenumbers.format_number(
        parsed, PhoneNumberFormat.INTERNATIONAL
    )
    result.country_code = parsed.country_code

    # Check if valid number
    if not phonenumbers.is_valid_number(parsed):
        result.status = PhoneStatus.FORMAT_INVALID
        return result

    # Detect line type
    result.line_type = detect_line_type(parsed)

    # Detect GCC carrier + region
    carrier, region = detect_gcc_carrier(parsed)
    result.carrier = carrier
    result.region = region
    result.is_gcc = region != GCCRegion.NON_GCC
    result.is_uae = region == GCCRegion.UAE

    # Is mobile? (critical for WhatsApp check)
    mobile_prefixes = GCC_MOBILE_PREFIXES.get(
        CALLING_CODE_TO_COUNTRY.get(parsed.country_code, GCCCountry.UAE),
        set(),
    )
    national = str(parsed.national_number)
    result.is_mobile = any(
        national[:len(p)] == p for p in mobile_prefixes
    )
    # Also use libphonenumbers type
    if result.line_type == LineType.MOBILE:
        result.is_mobile = True

    result.status = PhoneStatus.POSSIBLE
    return result


# ---------------------------------------------------------------------------
# Tier 2: WhatsApp Verification
# ---------------------------------------------------------------------------

async def check_whatsapp(e164_number: str) -> bool:
    """
    Verify if a phone number has WhatsApp by checking wa.me redirect.

    Strategy:
      1. GET https://wa.me/{phone} (no country code prefix +)
      2. If 200 and response contains WhatsApp-specific content → active
      3. If redirect to "Chat not found" → no WhatsApp

    Uses the wa.me short link which returns different behavior for
    registered vs unregistered numbers.
    """
    import aiohttp

    phone_digits = e164_number.lstrip("+")
    url = f"https://wa.me/{phone_digits}"

    try:
        async with aiohttp.ClientSession(
            allow_redirects=False,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as session:
            async with session.get(
                url,
                headers={"user-agent": "Mozilla/5.0"},
            ) as resp:
                if resp.status == 302:
                    location = resp.headers.get("Location", "")
                    # Redirect to web.whatsapp.com = number has WhatsApp
                    if "web.whatsapp.com" in location or "api.whatsapp.com" in location:
                        return True
                    # Redirect to "Phone number shared via url" = may or may not exist
                    if "wa.me" in location:
                        return False
                elif resp.status == 200:
                    text = await resp.text()
                    # WhatsApp page with "Chat with" = number active
                    if "Chat with" in text or "whatsapp" in text.lower():
                        return True
                return False
    except Exception:
        return False


async def run_tier2(result: PhoneValidationResult) -> PhoneValidationResult:
    """
    Execute Tier 2: WhatsApp verification.

    Only checks mobile numbers (WhatsApp requires mobile).
    """
    if not result.is_mobile or not result.e164:
        result.whatsapp_checked = True
        result.whatsapp_confirmed = False
        return result

    result.whatsapp_confirmed = await check_whatsapp(result.e164)
    result.whatsapp_checked = True

    if result.whatsapp_confirmed:
        result.status = PhoneStatus.WHATSAPP_CONFIRMED

    return result


# ---------------------------------------------------------------------------
# Tier 3: Twilio Lookup + Abstract API
# ---------------------------------------------------------------------------

async def twilio_lookup(
    e164_number: str, account_sid: str, auth_token: str
) -> Optional[dict]:
    """
    Twilio Lookup v2 — carrier + line type detection.

    Cost: $0.01/query
    UAE supported: Yes
    Returns: carrier name, line type, caller name (if available).
    """
    import aiohttp
    import base64

    url = f"https://lookups.twilio.com/v2/PhoneNumbers/{e164_number}"
    creds = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
    headers = {"Authorization": f"Basic {creds}"}
    params = {"Fields": "line_type_intelligence,caller_name"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
    except Exception:
        return None


async def abstract_api_lookup(e164_number: str, api_key: str) -> Optional[dict]:
    """
    Abstract API phone validation.

    Free: 100/month
    UAE supported: Yes
    Returns: valid, carrier, line_type, location.
    """
    import aiohttp

    url = (
        f"https://phonevalidation.abstractapi.com/v1/"
        f"?api_key={api_key}&phone={e164_number}"
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
    except Exception:
        return None


TWILIO_LINE_TYPE_MAP: dict[str, LineType] = {
    "landline": LineType.LANDLINE,
    "mobile": LineType.MOBILE,
    "voip": LineType.VOIP,
    "toll_free": LineType.TOLL_FREE,
    "premium": LineType.PREMIUM,
}


async def run_tier3(
    result: PhoneValidationResult,
    twilio_sid: str = "",
    twilio_token: str = "",
    abstract_key: str = "",
) -> PhoneValidationResult:
    """
    Execute Tier 3: External API validation.

    Priority:
      1. Twilio Lookup v2 ($0.01/query) — most accurate carrier/line type
      2. Abstract API (100/mo free) — backup validation
    """
    if not result.e164:
        return result

    # Twilio Lookup
    if twilio_sid and twilio_token:
        twilio_data = await twilio_lookup(result.e164, twilio_sid, twilio_token)
        if twilio_data:
            result.twilio_lookup_done = True
            result.twilio_carrier = twilio_data.get("line_type_intelligence", {}).get(
                "carrier_name", ""
            )
            twilio_type = twilio_data.get("line_type_intelligence", {}).get(
                "type", ""
            )
            result.twilio_line_type = twilio_type
            if twilio_type in TWILIO_LINE_TYPE_MAP:
                result.line_type = TWILIO_LINE_TYPE_MAP[twilio_type]

            # Override carrier if Twilio provides it
            if result.twilio_carrier:
                result.carrier = result.twilio_carrier

            # If Twilio confirms valid, upgrade status
            if twilio_data.get("valid", False):
                if result.status == PhoneStatus.POSSIBLE:
                    result.status = PhoneStatus.VALID

    # Abstract API backup
    if abstract_key and not result.twilio_lookup_done:
        abstract_data = await abstract_api_lookup(result.e164, abstract_key)
        if abstract_data:
            result.abstract_verified = abstract_data.get("valid", False)
            if result.abstract_verified and result.status == PhoneStatus.POSSIBLE:
                result.status = PhoneStatus.VALID

            # Use Abstract carrier if we don't have one
            if not result.carrier:
                result.carrier = abstract_data.get("carrier", "")

    return result


# ---------------------------------------------------------------------------
# Main Pipeline Orchestrator
# ---------------------------------------------------------------------------

@dataclass
class PhonePipelineConfig:
    """Configuration for phone validation pipeline."""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    abstract_api_key: str = ""
    check_whatsapp: bool = True
    check_carrier: bool = True


class PhoneValidationPipeline:
    """
    Multi-step Phone Validation Pipeline for UAE/GCC numbers.

    Usage:
        pipeline = PhoneValidationPipeline(config)
        result = await pipeline.validate("+971501234567")
    """

    def __init__(self, config: PhonePipelineConfig | None = None) -> None:
        self.config = config or PhonePipelineConfig()

    async def validate(self, raw_phone: str) -> PhoneValidationResult:
        """
        Run the full phone validation pipeline.

        Tier 1: Format validation + E.164 normalization (instant)
        Tier 2: WhatsApp verification (2-5s, mobile only)
        Tier 3: Twilio/Abstract API carrier validation (~200ms)
        """
        # Tier 1: Format + Normalization
        result = run_tier1(raw_phone)

        if result.status == PhoneStatus.FORMAT_INVALID:
            return result

        # Tier 2: WhatsApp check
        if self.config.check_whatsapp and result.is_mobile:
            result = await run_tier2(result)

        # Tier 3: External API validation
        if self.config.check_carrier:
            result = await run_tier3(
                result,
                twilio_sid=self.config.twilio_account_sid,
                twilio_token=self.config.twilio_auth_token,
                abstract_key=self.config.abstract_api_key,
            )

        # Calculate final confidence
        result.confidence = self._calculate_confidence(result)
        result.validated_at = time.time()

        return result

    async def verify_record(self, phone_record: "PhoneRecord") -> "PhoneRecord":
        """
        Verify a PhoneRecord (Pydantic model) and return it updated.

        Adapts between the spec-layer pipeline and the Pydantic PhoneRecord
        model used by the orchestrator.

        Updates:
          - validation_status  → mapped from PhoneStatus
          - carrier            → from pipeline result
          - line_type          → mapped from spec LineType
          - is_whatsapp        → from WhatsApp check
          - country_code       → from GCC region detection
        """
        from datetime import datetime, timezone
        from models.enums import VerificationStatus, VerificationMethod, PhoneType

        try:
            result = await self.validate(phone_record.phone)

            # Map PhoneStatus → VerificationStatus
            status_map = {
                PhoneStatus.VALID: VerificationStatus.API_VALID,
                PhoneStatus.POSSIBLE: VerificationStatus.SYNTAX_VALID,
                PhoneStatus.WHATSAPP_CONFIRMED: VerificationStatus.API_VALID,
                PhoneStatus.FORMAT_INVALID: VerificationStatus.INVALID,
                PhoneStatus.INVALID: VerificationStatus.INVALID,
            }
            phone_record.validation_status = status_map.get(
                result.status, VerificationStatus.UNVERIFIED
            )

            # Update carrier
            if result.carrier:
                phone_record.carrier = result.carrier

            # Map LineType → PhoneType
            line_type_map = {
                LineType.MOBILE: PhoneType.MOBILE,
                LineType.LANDLINE: PhoneType.LANDLINE,
                LineType.VOIP: PhoneType.UNKNOWN,
                LineType.TOLL_FREE: PhoneType.TOLLFREE,
                LineType.PREMIUM: PhoneType.PREMIUM,
            }
            phone_record.line_type = line_type_map.get(
                result.line_type, PhoneType.UNKNOWN
            )

            # WhatsApp
            phone_record.is_whatsapp = result.whatsapp_confirmed

            # Country code from GCC region
            region_to_country = {
                GCCRegion.UAE: "AE",
                GCCRegion.SAUDI_ARABIA: "SA",
                GCCRegion.QATAR: "QA",
                GCCRegion.KUWAIT: "KW",
                GCCRegion.BAHRAIN: "BH",
                GCCRegion.OMAN: "OM",
            }
            if result.region in region_to_country:
                phone_record.country_code = region_to_country[result.region]

        except Exception:
            pass  # Return record unchanged on failure

        return phone_record

    async def validate_batch(
        self, phones: list[str]
    ) -> list[PhoneValidationResult]:
        """Validate a batch of phone numbers with concurrency limit."""
        sem = asyncio.Semaphore(10)

        async def _limited_validate(phone: str) -> PhoneValidationResult:
            async with sem:
                return await self.validate(phone)

        return await asyncio.gather(*[_limited_validate(p) for p in phones])

    @staticmethod
    def _calculate_confidence(result: PhoneValidationResult) -> float:
        """
        Calculate phone-specific confidence score.

        Formula:
          base = 0.0
          + 0.05 if format valid (E.164 parseable)
          + 0.05 if carrier detected
          + 0.10 if WhatsApp confirmed
          + 0.05 if GCC region
          + 0.05 if Twilio verified
          + 0.05 if mobile (vs landline)
        Max = 0.35 (combined with email + source + profile = total ≤ 1.0)
        """
        score = 0.0

        if result.status not in (PhoneStatus.FORMAT_INVALID, PhoneStatus.INVALID):
            score += 0.05  # format valid

        if result.carrier:
            score += 0.05

        if result.whatsapp_confirmed:
            score += 0.10

        if result.is_gcc:
            score += 0.05

        if result.twilio_lookup_done:
            score += 0.05

        if result.is_mobile:
            score += 0.05

        return min(0.35, score)
