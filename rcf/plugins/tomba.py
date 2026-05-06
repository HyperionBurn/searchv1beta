"""
Tomba.io Plugin — Best Apollo alternative with generous free API.

Free tier: 50 credits/month (verification FREE, unlimited)
Rate limit: 60 req/min
API docs: https://developer.tomba.io/

Tomba provides:
  - Domain search (all emails at a company)
  - Email finder (by name + domain)
  - Email verifier (free, unlimited)
  - Email enrichment (person data from email)
  - LinkedIn finder (email from LinkedIn URL)
  - Phone finder (phone from email/domain/LinkedIn)
  - Author finder (email from article URL)

Auth: Two headers — X-Tomba-Key + X-Tomba-Secret
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult
from models.enums import VerificationStatus, VerificationMethod


class TombaPlugin(SourcePlugin):
    """Tomba.io — Email finder, verifier, phone finder, domain search."""

    SPEC = ALL_PLUGINS["tomba"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """Search for recruiter emails by domain and name."""
        results: list[SourceResult] = []
        api_key = os.environ.get("TOMBA_API_KEY", "")
        api_secret = os.environ.get("TOMBA_API_SECRET", "")
        if not api_key or not api_secret:
            return []

        headers = {
            "X-Tomba-Key": api_key,
            "X-Tomba-Secret": api_secret,
            "Accept": "application/json",
        }

        for company in query.company_names[:3]:
            domain = company.lower().replace(" ", "").replace("&", "and")

            # 1. Domain search — find all emails at company domain
            try:
                resp = await self.http_client.get(
                    f"{self.SPEC.url_pattern}/domain-search",
                    params={"domain": f"{domain}.com", "limit": 20},
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    emails = data.get("data", {}).get("emails", [])
                    for entry in emails[:10]:
                        results.append(SourceResult(
                            source_name=self.name,
                            source_type=self.source_type,
                            extracted_email=entry.get("email", ""),
                            extracted_name=entry.get("first_name", "") + " " + entry.get("last_name", ""),
                            extracted_company=company,
                            extracted_title=entry.get("position", ""),
                            extracted_linkedin=entry.get("linkedin", ""),
                            confidence_contribution=min(entry.get("score", 50) / 100, 0.9),
                            raw_data={
                                "tomba_score": entry.get("score"),
                                "tomba_sources": [s.get("uri") for s in entry.get("sources", [])[:3]],
                            },
                        ))
            except httpx.HTTPError:
                pass

            # 2. Email finder — if query has specific names
            for kw in (query.keywords or [])[:2]:
                parts = kw.strip().split()
                if len(parts) >= 2:
                    try:
                        resp = await self.http_client.get(
                            f"{self.SPEC.url_pattern}/email-finder",
                            params={
                                "domain": f"{domain}.com",
                                "first_name": parts[0],
                                "last_name": parts[-1],
                            },
                            headers=headers,
                        )
                        if resp.status_code == 200:
                            d = resp.json().get("data", {})
                            if d.get("email"):
                                results.append(SourceResult(
                                    source_name=self.name,
                                    source_type=self.source_type,
                                    extracted_email=d["email"],
                                    extracted_name=d.get("full_name", ""),
                                    extracted_company=d.get("company", company),
                                    extracted_title=d.get("position", ""),
                                    confidence_contribution=min(d.get("score", 50) / 100, 0.9),
                                    raw_data={"tomba_score": d.get("score")},
                                ))
                    except httpx.HTTPError:
                        pass

        return results

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """Enrich contact: verify emails + find phone numbers."""
        api_key = os.environ.get("TOMBA_API_KEY", "")
        api_secret = os.environ.get("TOMBA_API_SECRET", "")
        if not api_key or not api_secret:
            return contact

        headers = {
            "X-Tomba-Key": api_key,
            "X-Tomba-Secret": api_secret,
            "Accept": "application/json",
        }

        # Email verification (FREE, unlimited)
        for i, email_rec in enumerate(contact.emails):
            if email_rec.verification_status in (
                VerificationStatus.UNVERIFIED,
                VerificationStatus.SYNTAX_VALID,
            ):
                try:
                    resp = await self.http_client.get(
                        f"{self.SPEC.url_pattern}/email-verifier",
                        params={"email": email_rec.email},
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        data = resp.json().get("data", {})
                        status = data.get("result", "").lower()
                        if status == "deliverable":
                            contact.emails[i].verification_status = VerificationStatus.API_VALID
                            contact.emails[i].verification_method = VerificationMethod.API_CHECK
                        elif status in ("undeliverable", "risky"):
                            contact.emails[i].verification_status = VerificationStatus.INVALID
                            contact.emails[i].verification_method = VerificationMethod.API_CHECK
                        elif status == "catch-all":
                            contact.emails[i].verification_status = VerificationStatus.DNS_VALID
                            contact.emails[i].verification_method = VerificationMethod.API_CHECK
                except httpx.HTTPError:
                    pass

        # Phone finder — find phone from email
        for email_rec in contact.emails:
            if email_rec.email:
                try:
                    resp = await self.http_client.get(
                        f"{self.SPEC.url_pattern}/phone-finder",
                        params={"email": email_rec.email},
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        phone_data = resp.json().get("data", {})
                        if phone_data.get("valid") and phone_data.get("intl_format"):
                            from models.models import PhoneRecord
                            contact.phones.append(PhoneRecord(
                                phone=phone_data["intl_format"],
                                carrier=phone_data.get("carrier", ""),
                                country_code=phone_data.get("country_code", ""),
                            ))
                except httpx.HTTPError:
                    pass
                break

        return contact

    async def validate_config(self) -> bool:
        api_key = os.environ.get("TOMBA_API_KEY", "")
        api_secret = os.environ.get("TOMBA_API_SECRET", "")
        return bool(api_key and api_secret)

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(
            requests_per_minute=self.SPEC.rate_limit_rpm,
            credits_limit=self.SPEC.rate_limit_monthly,
        )
