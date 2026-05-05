"""Verification and scoring specification modules."""

import logging

logger = logging.getLogger(__name__)

try:
    from spec.scorer import ConfidenceScoringEngine, ScoreBreakdown, ConfidenceTier
except ImportError as e:
    logger.warning("spec.scorer import failed: %s", e)

try:
    from spec.email_verifier import EmailVerificationPipeline, EmailVerificationResult
except ImportError as e:
    logger.warning("spec.email_verifier import failed: %s", e)

try:
    from spec.phone_validator import PhoneValidationPipeline, PhoneValidationResult
except ImportError as e:
    logger.warning("spec.phone_validator import failed: %s", e)

try:
    from spec.deduplicator import DeduplicationEngine, MatchResult, MatchType
except ImportError as e:
    logger.warning("spec.deduplicator import failed: %s", e)

try:
    from spec.api_tracker import FreeTierTracker, APIProviderSelector
except ImportError as e:
    logger.warning("spec.api_tracker import failed: %s", e)
