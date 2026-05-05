"""Tests for the RCF verification module — re-export facade."""

import importlib

import pytest


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


def test_import_verification():
    """The rcf.verification module is importable."""
    mod = importlib.import_module("rcf.verification")
    assert mod is not None


def test_has_all_exports():
    """The module defines __all__ with the expected verification symbols."""
    import rcf.verification as ver

    assert hasattr(ver, "__all__")
    expected = {
        "EmailVerificationPipeline",
        "EmailVerificationResult",
        "EmailStatus",
        "EmailPipelineConfig",
        "PhoneValidationPipeline",
        "PhoneValidationResult",
        "PhoneStatus",
        "PhonePipelineConfig",
    }
    assert set(ver.__all__) == expected


def test_re_exports_work():
    """All re-exported symbols are present and callable (classes) in the module."""
    import rcf.verification as ver

    for name in ver.__all__:
        obj = getattr(ver, name)
        assert obj is not None, f"{name} is None"
        # These should all be classes (types)
        assert isinstance(obj, type), f"{name} should be a class, got {type(obj)}"
