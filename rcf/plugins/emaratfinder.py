"""
Emaratfinder Plugin — UAE recruitment agency directory with phone numbers.

Rate limit: 6 req/min
Regions: UAE only
Extraction: drissionpage_scrape (plain HTTP via DrissionPage SessionPage)

Emaratfinder.com lists recruitment agencies in the UAE with phone numbers,
addresses, and business hours — all via plain HTTP, no JS rendering needed.

Live test: 171K chars HTML, 10+ phone numbers via tel: links.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class EmaratfinderPlugin(SourcePlugin):
    """Emaratfinder — UAE recruitment agency directory via DrissionPage."""

    SPEC = ALL_PLUGINS["emaratfinder"]

    # Search categories on Emaratfinder
    _CATEGORIES = [
        "recruitment-agency",
        "employment-agency",
        "staffing-agency",
        "manpower-supply",
    ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        results: list[SourceResult] = []

        # Build search categories from keywords
        categories = self._CATEGORIES[:2]  # Start with top 2 categories
        for kw in (query.keywords or [])[:1]:
            categories.insert(0, kw.replace(" ", "-"))

        for cat in categories[:3]:
            url = f"https://emaratfinder.com/categories/en/{cat}"
            try:
                html = self._fetch_with_drissionpage(url)
                if not html:
                    continue
                extracted = self._extract_listings(html, url)
                results.extend(extracted)
            except Exception as exc:
                self.logger.warning("emaratfinder_fetch_error", error=str(exc)[:200])
                continue

        return results

    def _fetch_with_drissionpage(self, url: str) -> str:
        """Fetch HTML using DrissionPage SessionPage (HTTP-only, no browser)."""
        try:
            from DrissionPage import SessionPage
            page = SessionPage()
            page.get(url)
            return page.html if hasattr(page, "html") and page.html else ""
        except ImportError:
            self.logger.warning("drissionpage_not_installed")
            return ""

    def _extract_listings(self, html: str, source_url: str) -> list[SourceResult]:
        """Extract structured contact data from Emaratfinder HTML."""
        results: list[SourceResult] = []

        # Extract tel: links
        phones = re.findall(r'href="tel:([^"]+)"', html)

        # Extract company names from listing cards
        names = re.findall(
            r'class="(?:business-name|company-name|listing-name|title|'
            r'card-title|item-name)[^"]*"[^>]*>([^<]+)',
            html,
        )
        if not names:
            # Fallback: look for name patterns near phone numbers
            raw_names = re.findall(r'<h[234][^>]*class="[^"]*"[^>]*>([^<]{5,100})</h[234]>', html)
            _skip = {"home", "about", "contact", "search", "categories", "popular",
                     "emaratfinder", "browse", "all rights"}
            names = [n.strip() for n in raw_names
                     if n.strip().lower() not in _skip and not n.strip().startswith("<")]

        # Extract addresses
        addresses = re.findall(
            r'class="(?:address|location|area)[^"]*"[^>]*>([^<]+)',
            html,
        )

        # Build results
        seen = set()
        for i, phone in enumerate(phones[:20]):
            if phone in seen:
                continue
            seen.add(phone)
            company = names[i].strip() if i < len(names) else None
            addr = addresses[i].strip() if i < len(addresses) else None
            results.append(self._make_source_result(
                raw_data={"phone": phone, "address": addr},
                extracted_company=company,
                extracted_phone=phone,
                source_url=source_url,
                confidence_contribution=0.35,
            ))

        return results

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        return contact

    async def validate_config(self) -> bool:
        return True

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(requests_per_minute=self.SPEC.rate_limit_rpm)
