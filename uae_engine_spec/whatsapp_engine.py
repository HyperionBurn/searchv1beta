"""
WhatsAppEngine — WhatsApp number detection and enrichment for UAE/GCC.

Provides:
- WhatsApp account detection via wa.me link resolution
- Business profile extraction
- wa.me link generation
- Batch checking with rate limiting
- Legal compliance warnings

IMPORTANT LEGAL NOTES:
- Checking WhatsApp via wa.me may violate WhatsApp/Meta ToS.
- UAE Federal Decree-Law No. 34/2021 (Cybercrime Law) criminalizes
  unauthorized access to information systems and data collection.
- This tool is for PERSONAL, NON-COMMERCIAL research only.
- Do NOT use for spam, unsolicited bulk messaging, or commercial
  lead generation.
- Always obtain consent before contacting recruiters via WhatsApp.

Production-grade: no placeholders.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Compliance & Legal
# ---------------------------------------------------------------------------

LEGAL_DISCLAIMER: str = """
╔══════════════════════════════════════════════════════════════════════╗
║                     ⚠️  LEGAL DISCLAIMER ⚠️                        ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  WhatsApp number checking uses wa.me link resolution which may       ║
║  violate WhatsApp/Meta Terms of Service.                             ║
║                                                                      ║
║  UAE CYBERCRIME LAW (Federal Decree-Law No. 34/2021):               ║
║  • Unauthorized access to information systems is criminalized        ║
║  • Automated data collection may constitute a criminal offense       ║
║  • Penalties include imprisonment and fines up to AED 3,000,000     ║
║                                                                      ║
║  This tool is for PERSONAL, NON-COMMERCIAL use only.                ║
║  Do NOT use for:                                                     ║
║  • Spam or unsolicited bulk messaging                                ║
║  • Commercial lead generation                                        ║
║  • Reselling or redistributing contact data                          ║
║                                                                      ║
║  Always obtain explicit consent before contacting anyone via         ║
║  WhatsApp.                                                           ║
╚══════════════════════════════════════════════════════════════════════╝
"""

PERSONAL_USE_DISCLAIMER: str = (
    "This tool is designed for personal job-search research only. "
    "All data collected must be deleted within 90 days. "
    "Do not share, sell, or redistribute contact information."
)


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------

# WhatsApp rate limits:
# - wa.me: max ~1 request/second to avoid IP blocking
# - Recommended: 1 req/5 sec for sustained use
# - Batch: 12 requests/minute max

RATE_LIMIT_SECONDS: float = 5.0       # Minimum delay between requests
BATCH_RATE_LIMIT_SECONDS: float = 5.0  # Per-number delay in batch
MAX_BATCH_SIZE: int = 50                # Max numbers per batch call
REQUEST_TIMEOUT: float = 10.0           # HTTP timeout per request


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class WhatsAppInfo:
    """Result of a WhatsApp number check."""
    number: str                  # E.164 format
    has_whatsapp: bool           # Account detected
    is_business: bool            # WhatsApp Business account
    check_method: str            # "wa.me_status" or "manual"
    confidence: float            # 0.0–1.0 (wa.me is ~0.7 confidence)
    checked_at: float            # Unix timestamp
    error: Optional[str] = None  # Error message if check failed


@dataclass
class WhatsAppBusinessProfile:
    """WhatsApp Business profile information (if publicly available)."""
    number: str
    business_name: Optional[str] = None
    business_description: Optional[str] = None
    business_category: Optional[str] = None
    business_address: Optional[str] = None
    business_email: Optional[str] = None
    business_website: Optional[str] = None
    is_verified: bool = False
    profile_photo_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class WhatsAppEngine:
    """
    WhatsApp number detection and enrichment for UAE/GCC.

    Uses wa.me link resolution for number checking. Results are
    approximate — wa.me may return 200 for all mobile numbers
    regardless of WhatsApp registration.

    CONFIDENCE LEVELS:
    - wa.me returns 200: ~70% confidence number has WhatsApp
    - wa.me returns 404: ~90% confidence number does NOT have WhatsApp
    - These are approximations; wa.me behavior may change.
    """

    def __init__(self, http_client=None, respect_rate_limit: bool = True):
        """
        Args:
            http_client: HTTP client (requests.Session or compatible).
                         Must support .get(url, timeout=N).
            respect_rate_limit: If True, enforce rate limiting between checks.
        """
        self._http = http_client
        self._respect_rate_limit = respect_rate_limit
        self._last_request_time: float = 0.0

    # ---- Public API ----

    def check_whatsapp(self, number: str) -> WhatsAppInfo:
        """
        Check if a phone number has a WhatsApp account.

        Uses wa.me link resolution:
        1. Construct https://wa.me/{number}
        2. Check HTTP status code
        3. 200 → likely has WhatsApp, 404 → likely does not

        Args:
            number: Phone number in E.164 format (+971XXXXXXXXX).

        Returns:
            WhatsAppInfo with check results.

        Example:
            >>> eng = WhatsAppEngine(http_client=session)
            >>> result = eng.check_whatsapp("+971501234567")
            >>> result.has_whatsapp
            True
            >>> result.confidence
            0.7
        """
        if self._http is None:
            raise RuntimeError(
                "HTTP client required. Pass http_client to constructor."
            )

        self._enforce_rate_limit()

        e164 = self._normalize_e164(number)
        wa_number = e164.lstrip("+")
        url = f"https://wa.me/{wa_number}"

        try:
            resp = self._http.get(
                url,
                allow_redirects=True,
                timeout=REQUEST_TIMEOUT,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    ),
                },
            )

            has_wa = resp.status_code == 200
            confidence = 0.7 if has_wa else 0.9

            self._last_request_time = time.time()

            return WhatsAppInfo(
                number=e164,
                has_whatsapp=has_wa,
                is_business=False,  # Cannot determine from wa.me alone
                check_method="wa.me_status",
                confidence=confidence,
                checked_at=time.time(),
            )

        except Exception as e:
            return WhatsAppInfo(
                number=e164,
                has_whatsapp=False,
                is_business=False,
                check_method="wa.me_status",
                confidence=0.0,
                checked_at=time.time(),
                error=str(e),
            )

    def get_business_profile(
        self, number: str
    ) -> WhatsAppBusinessProfile:
        """
        Attempt to extract WhatsApp Business profile info.

        NOTE: WhatsApp does not provide a public API for business profiles.
        This method uses best-effort scraping of the wa.me page, which
        may include business name and description in the HTML meta tags.

        Reliability is LOW — do not depend on this for critical data.

        Args:
            number: Phone number in E.164 format.

        Returns:
            WhatsAppBusinessProfile (fields may be None).

        Example:
            >>> eng = WhatsAppEngine(http_client=session)
            >>> profile = eng.get_business_profile("+971501234567")
            >>> profile.business_name
            'ABC Recruitment Services'
        """
        if self._http is None:
            raise RuntimeError(
                "HTTP client required. Pass http_client to constructor."
            )

        self._enforce_rate_limit()

        e164 = self._normalize_e164(number)
        wa_number = e164.lstrip("+")
        url = f"https://wa.me/{wa_number}"

        profile = WhatsAppBusinessProfile(number=e164)

        try:
            resp = self._http.get(
                url,
                allow_redirects=True,
                timeout=REQUEST_TIMEOUT,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36"
                    ),
                },
            )

            if resp.status_code == 200:
                # Try to extract from HTML meta tags
                text = resp.text
                # Look for og:title which often contains business name
                import re
                og_title = re.search(
                    r'<meta\s+property="og:title"\s+content="([^"]*)"',
                    text,
                )
                if og_title:
                    profile.business_name = og_title.group(1)

                og_desc = re.search(
                    r'<meta\s+property="og:description"\s+content="([^"]*)"',
                    text,
                )
                if og_desc:
                    profile.business_description = og_desc.group(1)

                og_image = re.search(
                    r'<meta\s+property="og:image"\s+content="([^"]*)"',
                    text,
                )
                if og_image:
                    profile.profile_photo_url = og_image.group(1)

            self._last_request_time = time.time()

        except Exception:
            pass

        return profile

    def generate_wa_link(self, number: str, message: str = "") -> str:
        """
        Generate a wa.me click-to-chat link.

        Args:
            number: Phone number (any format, will be normalized).
            message: Optional pre-filled message text.

        Returns:
            wa.me URL string.

        Example:
            >>> eng = WhatsAppEngine()
            >>> eng.generate_wa_link("+971501234567")
            'https://wa.me/971501234567'
            >>> eng.generate_wa_link("+971501234567", "Hi, I found your contact...")
            'https://wa.me/971501234567?text=Hi%2C%20I%20found%20your%20contact...'
        """
        e164 = self._normalize_e164(number)
        wa_number = e164.lstrip("+")
        url = f"https://wa.me/{wa_number}"
        if message:
            from urllib.parse import quote
            url += f"?text={quote(message)}"
        return url

    def batch_check(self, numbers: list[str]) -> dict[str, WhatsAppInfo]:
        """
        Check multiple numbers for WhatsApp registration.

        Applies rate limiting between each check (1 req/5 sec by default).

        Args:
            numbers: List of phone numbers in any format.

        Returns:
            Dict mapping E.164 number → WhatsAppInfo.

        Example:
            >>> eng = WhatsAppEngine(http_client=session)
            >>> results = eng.batch_check([
            ...     "+971501234567",
            ...     "+971521234567",
            ...     "+971541234567",
            ... ])
            >>> results["+971501234567"].has_whatsapp
            True
        """
        if len(numbers) > MAX_BATCH_SIZE:
            raise ValueError(
                f"Batch size {len(numbers)} exceeds maximum {MAX_BATCH_SIZE}. "
                f"Split into smaller batches."
            )

        results: dict[str, WhatsAppInfo] = {}

        for number in numbers:
            info = self.check_whatsapp(number)
            results[info.number] = info

            if self._respect_rate_limit:
                time.sleep(BATCH_RATE_LIMIT_SECONDS)

        return results

    # ---- Private helpers ----

    def _normalize_e164(self, number: str) -> str:
        """Normalize phone number to E.164 format."""
        import re
        digits = re.sub(r"[^\d+]", "", number)
        if digits.startswith("+"):
            return digits
        elif digits.startswith("971"):
            return f"+{digits}"
        elif digits.startswith("0"):
            return f"+971{digits[1:]}"
        else:
            return f"+971{digits}"

    def _enforce_rate_limit(self) -> None:
        """Enforce minimum delay between requests."""
        if not self._respect_rate_limit:
            return
        elapsed = time.time() - self._last_request_time
        if elapsed < RATE_LIMIT_SECONDS:
            time.sleep(RATE_LIMIT_SECONDS - elapsed)
