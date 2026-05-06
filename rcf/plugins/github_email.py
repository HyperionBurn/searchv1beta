"""
GitHub Email Extractor Plugin — Extract emails from GitHub commit history.

Free tier: 60 req/hr unauthenticated, 5,000 req/hr with token
Rate limit: 10 req/min
API docs: https://docs.github.com/en/rest

Extracts public emails from GitHub user commit events.
Useful for finding tech recruiters who contribute to open source.

Strategy:
  1. Search GitHub for users matching company/role keywords
  2. Fetch public events for each user
  3. Extract emails from commit payloads
  4. Cross-reference with Gravatar for profile enrichment
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult
from models.enums import (
    VerificationStatus, VerificationMethod,
)


class GitHubEmailPlugin(SourcePlugin):
    """GitHub — Extract recruiter emails from public commit history."""

    SPEC = ALL_PLUGINS["github_email"]

    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """Search GitHub users by company/role and extract emails from commits."""
        results: list[SourceResult] = []

        headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        token = self._resolve_api_key()
        if token:
            headers["Authorization"] = f"token {token}"

        # Search for users matching query terms
        for company in query.company_names[:3]:
            search_queries = [
                f'"{company}" recruiter',
                f'"{company}" talent acquisition',
                f'"{company}" HR',
            ]

            for sq in search_queries[:2]:
                try:
                    resp = await self.http_client.get(
                        f"{self.SPEC.url_pattern}/search/users",
                        params={"q": sq, "per_page": 10},
                        headers=headers,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    users = data.get("items", [])

                    for user in users[:5]:
                        username = user.get("login", "")
                        if not username:
                            continue

                        # Fetch user profile for company info
                        profile = await self._fetch_user_profile(username, headers)
                        company_name = profile.get("company", "")

                        # Fetch public events to extract commit emails
                        email = await self._extract_commit_email(username, headers)
                        name = profile.get("name", "") or username

                        if email:
                            results.append(SourceResult(
                                source_name=self.name,
                                source_type=self.source_type,
                                extracted_name=name,
                                extracted_email=email,
                                extracted_company=company_name or company,
                                extracted_title="Recruiter",
                                confidence_contribution=0.35,
                                raw_data={
                                    "github_username": username,
                                    "github_url": user.get("html_url", ""),
                                    "source": "github_commits",
                                },
                            ))

                except httpx.HTTPError:
                    continue

        return results

    async def _fetch_user_profile(self, username: str, headers: dict) -> dict:
        """Fetch GitHub user profile for name, company, bio."""
        try:
            resp = await self.http_client.get(
                f"{self.SPEC.url_pattern}/users/{username}",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            return {}

    async def _extract_commit_email(self, username: str, headers: dict) -> str:
        """Extract email from user's public commit events."""
        try:
            resp = await self.http_client.get(
                f"{self.SPEC.url_pattern}/users/{username}/events/public",
                params={"per_page": 30},
                headers=headers,
            )
            resp.raise_for_status()
            events = resp.json()

            for event in events:
                if event.get("type") == "PushEvent":
                    commits = event.get("payload", {}).get("commits", [])
                    for commit in commits:
                        author = commit.get("author", {})
                        email = author.get("email", "")
                        # Skip noreply emails (GitHub privacy)
                        if email and "@users.noreply.github.com" not in email:
                            return email
            return ""
        except httpx.HTTPError:
            return ""

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """Enrich contact with Gravatar profile data if email available."""
        for email_rec in contact.emails:
            if email_rec.email and not email_rec.verification_status == VerificationStatus.API_VALID:
                try:
                    # Gravatar profile lookup from email hash
                    email_hash = hashlib.md5(
                        email_rec.email.strip().lower().encode()
                    ).hexdigest()
                    resp = await self.http_client.get(
                        f"https://en.gravatar.com/{email_hash}.json",
                        headers={"Accept": "application/json"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        entry = data.get("entry", [{}])[0]
                        if entry.get("displayName") and not contact.name:
                            contact.name = entry["displayName"]
                except httpx.HTTPError:
                    pass
                break
        return contact

    async def validate_config(self) -> bool:
        """GitHub works without token (60/hr) — always valid."""
        return True

    async def get_rate_limit_info(self) -> RateLimitInfo:
        token = self._resolve_api_key()
        return RateLimitInfo(
            requests_per_minute=self.SPEC.rate_limit_rpm,
            requests_per_month=5000 * 30 if token else 60 * 24 * 30,
        )
