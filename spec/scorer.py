"""
Confidence Scoring Engine — UAE/GCC-Optimized Recruiter Contact Quality
========================================================================
Precise, deterministic scoring formula for contact quality assessment.

Score Components:
  Source diversity:  up to 0.40
  Email verification: up to 0.25
  Phone verification: up to 0.20
  Profile richness: up to 0.10
  Freshness penalty: up to -0.15
  Regional bonus:   +0.05

Total range: 0.00 → 1.00

Threshold tiers:
  0.00-0.39: UNUSABLE  (discard)
  0.40-0.59: LOW       (include with warning)
  0.60-0.79: MEDIUM    (usable)
  0.80-0.89: HIGH      (confident)
  0.90-1.00: VERY HIGH (verified)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Threshold Tiers
# ---------------------------------------------------------------------------

class ConfidenceTier(Enum):
    UNUSABLE = "UNUSABLE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


TIER_THRESHOLDS: list[tuple[float, float, ConfidenceTier]] = [
    (0.90, 1.00, ConfidenceTier.VERY_HIGH),
    (0.80, 0.89, ConfidenceTier.HIGH),
    (0.60, 0.79, ConfidenceTier.MEDIUM),
    (0.40, 0.59, ConfidenceTier.LOW),
    (0.00, 0.39, ConfidenceTier.UNUSABLE),
]


def score_to_tier(score: float) -> ConfidenceTier:
    """Map a 0.0-1.0 score to its confidence tier."""
    for low, high, tier in TIER_THRESHOLDS:
        if low <= score <= high:
            return tier
    return ConfidenceTier.UNUSABLE


# ---------------------------------------------------------------------------
# Input Data Models
# ---------------------------------------------------------------------------

@dataclass
class SourceInfo:
    """Information about where the contact data was found."""
    source_names: list[str] = field(default_factory=list)
    """Distinct source names (e.g., 'linkedin', 'bayt', 'expatriates')."""
    first_seen: Optional[datetime] = None
    """When this contact was first discovered."""
    last_seen: Optional[datetime] = None
    """When this contact was last confirmed active."""


@dataclass
class EmailInfo:
    """Email verification state."""
    email: str = ""
    syntax_valid: bool = False
    dns_valid: bool = False
    smtp_verified: bool = False
    api_verified: bool = False
    is_m365_domain: bool = False
    smtp_skipped_m365: bool = False
    alt_verified: bool = False  # HIBP/Gravatar/Social confirmed


@dataclass
class PhoneInfo:
    """Phone verification state."""
    phone: str = ""
    format_valid: bool = False
    carrier_detected: bool = False
    whatsapp_confirmed: bool = False
    is_mobile: bool = False
    is_gcc: bool = False
    twilio_verified: bool = False


@dataclass
class ProfileInfo:
    """Profile richness indicators."""
    linkedin_found: bool = False
    company_verified: bool = False
    title_matched: bool = False
    has_both_email_and_phone: bool = False
    name: str = ""
    company: str = ""
    title: str = ""


@dataclass
class RegionalInfo:
    """Regional metadata."""
    is_uae: bool = False
    is_gcc: bool = False
    country: str = ""


# ---------------------------------------------------------------------------
# Score Breakdown (for transparency/debugging)
# ---------------------------------------------------------------------------

@dataclass
class ScoreBreakdown:
    """Detailed scoring breakdown for a single contact."""
    # Component scores
    source_diversity_score: float = 0.0
    email_score: float = 0.0
    phone_score: float = 0.0
    profile_score: float = 0.0
    freshness_penalty: float = 0.0
    regional_bonus: float = 0.0

    # Inputs used
    num_distinct_sources: int = 0
    days_old: float = 0.0

    # Final
    total_score: float = 0.0
    tier: ConfidenceTier = ConfidenceTier.UNUSABLE

    def to_dict(self) -> dict:
        return {
            "source_diversity": round(self.source_diversity_score, 3),
            "email": round(self.email_score, 3),
            "phone": round(self.phone_score, 3),
            "profile": round(self.profile_score, 3),
            "freshness_penalty": round(self.freshness_penalty, 3),
            "regional_bonus": round(self.regional_bonus, 3),
            "num_sources": self.num_distinct_sources,
            "days_old": round(self.days_old, 1),
            "total": round(self.total_score, 3),
            "tier": self.tier.value,
        }


# ---------------------------------------------------------------------------
# Scoring Formulas
# ---------------------------------------------------------------------------

def compute_source_diversity(num_distinct_sources: int) -> float:
    """
    Source diversity score.

    Formula: min(0.40, num_distinct_sources * 0.10)

    Rationale: More independent sources confirming the same contact
    increases confidence. Diminishing returns after 4 sources.

    Examples:
      1 source  → 0.10
      2 sources → 0.20
      3 sources → 0.30
      4 sources → 0.40 (cap)
      5+ sources → 0.40 (cap)
    """
    return min(0.40, num_distinct_sources * 0.10)


def compute_email_score(email_info: EmailInfo) -> float:
    """
    Email verification score.

    Formula:
      score = 0.0
      if syntax_valid: score += 0.05
      if dns_valid:    score += 0.05
      if smtp_verified: score += 0.10
      if api_verified: score += 0.15
      score = min(score, 0.25)

    UAE M365 adjustment:
      If smtp_skipped_m365 AND alt_verified:
        Treat alt_verified as equivalent to smtp_verified (+0.10)

    Component breakdown:
      Syntax valid:  +0.05  (regex + format check)
      DNS valid:     +0.05  (MX record exists)
      SMTP verified: +0.10  (RCPT TO confirmed on non-M365)
      API verified:  +0.15  (ZeroBounce/NeverBounce/Kickbox confirmed)
    """
    score = 0.0

    if email_info.syntax_valid:
        score += 0.05

    if email_info.dns_valid:
        score += 0.05

    if email_info.smtp_verified:
        score += 0.10

    # UAE M365: alternative verification substitutes for SMTP
    if email_info.smtp_skipped_m365 and email_info.alt_verified:
        score += 0.10

    if email_info.api_verified:
        score += 0.15

    return min(score, 0.25)


def compute_phone_score(phone_info: PhoneInfo) -> float:
    """
    Phone verification score.

    Formula:
      score = 0.0
      if format_valid: score += 0.05
      if carrier_detected: score += 0.05
      if whatsapp_confirmed: score += 0.10
      score = min(score, 0.20)

    Component breakdown:
      Format valid:      +0.05  (E.164 parseable)
      Carrier detected:  +0.05  (Etisalat/du/etc.)
      WhatsApp confirmed: +0.10  (wa.me HTTP check)
    """
    score = 0.0

    if phone_info.format_valid:
        score += 0.05

    if phone_info.carrier_detected:
        score += 0.05

    if phone_info.whatsapp_confirmed:
        score += 0.10

    return min(score, 0.20)


def compute_profile_score(profile_info: ProfileInfo) -> float:
    """
    Profile richness score.

    Formula:
      score = 0.0
      if linkedin_found: score += 0.03
      if company_verified: score += 0.03
      if title_matched: score += 0.02
      if has_both_email_and_phone: score += 0.02
      score = min(score, 0.10)

    Component breakdown:
      LinkedIn found:  +0.03  (profile URL verified)
      Company verified: +0.03  (company name matches source)
      Title matched:   +0.02  (title contains recruiter keywords)
      Both email+phone: +0.02  (contact completeness)
    """
    score = 0.0

    if profile_info.linkedin_found:
        score += 0.03

    if profile_info.company_verified:
        score += 0.03

    if profile_info.title_matched:
        score += 0.02

    if profile_info.has_both_email_and_phone:
        score += 0.02

    return min(score, 0.10)


def compute_freshness_penalty(
    first_seen: Optional[datetime],
    reference_date: Optional[datetime] = None,
) -> float:
    """
    Freshness penalty based on data age.

    Formula:
      days_old = (reference_date - first_seen).days
      penalty = max(-0.15, -(days_old / 180) * 0.15)

    Decay curve:
      0 days:  0.00  (fresh)
      30 days: -0.025
      60 days: -0.05
      90 days: -0.075
      180 days: -0.15 (cap)
      365 days: -0.15 (cap)
    """
    if first_seen is None:
        return -0.15  # Unknown age = maximum penalty

    ref = reference_date or datetime.now(timezone.utc)
    delta = ref - first_seen
    days_old = max(0, delta.total_seconds() / 86400)

    return max(-0.15, -(days_old / 180) * 0.15)


def compute_regional_bonus(regional_info: RegionalInfo) -> float:
    """
    Regional bonus for UAE/GCC contacts.

    Formula:
      bonus = 0.05 if is_uae or is_gcc else 0.0

    Rationale: UAE/GCC contacts are the primary target of this tool.
    Recruiters in the region are more valuable than international ones.
    """
    return 0.05 if (regional_info.is_uae or regional_info.is_gcc) else 0.0


# ---------------------------------------------------------------------------
# Main Scoring Engine
# ---------------------------------------------------------------------------

class ConfidenceScoringEngine:
    """
    Confidence Scoring Engine for recruiter contact quality.

    Combines email verification, phone validation, source diversity,
    profile richness, freshness, and regional relevance into a
    single 0.0-1.0 confidence score.

    Usage:
        engine = ConfidenceScoringEngine()
        score = engine.score(
            source_info=source,
            email_info=email,
            phone_info=phone,
            profile_info=profile,
            regional_info=regional,
        )
        print(f"Score: {score.total_score:.2f} ({score.tier.value})")
    """

    def score(
        self,
        source_info: SourceInfo,
        email_info: EmailInfo,
        phone_info: PhoneInfo,
        profile_info: ProfileInfo,
        regional_info: RegionalInfo,
        reference_date: Optional[datetime] = None,
    ) -> ScoreBreakdown:
        """
        Compute the full confidence score for a contact.

        Returns a ScoreBreakdown with all component scores and the final
        total, enabling transparency and debugging.

        Formula:
          total = min(1.0,
              source_diversity
            + email_score
            + phone_score
            + profile_score
            + freshness_penalty
            + regional_bonus
          )
        """
        # Compute components
        num_sources = len(set(source_info.source_names))
        source_diversity = compute_source_diversity(num_sources)
        email_score = compute_email_score(email_info)
        phone_score = compute_phone_score(phone_info)
        profile_score = compute_profile_score(profile_info)
        freshness_penalty = compute_freshness_penalty(
            source_info.first_seen, reference_date
        )
        regional_bonus = compute_regional_bonus(regional_info)

        # Calculate days_old for breakdown
        days_old = 0.0
        if source_info.first_seen:
            ref = reference_date or datetime.now(timezone.utc)
            days_old = max(0, (ref - source_info.first_seen).total_seconds() / 86400)

        # Final score
        total = min(
            1.0,
            source_diversity
            + email_score
            + phone_score
            + profile_score
            + freshness_penalty
            + regional_bonus,
        )

        # Clamp to [0.0, 1.0]
        total = max(0.0, total)

        return ScoreBreakdown(
            source_diversity_score=source_diversity,
            email_score=email_score,
            phone_score=phone_score,
            profile_score=profile_score,
            freshness_penalty=freshness_penalty,
            regional_bonus=regional_bonus,
            num_distinct_sources=num_sources,
            days_old=days_old,
            total_score=total,
            tier=score_to_tier(total),
        )

    def score_batch(
        self,
        contacts: list[tuple[SourceInfo, EmailInfo, PhoneInfo, ProfileInfo, RegionalInfo]],
        reference_date: Optional[datetime] = None,
    ) -> list[ScoreBreakdown]:
        """Score a batch of contacts."""
        return [
            self.score(src, email, phone, profile, regional, reference_date)
            for src, email, phone, profile, regional in contacts
        ]

    @staticmethod
    def filter_by_tier(
        scores: list[tuple[ScoreBreakdown, object]],
        min_tier: ConfidenceTier = ConfidenceTier.LOW,
    ) -> list[tuple[ScoreBreakdown, object]]:
        """
        Filter contacts by minimum confidence tier.

        Tiers are ordered: UNUSABLE < LOW < MEDIUM < HIGH < VERY_HIGH
        """
        tier_order = {
            ConfidenceTier.UNUSABLE: 0,
            ConfidenceTier.LOW: 1,
            ConfidenceTier.MEDIUM: 2,
            ConfidenceTier.HIGH: 3,
            ConfidenceTier.VERY_HIGH: 4,
        }
        min_level = tier_order[min_tier]
        return [
            (score, contact)
            for score, contact in scores
            if tier_order[score.tier] >= min_level
        ]


# ---------------------------------------------------------------------------
# Example Scenarios (for validation)
# ---------------------------------------------------------------------------

def _example_scores() -> None:
    """Print example scores for validation."""

    engine = ConfidenceScoringEngine()

    # Scenario 1: Perfect contact — LinkedIn + Bayt, verified email, WhatsApp phone
    score1 = engine.score(
        source_info=SourceInfo(
            source_names=["linkedin", "bayt", "expatriates"],
            first_seen=datetime(2026, 4, 1, tzinfo=timezone.utc),
        ),
        email_info=EmailInfo(
            email="ahmed@company.ae",
            syntax_valid=True,
            dns_valid=True,
            smtp_verified=False,
            api_verified=True,
            smtp_skipped_m365=True,
            alt_verified=True,
        ),
        phone_info=PhoneInfo(
            phone="+971501234567",
            format_valid=True,
            carrier_detected=True,
            whatsapp_confirmed=True,
            is_mobile=True,
        ),
        profile_info=ProfileInfo(
            linkedin_found=True,
            company_verified=True,
            title_matched=True,
            has_both_email_and_phone=True,
        ),
        regional_info=RegionalInfo(is_uae=True, is_gcc=True),
    )
    # Expected: ~0.95 (VERY HIGH)

    # Scenario 2: Minimal contact — single source, email only, no verification
    score2 = engine.score(
        source_info=SourceInfo(
            source_names=["expatriates"],
            first_seen=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        email_info=EmailInfo(
            email="recruiter@gmail.com",
            syntax_valid=True,
            dns_valid=True,
        ),
        phone_info=PhoneInfo(),
        profile_info=ProfileInfo(),
        regional_info=RegionalInfo(is_uae=False, is_gcc=False),
    )
    # Expected: ~0.15 (UNUSABLE) — freshness penalty + limited data

    # Scenario 3: Medium contact — 2 sources, phone + WhatsApp, no email verification
    score3 = engine.score(
        source_info=SourceInfo(
            source_names=["dubizzle", "linkedin"],
            first_seen=datetime(2026, 4, 15, tzinfo=timezone.utc),
        ),
        email_info=EmailInfo(
            syntax_valid=False,
        ),
        phone_info=PhoneInfo(
            phone="+971521234567",
            format_valid=True,
            carrier_detected=True,
            whatsapp_confirmed=True,
        ),
        profile_info=ProfileInfo(
            linkedin_found=True,
            has_both_email_and_phone=False,
        ),
        regional_info=RegionalInfo(is_uae=True, is_gcc=True),
    )
    # Expected: ~0.50 (LOW)

    print(f"Scenario 1 (Perfect): {score1.total_score:.3f} [{score1.tier.value}]")
    print(f"  Breakdown: {score1.to_dict()}")
    print(f"Scenario 2 (Minimal): {score2.total_score:.3f} [{score2.tier.value}]")
    print(f"  Breakdown: {score2.to_dict()}")
    print(f"Scenario 3 (Medium):  {score3.total_score:.3f} [{score3.tier.value}]")
    print(f"  Breakdown: {score3.to_dict()}")


if __name__ == "__main__":
    _example_scores()
