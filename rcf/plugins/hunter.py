"""
Hunter.io Plugin — Email discovery and domain search API.

Free tier: 50 credits/month
Rate limit: 10 req/min
API docs: https://hunter.io/api-documentation
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import (
    ALL_PLUGINS,
    PluginSpec,
    RateLimitInfo,
    SourcePlugin,
)
from models.models import ContactQuery, RecruiterContact, SourceResult

logger = structlog.get_logger().bind(plugin="hunter")


class HunterPlugin(SourcePlugin):
    """Hunter.io email discovery — domain search, email finder, email verifier."""

    SPEC = ALL_PLUGINS["hunter"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        api_key = self._resolve_api_key()
        if not api_key:
            return []

        results: list[SourceResult] = []

        for company in query.company_names:
            # Domain search: find all emails at a domain
            params: dict[str, Any] = {
                "api_key": api_key,
                "domain": company,
                "limit": 10,
            }
            if query.industry:
                params["industry"] = query.industry

            resp = await self.http_client.get(
                f"{self.SPEC.url_pattern}/domain-search",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            for email_data in data.get("data", {}).get("emails", []):
                results.append(self._make_source_result(
                    raw_data=email_data,
                    extracted_name=email_data.get("first_name", "") + " " + email_data.get("last_name", ""),
                    extracted_email=email_data.get("value"),
                    extracted_phone=email_data.get("phone_number"),
                    extracted_company=company,
                    extracted_title=email_data.get("position"),
                    extracted_linkedin=email_data.get("linkedin"),
                    source_url=email_data.get("sources", [{}])[0].get("uri") if email_data.get("sources") else None,
                    confidence_contribution=0.4,
                    request_id=data.get("meta", {}).get("request_id"),
                ))

        return results

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """Use Hunter email finder to find additional emails for a contact."""
        api_key = self._resolve_api_key()
        if not api_key or not contact.name:
            return contact

        parts = contact.name.split(maxsplit=1)
        first_name = parts[0] if parts else ""
        last_name = parts[1] if len(parts) > 1 else ""
        domain = None
        if contact.company_profile and contact.company_profile.domain_com:
            domain = contact.company_profile.domain_com

        if not domain or not first_name:
            return contact

        params = {
            "api_key": api_key,
            "first_name": first_name,
            "last_name": last_name,
            "domain": domain,
        }

        try:
            resp = await self.http_client.get(
                f"{self.SPEC.url_pattern}/email-finder",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})

            email = data.get("email")
            if email and not any(e.email == email for e in contact.emails):
                from models.models import EmailRecord
                from models.enums import SourceType, VerificationStatus
                contact.emails.append(EmailRecord(
                    email=email,
                    verification_status=VerificationStatus.UNVERIFIED,
                    source=SourceType.API,
                    is_primary=False,
                ))
        except httpx.HTTPError:
            pass

        return contact

    async def validate_config(self) -> bool:
        api_key = self._resolve_api_key()
        if not api_key:
            return False
        try:
            resp = await self.http_client.get(
                f"{self.SPEC.url_pattern}/account",
                params={"api_key": api_key},
            )
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def get_rate_limit_info(self) -> RateLimitInfo:
        api_key = self._resolve_api_key()
        if not api_key:
            return RateLimitInfo(requests_per_minute=0, is_depleted=True)

        try:
            resp = await self.http_client.get(
                f"{self.SPEC.url_pattern}/account",
                params={"api_key": api_key},
            )
            data = resp.json().get("data", {})
            return RateLimitInfo(
                requests_per_minute=self.SPEC.rate_limit_rpm,
                credits_used=data.get("usage", {}).get("requests", 0),
                credits_limit=self.SPEC.rate_limit_monthly,
                credits_remaining=self.SPEC.rate_limit_monthly - data.get("usage", {}).get("requests", 0)
                    if self.SPEC.rate_limit_monthly else None,
                is_depleted=data.get("usage", {}).get("requests", 0) >= (self.SPEC.rate_limit_monthly or 0),
            )
        except httpx.HTTPError:
            return RateLimitInfo(requests_per_minute=self.SPEC.rate_limit_rpm)
