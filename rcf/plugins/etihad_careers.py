"""
Etihad Careers Plugin — Etihad Airways recruitment page with recruiter contacts.

Rate limit: 6 req/min
Regions: UAE only
Extraction: drissionpage_scrape (plain HTTP via DrissionPage SessionPage)

Etihad's careers page exposes recruiter/agency email addresses in the HTML.
Live test: 177K chars HTML, 4 recruiter emails found (wearewiser.com agency).
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class EtihadCareersPlugin(SourcePlugin):
    """Etihad Careers — airline recruitment page via DrissionPage."""

    SPEC = ALL_PLUGINS["etihad_careers"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        results: list[SourceResult] = []

        # Search Etihad careers for recruiter-related pages
        search_paths = [
            "https://careers.etihad.com/",
            "https://careers.etihad.com/en/careers",
        ]

        for kw in (query.keywords or [])[:1]:
            search_paths.append(f"https://careers.etihad.com/en/search?q={kw}")

        for url in search_paths[:3]:
            try:
                html = self._fetch_with_drissionpage(url)
                if not html:
                    continue
                extracted = self._extract_contacts(html, url)
                results.extend(extracted)
            except Exception as exc:
                self.logger.warning("etihad_careers_fetch_error", error=str(exc)[:200])
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

    def _extract_contacts(self, html: str, source_url: str) -> list[SourceResult]:
        """Extract recruiter contact data from Etihad Careers HTML."""
        results: list[SourceResult] = []

        # Extract mailto: links (primary source)
        mailto_emails = re.findall(r'href="mailto:([^"]+)"', html)
        # Fallback: raw email patterns
        raw_emails = list(set(re.findall(
            r'[a-zA-Z][a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html,
        )))
        # Filter out non-contact emails
        _skip_domains = ["sentry", "google", "analytics", "facebook", "cdn",
                         "gravatar", "example.com", "w3.org", "schema.org"]
        _skip_patterns = ["noreply", "no-reply", "notification", "newsletter"]
        emails = mailto_emails + [
            e for e in raw_emails
            if not any(s in e.lower() for s in _skip_domains + _skip_patterns)
            and e not in mailto_emails
        ]

        # Extract phone numbers
        phones = re.findall(r'href="tel:([^"]+)"', html)

        # Extract names from email patterns (first.last@domain)
        names = []
        for email in emails:
            local = email.split("@")[0]
            if "." in local and not any(c.isdigit() for c in local):
                parts = local.split(".")
                name = " ".join(p.capitalize() for p in parts if len(p) > 1)
                if name:
                    names.append(name)

        # Build results
        seen = set()
        for i, email in enumerate(emails[:10]):
            if email in seen:
                continue
            seen.add(email)
            name = names[i] if i < len(names) else None
            results.append(self._make_source_result(
                raw_data={"email": email},
                extracted_name=name,
                extracted_email=email,
                extracted_company="Etihad Airways",
                extracted_title="Recruiter" if name else None,
                source_url=source_url,
                confidence_contribution=0.4,
            ))

        for i, phone in enumerate(phones[:10]):
            if phone in seen:
                continue
            seen.add(phone)
            results.append(self._make_source_result(
                raw_data={"phone": phone},
                extracted_company="Etihad Airways",
                extracted_phone=phone,
                source_url=source_url,
                confidence_contribution=0.3,
            ))

        return results

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        return contact

    async def validate_config(self) -> bool:
        return True

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(requests_per_minute=self.SPEC.rate_limit_rpm)
