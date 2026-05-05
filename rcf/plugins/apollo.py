"""
Apollo.io Plugin — People search and company data API.

Free tier: 60 credits/month
Rate limit: 10 req/min
API docs: https://docs.apollo.io
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, PluginSpec, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult

logger = structlog.get_logger().bind(plugin="apollo")


class ApolloPlugin(SourcePlugin):
    """Apollo.io — people search, email discovery, company data."""

    SPEC = ALL_PLUGINS["apollo"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        api_key = self._resolve_api_key()
        if not api_key:
            return []

        results: list[SourceResult] = []

        for company in query.company_names:
            payload: dict[str, Any] = {
                "api_key": api_key,
                "q_organization_name": company,
                "page": 1,
                "per_page": 10,
                "person_titles": ["recruiter", "talent acquisition", "hr manager", "headhunter"],
            }
            if query.keywords:
                payload["q_keywords"] = " ".join(query.keywords)

            resp = await self.http_client.post(
                f"{self.SPEC.url_pattern}/people/search",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

            for person in data.get("people", []):
                results.append(self._make_source_result(
                    raw_data=person,
                    extracted_name=person.get("name", ""),
                    extracted_email=person.get("email"),
                    extracted_phone=person.get("phone_numbers", [None])[0] if person.get("phone_numbers") else None,
                    extracted_company=person.get("organization", {}).get("name"),
                    extracted_title=person.get("title"),
                    extracted_linkedin=person.get("linkedin_url"),
                    source_url=person.get("linkedin_url"),
                    confidence_contribution=0.45,
                ))

        return results

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        api_key = self._resolve_api_key()
        if not api_key or not contact.name:
            return contact

        try:
            resp = await self.http_client.post(
                f"{self.SPEC.url_pattern}/people/match",
                json={
                    "api_key": api_key,
                    "first_name": contact.name.split()[0] if contact.name.split() else "",
                    "last_name": contact.name.split()[-1] if len(contact.name.split()) > 1 else "",
                    "organization_name": contact.company or "",
                },
            )
            resp.raise_for_status()
            person = resp.json().get("person", {})
            if person:
                email = person.get("email")
                if email and not any(e.email == email for e in contact.emails):
                    from models.models import EmailRecord
                    from models.enums import SourceType
                    contact.emails.append(EmailRecord(email=email, source=SourceType.API))
                phone = person.get("phone_numbers", [None])[0] if person.get("phone_numbers") else None
                if phone and not any(p.phone == phone for p in contact.phones):
                    from models.models import PhoneRecord
                    from models.enums import SourceType
                    contact.phones.append(PhoneRecord(phone=phone, source=SourceType.API))
        except httpx.HTTPError:
            pass
        return contact

    async def validate_config(self) -> bool:
        api_key = self._resolve_api_key()
        return bool(api_key)

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(
            requests_per_minute=self.SPEC.rate_limit_rpm,
            credits_limit=self.SPEC.rate_limit_monthly,
        )
