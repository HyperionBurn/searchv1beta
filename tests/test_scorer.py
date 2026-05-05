"""
Tests for the confidence scoring engine (spec/scorer.py + rcf/core/scorer.py).

Covers:
  - Known input produces expected score range
  - High source diversity → higher score
  - Verified email → higher score
  - Fresh data → higher score
  - Score tiers map correctly (UNUSABLE, LOW, MEDIUM, HIGH, VERY_HIGH)
"""

import pytest
from datetime import datetime, timezone, timedelta

from spec.scorer import (
    ConfidenceTier,
    ConfidenceScoringEngine as SpecScoringEngine,
    EmailInfo,
    PhoneInfo,
    ProfileInfo,
    RegionalInfo,
    ScoreBreakdown,
    SourceInfo,
    compute_email_score,
    compute_freshness_penalty,
    compute_phone_score,
    compute_profile_score,
    compute_regional_bonus,
    compute_source_diversity,
    score_to_tier,
)


# ===========================================================================
# Individual scoring functions
# ===========================================================================


class TestComputeSourceDiversity:
    def test_one_source(self):
        assert compute_source_diversity(1) == 0.10

    def test_two_sources(self):
        assert compute_source_diversity(2) == 0.20

    def test_three_sources(self):
        assert compute_source_diversity(3) == pytest.approx(0.30)

    def test_four_sources_caps_at_040(self):
        assert compute_source_diversity(4) == 0.40

    def test_five_sources_still_040(self):
        assert compute_source_diversity(5) == 0.40

    def test_zero_sources(self):
        assert compute_source_diversity(0) == 0.0


class TestComputeEmailScore:
    def test_no_verification(self):
        info = EmailInfo()
        assert compute_email_score(info) == 0.0

    def test_syntax_only(self):
        info = EmailInfo(syntax_valid=True)
        assert compute_email_score(info) == pytest.approx(0.05)

    def test_dns_valid(self):
        info = EmailInfo(syntax_valid=True, dns_valid=True)
        assert compute_email_score(info) == pytest.approx(0.10)

    def test_smtp_verified(self):
        info = EmailInfo(syntax_valid=True, dns_valid=True, smtp_verified=True)
        assert compute_email_score(info) == pytest.approx(0.20)

    def test_api_verified(self):
        info = EmailInfo(
            syntax_valid=True, dns_valid=True, smtp_verified=True, api_verified=True
        )
        assert compute_email_score(info) == pytest.approx(0.25)  # capped

    def test_max_cap(self):
        """Even with all flags, score caps at 0.25."""
        info = EmailInfo(
            syntax_valid=True, dns_valid=True,
            smtp_verified=True, api_verified=True,
        )
        assert compute_email_score(info) <= 0.25


class TestComputePhoneScore:
    def test_no_info(self):
        info = PhoneInfo()
        assert compute_phone_score(info) == 0.0

    def test_format_valid_only(self):
        info = PhoneInfo(format_valid=True)
        assert compute_phone_score(info) == pytest.approx(0.05)

    def test_format_and_carrier(self):
        info = PhoneInfo(format_valid=True, carrier_detected=True)
        assert compute_phone_score(info) == pytest.approx(0.10)

    def test_whatsapp_confirmed(self):
        info = PhoneInfo(
            format_valid=True, carrier_detected=True, whatsapp_confirmed=True
        )
        assert compute_phone_score(info) == pytest.approx(0.20)  # cap

    def test_max_cap(self):
        info = PhoneInfo(
            format_valid=True, carrier_detected=True,
            whatsapp_confirmed=True,
        )
        assert compute_phone_score(info) <= 0.20


class TestComputeProfileScore:
    def test_no_info(self):
        info = ProfileInfo()
        assert compute_profile_score(info) == 0.0

    def test_linkedin_only(self):
        info = ProfileInfo(linkedin_found=True)
        assert compute_profile_score(info) == pytest.approx(0.03)

    def test_all_richness(self):
        info = ProfileInfo(
            linkedin_found=True,
            company_verified=True,
            title_matched=True,
            has_both_email_and_phone=True,
        )
        assert compute_profile_score(info) == pytest.approx(0.10)  # cap

    def test_max_cap(self):
        info = ProfileInfo(
            linkedin_found=True,
            company_verified=True,
            title_matched=True,
            has_both_email_and_phone=True,
        )
        assert compute_profile_score(info) <= 0.10


class TestComputeFreshnessPenalty:
    def test_fresh_data_no_penalty(self):
        now = datetime.now(timezone.utc)
        assert compute_freshness_penalty(now) == pytest.approx(0.0, abs=0.01)

    def test_old_data_penalty(self):
        old = datetime.now(timezone.utc) - timedelta(days=180)
        penalty = compute_freshness_penalty(old)
        assert penalty <= 0.0
        assert penalty >= -0.15

    def test_none_data_max_penalty(self):
        assert compute_freshness_penalty(None) == -0.15

    def test_very_old_data_caps_at_minus_015(self):
        very_old = datetime.now(timezone.utc) - timedelta(days=365)
        assert compute_freshness_penalty(very_old) >= -0.15


class TestComputeRegionalBonus:
    def test_uae_gets_bonus(self):
        info = RegionalInfo(is_uae=True)
        assert compute_regional_bonus(info) == pytest.approx(0.05)

    def test_gcc_gets_bonus(self):
        info = RegionalInfo(is_gcc=True, is_uae=False)
        assert compute_regional_bonus(info) == pytest.approx(0.05)

    def test_non_gcc_no_bonus(self):
        info = RegionalInfo(is_uae=False, is_gcc=False)
        assert compute_regional_bonus(info) == pytest.approx(0.0)


# ===========================================================================
# Score tier mapping
# ===========================================================================


class TestScoreToTier:
    @pytest.mark.parametrize("score,expected_tier", [
        (0.95, ConfidenceTier.VERY_HIGH),
        (0.90, ConfidenceTier.VERY_HIGH),
        (0.85, ConfidenceTier.HIGH),
        (0.80, ConfidenceTier.HIGH),
        (0.70, ConfidenceTier.MEDIUM),
        (0.60, ConfidenceTier.MEDIUM),
        (0.50, ConfidenceTier.LOW),
        (0.40, ConfidenceTier.LOW),
        (0.30, ConfidenceTier.UNUSABLE),
        (0.10, ConfidenceTier.UNUSABLE),
        (0.00, ConfidenceTier.UNUSABLE),
    ])
    def test_tier_mapping(self, score, expected_tier):
        assert score_to_tier(score) == expected_tier


# ===========================================================================
# Full scoring engine
# ===========================================================================


class TestSpecScoringEngine:
    def setup_method(self):
        self.engine = SpecScoringEngine()

    def _make_ideal_inputs(self):
        """Returns inputs for a near-perfect score."""
        return (
            SourceInfo(source_names=["linkedin", "bayt", "google_maps", "hunter"]),
            EmailInfo(syntax_valid=True, dns_valid=True, smtp_verified=True, api_verified=True),
            PhoneInfo(format_valid=True, carrier_detected=True, whatsapp_confirmed=True),
            ProfileInfo(
                linkedin_found=True,
                company_verified=True,
                title_matched=True,
                has_both_email_and_phone=True,
            ),
            RegionalInfo(is_uae=True),
        )

    def test_ideal_contact_high_score(self):
        src, email, phone, profile, regional = self._make_ideal_inputs()
        result = self.engine.score(src, email, phone, profile, regional)
        assert result.total_score >= 0.80
        assert result.tier in (ConfidenceTier.HIGH, ConfidenceTier.VERY_HIGH)

    def test_minimal_contact_low_score(self):
        src = SourceInfo(source_names=["one_source"])
        email = EmailInfo()
        phone = PhoneInfo()
        profile = ProfileInfo()
        regional = RegionalInfo()

        result = self.engine.score(src, email, phone, profile, regional)
        assert result.total_score < 0.30
        assert result.tier == ConfidenceTier.UNUSABLE

    def test_high_source_diversity_increases_score(self):
        src = SourceInfo(source_names=["a", "b", "c", "d"])
        email = EmailInfo()
        phone = PhoneInfo()
        profile = ProfileInfo()
        regional = RegionalInfo(is_uae=True)

        result = self.engine.score(src, email, phone, profile, regional)

        # 4 sources = 0.40 diversity + 0.05 regional - 0.15 freshness (no first_seen) = 0.30
        assert result.source_diversity_score == pytest.approx(0.40)
        assert result.total_score >= 0.30  # Source diversity + regional bonus exceeds 0.30

    def test_verified_email_increases_score(self):
        src = SourceInfo(source_names=["src"])
        email_unverified = EmailInfo()
        email_verified = EmailInfo(syntax_valid=True, dns_valid=True, api_verified=True)
        phone = PhoneInfo()
        profile = ProfileInfo()
        regional = RegionalInfo()

        score_unverified = self.engine.score(src, email_unverified, phone, profile, regional)
        score_verified = self.engine.score(src, email_verified, phone, profile, regional)

        assert score_verified.total_score > score_unverified.total_score

    def test_fresh_data_higher_than_stale(self):
        src = SourceInfo(
            source_names=["src"],
            first_seen=datetime.now(timezone.utc),
        )
        src_stale = SourceInfo(
            source_names=["src"],
            first_seen=datetime.now(timezone.utc) - timedelta(days=180),
        )
        email = EmailInfo()
        phone = PhoneInfo()
        profile = ProfileInfo()
        regional = RegionalInfo()

        fresh_score = self.engine.score(src, email, phone, profile, regional)
        stale_score = self.engine.score(src_stale, email, phone, profile, regional)

        assert fresh_score.total_score > stale_score.total_score

    def test_breakdown_dict(self):
        src, email, phone, profile, regional = self._make_ideal_inputs()
        result = self.engine.score(src, email, phone, profile, regional)
        d = result.to_dict()
        assert "source_diversity" in d
        assert "email" in d
        assert "phone" in d
        assert "profile" in d
        assert "freshness_penalty" in d
        assert "regional_bonus" in d
        assert "total" in d
        assert "tier" in d

    def test_score_batch(self):
        inputs = self._make_ideal_inputs()
        results = self.engine.score_batch([inputs, inputs])
        assert len(results) == 2
        assert all(isinstance(r, ScoreBreakdown) for r in results)

    def test_filter_by_tier(self):
        src, email, phone, profile, regional = self._make_ideal_inputs()
        high_score = self.engine.score(src, email, phone, profile, regional)

        low_src = SourceInfo(source_names=["a"])
        low_email = EmailInfo()
        low_phone = PhoneInfo()
        low_profile = ProfileInfo()
        low_regional = RegionalInfo()
        low_score = self.engine.score(low_src, low_email, low_phone, low_profile, low_regional)

        contacts = [("high", high_score), ("low", low_score)]
        filtered = SpecScoringEngine.filter_by_tier(
            [(s, label) for (label, s) in contacts],
            min_tier=ConfidenceTier.MEDIUM,
        )
        # The high score should pass, low should not
        assert any(label == "high" for s, label in filtered)
