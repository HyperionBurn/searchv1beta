"""
Dropcontact Plugin — GDPR-compliant email + phone enrichment.

Free tier: 100 credits (one-time trial)
Rate limit: 60 req/sec
API docs: https://api.dropcontact.com/

Dropcontact provides:
  - Email finding (by name + company)
  - Email verification (included)
  - Phone number discovery
  - LinkedIn profile enrichment
  - GDPR-compliant data (no personal data storage)
  - Job title + function + seniority level

Note: Async API — POST to start job, GET to retrieve results (~30s delay)
Auth: X-Access-Token header
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult
from models.enums import VerificationStatus, VerificationMethod


class DropcontactPlugin(SourcePlugin):
    """Dropcontact — GDPR-compliant email + phone enrichment."""

    SPEC = ALL_PLUGINS["dropcontact"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """Find emails by name + company via async enrichment."""
        results: list[SourceResult] = []
        api_key = os.environ.get("DROPCONTACT_API_KEY", "")
        if not api_key:
            return []

        headers = {
            "X-Access-Token": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        for company in query.company_names[:3]:
            domain = company.lower().replace(" ", "").replace("&", "and")

            # Submit enrichment job
            try:
                resp = await self.http_client.post(
                    f"{self.SPEC.url_pattern}/enrich/all",
                    json={
                        "data": [
                            {"website": f"{domain}.com"},
                        ],
                        "siren": False,
                        "language": "en",
                    },
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    request_id = data.get("request_id", "")
                    if request_id:
                        # Poll for results (wait ~10s for processing)
                        await asyncio.sleep(10)
                        poll_resp = await self.http_client.get(
                            f"{self.SPEC.url_pattern}/enrich/all/{request_id}",
                            headers=headers,
                        )
                        if poll_resp.status_code == 200:
                            poll_data = poll_resp.json()
                            contacts = poll_data.get("data", [])
                            for c in contacts[:10]:
                                emails = c.get("email", [])
                                email_str = emails[0].get("email", "") if emails else ""
                                results.append(SourceResult(
                                    source_name=self.name,
                                    source_type=self.source_type,
                                    extracted_email=email_str,
                                    extracted_name=f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
                                    extracted_company=c.get("company", company),
                                    extracted_title=c.get("job", ""),
                                    extracted_linkedin=c.get("linkedin", ""),
                                    extracted_phone=c.get("phone", "") or c.get("mobile_phone", ""),
                                    confidence_contribution=0.7,
                                    raw_data={
                                        "dropcontact_qualification": emails[0].get("qualification", "") if emails else "",
                                        "dropcontact_job_level": c.get("job_level", ""),
                                        "dropcontact_job_function": c.get("job_function", ""),
                                    },
                                ))
            except httpx.HTTPError:
                pass

        return results

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """Enrich contact with Dropcontact data."""
        api_key = os.environ.get("DROPCONTACT_API_KEY", "")
        if not api_key:
            return contact

        headers = {
            "X-Access-Token": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Build query from existing data
        query_data = {}
        if contact.emails:
            query_data["email"] = contact.emails[0].email
        elif contact.name:
            parts = contact.name.split(None, 1)
            query_data["first_name"] = parts[0] if parts else ""
            query_data["last_name"] = parts[1] if len(parts) > 1 else ""
            if contact.company:
                domain = contact.company.lower().replace(" ", "").replace("&", "and")
                query_data["website"] = f"{domain}.com"

        if not query_data:
            return contact

        try:
            resp = await self.http_client.post(
                f"{self.SPEC.url_pattern}/enrich/all",
                json={"data": [query_data], "siren": False, "language": "en"},
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                request_id = data.get("request_id", "")
                if request_id:
                    await asyncio.sleep(8)
                    poll_resp = await self.http_client.get(
                        f"{self.SPEC.url_pattern}/enrich/all/{request_id}",
                        headers=headers,
                    )
                    if poll_resp.status_code == 200:
                        poll_data = poll_resp.json()
                        contacts = poll_data.get("data", [])
                        if contacts:
                            c = contacts[0]
                            if c.get("first_name") and not contact.name:
                                contact.name = f"{c['first_name']} {c.get('last_name', '')}".strip()
                            if c.get("job") and not contact.title:
                                contact.title = c["job"]
                            if c.get("linkedin") and not contact.linkedin_url:
                                contact.linkedin_url = c["linkedin"]
                            # Add phone if found
                            phone = c.get("phone") or c.get("mobile_phone")
                            if phone:
                                from models.models import PhoneRecord
                                contact.phones.append(PhoneRecord(phone=phone))
        except httpx.HTTPError:
            pass

        return contact

    async def validate_config(self) -> bool:
        return bool(os.environ.get("DROPCONTACT_API_KEY"))

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(
            requests_per_minute=self.SPEC.rate_limit_rpm,
            credits_limit=self.SPEC.rate_limit_monthly,
        )
