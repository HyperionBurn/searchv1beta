"""
Lusha Plugin — B2B contact enrichment with email + phone.

Free tier: 5 credits/month (free plan), 40 on Pro trial
Rate limit: 25 req/sec
API docs: https://app.lusha.com/api

Lusha provides:
  - Person enrichment (email + phone by name + company)
  - Company enrichment
  - Prospecting search
  - Direct dial phone numbers

Auth: api_key header with Bearer token
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult
from models.enums import VerificationStatus, VerificationMethod


class LushaPlugin(SourcePlugin):
    """Lusha — B2B email + phone enrichment."""

    SPEC = ALL_PLUGINS["lusha"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """Find recruiter contacts by name + company."""
        results: list[SourceResult] = []
        api_key = os.environ.get("LUSHA_API_KEY", "")
        if not api_key:
            return []

        headers = {
            "api_key": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        for company in query.company_names[:3]:
            for kw in (query.keywords or [])[:2]:
                parts = kw.strip().split()
                if len(parts) >= 2:
                    try:
                        resp = await self.http_client.get(
                            f"{self.SPEC.url_pattern}/v2/person",
                            params={
                                "firstName": parts[0],
                                "lastName": parts[-1],
                                "company": company,
                            },
                            headers=headers,
                        )
                        if resp.status_code == 200:
                            data = resp.json().get("data", {})
                            emails = data.get("emails", [])
                            phones = data.get("phones", [])
                            email = emails[0].get("email", "") if emails else ""
                            phone = phones[0].get("phone", "") if phones else ""

                            if email or phone:
                                results.append(SourceResult(
                                    source_name=self.name,
                                    source_type=self.source_type,
                                    extracted_email=email,
                                    extracted_phone=phone,
                                    extracted_name=f"{data.get('firstName', '')} {data.get('lastName', '')}".strip(),
                                    extracted_company=company,
                                    extracted_title=data.get("jobTitle", ""),
                                    confidence_contribution=0.65,
                                    raw_data={"lusha_source": "person_enrichment"},
                                ))
                    except httpx.HTTPError:
                        pass

        return results

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """Enrich contact with Lusha data (email + phone)."""
        api_key = os.environ.get("LUSHA_API_KEY", "")
        if not api_key:
            return contact

        headers = {
            "api_key": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        params = {}
        if contact.name:
            parts = contact.name.split(None, 1)
            params["firstName"] = parts[0]
            params["lastName"] = parts[1] if len(parts) > 1 else ""
        if contact.company:
            params["company"] = contact.company

        if not params:
            return contact

        try:
            resp = await self.http_client.get(
                f"{self.SPEC.url_pattern}/v2/person",
                params=params,
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                emails = data.get("emails", [])
                phones = data.get("phones", [])

                # Add email if found and not already present
                if emails and not contact.emails:
                    from models.models import EmailRecord
                    contact.emails.append(EmailRecord(
                        email=emails[0]["email"],
                        verification_status=VerificationStatus.API_VALID,
                        verification_method=VerificationMethod.API_CHECK,
                    ))

                # Add phone if found
                if phones:
                    from models.models import PhoneRecord
                    contact.phones.append(PhoneRecord(phone=phones[0]["phone"]))

                if data.get("jobTitle") and not contact.title:
                    contact.title = data["jobTitle"]
        except httpx.HTTPError:
            pass

        return contact

    async def validate_config(self) -> bool:
        return bool(os.environ.get("LUSHA_API_KEY"))

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(
            requests_per_minute=self.SPEC.rate_limit_rpm,
            credits_limit=self.SPEC.rate_limit_monthly,
        )
