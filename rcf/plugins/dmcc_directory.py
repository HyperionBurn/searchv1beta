"""
DMCC Directory Plugin — Dubai Multi Commodities Centre free-zone business directory.

Rate limit: 6 req/min
Regions: UAE only
Extraction: html_scrape
"""

from __future__ import annotations

import re
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class DMCCDirectoryPlugin(SourcePlugin):
    """DMCC Directory — free-zone company listings with contact details."""

    SPEC = ALL_PLUGINS["dmcc_directory"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        results: list[SourceResult] = []

        for company in query.company_names:
            search_url = f"https://www.dmcc.ae/business-search?q={company}"
            try:
                resp = await self.http_client.get(search_url)
                resp.raise_for_status()
                html = resp.text

                # Parse business listings from HTML
                # DMCC returns company cards with name, phone, email, category
                company_blocks = re.findall(
                    r'<div class="business-card[^"]*">(.*?)</div>\s*</div>',
                    html, re.DOTALL,
                )
                for block in company_blocks[:10]:
                    name_match = re.search(r'class="title"[^>]*>([^<]+)', block)
                    phone_match = re.search(r'href="tel:([^"]+)"', block)
                    email_match = re.search(r'href="mailto:([^"]+)"', block)

                    if name_match:
                        name = name_match.group(1).strip()
                        # Check if company name matches query
                        if company.lower() in name.lower() or any(
                            kw in name.lower() for kw in query.keywords
                        ):
                            results.append(self._make_source_result(
                                raw_data={"html_block": block[:500]},
                                extracted_name=name,
                                extracted_email=email_match.group(1) if email_match else None,
                                extracted_phone=phone_match.group(1) if phone_match else None,
                                extracted_company=name,
                                source_url=search_url,
                                confidence_contribution=0.4,
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
