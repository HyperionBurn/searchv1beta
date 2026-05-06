"""
Greenhouse Plugin — ATS job board API for recruiter discovery.

Free tier: Unlimited (public API)
Rate limit: 12 req/min
API docs: https://developers.greenhouse.io

Uses the public Greenhouse API at boards-api.greenhouse.io/v1/boards/{company}/jobs
to find recruiters from companies that use Greenhouse as their ATS.
"""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


# Known UAE/GCC companies using Greenhouse ATS (add more as discovered)
GREENHOUSE_BOARDS = [
    "careem",
    "talabat",
    "noon",
    "amazon",
    "kitopi",
    "propertyfinder",
    "bayut",
    "dubizzle",
    "wuzzuf",
    "olx",
]


class GreenhousePlugin(SourcePlugin):
    """Greenhouse — ATS board scraping for recruiter names and companies."""

    SPEC = ALL_PLUGINS["greenhouse"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """Scrape Greenhouse-hosted job boards for recruiter info."""
        results: list[SourceResult] = []

        # Build list of boards to check: query companies + known boards
        boards = []
        for company in query.company_names:
            slug = company.lower().replace(" ", "-").replace("&", "and")
            boards.append(slug)
        # Also check known boards for matching jobs
        boards.extend(b for b in GREENHOUSE_BOARDS if b not in boards)

        region_filter = query.region.value if query.region else "uae"

        for slug in boards[:8]:  # Limit to avoid rate limits
            try:
                resp = await self.http_client.get(
                    f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
                )
                if resp.status_code != 200:
                    continue

                data = resp.json()
                jobs = data.get("jobs", [])

                for job in jobs:
                    location = job.get("location", {})
                    loc_name = location.get("name", "") if isinstance(location, dict) else str(location)

                    # Filter for UAE/GCC region
                    region_match = any(
                        region_keyword in loc_name.lower()
                        for region_keyword in [region_filter, "dubai", "abu dhabi", "uae", "gcc", "riyadh", "doha"]
                    )
                    if not region_match:
                        continue

                    title = job.get("title", "")
                    company_name = slug.replace("-", " ").title()

                    # Check for recruiter metadata
                    recruiters = []
                    for meta in job.get("metadata", []):
                        if "recruiter" in meta.get("name", "").lower():
                            recruiters.append(meta.get("value", ""))

                    # Also extract from content if available
                    content = job.get("content", "") or ""

                    results.append(self._make_source_result(
                        raw_data={
                            "greenhouse_board": slug,
                            "job_id": job.get("id"),
                            "location": loc_name,
                            "updated_at": job.get("updated_at"),
                        },
                        extracted_name=recruiters[0] if recruiters else None,
                        extracted_company=company_name,
                        extracted_title=title,
                        source_url=job.get("absolute_url"),
                        confidence_contribution=0.35 if recruiters else 0.25,
                    ))

                self.logger.info(
                    "greenhouse_board_scraped",
                    board=slug,
                    total_jobs=len(jobs),
                    region_matches=len([r for r in results if r.raw_data.get("greenhouse_board") == slug]),
                )

            except (httpx.HTTPError, ValueError) as exc:
                self.logger.debug("greenhouse_board_error", board=slug, error=str(exc))
                continue

        return results

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        return contact  # Greenhouse enrichment is covered in discover

    async def validate_config(self) -> bool:
        return True  # No API key required

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(requests_per_minute=self.SPEC.rate_limit_rpm)
