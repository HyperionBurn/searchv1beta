"""RCF verification — re-export facade for spec/ modules.

Provides unified access to email and phone verification pipelines
from the canonical spec-layer implementations.
"""
from __future__ import annotations

# Email verification
from spec.email_verifier import (
    EmailVerificationPipeline,
    EmailVerificationResult,
    EmailStatus,
    PipelineConfig as EmailPipelineConfig,
)

# Phone validation
from spec.phone_validator import (
    PhoneValidationPipeline,
    PhoneValidationResult,
    PhoneStatus,
    PhonePipelineConfig,
)

__all__ = [
    "EmailVerificationPipeline",
    "EmailVerificationResult",
    "EmailStatus",
    "EmailPipelineConfig",
    "PhoneValidationPipeline",
    "PhoneValidationResult",
    "PhoneStatus",
    "PhonePipelineConfig",
]
