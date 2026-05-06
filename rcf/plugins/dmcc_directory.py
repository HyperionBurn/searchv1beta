"""
DMCC Directory Plugin — Dubai Multi Commodities Centre free-zone business directory.

Rate limit: 6 req/min
Regions: UAE only
Extraction: browser_scrape via Playwright (JS SPA)

NOTE: The DMCC member directory is proprietary and requires member login.
      The SPA search form does not execute via URL parameters alone.
      Playwright rendering yields the page shell but no business listings.
      This plugin attempts extraction but may return 0 results if blocked.
"""

from __future__ import annotations

import re
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class DMCCDirectoryPlugin(SourcePlugin):
    """DMCC Directory — free-zone company listings (limited by proprietary access)."""

    SPEC = ALL_PLUGINS["dmcc_directory"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        results: list[SourceResult] = []

        # Build search terms from companies and keywords
        search_terms = list(query.company_names) + list(query.keywords or [])
        if not search_terms:
            search_terms = ["recruitment"]

        for term in search_terms[:3]:
            search_url = f"https://dmcc.ae/business-directory?q={term}"

            # Try Playwright first (DMCC is a JS SPA)
            pw_results = await self._discover_with_playwright(search_url, query)
            if pw_results:
                results.extend(pw_results)
                continue

            # Fallback to httpx
            try:
                resp = await self.http_client.get(search_url)
                resp.raise_for_status()
                html = resp.text
                fallback = self._extract_from_html(html, search_url, query)
                results.extend(fallback)
            except httpx.HTTPError:
                continue

        return results

    async def _discover_with_playwright(
        self, url: str, query: ContactQuery,
    ) -> list[SourceResult]:
        """Render DMCC SPA with Playwright and attempt listing extraction."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return []

        results: list[SourceResult] = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                )
                context = await browser.new_context(
                    viewport={"width": 1440, "height": 900},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    ),
                )
                await context.add_init_script(
                    'Object.defineProperty(navigator, "webdriver", { get: () => undefined });'
                )
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
                await page.wait_for_timeout(5000)

                # Check if business listings are present in visible text
                visible = await page.inner_text("body")
                if "proprietary information" in visible.lower():
                    self.logger.info("dmcc_directory_blocked", reason="proprietary access required")
                    await context.close()
                    await browser.close()
                    return []

                html = await page.content()
                extracted = self._extract_from_html(html, url, query)
                results.extend(extracted)

                await context.close()
                await browser.close()
        except Exception as exc:
            self.logger.warning("dmcc_playwright_error", error=str(exc)[:200])

        return results

    def _extract_from_html(
        self, html: str, source_url: str, query: ContactQuery,
    ) -> list[SourceResult]:
        """Extract contact data from rendered DMCC HTML.

        Only extracts structured contact links (tel:/mailto:) to avoid false positives
        from menu IDs, CSS values, and JSON-LD metadata.
        """
        results: list[SourceResult] = []

        # Extract tel: links only (no raw phone number guessing)
        phones = re.findall(r'href="tel:([^"]+)"', html)
        # Extract mailto: links
        emails = re.findall(r'href="mailto:([^"]+)"', html)

        # No results if no structured contact links found
        if not phones and not emails:
            return results

        # Extract company names from listing cards
        names = re.findall(
            r'class="(?:title|company-name|business-name|listing-name)[^"]*"[^>]*>([^<]+)', html,
        )

        # Deduplicate phones/emails
        seen_phones = set()
        seen_emails = set()

        for i, phone in enumerate(phones[:10]):
            if phone not in seen_phones:
                seen_phones.add(phone)
                company = names[i].strip() if i < len(names) else None
                results.append(self._make_source_result(
                    raw_data={"phone": phone, "email": emails[i] if i < len(emails) else None},
                    extracted_company=company,
                    extracted_phone=phone,
                    extracted_email=emails[i] if i < len(emails) else None,
                    source_url=source_url,
                    confidence_contribution=0.4,
                ))

        for i, email in enumerate(emails[:10]):
            if email not in seen_emails:
                seen_emails.add(email)
                if any(r.raw_data.get("email") == email for r in results):
                    continue
                company = names[i].strip() if i < len(names) else None
                results.append(self._make_source_result(
                    raw_data={"email": email},
                    extracted_company=company,
                    extracted_email=email,
                    source_url=source_url,
                    confidence_contribution=0.4,
                ))

        return results

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        return contact

    async def validate_config(self) -> bool:
        return True

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(requests_per_minute=self.SPEC.rate_limit_rpm)
