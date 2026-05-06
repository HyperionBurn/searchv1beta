"""
UAE Yellow Pages Plugin — Business directory for UAE companies.

Rate limit: 6 req/min
Regions: UAE only
Extraction: browser_scrape via Playwright (JS SPA)

NOTE: YellowPages uses an Angular SPA with anti-bot measures.
      Automated searches often hit error-result-page.
      Playwright rendering may yield the shell but no business listings.
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


class UAEYellowPagesPlugin(SourcePlugin):
    """UAE Yellow Pages — business directory (limited by anti-bot measures)."""

    SPEC = ALL_PLUGINS["uae_yellow_pages"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        results: list[SourceResult] = []
        search_terms = list(query.company_names) + list(query.keywords or [])
        if not search_terms:
            search_terms = ["recruitment agency"]

        for term in search_terms[:3]:
            url = f"https://www.yellowpages.ae/search?q={term}+recruitment"

            # Try Playwright first (YellowPages is an Angular SPA)
            pw_results = await self._discover_with_playwright(url, query)
            if pw_results:
                results.extend(pw_results)
                continue

            # Fallback to httpx
            try:
                resp = await self.http_client.get(url)
                resp.raise_for_status()
                html = resp.text
                fallback = self._extract_from_html(html, url, query)
                results.extend(fallback)
            except httpx.HTTPError:
                continue

        return results

    async def _discover_with_playwright(
        self, url: str, query: ContactQuery,
    ) -> list[SourceResult]:
        """Render YellowPages Angular SPA with Playwright and extract listings."""
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

                # Check for error/blocked page
                html = await page.content()
                if "error-result-page" in html:
                    self.logger.info("yellowpages_blocked", reason="error result page returned")
                    await context.close()
                    await browser.close()
                    return []

                extracted = self._extract_from_html(html, url, query)
                results.extend(extracted)

                await context.close()
                await browser.close()
        except Exception as exc:
            self.logger.warning("yellowpages_playwright_error", error=str(exc)[:200])

        return results

    def _extract_from_html(
        self, html: str, source_url: str, query: ContactQuery,
    ) -> list[SourceResult]:
        """Extract contact data from rendered YellowPages HTML.

        Only extracts structured contact links (tel:/mailto:) to avoid false positives
        from JSON-LD metadata and internal phone numbers.
        """
        results: list[SourceResult] = []

        # Extract tel: links only
        phones = re.findall(r'href="tel:([^"]+)"', html)
        # Extract mailto: links
        emails = re.findall(r'href="mailto:([^"]+)"', html)

        # No results if no structured contact links found
        if not phones and not emails:
            return results

        # Extract company names
        names = re.findall(
            r'class="(?:company-name|listing-name|business-name|title)[^"]*"[^>]*>([^<]+)', html,
        )
        # Extract website links (filter out internal/dev/uat domains)
        websites = [
            w for w in re.findall(r'href="(https?://([^"]+))"', html)
            if not any(skip in w[1].lower() for skip in [
                "yellowpages.ae", "uat", "dev", "staging", "localhost",
            ])
        ]
        websites = [w[0] for w in websites]

        seen = set()

        for i, phone in enumerate(phones[:10]):
            if phone in seen:
                continue
            seen.add(phone)
            company = names[i].strip() if i < len(names) else None
            email = emails[i] if i < len(emails) else None
            website = websites[i] if i < len(websites) else None
            results.append(self._make_source_result(
                raw_data={"phone": phone, "email": email},
                extracted_company=company,
                extracted_phone=phone,
                extracted_email=email,
                source_url=website or source_url,
                confidence_contribution=0.35,
            ))

        for i, email in enumerate(emails[:10]):
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
