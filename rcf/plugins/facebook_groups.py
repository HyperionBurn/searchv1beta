"""
Facebook Groups Plugin — Browser-based Facebook group scraping.

Rate limit: 4 req/min (browser-based)
Requires browser: True
Extraction: browser_scrape
Fallback: httpx against m.facebook.com (limited but works without auth)

Supports:
  - Cookie-based authenticated session loading
  - Configurable group URLs (from config.yml or defaults)
  - Playwright full browser scrape with post parsing
  - httpx fallback for lightweight scraping
  - Phone, email, and name extraction from post text
  - Proper retry logic and rate limiting
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote as _url_quote

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


# ── Extraction Patterns ────────────────────────────────────────────────

# UAE phone: +971 followed by 5-9 then 7-8 digits, or 05X local format
_UAE_PHONE_RE = re.compile(r'(?:\+971|05)[0-9]\d{7,8}')
_EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
# Simple name pattern: "My name is Ahmed" or "Contact: Mohammed"
_NAME_HINT_RE = re.compile(
    r'(?:my name is|contact[:\s]+|name[:\s]+|I am|I\'m)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})',
    re.IGNORECASE,
)
# WhatsApp click-to-chat links
_WHATSAPP_LINK_RE = re.compile(r'wa\.me/(\d{10,15})')
# Facebook post author selectors
_AUTHOR_SELECTORS = [
    "a[oakindle-click='actor'] strong",
    "span.x1lliihq.x1plvlek.xryxfnj.x1n2onr6.x193ipt5.x1xmvt09.x1xmf6yo",
    "a[href*='/groups/'] strong",
    "[data-ad-preview='message'] strong",
    "strong span",
]
# Post text selectors
_POST_TEXT_SELECTORS = [
    "[data-ad-preview='message']",
    "div.x1iorvi4.x1pi30zi.x1l90r2v.x1swvt13",
    "div.story_body_container",
    "div[data-ft*='top_level_post_id']",
    "[role='article'] div[dir='auto']",
]

# Default UAE recruiter groups (searchable public groups)
_DEFAULT_GROUP_SLUGS = [
    "uae.recruitment.jobs",
    "dubai.jobs.careers",
    "gcc.hr.professionals",
    "dubai.recruitment.agency",
    "uae.jobs.vacancies",
]

# Default cookie file paths
_COOKIE_PATHS = [
    Path("data/facebook_cookies.json"),
    Path("cookies/facebook.json"),
    Path(".secrets/facebook_cookies.json"),
]


class FacebookGroupsPlugin(SourcePlugin):
    """Facebook Groups — recruiter-focused group posts with contact info."""

    SPEC = ALL_PLUGINS["facebook_groups"]

    def __init__(self, max_concurrency: int = 3) -> None:
        super().__init__(max_concurrency=max_concurrency)
        self._cookies: list[dict[str, Any]] = []
        self._cookies_loaded = False
        self._group_urls: list[str] | None = None

    # ── Configuration ───────────────────────────────────────────────

    def _load_cookies(self) -> list[dict[str, Any]]:
        """
        Load Facebook session cookies from a JSON file.

        Cookie file format: list of dicts with keys:
          {"name": "c_user", "value": "...", "domain": ".facebook.com", ...}

        Key cookies for auth: c_user, xs, fr, sb
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
                            "fb_cookies_loaded",
                            source=str(path),
                            cookie_count=len(data),
                        )
                        return self._cookies
                except (json.JSONDecodeError, OSError) as exc:
                    self.logger.warning(
                        "fb_cookie_load_failed", path=str(path), error=str(exc)
                    )
                    continue

        self._cookies_loaded = True
        self.logger.info("fb_no_cookies", message="No cookie file found; will use limited public access")
        return self._cookies

    def _get_group_urls(self, query: ContactQuery) -> list[str]:
        """
        Get group URLs to scrape. Tries to load from config, falls back to defaults.

        For region-aware group selection, picks relevant groups based on query.region.
        """
        if self._group_urls is not None:
            return self._group_urls

        # Region-based group selection
        region = query.region.value if query.region else "uae"
        slugs = _DEFAULT_GROUP_SLUGS

        # Build mobile FB URLs (lighter pages, easier to parse)
        urls = [f"https://m.facebook.com/groups/{slug}" for slug in slugs]

        # If query has keywords, add search URL for each group
        if query.keywords or query.company_names:
            search_terms = " ".join(
                (query.keywords or []) + query.company_names[:2]
            )
            for slug in slugs[:2]:  # Limit search queries
                encoded = _url_quote(search_terms)
                urls.append(
                    f"https://m.facebook.com/groups/{slug}/search/?q={encoded}"
                )

        self._group_urls = urls
        self.logger.info("fb_groups_configured", group_count=len(urls))
        return urls

    def _apply_cookies_to_context(self, context: Any) -> None:
        """Add loaded cookies to a Playwright browser context."""
        cookies = self._load_cookies()
        if cookies:
            context.add_cookies(cookies)

    # ── Main Discovery ──────────────────────────────────────────────

    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """
        Scrape UAE recruiter Facebook groups for contact posts.

        Strategy:
          1. Try Playwright first for full browser rendering (requires auth cookies)
          2. Fall back to httpx against m.facebook.com (limited but works without auth)
        """
        results: list[SourceResult] = []
        group_urls = self._get_group_urls(query)

        # Attempt Playwright-based scraping
        playwright_available = False
        try:
            from playwright.async_api import async_playwright

            playwright_available = True
        except ImportError:
            self.logger.info(
                "playwright_not_installed",
                message="pip install playwright && playwright install chromium",
            )

        if playwright_available:
            results = await self._scrape_with_playwright(group_urls, query)

        # If Playwright yielded nothing, use httpx fallback
        if not results:
            self.logger.info("fb_fallback_to_httpx", reason="no results from Playwright")
            results = await self._scrape_with_httpx(group_urls)

        self.logger.info(
            "fb_discovery_complete",
            total_results=len(results),
            groups_scraped=len(group_urls),
        )
        return results

    # ── Playwright Scrape ───────────────────────────────────────────

    async def _scrape_with_playwright(
        self,
        group_urls: list[str],
        query: ContactQuery,
    ) -> list[SourceResult]:
        """Full browser scrape via Playwright for richer page content."""
        from playwright.async_api import async_playwright

        results: list[SourceResult] = []
        request_id = f"fb-pw-{id(self)}"

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )

            context = await browser.new_context(
                viewport={"width": 375, "height": 812},
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/16.0 Mobile/15E148 Safari/604.1"
                ),
                locale="en_US",
            )

            # Stealth patch
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)

            # Load cookies for authenticated access
            self._apply_cookies_to_context(context)

            page = await context.new_page()

            for url in group_urls:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=18_000)

                    # Check if redirected to login wall
                    if "login" in page.url and "/groups/" not in page.url:
                        self.logger.warning(
                            "fb_auth_wall",
                            url=url,
                            message="Facebook requires login; will try next URL",
                        )
                        continue

                    # Wait for posts to render
                    try:
                        await page.wait_for_selector(
                            "[data-ft], [role='article'], .story_body_container",
                            timeout=6_000,
                        )
                    except Exception:
                        # No posts loaded — might be auth-required group
                        self.logger.warning("fb_posts_did_not_load", url=url)
                        continue

                    # Rate limit between group pages
                    await asyncio.sleep(2.0)

                    # Extract post content
                    page_results = await self._extract_posts_playwright(
                        page, url, query, request_id
                    )
                    results.extend(page_results)

                    self.logger.info(
                        "fb_group_scraped",
                        url=url,
                        results=len(page_results),
                    )

                except Exception as exc:
                    self.logger.warning(
                        "fb_group_scrape_failed",
                        url=url,
                        error=str(exc),
                    )
                    continue

            await context.close()
            await browser.close()

        return results

    async def _extract_posts_playwright(
        self,
        page: Any,
        source_url: str,
        query: ContactQuery,
        request_id: str,
    ) -> list[SourceResult]:
        """Extract contact info from rendered Facebook group posts."""
        results: list[SourceResult] = []
        seen_phones: set[str] = set()
        seen_emails: set[str] = set()

        # Find all post containers
        posts = await page.query_selector_all("[role='article'], .story_body_container")
        if not posts:
            # Fallback: grab full page text and regex-parse it
            html = await page.content()
            return self._extract_contacts(html, source_url, request_id)

        for post in posts[:20]:  # Limit to 20 posts per group
            try:
                # Extract post text
                post_text = ""
                for sel in _POST_TEXT_SELECTORS:
                    el = await post.query_selector(sel)
                    if el:
                        post_text = (await el.inner_text()).strip()
                        if post_text:
                            break

                if not post_text or len(post_text) < 10:
                    continue

                # Extract author name
                author_name = None
                for sel in _AUTH_SELECTORS:
                    author_el = await post.query_selector(sel)
                    if author_el:
                        author_name = (await author_el.inner_text()).strip()
                        if author_name:
                            break

                # Extract phone numbers
                phones = set(_UAE_PHONE_RE.findall(post_text))
                # Also check for WhatsApp links
                wa_numbers = _WHATSAPP_LINK_RE.findall(post_text)
                for wn in wa_numbers:
                    if wn.startswith("971"):
                        phones.add(f"+{wn}")
                    elif wn.startswith("0"):
                        phones.add(wn)

                # Extract emails
                emails = set(_EMAIL_RE.findall(post_text))

                # Extract name hints from post text
                name_hint = None
                name_match = _NAME_HINT_RE.search(post_text)
                if name_match:
                    name_hint = name_match.group(1).strip()

                # Build results for each phone found
                for phone in phones:
                    if phone in seen_phones:
                        continue
                    seen_phones.add(phone)
                    results.append(self._make_source_result(
                        raw_data={
                            "post_text": post_text[:500],
                            "author": author_name,
                            "name_hint": name_hint,
                            "source": "playwright",
                        },
                        extracted_name=author_name or name_hint,
                        extracted_phone=phone,
                        source_url=source_url,
                        confidence_contribution=0.35,
                        request_id=request_id,
                    ))

                # Build results for each email found
                for email in emails:
                    if email in seen_emails:
                        continue
                    seen_emails.add(email)
                    results.append(self._make_source_result(
                        raw_data={
                            "post_text": post_text[:500],
                            "author": author_name,
                            "source": "playwright",
                        },
                        extracted_name=author_name or name_hint,
                        extracted_email=email,
                        source_url=source_url,
                        confidence_contribution=0.35,
                        request_id=request_id,
                    ))

            except Exception as exc:
                self.logger.debug("fb_post_parse_error", error=str(exc))
                continue

        return results

    # ── HTTPX Fallback ──────────────────────────────────────────────

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=20))
    async def _scrape_with_httpx(self, group_urls: list[str]) -> list[SourceResult]:
        """Lightweight fallback using httpx against m.facebook.com."""
        results: list[SourceResult] = []
        request_id = f"fb-httpx-{id(self)}"
        cookies = self._load_cookies()

        cookie_jar = {}
        for c in cookies:
            if "name" in c and "value" in c:
                cookie_jar[c["name"]] = c["value"]

        for url in group_urls:
            try:
                async with self.semaphore:
                    resp = await self.http_client.get(
                        url,
                        follow_redirects=True,
                        cookies=cookie_jar if cookie_jar else None,
                        headers={
                            "User-Agent": (
                                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                                "Version/16.0 Mobile/15E148 Safari/604.1"
                            ),
                            "Accept-Language": "en-US,en;q=0.9",
                        },
                    )
                    resp.raise_for_status()

                results.extend(self._extract_contacts(resp.text, url, request_id))
                self.logger.info("fb_httpx_group_scraped", url=url)

            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                self.logger.warning(
                    "fb_group_httpx_failed",
                    url=url,
                    error=str(exc),
                )
                continue

        return results

    # ── Shared Extraction ───────────────────────────────────────────

    def _extract_contacts(
        self,
        html: str,
        source_url: str,
        request_id: str | None = None,
    ) -> list[SourceResult]:
        """
        Parse phone numbers, emails, and name hints from HTML/text content.

        Used by both Playwright (as fallback for failed post parsing)
        and httpx scraper.
        """
        results: list[SourceResult] = []

        phones = set(_UAE_PHONE_RE.findall(html))
        emails = set(_EMAIL_RE.findall(html))

        # Also extract WhatsApp links
        for wa_num in _WHATSAPP_LINK_RE.findall(html):
            if wa_num.startswith("971"):
                phones.add(f"+{wa_num}")

        # Try to extract name hints from the text
        name_hint = None
        name_match = _NAME_HINT_RE.search(html)
        if name_match:
            name_hint = name_match.group(1).strip()

        for phone in phones:
            results.append(self._make_source_result(
                raw_data={"phone": phone, "extraction": "regex"},
                extracted_name=name_hint,
                extracted_phone=phone,
                source_url=source_url,
                confidence_contribution=0.35,
                request_id=request_id,
            ))

        for email in emails:
            # Filter out Facebook/system emails
            if any(skip in email.lower() for skip in ["facebookmail.com", "facebook.com"]):
                continue
            results.append(self._make_source_result(
                raw_data={"email": email, "extraction": "regex"},
                extracted_name=name_hint,
                extracted_email=email,
                source_url=source_url,
                confidence_contribution=0.35,
                request_id=request_id,
            ))

        return results

    # ── Enrich ──────────────────────────────────────────────────────

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """Enrich contact with additional Facebook group data."""
        return contact

    # ── Config Validation ───────────────────────────────────────────

    async def validate_config(self) -> bool:
        """
        Check if plugin can operate.

        Returns True if either Playwright is installed (preferred)
        or httpx is available (fallback always works).
        """
        try:
            import playwright

            self.logger.info("fb_validate_ok", mode="playwright+httpx")
            return True
        except ImportError:
            self.logger.info(
                "fb_validate_ok",
                mode="httpx_only",
                note="Install playwright for full Facebook group scraping",
            )
            return True

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(requests_per_minute=self.SPEC.rate_limit_rpm)

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(requests_per_minute=self.SPEC.rate_limit_rpm)
