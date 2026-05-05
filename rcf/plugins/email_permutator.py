"""
Email Permutator Plugin — Generate email permutations from name + domain.

Rate limit: 60 req/min (local computation)
Priority: 5 (fallback / supplementary)
Extraction: local_computation
"""

from __future__ import annotations

from typing import Any

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult
from models.enums import SourceType


# Email pattern templates (common in UAE/GCC corporate)
EMAIL_PATTERNS: list[str] = [
    "{first}.{last}",
    "{first}{last}",
    "{first}_{last}",
    "{f}{last}",
    "{first}{l}",
    "{first}",
    "{first}.{last}2",
    "{last}.{first}",
    "{f}.{last}",
    "{first}-{last}",
]


class EmailPermutatorPlugin(SourcePlugin):
    """Email Permutator — generate email guesses from name + company domain."""

    SPEC = ALL_PLUGINS["email_permutator"]

    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        """
        Generate email permutations for each company in the query.

        Uses known email patterns and company domain to produce
        candidate email addresses. These are then verified by
        the email verification pipeline.
        """
        results: list[SourceResult] = []

        for company in query.company_names:
            domain = self._guess_domain(company)
            if not domain:
                continue

            # For each keyword (potential person name), generate permutations
            for keyword in query.keywords[:5]:
                name_parts = keyword.strip().split()
                if len(name_parts) < 2:
                    continue

                first = name_parts[0].lower()
                last = name_parts[-1].lower()
                f = first[0] if first else ""
                l = last[0] if last else ""

                for pattern in EMAIL_PATTERNS:
                    local_part = pattern.format(
                        first=first, last=last, f=f, l=l,
                    )
                    email = f"{local_part}@{domain}"

                    results.append(self._make_source_result(
                        raw_data={"pattern": pattern, "domain": domain},
                        extracted_email=email,
                        extracted_company=company,
                        confidence_contribution=0.15,  # Low — unverified guess
                    ))

        return results

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """Generate email permutations for a contact if they have no email."""
        if contact.emails or not contact.name:
            return contact

        domain = None
        if contact.company_profile:
            domain = contact.company_profile.domain_com or contact.company_profile.domain_ae
        if not domain and contact.company:
            domain = self._guess_domain(contact.company)
        if not domain:
            return contact

        parts = contact.name.strip().split()
        if len(parts) < 2:
            return contact

        first = parts[0].lower()
        last = parts[-1].lower()
        f = first[0]
        l = last[0]

        from models.models import EmailRecord
        from models.enums import VerificationStatus

        for pattern in EMAIL_PATTERNS:
            local_part = pattern.format(first=first, last=last, f=f, l=l)
            email = f"{local_part}@{domain}"
            if not any(e.email == email for e in contact.emails):
                contact.emails.append(EmailRecord(
                    email=email,
                    verification_status=VerificationStatus.UNVERIFIED,
                    source=SourceType.PERMUTATION,
                    is_primary=False,
                ))

        return contact

    async def validate_config(self) -> bool:
        return True  # No config needed

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(requests_per_minute=self.SPEC.rate_limit_rpm)

    @staticmethod
    def _guess_domain(company: str) -> str | None:
        """Guess a company domain from its name."""
        if not company:
            return None
        slug = company.lower().strip()
        # Remove common suffixes
        for suffix in (" llc", " fze", " fzco", " fzc", " l.l.c", " inc", " ltd"):
            slug = slug.replace(suffix, "")
        slug = slug.replace(" ", "").replace("&", "and")
        # Try .com first (60% of UAE companies use .com)
        return f"{slug}.com"
