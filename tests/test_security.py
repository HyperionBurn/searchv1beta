"""Security-focused tests — scan for hardcoded secrets in source files."""

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Pattern for detecting hardcoded API keys / secrets / tokens / passwords
# ---------------------------------------------------------------------------

SECRET_PATTERN = re.compile(
    r'(?:api[_-]?key|secret|token|password)\s*[=:]\s*["\'][^"\']{8,}["\']',
    re.IGNORECASE,
)

# Lines containing these substrings are skipped (env-var lookups, examples)
SKIP_LINE_SUBSTRINGS = (
    "os.environ",
    "os.getenv",
    "environ.get",
    "environ[",
    "example",
    "placeholder",
    "your_",
    "xxx",
    "REDACT",
    "redact",
    "#",  # comment lines
)

REPO_ROOT = Path(__file__).parent.parent


def _iter_python_files():
    """Yield all .py files in the project, excluding test directories."""
    for py_file in REPO_ROOT.rglob("*.py"):
        # Skip test files themselves
        if "test" in py_file.name.lower():
            continue
        # Skip node_modules / .git / __pycache__
        parts = py_file.parts
        if any(p in parts for p in (".git", "__pycache__", "node_modules", ".venv", "venv")):
            continue
        yield py_file


def test_no_api_keys_in_source():
    """Scan all .py source files for hardcoded API key / secret / token patterns.

    Skips lines that reference os.environ, os.getenv, or contain example/
    placeholder markers.
    """
    violations: list[str] = []

    for py_file in _iter_python_files():
        try:
            lines = py_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            # Skip lines that reference env-var lookups or are examples
            if any(skip in stripped.lower() for skip in SKIP_LINE_SUBSTRINGS):
                continue

            if SECRET_PATTERN.search(stripped):
                rel_path = py_file.relative_to(REPO_ROOT)
                violations.append(f"{rel_path}:{lineno}: {stripped}")

    assert not violations, (
        f"Found {len(violations)} potential hardcoded secret(s):\n"
        + "\n".join(violations)
    )
