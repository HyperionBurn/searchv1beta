"""
Confidence Scoring Engine — Adapter for the spec scorer.

Computes composite confidence scores for merged recruiter contacts.
Delegates to spec/scorer.py for the detailed scoring formulas.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from models.models import RecruiterContact

import structlog

logger = structlog.get_logger().bind(component="scorer")


class ConfidenceScoringEngine:
    """
    Scores merged contacts using the multi-factor formula from spec/scorer.py.

    Components:
      Source diversity:  up to 0.40
      Email verification: up to 0.25
      Phone verification: up to 0.20
      Profile richness: up to 0.10
      Freshness penalty: up to -0.15
      Regional bonus:   +0.05

    Total range: 0.00 → 1.00
    """

    def score(self, contact: RecruiterContact) -> RecruiterContact:
        """
        Compute and attach confidence score to a contact.

        Args:
            contact: Merged contact to score.

        Returns:
            Same contact with updated confidence score.
        """
        from spec.scorer import (
            compute_source_diversity,
            compute_email_score,
            compute_phone_score,
            compute_profile_score,
            compute_freshness_penalty,
            compute_regional_bonus,
            EmailInfo,
            PhoneInfo,
            ProfileInfo,
            RegionalInfo,
        )

        # Build info objects from contact data
        num_sources = len(set(s.source_name for s in contact.sources))

        # Email info
        email_info = EmailInfo()
        for email_rec in contact.emails:
            email_info.email = email_rec.email
            email_info.syntax_valid = email_rec.verification_status.value in (
                "syntax_valid", "dns_valid", "smtp_valid", "api_valid"
            )
            email_info.dns_valid = email_rec.verification_status.value in (
                "dns_valid", "smtp_valid", "api_valid"
            )
            email_info.smtp_verified = email_rec.verification_status.value == "smtp_valid"
            email_info.api_verified = email_rec.verification_status.value == "api_valid"
            break  # Use primary email

        # Phone info
        phone_info = PhoneInfo()
        for phone_rec in contact.phones:
            phone_info.phone = phone_rec.phone
            phone_info.format_valid = phone_rec.validation_status.value != "invalid"
            phone_info.carrier_detected = phone_rec.carrier is not None
            phone_info.is_mobile = phone_rec.line_type.value == "mobile"
            phone_info.whatsapp_confirmed = phone_rec.is_whatsapp
            break

        # Profile info
        profile_info = ProfileInfo(
            linkedin_found=bool(contact.linkedin_url),
            company_verified=bool(contact.company),
            title_matched=bool(contact.title),
            has_both_email_and_phone=bool(contact.emails and contact.phones),
            name=contact.name,
            company=contact.company or "",
            title=contact.title or "",
        )

        # Regional info
        from models.enums import Region
        is_uae = contact.region == Region.UAE
        is_gcc = contact.region in (
            Region.UAE, Region.SAUDI, Region.QATAR,
            Region.BAHRAIN, Region.OMAN, Region.KUWAIT,
        )
        regional_info = RegionalInfo(
            is_uae=is_uae,
            is_gcc=is_gcc,
            country=contact.country,
        )

        # Compute scores
        source_diversity = compute_source_diversity(num_sources)
        email_score = compute_email_score(email_info)
        phone_score = compute_phone_score(phone_info)
        profile_score = compute_profile_score(profile_info)

        # Freshness penalty
        freshness_penalty = compute_freshness_penalty(
            first_seen=contact.created_at,
        )

        # Regional bonus
        regional_bonus = compute_regional_bonus(regional_info)

        # Total
        total = source_diversity + email_score + phone_score + profile_score + freshness_penalty + regional_bonus
        total = max(0.0, min(1.0, total))

        # Update contact confidence
        contact.confidence.value = round(total, 4)
        contact.confidence.source_count = num_sources
        contact.confidence.email_verified = email_info.api_verified or email_info.smtp_verified
        contact.confidence.phone_verified = phone_info.format_valid
        contact.confidence.linkedin_found = profile_info.linkedin_found
        contact.confidence.whatsapp_found = phone_info.whatsapp_confirmed
        contact.confidence.calculation_details = {
            "source_diversity": round(source_diversity, 3),
            "email_score": round(email_score, 3),
            "phone_score": round(phone_score, 3),
            "profile_score": round(profile_score, 3),
            "freshness_penalty": round(freshness_penalty, 3),
            "regional_bonus": round(regional_bonus, 3),
        }

        return contact
