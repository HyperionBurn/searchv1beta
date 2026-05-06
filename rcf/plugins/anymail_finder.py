"""
Anymail Finder Plugin — Simple POST-based email finder API.

Free tier: 100 credits (one-time trial)
Rate limit: No rate limits
API docs: https://docs.anymailfinder.com/

Anymail Finder provides:
  - Find person email (by name + domain)
  - Find company emails (all at a domain)
  - Find decision maker email (by role)
  - Find by LinkedIn URL
  - Email verification (included)
  - 97%+ deliverability guarantee

Auth: Authorization header with API key
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult
from models.enums import VerificationStatus, VerificationMethod


class AnymailFinderPlugin(SourcePlugin):
    """Anymail Finder — Email finder with 97%+ deliverability."""

    SPEC = ALL_PLUGINS["anymail_finder"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """Find emails by company domain and person name."""
        results: list[SourceResult] = []
        api_key = os.environ.get("ANYMAIL_FINDER_API_KEY", "")
        if not api_key:
            return []

        headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        for company in query.company_names[:3]:
            domain = company.lower().replace(" ", "").replace("&", "and")

            # 1. Company search — find all emails at domain
            try:
                resp = await self.http_client.post(
                    f"{self.SPEC.url_pattern}/find-email/company",
                    json={"domain": f"{domain}.com"},
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    emails = data.get("emails", []) or data.get("valid_emails", [])
                    for email in emails[:10]:
                        results.append(SourceResult(
                            source_name=self.name,
                            source_type=self.source_type,
                            extracted_email=email,
                            extracted_company=company,
                            confidence_contribution=0.6,
                            raw_data={"anymail_status": data.get("email_status", "")},
                        ))
            except httpx.HTTPError:
                pass

            # 2. Decision maker search — find recruiter/HR at company
            try:
                resp = await self.http_client.post(
                    f"{self.SPEC.url_pattern}/find-email/decision-maker",
                    json={
                        "domain": f"{domain}.com",
                        "role": "recruiter",
                    },
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("email"):
                        results.append(SourceResult(
                            source_name=self.name,
                            source_type=self.source_type,
                            extracted_email=data["email"],
                            extracted_company=company,
                            extracted_title="Recruiter",
                            confidence_contribution=0.65,
                            raw_data={"anymail_status": data.get("email_status", "")},
                        ))
            except httpx.HTTPError:
                pass

        return results

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """Verify emails using Anymail Finder."""
        api_key = os.environ.get("ANYMAIL_FINDER_API_KEY", "")
        if not api_key:
            return contact

        headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        for i, email_rec in enumerate(contact.emails):
            if email_rec.verification_status in (
                VerificationStatus.UNVERIFIED,
                VerificationStatus.SYNTAX_VALID,
            ):
                try:
                    resp = await self.http_client.post(
                        f"{self.SPEC.url_pattern}/verify-email",
                        json={"email": email_rec.email},
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        status = data.get("email_status", "").lower()
                        if status == "valid":
                            contact.emails[i].verification_status = VerificationStatus.API_VALID
                            contact.emails[i].verification_method = VerificationMethod.API_CHECK
                        elif status in ("invalid", "risky"):
                            contact.emails[i].verification_status = VerificationStatus.INVALID
                            contact.emails[i].verification_method = VerificationMethod.API_CHECK
                except httpx.HTTPError:
                    pass

        return contact

    async def validate_config(self) -> bool:
        return bool(os.environ.get("ANYMAIL_FINDER_API_KEY"))

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(
            requests_per_minute=self.SPEC.rate_limit_rpm,
            credits_limit=self.SPEC.rate_limit_monthly,
        )
