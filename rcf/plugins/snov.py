"""
Snov.io Plugin — Email finder and domain search API.

Free tier: 50 credits/month
Rate limit: 10 req/min
API docs: https://snov.io/api
"""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class SnovPlugin(SourcePlugin):
    """Snov.io — email finder, domain search, email verification."""

    SPEC = ALL_PLUGINS["snov"]

    async def _get_access_token(self) -> str:
        """Exchange API credentials for OAuth2 access token."""
        import os
        api_key = os.environ.get(self.SPEC.api_key_env, "")
        # Snov.io uses API key directly as Bearer token for v2 API
        # If user provides SNOV_CLIENT_ID + SNOV_CLIENT_SECRET, use OAuth flow
        client_id = os.environ.get("SNOV_CLIENT_ID", "")
        client_secret = os.environ.get("SNOV_CLIENT_SECRET", "")

        if client_id and client_secret:
            resp = await self.http_client.post(
                "https://api.snov.io/v1/oauth/access_token",
                json={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            resp.raise_for_status()
            return resp.json().get("access_token", "")
        # Fallback: use API key as Bearer token (Snov v2 supports this)
        return api_key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        token = await self._get_access_token()
        if not token:
            return []

        results: list[SourceResult] = []
        for company in query.company_names:
            params = {
                "domain": company,
                "type": "all",
                "limit": 10,
                "lastId": 0,
            }
            headers = {"Authorization": f"Bearer {token}"}
            resp = await self.http_client.get(
                f"{self.SPEC.url_pattern}/get-domain-emails",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

            for email_data in data.get("emails", []):
                results.append(self._make_source_result(
                    raw_data=email_data,
                    extracted_name=email_data.get("firstName", "") + " " + email_data.get("lastName", ""),
                    extracted_email=email_data.get("email"),
                    extracted_phone=email_data.get("phone"),
                    extracted_company=company,
                    extracted_title=email_data.get("position"),
                    extracted_linkedin=email_data.get("linkedin"),
                    source_url=email_data.get("sourcePage"),
                    confidence_contribution=0.4,
                ))
        return results

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        return contact  # Snov enrichment is covered in discover

    async def validate_config(self) -> bool:
        return bool(self._resolve_api_key())

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(
            requests_per_minute=self.SPEC.rate_limit_rpm,
            credits_limit=self.SPEC.rate_limit_monthly,
        )
