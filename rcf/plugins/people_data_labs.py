"""
PeopleDataLabs Plugin — Person search and enrichment API.

Free tier: 100 credits/month (enrichment)
Rate limit: 10 req/min
API docs: https://docs.peopledatalabs.com
"""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class PeopleDataLabsPlugin(SourcePlugin):
    """PeopleDataLabs — person search, company enrichment, email discovery."""

    SPEC = ALL_PLUGINS["people_data_labs"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        api_key = self._resolve_api_key()
        if not api_key:
            return []

        results: list[SourceResult] = []
        for company in query.company_names:
            company_safe = company.replace("'", "''")

            resp = await self.http_client.post(
                f"{self.SPEC.url_pattern}/person/search",
                json={
                    "sql": f"SELECT * FROM person WHERE (current_employer_name='{company_safe}' OR past_employer_name='{company_safe}') AND (job_title LIKE '%recruiter%' OR job_title LIKE '%talent acquisition%' OR job_title LIKE '%hr%')",
                    "size": 10,
                },
                headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

            for person in data.get("data", []):
                results.append(self._make_source_result(
                    raw_data=person,
                    extracted_name=person.get("names", [""])[0] if person.get("names") else person.get("full_name", ""),
                    extracted_email=person.get("emails", [None])[0] if person.get("emails") else None,
                    extracted_phone=person.get("phone_numbers", [None])[0] if person.get("phone_numbers") else None,
                    extracted_company=company,
                    extracted_title=person.get("job_title"),
                    extracted_linkedin=person.get("linkedin_url"),
                    confidence_contribution=0.45,
                ))
        return results

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        api_key = self._resolve_api_key()
        if not api_key:
            return contact

        # Use PDL enrichment endpoint
        try:
            resp = await self.http_client.get(
                f"{self.SPEC.url_pattern}/person/enrich",
                params={
                    "name": contact.name,
                    "company": contact.company or "",
                },
                headers={"X-Api-Key": api_key},
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})

            email = data.get("work_email") or (data.get("emails", [None])[0] if data.get("emails") else None)
            if email and not any(e.email == email for e in contact.emails):
                from models.models import EmailRecord
                from models.enums import SourceType
                contact.emails.append(EmailRecord(email=email, source=SourceType.API))

            phone = data.get("phone_numbers", [None])[0] if data.get("phone_numbers") else None
            if phone and not any(p.phone == phone for p in contact.phones):
                from models.models import PhoneRecord
                from models.enums import SourceType
                contact.phones.append(PhoneRecord(phone=phone, source=SourceType.API))
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
