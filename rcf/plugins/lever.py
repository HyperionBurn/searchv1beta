"""
Lever Plugin — ATS job board API for recruiter discovery.

Free tier: Unlimited (public API)
Rate limit: 12 req/min
API docs: https://developer.lever.co
"""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class LeverPlugin(SourcePlugin):
    """Lever — ATS board scraping for recruiter names and companies."""

    SPEC = ALL_PLUGINS["lever"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        results: list[SourceResult] = []

        for company in query.company_names:
            slug = company.lower().replace(" ", "").replace("&", "and")
            try:
                resp = await self.http_client.get(
                    f"https://api.lever.co/v1/postings/{slug}?mode=json",
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()

                for posting in data.get("postings", [])[:10]:
                    owner = posting.get("owner", {})
                    if owner:
                        results.append(self._make_source_result(
                            raw_data=posting,
                            extracted_name=owner.get("name", ""),
                            extracted_email=owner.get("email"),
                            extracted_company=company,
                            extracted_title=posting.get("text", ""),
                            source_url=posting.get("urls", {}).get("list"),
                            confidence_contribution=0.35,
                        ))
            except httpx.HTTPError:
                continue

        return results

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        return contact

    async def validate_config(self) -> bool:
        return True  # No API key required

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(requests_per_minute=self.SPEC.rate_limit_rpm)
