"""
UAE Phone Detector Plugin — Validate and enrich UAE phone numbers.

Rate limit: 60 req/min (local computation)
Priority: 5 (verification-only)
Regions: UAE only
Extraction: local_computation
Delegates to: uae_engine_spec/uae_phone_engine.py
"""

from __future__ import annotations

from typing import Any

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class UAEPhoneDetectorPlugin(SourcePlugin):
    """UAE Phone Detector — validate, format, and enrich UAE phone numbers."""

    SPEC = ALL_PLUGINS["uae_phone_detector"]

    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """Phone detector is verification-only — returns empty for discovery."""
        return []

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """Validate and enrich UAE phone numbers on a contact."""
        try:
            from models.validators import (
                validate_uae_phone,
                infer_uae_carrier,
                infer_uae_emirate,
                is_uae_mobile,
            )
            from models.enums import PhoneType, UAECarrier

            for i, phone_rec in enumerate(contact.phones):
                phone = phone_rec.phone
                if not phone.startswith("+971"):
                    continue

                # Validate format
                try:
                    validated = validate_uae_phone(phone)
                    contact.phones[i].phone = validated
                except ValueError:
                    continue

                # Detect carrier
                carrier_str = infer_uae_carrier(phone)
                if carrier_str and carrier_str != "unknown":
                    try:
                        contact.phones[i].carrier = carrier_str
                    except ValueError:
                        pass

                # Detect line type
                if is_uae_mobile(phone):
                    contact.phones[i].line_type = PhoneType.MOBILE

                # Detect emirate (for landlines)
                emirate = infer_uae_emirate(phone)
                if emirate:
                    # Store emirate info using the existing PhoneRecord fields
                    # (PhoneRecord has no uae_info field, so we avoid setting it)
                    if contact.phones[i].line_type == PhoneType.UNKNOWN:
                        contact.phones[i].line_type = (
                            PhoneType.MOBILE if is_uae_mobile(phone) else PhoneType.LANDLINE
                        )

        except ImportError:
            pass

        return contact

    async def validate_config(self) -> bool:
        return True

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(requests_per_minute=self.SPEC.rate_limit_rpm)
