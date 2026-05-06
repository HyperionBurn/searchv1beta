"""
YellowPages-UAE.com Directory Plugin — Comprehensive UAE recruitment agency directory.

Rate limit: 6 req/min
Regions: UAE only
Extraction: drissionpage_scrape (plain HTTP via DrissionPage SessionPage)

This is a DIFFERENT site from yellowpages.ae (Angular SPA that blocks).
yellowpages-uae.com returns full HTML with structured tel:/mailto: links,
company names, and addresses — all via plain HTTP, no JS rendering needed.

Live test: 333K chars HTML, 10+ emails, 20+ phones, 8+ company names.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class YpUaeDirectoryPlugin(SourcePlugin):
    """YellowPages-UAE.com — structured recruitment agency directory via DrissionPage."""

    SPEC = ALL_PLUGINS["yp_uae_directory"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        results: list[SourceResult] = []
        search_terms = list(query.company_names) + list(query.keywords or [])
        if not search_terms:
            search_terms = ["recruitment"]

        for term in search_terms[:3]:
            url = f"https://www.yellowpages-uae.com/uae/{term.replace(' ', '-')}"
            try:
                html = self._fetch_with_drissionpage(url)
                if not html:
                    continue
                extracted = self._extract_listings(html, url)
                results.extend(extracted)
            except Exception as exc:
                self.logger.warning("yp_uae_fetch_error", error=str(exc)[:200])
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
        """Extract structured contact data from YellowPages-UAE HTML."""
        results: list[SourceResult] = []

        # Extract tel: links
        phones = re.findall(r'href="tel:([^"]+)"', html)
        # Extract mailto: links
        emails = re.findall(r'href="mailto:([^"]+)"', html)
        # Clean up HTML entity artifacts
        emails = [e.replace("&gt;", "").replace("u003e", "") for e in emails]
        emails = [e for e in emails if "@" in e and "." in e.split("@")[1]]

        # Extract company names from listing headings
        names = re.findall(
            r'class="(?:company-name|listing-name|business-name|title|'
            r'listing_title|entry-title)[^"]*"[^>]*>([^<]+)',
            html,
        )
        if not names:
            # Fallback: h2/h3 headings with meaningful length
            raw_names = re.findall(r'<h[23][^>]*>([^<]{5,100})</h[23]>', html)
            _skip = {"home", "about", "contact", "search", "login", "privacy",
                     "terms", "categories", "popular", "browse"}
            names = [n.strip() for n in raw_names
                     if n.strip().lower() not in _skip and not n.strip().startswith("<")]

        # Extract addresses
        addresses = re.findall(
            r'class="(?:address|location|area)[^"]*"[^>]*>([^<]+)',
            html,
        )

        # Build results by pairing phones with companies
        seen = set()
        for i, phone in enumerate(phones[:20]):
            if phone in seen:
                continue
            seen.add(phone)
            company = names[i].strip() if i < len(names) else None
            email = emails[i] if i < len(emails) else None
            addr = addresses[i].strip() if i < len(addresses) else None
            results.append(self._make_source_result(
                raw_data={"phone": phone, "email": email, "address": addr},
                extracted_company=company,
                extracted_phone=phone,
                extracted_email=email,
                source_url=source_url,
                confidence_contribution=0.4,
            ))

        # Add remaining emails not already paired
        for i, email in enumerate(emails[:20]):
            if email in seen:
                continue
            seen.add(email)
            if any(r.raw_data.get("email") == email for r in results):
                continue
            company = names[i].strip() if i < len(names) else None
            results.append(self._make_source_result(
                raw_data={"email": email},
                extracted_company=company,
                extracted_email=email,
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
