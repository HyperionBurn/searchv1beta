"""
WhatsApp Checker Plugin — Verify WhatsApp presence for phone numbers.

Rate limit: 10 req/min
Priority: 5 (verification-only)
Extraction: whatsapp_api
Delegates to: uae_engine_spec/whatsapp_engine.py
"""

from __future__ import annotations

from typing import Any

import httpx

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class WhatsAppCheckerPlugin(SourcePlugin):
    """WhatsApp Checker — verify if phone numbers have WhatsApp accounts."""

    SPEC = ALL_PLUGINS["whatsapp_checker"]

    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """WhatsApp checker is verification-only — returns empty for discovery."""
        return []

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """Check WhatsApp presence for all phone numbers on a contact."""
        try:
            from uae_engine_spec.whatsapp_engine import check_whatsapp_presence

            for i, phone_rec in enumerate(contact.phones):
                try:
                    result = await check_whatsapp_presence(phone_rec.phone)
                    if result:
                        contact.phones[i].is_whatsapp = result.get("has_whatsapp", False)
                        contact.phones[i].whatsapp_business = result.get("is_business", False)
                        contact.confidence.whatsapp_found = True
                except Exception:
                    continue

            # Check dedicated WhatsApp number
            if contact.whatsapp_number:
                try:
                    result = await check_whatsapp_presence(contact.whatsapp_number)
                    if result and result.get("has_whatsapp"):
                        contact.confidence.whatsapp_found = True
                except Exception:
                    pass

        except ImportError:
            # Fallback: simple HTTP check via wa.me
            for i, phone_rec in enumerate(contact.phones):
                try:
                    # Strip + from E.164 for wa.me URL
                    clean = phone_rec.phone.replace("+", "")
                    resp = await self.http_client.get(
                        f"https://wa.me/{clean}",
                        follow_redirects=True,
                    )
                    # If we get a 200, number has WhatsApp
                    if resp.status_code == 200:
                        contact.phones[i].is_whatsapp = True
                        contact.confidence.whatsapp_found = True
                except httpx.HTTPError:
                    continue

        return contact

    async def validate_config(self) -> bool:
        return True  # No API key required for basic checks

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(requests_per_minute=self.SPEC.rate_limit_rpm)
