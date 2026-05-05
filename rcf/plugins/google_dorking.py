"""
Google Dorking Plugin — Advanced Google search operators for email/phone discovery.

Rate limit: 6 req/min
Priority: 2
Extraction: html_scrape
Delegates to: uae_engine_spec/uae_google_dork.py
"""

from __future__ import annotations

import re
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


# Google dork templates for recruiter email/phone discovery
DORK_TEMPLATES: list[str] = [
    '"{company}" "recruiter" "@{domain}" email',
    '"{company}" "recruitment" email contact',
    '"{company}" "HR" site:linkedin.com',
    '"{company}" "recruiter" "+971" OR "05"',
    '"{company}" "talent acquisition" email',
    '"{company}" "@{domain}" "recruiter"',
]


class GoogleDorkingPlugin(SourcePlugin):
    """Google Dorking — OSINT email/phone discovery via Google search operators."""

    SPEC = ALL_PLUGINS["google_dorking"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        results: list[SourceResult] = []

        for company in query.company_names:
            domain = company.lower().replace(" ", "").replace("&", "and") + ".com"

            for dork in DORK_TEMPLATES[:3]:
                search_query = dork.format(company=company, domain=domain)
                url = "https://www.google.com/search"
                try:
                    resp = await self.http_client.get(
                        url, params={"q": search_query, "num": 10},
                        headers={"Accept-Language": "en-US,en;q=0.9"},
                    )
                    resp.raise_for_status()
                    html = resp.text

                    # Extract emails
                    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)
                    # Extract UAE phone numbers
                    phones = re.findall(r'(?:\+971|05)\d{8,9}', html)

                    for email in set(emails[:5]):
                        # Filter out Google's own emails and common non-personal
                        if any(skip in email.lower() for skip in ["google.com", "gmail.com", "support@", "info@"]):
                            continue
                        results.append(self._make_source_result(
                            raw_data={"dork": dork, "email": email},
                            extracted_email=email,
                            extracted_company=company,
                            source_url=f"https://www.google.com/search?q={search_query}",
                            confidence_contribution=0.3,
                        ))

                    for phone in set(phones[:5]):
                        results.append(self._make_source_result(
                            raw_data={"dork": dork, "phone": phone},
                            extracted_phone=phone,
                            extracted_company=company,
                            source_url=f"https://www.google.com/search?q={search_query}",
                            confidence_contribution=0.3,
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
