"""
NumLookupAPI Phone Validation Plugin — Free phone number validation.

Free tier: 100 requests/month
Rate limit: 6 req/min
API docs: https://numlookupapi.com/

NumLookupAPI provides:
  - Phone number validation (format + carrier + line type)
  - Caller ID / caller name lookup
  - International format normalization
  - Line type detection (mobile, landline, VoIP)
  - Carrier identification

Supports UAE (+971) and all GCC countries.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult
from models.enums import VerificationStatus, VerificationMethod
from models.enums import PhoneType


class NumLookupPlugin(SourcePlugin):
    """NumLookupAPI — Free phone validation + carrier detection."""

    SPEC = ALL_PLUGINS["numlookup"]

    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """NumLookup is validation-only — returns empty for discovery."""
        return []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """Validate phone numbers using NumLookupAPI."""
        api_key = self._resolve_api_key()
        if not api_key:
            return contact

        for i, phone_rec in enumerate(contact.phones):
            if phone_rec.validation_status in (
                VerificationStatus.UNVERIFIED,
                VerificationStatus.SYNTAX_VALID,
            ):
                try:
                    resp = await self.http_client.get(
                        f"{self.SPEC.url_pattern}/validate/{phone_rec.phone}",
                        params={"apikey": api_key},
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    valid = data.get("valid", False)
                    if valid:
                        contact.phones[i].validation_status = VerificationStatus.API_VALID
                        contact.phones[i].validation_method = VerificationMethod.API_CHECK

                        # Enrich carrier info
                        carrier = data.get("carrier", "")
                        if carrier:
                            contact.phones[i].carrier = carrier

                        # Line type
                        line_type = data.get("line_type", "").lower()
                        line_map = {
                            "mobile": PhoneType.MOBILE,
                            "landline": PhoneType.LANDLINE,
                            "voip": PhoneType.MOBILE,
                            "tollfree": PhoneType.TOLLFREE,
                            "premium": PhoneType.PREMIUM,
                        }
                        if line_type in line_map:
                            contact.phones[i].line_type = line_map[line_type]

                        # Caller name (if available)
                        caller_name = data.get("caller_name", "")
                        if caller_name and not contact.name:
                            contact.name = caller_name

                        # Country info
                        country_code = data.get("country_code", "")
                        country_name = data.get("country_name", "")
                        if country_code:
                            contact.phones[i].country_code = country_code
                    else:
                        contact.phones[i].validation_status = VerificationStatus.INVALID
                        contact.phones[i].validation_method = VerificationMethod.API_CHECK

                except httpx.HTTPError:
                    pass

        return contact

    async def validate_config(self) -> bool:
        return bool(self._resolve_api_key())

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(
            requests_per_minute=self.SPEC.rate_limit_rpm,
            credits_limit=self.SPEC.rate_limit_monthly,
        )
