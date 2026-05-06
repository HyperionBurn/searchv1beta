"""
Kaspr Plugin — LinkedIn-based phone + email enrichment.

Free tier: 20 credits/month
Rate limit: varies by plan
API docs: https://kaspr.stoplight.io/docs/kaspr-api

Kaspr provides:
  - Email discovery from LinkedIn URL
  - Phone number discovery from LinkedIn URL
  - Direct dial + work email + personal email

Note: Requires LinkedIn profile URL as input (not domain-based search).
Auth: Bearer token in authorization header
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult
from models.enums import VerificationStatus, VerificationMethod


class KasprPlugin(SourcePlugin):
    """Kaspr — LinkedIn-based phone + email enrichment."""

    SPEC = ALL_PLUGINS["kaspr"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """Kaspr requires LinkedIn URL input — limited discovery via enrichment."""
        # Kaspr can't search by domain/name — it needs a LinkedIn URL
        # Return empty; enrichment will be the main use case
        return []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """Enrich contact with Kaspr if LinkedIn URL is available."""
        api_key = os.environ.get("KASPR_API_KEY", "")
        if not api_key:
            return contact

        if not contact.linkedin_url:
            return contact

        headers = {
            "authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }

        try:
            resp = await self.http_client.get(
                f"{self.SPEC.url_pattern}/enrich",
                params={"linkedin_url": contact.linkedin_url},
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()

                # Add email if found
                email = data.get("email") or data.get("work_email")
                if email and not contact.emails:
                    from models.models import EmailRecord
                    contact.emails.append(EmailRecord(
                        email=email,
                        verification_status=VerificationStatus.API_VALID,
                        verification_method=VerificationMethod.API_CHECK,
                    ))

                # Add phone if found
                phone = data.get("phone") or data.get("direct_dial")
                if phone:
                    from models.models import PhoneRecord
                    contact.phones.append(PhoneRecord(phone=phone))

                # Fill in missing name/title
                if data.get("full_name") and not contact.name:
                    contact.name = data["full_name"]
                if data.get("job_title") and not contact.title:
                    contact.title = data["job_title"]

        except httpx.HTTPError:
            pass

        return contact

    async def validate_config(self) -> bool:
        return bool(os.environ.get("KASPR_API_KEY"))

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(
            requests_per_minute=self.SPEC.rate_limit_rpm,
            credits_limit=self.SPEC.rate_limit_monthly,
        )
