"""
RocketReach Plugin — Professional contact data API.

Free tier: 25 credits/month
Rate limit: 10 req/min
API docs: https://rocketreach.co/api
"""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class RocketReachPlugin(SourcePlugin):
    """RocketReach — professional contact lookup, email and phone finder."""

    SPEC = ALL_PLUGINS["rocketreach"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        api_key = self._resolve_api_key()
        if not api_key:
            return []

        results: list[SourceResult] = []
        for company in query.company_names:
            params: dict[str, Any] = {
                "current_employer": company,
                "title": "recruiter OR 'talent acquisition' OR 'HR manager'",
                "start": 1,
                "page_size": 10,
            }
            headers = {"Api-Key": api_key}
            resp = await self.http_client.get(
                f"{self.SPEC.url_pattern}/search",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

            for profile in data.get("profiles", []):
                results.append(self._make_source_result(
                    raw_data=profile,
                    extracted_name=profile.get("name", ""),
                    extracted_email=profile.get("email"),
                    extracted_phone=profile.get("phone"),
                    extracted_company=company,
                    extracted_title=profile.get("current_title"),
                    extracted_linkedin=profile.get("linkedin_url"),
                    confidence_contribution=0.5,
                ))
        return results

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        return contact  # RocketReach enrichment covered in discover

    async def validate_config(self) -> bool:
        return bool(self._resolve_api_key())

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(
            requests_per_minute=self.SPEC.rate_limit_rpm,
            credits_limit=self.SPEC.rate_limit_monthly,
        )
