"""
GulfTalent Plugin — GCC professional job board.

Rate limit: 6 req/min
Regions: All GCC
Extraction: html_scrape
"""

from __future__ import annotations

import re

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class GulfTalentPlugin(SourcePlugin):
    """GulfTalent — professional recruitment portal for GCC region."""

    SPEC = ALL_PLUGINS["gulf_talent"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        results: list[SourceResult] = []
        keywords = " ".join(query.keywords or ["recruiter"])
        search_terms = query.company_names + [keywords]

        for term in search_terms[:3]:
            url = "https://www.gulftalent.com/jobs/search"
            try:
                resp = await self.http_client.get(
                    url, params={"keywords": f"{term} recruitment", "location": query.region.value},
                )
                resp.raise_for_status()
                html = resp.text

                # Extract job listings with poster info
                listings = re.findall(r'class="job-item[^"]*"(.*?)</div>', html, re.DOTALL)
                for listing in listings[:10]:
                    name_match = re.search(r'class="poster-name[^"]*"[^>]*>([^<]+)', listing)
                    title_match = re.search(r'class="job-title[^"]*"[^>]*>([^<]+)', listing)
                    company_match = re.search(r'class="company[^"]*"[^>]*>([^<]+)', listing)

                    results.append(self._make_source_result(
                        raw_data={"listing": listing[:500]},
                        extracted_name=name_match.group(1).strip() if name_match else None,
                        extracted_company=company_match.group(1).strip() if company_match else None,
                        extracted_title=title_match.group(1).strip() if title_match else None,
                        source_url=url,
                        confidence_contribution=0.35,
                    ))
            except httpx.HTTPError:
                continue

        return results

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        return contact

    async def validate_config(self) -> bool:
        return True

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(requests_per_minute=self.SPEC.rate_limit_rpm)
