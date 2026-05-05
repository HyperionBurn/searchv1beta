"""
Seamless.ai Plugin — Contact and company data API.

Free tier: 50 lifetime credits
Rate limit: 8 req/min
"""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class SeamlessAIPlugin(SourcePlugin):
    """Seamless.ai — contact search and email discovery."""

    SPEC = ALL_PLUGINS["seamless_ai"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        api_key = self._resolve_api_key()
        if not api_key:
            return []

        results: list[SourceResult] = []
        for company in query.company_names:
            params = {
                "api_key": api_key,
                "company": company,
                "title": "recruiter",
                "limit": 10,
            }
            resp = await self.http_client.get(
                f"{self.SPEC.url_pattern}/contacts",
                params=params,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()

            for contact in data.get("contacts", data if isinstance(data, list) else []):
                results.append(self._make_source_result(
                    raw_data=contact,
                    extracted_name=contact.get("name", ""),
                    extracted_email=contact.get("email"),
                    extracted_phone=contact.get("phone"),
                    extracted_company=company,
                    extracted_title=contact.get("title"),
                    confidence_contribution=0.35,
                ))
        return results

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        return contact  # Seamless.ai enrich is same as discover

    async def validate_config(self) -> bool:
        return bool(self._resolve_api_key())

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(
            requests_per_minute=self.SPEC.rate_limit_rpm,
            credits_limit=self.SPEC.rate_limit_monthly,
        )
