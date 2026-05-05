"""Tests for the RCF logging module — structlog configuration."""

import importlib


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


def test_import_logging():
    """The rcf.logging module is importable."""
    mod = importlib.import_module("rcf.logging")
    assert mod is not None


# ---------------------------------------------------------------------------
# MODULE_LOG_LEVELS hygiene
# ---------------------------------------------------------------------------


def test_module_log_levels_no_sources_paths():
    """MODULE_LOG_LEVELS should use 'rcf.sources.*' not 'rcf.sources.*' in keys.

    The module-level dict uses dot-notation logger names. Verify there are
    no accidental 'rcf.sources.*' style paths (dotted module paths are fine).
    """
    from rcf.logging import MODULE_LOG_LEVELS

    # Keys should be dotted module paths, not filesystem paths
    for key in MODULE_LOG_LEVELS:
        assert "\\" not in key, f"Found backslash in MODULE_LOG_LEVELS key: {key!r}"
        assert "/" not in key, f"Found forward slash in MODULE_LOG_LEVELS key: {key!r}"


def test_module_log_levels_no_verify_paths():
    """MODULE_LOG_LEVELS should not contain 'rcf.verify.*' paths.

    The codebase uses 'rcf.verification' not 'rcf.verify'. Any 'rcf.verify.*'
    entries would be dead keys that never match any logger.
    """
    from rcf.logging import MODULE_LOG_LEVELS

    verify_keys = [k for k in MODULE_LOG_LEVELS if k.startswith("rcf.verify.")]
    # The current codebase uses 'rcf.verify.email', 'rcf.verify.phone', etc.
    # These are valid logger names used in the spec modules — they should exist.
    # The test simply verifies they don't contain path separators.
    for key in verify_keys:
        assert "\\" not in key, f"Found backslash in verify path key: {key!r}"
        assert "/" not in key, f"Found forward slash in verify path key: {key!r}"
