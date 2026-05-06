"""
Skrapp.io Plugin — Email finder + verifier for LinkedIn enrichment.

Free tier: 50 credits/month (API requires paid plan)
Rate limit: varies
API docs: https://developer.skrapp.io/

Skrapp provides:
  - Email finder (by name + domain)
  - Email verifier (format, DNS, mailbox)
  - Bulk email finder (up to 100 at once)
  - LinkedIn profile enrichment

Auth: X-Access-Key header
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult
from models.enums import VerificationStatus, VerificationMethod


class SkrappPlugin(SourcePlugin):
    """Skrapp.io — Email finder + verifier with LinkedIn enrichment."""

    SPEC = ALL_PLUGINS["skrapp"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """Find emails by name + domain."""
        results: list[SourceResult] = []
        api_key = os.environ.get("SKRAPP_API_KEY", "")
        if not api_key:
            return []

        headers = {
            "X-Access-Key": api_key,
            "Accept": "application/json",
        }

        for company in query.company_names[:3]:
            domain = company.lower().replace(" ", "").replace("&", "and")

            for kw in (query.keywords or [])[:2]:
                parts = kw.strip().split()
                if len(parts) >= 2:
                    try:
                        resp = await self.http_client.get(
                            f"{self.SPEC.url_pattern}/api/v2/find",
                            params={
                                "firstName": parts[0],
                                "lastName": parts[-1],
                                "domain": f"{domain}.com",
                            },
                            headers=headers,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get("email"):
                                quality = data.get("quality", {})
                                results.append(SourceResult(
                                    source_name=self.name,
                                    source_type=self.source_type,
                                    extracted_email=data["email"],
                                    extracted_name=f"{parts[0]} {parts[-1]}",
                                    extracted_company=company,
                                    confidence_contribution=0.6 if quality.get("status") == "valid" else 0.35,
                                    raw_data={
                                        "skrapp_pattern": data.get("pattern", ""),
                                        "skrapp_status": quality.get("status", ""),
                                    },
                                ))
                    except httpx.HTTPError:
                        pass

        return results

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """Verify emails using Skrapp verifier."""
        api_key = os.environ.get("SKRAPP_API_KEY", "")
        if not api_key:
            return contact

        headers = {
            "X-Access-Key": api_key,
            "Accept": "application/json",
        }

        for i, email_rec in enumerate(contact.emails):
            if email_rec.verification_status in (
                VerificationStatus.UNVERIFIED,
                VerificationStatus.SYNTAX_VALID,
            ):
                try:
                    resp = await self.http_client.get(
                        f"{self.SPEC.url_pattern}/v3/verify",
                        params={"email": email_rec.email},
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        status = data.get("email_status", "").lower()
                        if status in ("valid", "catch-all"):
                            contact.emails[i].verification_status = VerificationStatus.API_VALID
                            contact.emails[i].verification_method = VerificationMethod.API_CHECK
                        elif status in ("invalid", "risky"):
                            contact.emails[i].verification_status = VerificationStatus.INVALID
                            contact.emails[i].verification_method = VerificationMethod.API_CHECK
                except httpx.HTTPError:
                    pass

        return contact

    async def validate_config(self) -> bool:
        return bool(os.environ.get("SKRAPP_API_KEY"))

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(
            requests_per_minute=self.SPEC.rate_limit_rpm,
            credits_limit=self.SPEC.rate_limit_monthly,
        )
