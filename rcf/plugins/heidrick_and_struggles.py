"""
Heidrick & Struggles Plugin — Executive search firm consultant directory.

Rate limit: 6 req/min
Priority: 4 (executive-level only)
Extraction: html_scrape
"""

from __future__ import annotations

import re

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class HeidrickAndStrugglesPlugin(SourcePlugin):
    """Heidrick & Struggles — global executive search consultant profiles."""

    SPEC = ALL_PLUGINS["heidrick_and_struggles"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        results: list[SourceResult] = []
        url = "https://www.heidrick.com/consultants"

        try:
            region_filter = {
                "uae": "middle-east",
                "saudi": "middle-east",
                "qatar": "middle-east",
            }.get(query.region.value, "middle-east")

            resp = await self.http_client.get(
                url, params={"region": region_filter, "q": "recruitment"},
            )
            resp.raise_for_status()
            html = resp.text

            profiles = re.findall(r'class="consultant-card[^"]*"(.*?)</div>', html, re.DOTALL)
            for profile in profiles[:10]:
                name_match = re.search(r'class="name[^"]*"[^>]*>([^<]+)', profile)
                title_match = re.search(r'class="title[^"]*"[^>]*>([^<]+)', profile)
                office_match = re.search(r'class="office[^"]*"[^>]*>([^<]+)', profile)
                link_match = re.search(r'href="(/consultants/[^"]+)"', profile)

                if name_match:
                    results.append(self._make_source_result(
                        raw_data={"profile": profile[:500]},
                        extracted_name=name_match.group(1).strip(),
                        extracted_company="Heidrick & Struggles",
                        extracted_title=title_match.group(1).strip() if title_match else None,
                        source_url=f"https://www.heidrick.com{link_match.group(1)}" if link_match else url,
                        confidence_contribution=0.45,
                    ))
        except httpx.HTTPError:
            pass

        return results

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        return contact

    async def validate_config(self) -> bool:
        return True

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(requests_per_minute=self.SPEC.rate_limit_rpm)
