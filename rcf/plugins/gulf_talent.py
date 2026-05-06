"""
GulfTalent Plugin — GCC professional job board.

Rate limit: 6 req/min
Regions: All GCC
Extraction: rest_api (internal JSON API discovered at /api/jobs/search)
"""

from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class GulfTalentPlugin(SourcePlugin):
    """GulfTalent — professional recruitment portal for GCC region.

    Uses GulfTalent's internal JSON API at /api/jobs/search which returns
    structured job data including company name, title, location, salary, etc.
    """

    SPEC = ALL_PLUGINS["gulf_talent"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        results: list[SourceResult] = []
        keywords = " ".join(query.keywords or ["recruiter"])
        search_terms = query.company_names + [keywords]

        for term in search_terms[:3]:
            api_url = "https://www.gulftalent.com/api/jobs/search"
            try:
                resp = await self.http_client.get(
                    api_url,
                    params={
                        "keywords": f"{term} recruitment",
                        "location": query.region.value,
                    },
                    headers={"Accept": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()

                positions = data.get("positions", [])
                total = data.get("total_results", 0)
                self.logger.info(
                    "gulf_talent_api_results",
                    total_available=total,
                    returned=len(positions),
                    term=term,
                )

                for pos in positions[:15]:
                    company = pos.get("company_name")
                    title = pos.get("title")
                    location = pos.get("location")
                    link = pos.get("link")
                    street = pos.get("street_address")
                    industry = pos.get("industry_name_standard")

                    # Build a rich result
                    results.append(self._make_source_result(
                        raw_data={
                            "gulf_talent_id": pos.get("id"),
                            "salary_min": pos.get("minSalary"),
                            "salary_max": pos.get("maxSalary"),
                            "salary_currency": pos.get("salaryCurrency"),
                            "employment_type": pos.get("employment_type"),
                            "posted_date": pos.get("posted_date"),
                            "industry": industry,
                        },
                        extracted_name=None,  # GulfTalent doesn't expose poster names
                        extracted_company=company,
                        extracted_title=title,
                        source_url=link or f"https://www.gulftalent.com/jobs/search?keywords={term}",
                        confidence_contribution=0.35,
                    ))

            except (httpx.HTTPError, ValueError, KeyError) as exc:
                self.logger.warning("gulf_talent_error", error=str(exc), term=term)
                continue

        return results

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        return contact

    async def validate_config(self) -> bool:
        return True

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(requests_per_minute=self.SPEC.rate_limit_rpm)
