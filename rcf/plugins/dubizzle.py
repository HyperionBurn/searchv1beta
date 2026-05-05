"""
Dubizzle Plugin — UAE classified ads (direct phone numbers).

Rate limit: 6 req/min
Regions: UAE only
Priority: 1 (highest — direct phone numbers)
"""

from __future__ import annotations

import re

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class DubizzlePlugin(SourcePlugin):
    """Dubizzle — UAE classifieds with recruiter phone numbers."""

    SPEC = ALL_PLUGINS["dubizzle"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        results: list[SourceResult] = []
        search_terms = query.company_names + query.keywords

        for term in search_terms[:3]:
            url = "https://dubai.dubizzle.com/search/"
            try:
                resp = await self.http_client.get(
                    url, params={"q": f"{term} recruiter"},
                )
                resp.raise_for_status()
                html = resp.text

                # Extract phone numbers and titles from listing pages.
                # NOTE: These come from full-page HTML, so phones and titles
                # have NO positional correlation. Return them independently
                # to avoid false phone↔name pairings.
                phones = re.findall(r'(?:\+971|05)\d{8,9}', html)
                titles = re.findall(r'class="title[^"]*"[^>]*>([^<]+)', html)

                for phone in phones[:10]:
                    results.append(self._make_source_result(
                        raw_data={"phone": phone},
                        extracted_name="",
                        extracted_phone=phone,
                        source_url=url,
                        confidence_contribution=0.3,
                    ))
                for title in titles[:10]:
                    results.append(self._make_source_result(
                        raw_data={"listing_title": title.strip()},
                        extracted_name=title.strip(),
                        extracted_phone="",
                        source_url=url,
                        confidence_contribution=0.2,
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
