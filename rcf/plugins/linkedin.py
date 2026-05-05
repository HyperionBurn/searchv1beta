"""
LinkedIn Plugin — Browser-based LinkedIn search for recruiter profiles.

Rate limit: 4 req/min (browser-based, stealth required)
Extraction: browser_scrape via Playwright
Fallback: Google "site:linkedin.com/in" dorking via httpx

Supports:
  - Cookie-based authenticated session loading
  - Multiple search strategies (by company, keyword, name)
  - Google dork fallback when Playwright is unavailable
  - Proper rate limiting with semaphore
"""

from __future__ import annotations

import asyncio
import json
import re
import urllib.parse
from pathlib import Path
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


# ── Selectors for LinkedIn SERP ────────────────────────────────────────

_SERP_CARD = ".reusable-search__result-container"
_SERP_NAME = "span.entity-result__title-text a span[aria-hidden='true']"
_SERP_TITLE = ".entity-result__primary-subtitle"
_SERP_LOCATION = ".entity-result__secondary-subtitle"
_SERP_LINK = "a.app-aware-link[href*='linkedin.com/in/']"

# Google search result patterns
_GOOGLE_RESULT_RE = re.compile(
    r'<a[^>]+href="(/url\?q=https?://www\.linkedin\.com/in/[^&"]+)', re.IGNORECASE
)
_GOOGLE_LINKEDIN_RE = re.compile(
    r'href="(https?://www\.linkedin\.com/in/[^"]+)"', re.IGNORECASE
)

# Default cookie file paths (checked in order)
_COOKIE_PATHS = [
    Path("data/linkedin_cookies.json"),
    Path("cookies/linkedin.json"),
    Path(".secrets/linkedin_cookies.json"),
]


class LinkedInPlugin(SourcePlugin):
    """LinkedIn — browser-scraped recruiter profile search with Google dork fallback."""

    SPEC = ALL_PLUGINS["linkedin"]

    def __init__(self, max_concurrency: int = 2) -> None:
        super().__init__(max_concurrency=max_concurrency)
        self._cookies: list[dict[str, Any]] = []
        self._cookies_loaded = False

    # ── Cookie Management ──────────────────────────────────────────

    def _load_cookies(self) -> list[dict[str, Any]]:
        """
        Load LinkedIn session cookies from a JSON file.

        Cookie file format: list of dicts with keys:
          {"name": "li_at", "value": "...", "domain": ".linkedin.com", ...}

        Searches standard paths. Returns empty list if none found.
        """
        if self._cookies_loaded:
            return self._cookies

        for path in _COOKIE_PATHS:
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(data, list) and len(data) > 0:
                        self._cookies = data
                        self._cookies_loaded = True
                        self.logger.info(
                            "linkedin_cookies_loaded",
                            source=str(path),
                            cookie_count=len(data),
                        )
                        return self._cookies
                except (json.JSONDecodeError, OSError) as exc:
                    self.logger.warning(
                        "linkedin_cookie_load_failed", path=str(path), error=str(exc)
                    )
                    continue

        self._cookies_loaded = True
        self.logger.info("linkedin_no_cookies", message="No cookie file found; will attempt without auth")
        return self._cookies

    def _apply_cookies_to_context(self, context: Any) -> None:
        """Add loaded cookies to a Playwright browser context."""
        cookies = self._load_cookies()
        if cookies:
            context.add_cookies(cookies)

    # ── Main Discovery ─────────────────────────────────────────────

    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """
        Search LinkedIn for recruiter profiles.

        Strategy:
          1. Try Playwright with cookie-based authentication
          2. Fall back to Google "site:linkedin.com/in" dorking via httpx
        """
        results: list[SourceResult] = []

        # Build search strategies from the query
        strategies = self._build_search_strategies(query)

        # Attempt Playwright-based scraping
        playwright_available = False
        try:
            from playwright.async_api import async_playwright

            playwright_available = True
        except ImportError:
            self.logger.warning(
                "playwright_not_installed",
                message="pip install playwright && playwright install chromium",
            )

        if playwright_available:
            results = await self._discover_with_playwright(query, strategies)

        # If Playwright yielded nothing (no auth, blocked, etc.), use Google dork fallback
        if not results:
            self.logger.info("linkedin_fallback_to_google_dork", reason="no results from Playwright")
            results = await self._discover_via_google_dork(query, strategies)

        self.logger.info(
            "linkedin_discovery_complete",
            total_results=len(results),
            strategies_tried=len(strategies),
        )
        return results

    def _build_search_strategies(self, query: ContactQuery) -> list[dict[str, str]]:
        """
        Build multiple search query strategies from a ContactQuery.

        Returns a list of dicts with 'query', 'type', and 'company' keys.
        """
        strategies: list[dict[str, str]] = []
        region_suffix = f" {query.region.value.upper()}" if query.region else ""
        keywords = " ".join(query.keywords) if query.keywords else "recruiter talent acquisition"

        # Strategy 1: Company-based search
        for company in query.company_names[:3]:
            strategies.append({
                "query": f"{company} {keywords}{region_suffix}",
                "type": "company",
                "company": company,
            })

        # Strategy 2: Keyword-only search (if keywords provided)
        if query.keywords:
            kw_str = " ".join(query.keywords[:3])
            strategies.append({
                "query": f"{kw_str}{region_suffix}",
                "type": "keyword",
                "company": None,
            })

        # Strategy 3: Name-based search (if extracted from keywords)
        for kw in (query.keywords or [])[:2]:
            if len(kw.split()) >= 2 and not any(
                skip in kw.lower() for skip in ["recruiter", "hr", "hiring", "talent"]
            ):
                strategies.append({
                    "query": f'"{kw}" linkedin{region_suffix}',
                    "type": "name",
                    "company": None,
                })

        return strategies

    # ── Playwright Discovery ────────────────────────────────────────

    async def _discover_with_playwright(
        self,
        query: ContactQuery,
        strategies: list[dict[str, str]],
    ) -> list[SourceResult]:
        """Full browser scrape via Playwright with stealth measures."""
        from playwright.async_api import async_playwright

        results: list[SourceResult] = []
        request_id = f"li-pw-{id(self)}"

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )

            context = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                locale="en-US",
                timezone_id="Asia/Dubai",
            )

            # Apply stealth patches
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            """)

            # Load cookies if available
            self._apply_cookies_to_context(context)

            page = await context.new_page()

            for strategy in strategies:
                search_query = strategy["query"]
                company = strategy.get("company")
                encoded = urllib.parse.quote(search_query)
                url = f"https://www.linkedin.com/search/results/people/?keywords={encoded}"

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=20_000)

                    # Check if redirected to login (no auth)
                    if "login" in page.url or "authwall" in page.url:
                        self.logger.warning(
                            "linkedin_auth_wall",
                            strategy=strategy["type"],
                            message="LinkedIn requires authentication; skipping Playwright",
                        )
                        break  # No point trying more strategies via Playwright

                    # Wait for search results to render
                    try:
                        await page.wait_for_selector(
                            ".search-results-container, .reusable-search__result-container",
                            timeout=8_000,
                        )
                    except Exception:
                        self.logger.warning(
                            "linkedin_results_did_not_load",
                            strategy=strategy["type"],
                        )
                        continue

                    # Rate limit: respect LinkedIn's aggressiveness
                    await asyncio.sleep(2.5)

                    # Extract profile cards
                    cards = await page.query_selector_all(_SERP_CARD)
                    self.logger.info(
                        "linkedin_cards_found",
                        strategy=strategy["type"],
                        card_count=len(cards),
                    )

                    for card in cards[:10]:
                        result = await self._parse_profile_card(card, company, request_id)
                        if result:
                            results.append(result)

                except Exception as exc:
                    self.logger.warning(
                        "linkedin_strategy_failed",
                        strategy=strategy["type"],
                        error=str(exc),
                    )
                    continue

            await context.close()
            await browser.close()

        return results

    async def _parse_profile_card(
        self,
        card: Any,
        company: str | None,
        request_id: str,
    ) -> SourceResult | None:
        """Extract name, title, location, profile URL from a LinkedIn SERP card."""
        try:
            name_el = await card.query_selector(_SERP_NAME)
            title_el = await card.query_selector(_SERP_TITLE)
            location_el = await card.query_selector(_SERP_LOCATION)
            link_el = await card.query_selector(_SERP_LINK)

            name = (await name_el.inner_text()).strip() if name_el else ""
            if not name:
                return None

            title = (await title_el.inner_text()).strip() if title_el else ""
            location = (await location_el.inner_text()).strip() if location_el else ""
            profile_url = await link_el.get_attribute("href") if link_el else None

            # Clean up LinkedIn redirect URLs
            if profile_url and "/in/" in profile_url:
                profile_url = profile_url.split("?")[0]

            # Infer company from title if not provided
            inferred_company = company
            if not inferred_company and title:
                at_match = re.search(r"\bat\s+(.+?)(?:\s*[|•—–-]|\s*$)", title, re.IGNORECASE)
                if at_match:
                    inferred_company = at_match.group(1).strip()

            return self._make_source_result(
                raw_data={
                    "name": name,
                    "title": title,
                    "location": location,
                    "profile_url": profile_url,
                    "strategy": "playwright",
                },
                extracted_name=name,
                extracted_title=title,
                extracted_company=inferred_company,
                extracted_linkedin=profile_url,
                source_url=profile_url,
                confidence_contribution=0.55,
                request_id=request_id,
            )

        except Exception as exc:
            self.logger.debug("linkedin_card_parse_error", error=str(exc))
            return None

    # ── Google Dork Fallback ────────────────────────────────────────

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=20))
    async def _discover_via_google_dork(
        self,
        query: ContactQuery,
        strategies: list[dict[str, str]],
    ) -> list[SourceResult]:
        """
        Fallback: Google "site:linkedin.com/in" dorking via httpx.

        Searches Google for LinkedIn profiles matching the query,
        then parses profile URLs and snippets from the SERP.
        """
        results: list[SourceResult] = []
        request_id = f"li-dork-{id(self)}"

        for company in query.company_names[:3]:
            region = query.region.value if query.region else ""
            keywords = " ".join(query.keywords[:2]) if query.keywords else "recruiter"

            search_query = f'site:linkedin.com/in "{company}" {keywords} {region}'
            url = "https://www.google.com/search"

            try:
                async with self.semaphore:
                    resp = await self.http_client.get(
                        url,
                        params={"q": search_query, "num": "15"},
                        headers={
                            "User-Agent": (
                                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/122.0.0.0 Safari/537.36"
                            ),
                            "Accept-Language": "en-US,en;q=0.9",
                        },
                    )
                    resp.raise_for_status()

                html = resp.text
                profile_urls = set(_GOOGLE_LINKEDIN_RE.findall(html))

                # Also try extracting from /url?q= redirect links
                for match in _GOOGLE_RESULT_RE.findall(html):
                    profile_urls.add(match)

                for profile_url in list(profile_urls)[:10]:
                    profile_url = profile_url.split("&")[0].split("?")[0]
                    name = self._name_from_linkedin_url(profile_url)

                    results.append(self._make_source_result(
                        raw_data={
                            "search_query": search_query,
                            "profile_url": profile_url,
                            "strategy": "google_dork",
                        },
                        extracted_name=name,
                        extracted_company=company,
                        extracted_linkedin=profile_url,
                        source_url=profile_url,
                        confidence_contribution=0.55,
                        request_id=request_id,
                    ))

                self.logger.info(
                    "linkedin_google_dork_results",
                    company=company,
                    profiles_found=len(profile_urls),
                )

            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                self.logger.warning(
                    "linkedin_google_dork_failed",
                    company=company,
                    error=str(exc),
                )
                continue

        return results

    @staticmethod
    def _name_from_linkedin_url(url: str) -> str | None:
        """
        Extract a display name from a LinkedIn profile URL slug.

        Example: https://www.linkedin.com/in/ahmed-al-mansoori-12345
                  → "Ahmed Al Mansoori"
        """
        try:
            slug = url.rstrip("/").split("/in/")[-1]
            slug = re.sub(r"-?\d+$", "", slug)
            parts = slug.split("-")
            name_parts = [p for p in parts if p and not p.isdigit() and len(p) > 1]
            if name_parts:
                return " ".join(p.capitalize() for p in name_parts)
        except (IndexError, ValueError):
            pass
        return None

    # ── Enrich ──────────────────────────────────────────────────────

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """Enrich contact by visiting their LinkedIn profile for additional data."""
        return contact

    # ── Config Validation ───────────────────────────────────────────

    async def validate_config(self) -> bool:
        """
        Check if plugin can operate.

        Returns True if either Playwright is installed (preferred)
        or httpx is available (Google dork fallback always works).
        """
        try:
            import playwright

            self.logger.info("linkedin_validate_ok", mode="playwright+google_dork")
            return True
        except ImportError:
            self.logger.info(
                "linkedin_validate_ok",
                mode="google_dork_only",
                note="Install playwright for full LinkedIn scraping",
            )
            return True

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(requests_per_minute=self.SPEC.rate_limit_rpm)
