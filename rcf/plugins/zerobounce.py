"""
ZeroBounce Plugin — Email verification API.

Free tier: 100 credits/month
Rate limit: 10 req/min
API docs: https://www.zerobounce.net/docs/
"""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult
from models.enums import VerificationStatus, VerificationMethod


class ZeroBouncePlugin(SourcePlugin):
    """ZeroBounce — email verification (syntax, DNS, SMTP, API validation)."""

    SPEC = ALL_PLUGINS["zerobounce"]

    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """ZeroBounce is a verification-only API — returns empty for discovery."""
        return []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """Verify all unverified emails on a contact."""
        api_key = self._resolve_api_key()
        if not api_key:
            return contact

        for i, email_rec in enumerate(contact.emails):
            if email_rec.verification_status in (
                VerificationStatus.UNVERIFIED,
                VerificationStatus.SYNTAX_VALID,
                VerificationStatus.DNS_VALID,
            ):
                try:
                    resp = await self.http_client.get(
                        f"{self.SPEC.url_pattern}/validate",
                        params={"api_key": api_key, "email": email_rec.email},
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    status = data.get("status", "").lower()
                    sub_status = data.get("sub_status", "").lower()

                    if status == "valid":
                        contact.emails[i].verification_status = VerificationStatus.API_VALID
                        contact.emails[i].verification_method = VerificationMethod.API_CHECK
                    elif status in ("invalid", "spamtrap", "abuse"):
                        contact.emails[i].verification_status = VerificationStatus.INVALID
                        contact.emails[i].verification_method = VerificationMethod.API_CHECK
                    elif status == "catch-all":
                        contact.emails[i].verification_status = VerificationStatus.DNS_VALID
                        contact.emails[i].verification_method = VerificationMethod.API_CHECK

                except httpx.HTTPError:
                    pass

        return contact

    async def validate_config(self) -> bool:
        return bool(self._resolve_api_key())

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(
            requests_per_minute=self.SPEC.rate_limit_rpm,
            credits_limit=self.SPEC.rate_limit_monthly,
        )
