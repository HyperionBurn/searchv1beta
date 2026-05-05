"""
Greenhouse Plugin — ATS job board API for recruiter discovery.

Free tier: Unlimited (public API)
Rate limit: 12 req/min
API docs: https://developers.greenhouse.io
"""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class GreenhousePlugin(SourcePlugin):
    """Greenhouse — ATS board scraping for recruiter names and companies."""

    SPEC = ALL_PLUGINS["greenhouse"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """Scrape Greenhouse-hosted job boards for recruiter info."""
        results: list[SourceResult] = []

        for company in query.company_names:
            slug = company.lower().replace(" ", "-").replace("&", "and")
            try:
                resp = await self.http_client.get(
                    f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
                )
                resp.raise_for_status()
                data = resp.json()

                for job in data.get("jobs", [])[:10]:
                    recruiters = job.get("metadata", [])
                    for meta in recruiters:
                        if "recruiter" in meta.get("name", "").lower():
                            results.append(self._make_source_result(
                                raw_data={"job": job, "meta": meta},
                                extracted_name=meta.get("value", ""),
                                extracted_company=company,
                                extracted_title=job.get("title", ""),
                                source_url=job.get("absolute_url"),
                                confidence_contribution=0.3,
                            ))
            except httpx.HTTPError:
                continue

        return results

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        return contact  # Greenhouse enrichment is covered in discover

    async def validate_config(self) -> bool:
        return True  # No API key required

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(requests_per_minute=self.SPEC.rate_limit_rpm)
