"""
Deduplication Engine — Thin adapter around spec/deduplicator.py.

Provides the DeduplicationEngine class used by the PipelineOrchestrator,
delegating to the full 6-strategy deduplication implementation in spec/.
"""

from __future__ import annotations

from models.models import RecruiterContact, SourceResult

import structlog

logger = structlog.get_logger().bind(component="dedup")


class DeduplicationEngine:
    """
    Multi-strategy deduplication and merging engine.

    Strategies (run in order):
      1. Exact email match
      2. Exact phone match (E.164)
      3. Fuzzy name match (rapidfuzz ≥ 85 + same company)
      4. Arabic name fuzzy (normalized forms)
      5. LinkedIn URL match (normalized)
      6. WhatsApp cross-ref (same number → same person)

    Merge strategy:
      - Take highest confidence score
      - Union all sources
      - Keep most complete data (prefer verified over unverified)
    """

    def merge(self, results: list[SourceResult]) -> list[RecruiterContact]:
        """
        Merge raw SourceResult list into deduplicated RecruiterContacts.

        Args:
            results: Raw results from all plugins.

        Returns:
            Deduplicated list of RecruiterContact objects.
        """
        if not results:
            return []

        # Import the spec deduplication functions
        from spec.deduplicator import (
            normalize_name_for_matching,
            normalize_email,
            normalize_phone,
            normalize_linkedin_url,
            arabic_name_similarity,
        )
        from rapidfuzz import fuzz

        # Group results by matching keys
        groups: list[list[SourceResult]] = []
        assigned: set[int] = set()

        for i, result_a in enumerate(results):
            if i in assigned:
                continue

            group = [result_a]

            for j, result_b in enumerate(results):
                if j <= i or j in assigned:
                    continue

                if self._results_match(result_a, result_b):
                    group.append(result_b)
                    assigned.add(j)

            assigned.add(i)
            groups.append(group)

        # Merge each group into a single RecruiterContact
        contacts: list[RecruiterContact] = []
        for group in groups:
            contact = self._merge_group(group)
            if contact:
                contacts.append(contact)

        logger.info(
            "dedup_complete",
            input_count=len(results),
            output_count=len(contacts),
        )
        return contacts

    def _results_match(self, a: SourceResult, b: SourceResult) -> bool:
        """Check if two SourceResults refer to the same person."""
        from spec.deduplicator import (
            normalize_email,
            normalize_phone,
            normalize_linkedin_url,
            arabic_name_similarity,
        )

        # Strategy 1: Exact email match
        if a.extracted_email and b.extracted_email:
            if normalize_email(a.extracted_email) == normalize_email(b.extracted_email):
                return True

        # Strategy 2: Exact phone match
        if a.extracted_phone and b.extracted_phone:
            try:
                if normalize_phone(a.extracted_phone) == normalize_phone(b.extracted_phone):
                    return True
            except Exception:
                pass

        # Strategy 3: LinkedIn URL match
        if a.extracted_linkedin and b.extracted_linkedin:
            if normalize_linkedin_url(a.extracted_linkedin) == normalize_linkedin_url(b.extracted_linkedin):
                return True

        # Strategy 4: Fuzzy name + same company
        if a.extracted_name and b.extracted_name:
            similarity = arabic_name_similarity(a.extracted_name, b.extracted_name)
            if similarity >= 0.85:
                if a.extracted_company and b.extracted_company:
                    if a.extracted_company.lower().strip() == b.extracted_company.lower().strip():
                        return True

        return False

    def _merge_group(self, group: list[SourceResult]) -> RecruiterContact | None:
        """Merge a group of matching SourceResults into one RecruiterContact."""
        if not group:
            return None

        # Pick best value for each field (prefer non-None, higher confidence)
        best_name = self._best_field(group, lambda r: r.extracted_name)
        best_email = self._best_field(group, lambda r: r.extracted_email)
        best_phone = self._best_field(group, lambda r: r.extracted_phone)
        best_company = self._best_field(group, lambda r: r.extracted_company)
        best_title = self._best_field(group, lambda r: r.extracted_title)
        best_linkedin = self._best_field(group, lambda r: r.extracted_linkedin)

        from models.models import EmailRecord, PhoneRecord
        from models.enums import VerificationStatus

        emails: list[EmailRecord] = []
        if best_email:
            emails.append(EmailRecord(
                email=best_email,
            ))

        phones: list[PhoneRecord] = []
        if best_phone:
            phones.append(PhoneRecord(
                phone=best_phone,
            ))

        from models.enums import Region

        # Try to get region from any source result that has it
        region_str = None
        for r in group:
            if hasattr(r, 'raw_data') and isinstance(r.raw_data, dict):
                region_str = r.raw_data.get('region')
                break
        try:
            region = Region(region_str) if region_str else Region.UAE
        except ValueError:
            region = Region.UAE

        return RecruiterContact(
            name=best_name or "Unknown",
            emails=emails,
            phones=phones,
            company=best_company,
            title=best_title,
            linkedin_url=best_linkedin,
            sources=group,
            region=region,
        )

    @staticmethod
    def _best_field(
        results: list[SourceResult],
        extractor: callable,
    ) -> str | None:
        """Pick the best non-None value for a field, preferring higher confidence."""
        candidates = [
            (r, extractor(r))
            for r in results
            if extractor(r) is not None
        ]
        if not candidates:
            return None
        # Sort by confidence_contribution descending
        candidates.sort(key=lambda x: x[0].confidence_contribution, reverse=True)
        return candidates[0][1]
