"""
Verifalia Email Verification Plugin — Generous free tier.

Free tier: 25 verifications/day = ~750/month
Rate limit: 6 req/min
API docs: https://verifalia.com/developers

Verifalia provides:
  - Syntax validation
  - DNS/MX verification
  - SMTP mailbox verification (with catch-all detection)
  - Quality score (0-1)
  - Disposable email detection
  - Role account detection (info@, admin@)

Requires free signup at verifalia.com for API credentials.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult
from models.enums import VerificationStatus, VerificationMethod


class VerifaliaPlugin(SourcePlugin):
    """Verifalia — Email verification with generous free tier (25/day = 750/mo)."""

    SPEC = ALL_PLUGINS["verifalia"]

    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """Verifalia is verification-only — returns empty for discovery."""
        return []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """Verify emails using Verifalia API (async submit + poll for results)."""
        username = os.environ.get("VERIFALIA_USERNAME", "")
        password = os.environ.get("VERIFALIA_PASSWORD", "")
        if not username or not password:
            return contact

        for i, email_rec in enumerate(contact.emails):
            if email_rec.verification_status in (
                VerificationStatus.UNVERIFIED,
                VerificationStatus.SYNTAX_VALID,
                VerificationStatus.DNS_VALID,
            ):
                try:
                    # Submit email for verification
                    resp = await self.http_client.post(
                        f"{self.SPEC.url_pattern}/email-validations",
                        auth=(username, password),
                        json={"entries": [{"inputData": email_rec.email}]},
                        headers={"Content-Type": "application/json", "Accept": "application/json"},
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    # Check if result is immediately available
                    entries = data.get("entries", {}).get("values", [])
                    if not entries:
                        # Poll for results (Verifalia processes async)
                        validation_id = data.get("uniqueID", "")
                        if validation_id:
                            poll_resp = await self.http_client.get(
                                f"{self.SPEC.url_pattern}/email-validations/{validation_id}",
                                auth=(username, password),
                                headers={"Accept": "application/json"},
                            )
                            if poll_resp.status_code == 200:
                                poll_data = poll_resp.json()
                                entries = poll_data.get("entries", {}).get("values", [])

                    if entries:
                        entry = entries[0]
                        classification = entry.get("classification", {}).get("value", "").lower()
                        status = entry.get("status", "").lower()

                        if classification == "valid":
                            contact.emails[i].verification_status = VerificationStatus.API_VALID
                            contact.emails[i].verification_method = VerificationMethod.API_CHECK
                        elif classification == "invalid":
                            contact.emails[i].verification_status = VerificationStatus.INVALID
                            contact.emails[i].verification_method = VerificationMethod.API_CHECK
                        elif classification in ("risky", "unknown"):
                            contact.emails[i].verification_status = VerificationStatus.DNS_VALID
                            contact.emails[i].verification_method = VerificationMethod.API_CHECK

                        # Check disposable status in raw data
                        # (EmailRecord doesn't have is_disposable field yet)

                except httpx.HTTPError:
                    pass

        return contact

    async def validate_config(self) -> bool:
        username = os.environ.get("VERIFALIA_USERNAME", "")
        password = os.environ.get("VERIFALIA_PASSWORD", "")
        return bool(username and password)

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(
            requests_per_minute=self.SPEC.rate_limit_rpm,
            credits_limit=self.SPEC.rate_limit_monthly,
        )
