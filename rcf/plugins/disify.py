"""
Disify Email Verification Plugin — Free, no API key required.

Free tier: Unlimited (rate-limited, no auth)
Rate limit: 6 req/min (conservative)
API docs: https://disify.com/
Integration: Email verification + disposable domain detection

Disify provides:
  - Email format validation
  - DNS/MX record verification
  - Disposable/temporary email detection (62K+ providers)
  - Role-based email detection (info@, admin@, etc.)

No API key needed — completely free.
"""

from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult
from models.enums import VerificationStatus, VerificationMethod


class DisifyPlugin(SourcePlugin):
    """Disify — Free email verification + disposable detection (no API key)."""

    SPEC = ALL_PLUGINS["disify"]

    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """Disify is verification-only — returns empty for discovery."""
        return []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """Verify emails using Disify free API."""
        for i, email_rec in enumerate(contact.emails):
            if email_rec.verification_status in (
                VerificationStatus.UNVERIFIED,
                VerificationStatus.SYNTAX_VALID,
            ):
                try:
                    # Disify API: GET https://disify.com/api/email/{email}
                    resp = await self.http_client.get(
                        f"{self.SPEC.url_pattern}/{email_rec.email}",
                        headers={"Accept": "application/json"},
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    # Disify returns: format (bool), disposable (bool), dns (bool)
                    format_valid = data.get("format", False)
                    disposable = data.get("disposable", False)
                    dns_valid = data.get("dns", False)

                    if not format_valid:
                        contact.emails[i].verification_status = VerificationStatus.INVALID
                        contact.emails[i].verification_method = VerificationMethod.API_CHECK
                    elif disposable:
                        # Mark as invalid if disposable
                        contact.emails[i].verification_status = VerificationStatus.INVALID
                        contact.emails[i].verification_method = VerificationMethod.API_CHECK
                    elif dns_valid:
                        contact.emails[i].verification_status = VerificationStatus.DNS_VALID
                        contact.emails[i].verification_method = VerificationMethod.API_CHECK
                    else:
                        # Format valid but DNS failed — likely invalid
                        contact.emails[i].verification_status = VerificationStatus.SYNTAX_VALID
                        contact.emails[i].verification_method = VerificationMethod.REGEX

                except httpx.HTTPError:
                    pass

        return contact

    async def validate_config(self) -> bool:
        """Disify needs no configuration — always valid."""
        return True

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(
            requests_per_minute=self.SPEC.rate_limit_rpm,
            credits_limit=self.SPEC.rate_limit_monthly,
        )
