"""
UAE Yellow Pages Plugin — Business directory for UAE companies.

Rate limit: 6 req/min
Regions: UAE only
Extraction: html_scrape
"""

from __future__ import annotations

import re

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class UAEYellowPagesPlugin(SourcePlugin):
    """UAE Yellow Pages — business directory with company phone and address data."""

    SPEC = ALL_PLUGINS["uae_yellow_pages"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        results: list[SourceResult] = []
        search_terms = query.company_names + query.keywords

        for term in search_terms[:3]:
            url = f"https://www.yellowpages.ae/search?q={term}+recruitment"
            try:
                resp = await self.http_client.get(url)
                resp.raise_for_status()
                html = resp.text

                # Parse business listings
                blocks = re.findall(r'<div class="company-card[^"]*">(.*?)</div>', html, re.DOTALL)
                for block in blocks[:10]:
                    name_match = re.search(r'class="company-name[^"]*"[^>]*>([^<]+)', block)
                    phone_match = re.search(r'href="tel:([^"]+)"', block)
                    email_match = re.search(r'href="mailto:([^"]+)"', block)
                    web_match = re.search(r'href="(https?://[^"]+)"[^>]*>.*?website', block, re.IGNORECASE)

                    if name_match:
                        results.append(self._make_source_result(
                            raw_data={"block": block[:500]},
                            extracted_company=name_match.group(1).strip(),
                            extracted_phone=phone_match.group(1) if phone_match else None,
                            extracted_email=email_match.group(1) if email_match else None,
                            source_url=web_match.group(1) if web_match else url,
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
