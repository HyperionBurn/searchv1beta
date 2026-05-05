"""
AbstractAPI Plugin — Email verification and phone validation.

Free tier: 100 credits/month
Rate limit: 8 req/min
API docs: https://docs.abstractapi.com
"""

from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class AbstractAPIPlugin(SourcePlugin):
    """AbstractAPI — email verification and phone validation."""

    SPEC = ALL_PLUGINS["abstract_api"]

    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        return []  # Verification-only API

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        api_key = self._resolve_api_key()
        if not api_key:
            return contact

        # Verify emails
        for i, email_rec in enumerate(contact.emails):
            try:
                resp = await self.http_client.get(
                    f"{self.SPEC.url_pattern}/emailvalidation/v1",
                    params={"api_key": api_key, "email": email_rec.email},
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("deliverability") == "DELIVERABLE":
                    from models.enums import VerificationStatus, VerificationMethod
                    contact.emails[i].verification_status = VerificationStatus.API_VALID
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
