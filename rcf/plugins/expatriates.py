"""
Expatriates.com Plugin — GCC classified ads (direct phone numbers).

Rate limit: 6 req/min
Priority: 1 (highest — direct phone numbers)
Extraction: html_scrape
"""

from __future__ import annotations

import re

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class ExpatriatesPlugin(SourcePlugin):
    """Expatriates.com — classified ads with recruiter phone numbers."""

    SPEC = ALL_PLUGINS["expatriates"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        results: list[SourceResult] = []
        region_map = {
            "uae": "dubai", "saudi": "riyadh", "qatar": "doha",
            "kuwait": "kuwait", "bahrain": "bahrain", "oman": "oman",
        }
        region_slug = region_map.get(query.region.value, "dubai")

        keywords = query.keywords or ["recruiter", "recruitment", "hiring", "HR"]
        for kw in keywords[:3]:
            url = f"https://www.expatriates.com/classifieds/{region_slug}/index.html"
            try:
                resp = await self.http_client.get(url, params={"q": kw})
                resp.raise_for_status()
                html = resp.text

                # Extract phone numbers and names from classified listings.
                # NOTE: These come from full-page HTML, so phones and names
                # have NO positional correlation. Return them independently
                # to avoid false phone↔name pairings.
                phones = re.findall(r'(?:\+971|05)\d{8,9}', html)
                names = re.findall(r'class="title"[^>]*>([^<]+)', html)

                for phone in phones[:10]:
                    results.append(self._make_source_result(
                        raw_data={"phone": phone},
                        extracted_name="",
                        extracted_phone=phone,
                        source_url=url,
                        confidence_contribution=0.3,
                    ))
                for name in names[:10]:
                    results.append(self._make_source_result(
                        raw_data={"listing_title": name.strip()},
                        extracted_name=name.strip(),
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
