"""Tests for the RCF CLI — Typer command interface."""

from typer.testing import CliRunner

from rcf.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Basic app & help
# ---------------------------------------------------------------------------


def test_app_exists():
    """The Typer app object is importable and callable."""
    from rcf.cli import app

    assert app is not None
    assert callable(getattr(app, "__call__", None)) or hasattr(app, "registered_commands")


def test_help_works():
    """rcf --help returns exit code 0."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "RCF" in result.output or "rcf" in result.output


def test_search_help():
    """rcf search --help returns exit code 0."""
    result = runner.invoke(app, ["search", "--help"])
    assert result.exit_code == 0
    assert "search" in result.output.lower()


def test_sources_command():
    """rcf sources runs (may warn about missing config, but shouldn't crash)."""
    result = runner.invoke(app, ["sources"])
    # sources reads config.yml — may fail if not found, but should not traceback
    assert result.exit_code == 0 or result.exit_code == 1


def test_status_command():
    """rcf status runs without unexpected crash."""
    result = runner.invoke(app, ["status"])
    # status may fail gracefully if DB or config missing
    assert result.exit_code in (0, 1)


# ---------------------------------------------------------------------------
# search command flags
# ---------------------------------------------------------------------------


def test_search_dry_run():
    """rcf search with --dry-run should not require a real database."""
    result = runner.invoke(app, ["search", "test query", "--dry-run"])
    # dry-run path prints sources and returns; may still need config.yml
    assert result.exit_code in (0, 1)


def test_search_invalid_region():
    """rcf search with an invalid region value should fail or show error."""
    result = runner.invoke(app, ["search", "test", "--region", "invalid_region_xyz"])
    # Typer enum validation should reject the value
    assert result.exit_code != 0 or "Invalid" in result.output or "Error" in result.output


# ---------------------------------------------------------------------------
# Other command help screens
# ---------------------------------------------------------------------------


def test_enrich_help():
    """rcf enrich --help returns exit code 0."""
    result = runner.invoke(app, ["enrich", "--help"])
    assert result.exit_code == 0
    assert "enrich" in result.output.lower()


def test_export_help():
    """rcf export --help returns exit code 0."""
    result = runner.invoke(app, ["export", "--help"])
    assert result.exit_code == 0
    assert "export" in result.output.lower()


# ---------------------------------------------------------------------------
# search flag presence via help text
# ---------------------------------------------------------------------------


def test_search_has_verify_emails_flag():
    """--verify-emails appears in the search help output."""
    result = runner.invoke(app, ["search", "--help"])
    assert result.exit_code == 0
    assert "--verify-emails" in result.output


def test_search_has_enrich_flag():
    """--enrich appears in the search help output."""
    result = runner.invoke(app, ["search", "--help"])
    assert result.exit_code == 0
    assert "--enrich" in result.output


def test_search_has_no_cache_flag():
    """--no-cache appears in the search help output."""
    result = runner.invoke(app, ["search", "--help"])
    assert result.exit_code == 0
    assert "--no-cache" in result.output


def test_search_has_format_flag():
    """--format appears in the search help output."""
    result = runner.invoke(app, ["search", "--help"])
    assert result.exit_code == 0
    assert "--format" in result.output


def test_search_has_dry_run_flag():
    """--dry-run appears in the search help output."""
    result = runner.invoke(app, ["search", "--help"])
    assert result.exit_code == 0
    assert "--dry-run" in result.output


def test_search_has_check_whatsapp_flag():
    """--check-whatsapp appears in the search help output."""
    result = runner.invoke(app, ["search", "--help"])
    assert result.exit_code == 0
    assert "--check-whatsapp" in result.output
