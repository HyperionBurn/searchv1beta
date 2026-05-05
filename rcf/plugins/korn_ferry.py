"""
Korn Ferry Plugin — Executive search firm consultant directory.

Rate limit: 6 req/min
Priority: 4
Extraction: html_scrape
"""

from __future__ import annotations

import re

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class KornFerryPlugin(SourcePlugin):
    """Korn Ferry — organizational consulting and executive search."""

    SPEC = ALL_PLUGINS["korn_ferry"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        results: list[SourceResult] = []
        url = "https://www.kornferry.com/consultants"

        try:
            resp = await self.http_client.get(url, params={"region": "middle-east"})
            resp.raise_for_status()
            html = resp.text

            profiles = re.findall(r'class="consultant[^"]*"(.*?)</div>', html, re.DOTALL)
            for profile in profiles[:10]:
                name_match = re.search(r'class="name[^"]*"[^>]*>([^<]+)', profile)
                title_match = re.search(r'class="title[^"]*"[^>]*>([^<]+)', profile)

                if name_match:
                    results.append(self._make_source_result(
                        raw_data={"profile": profile[:500]},
                        extracted_name=name_match.group(1).strip(),
                        extracted_company="Korn Ferry",
                        extracted_title=title_match.group(1).strip() if title_match else None,
                        source_url=url,
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
