"""
Arabic Name Normalizer Plugin — Normalize Arabic names and generate email permutations.

Rate limit: 60 req/min (local computation)
Priority: 5 (supplementary)
Extraction: local_computation
Delegates to: uae_engine_spec/arabic_name_engine.py
"""

from __future__ import annotations

from typing import Any

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult, ArabicName
from models.enums import SourceType


class ArabicNameNormalizerPlugin(SourcePlugin):
    """Arabic Name Normalizer — normalize Arabic names, generate variants and permutations."""

    SPEC = ALL_PLUGINS["arabic_name_normalizer"]

    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """Name normalizer is a utility — returns empty for discovery."""
        return []

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """
        Normalize Arabic name and generate email permutations.

        Handles:
          - Al/El/Bin/Bint prefix stripping
          - Mohammed variant unification (30+ spellings)
          - Arabic name variant generation
          - Email local-part permutation generation
        """
        if not contact.name:
            return contact

        # Parse Arabic name using existing engine
        try:
            arabic_name = ArabicName(original_name=contact.name)
            contact.arabic_name = arabic_name

            # If contact has no first/last name set, use parsed values
            # Generate additional email permutations if we have a domain
            if arabic_name.email_permutations and contact.company_profile:
                domain = (
                    contact.company_profile.domain_com
                    or contact.company_profile.domain_ae
                )
                if domain:
                    from models.models import EmailRecord
                    from models.enums import VerificationStatus

                    for local_part in arabic_name.email_permutations[:20]:
                        email = f"{local_part}@{domain}"
                        if not any(e.email == email for e in contact.emails):
                            contact.emails.append(EmailRecord(
                                email=email,
                                verification_status=VerificationStatus.UNVERIFIED,
                                source=SourceType.PERMUTATION,
                                is_primary=False,
                            ))

        except Exception:
            pass

        return contact

    async def validate_config(self) -> bool:
        return True

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(requests_per_minute=self.SPEC.rate_limit_rpm)
