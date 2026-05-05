"""
RCF Logging — structlog configuration for JSON file + colored console output.

What gets logged:
  - Source queries (source name, query, result count, latency)
  - Rate limit events (source, wait time)
  - Verification results (email/phone, pass/fail, tier)
  - Errors (exceptions, API failures, network issues)
  - API usage (credits consumed, remaining, reset date)

What does NOT get logged (privacy):
  - API keys or secrets
  - Full contact data (email, phone, name)
  - Request/response bodies with personal data
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import structlog
except ImportError:
    structlog = None  # type: ignore[assignment]

from rcf.config import LogLevel


# ---------------------------------------------------------------------------
# Redaction — strip secrets from log events
# ---------------------------------------------------------------------------

REDACTED_KEYS = frozenset({
    "api_key", "apikey", "api_key_env",
    "authorization", "token", "secret",
    "password", "credential",
})

SENSITIVE_PATTERNS = frozenset({
    "email", "phone", "whatsapp",
    "first_name", "last_name", "full_name",
})


def _redact_value(value: Any) -> str:
    """Redact a value that might contain sensitive data."""
    return "[REDACTED]"


def redact_processor(
    logger: Any, method_name: str, event_dict: Dict[str, Any],
) -> Dict[str, Any]:
    """
    structlog processor that redacts API keys and sensitive contact fields.

    - Keys in REDACTED_KEYS are fully replaced with [REDACTED]
    - Keys in SENSITIVE_PATTERNS are replaced with [REDACTED]
    - 'query' values longer than 100 chars are truncated
    """
    for key in list(event_dict.keys()):
        lower_key = key.lower()
        if lower_key in REDACTED_KEYS:
            event_dict[key] = "[REDACTED]"
        elif lower_key in SENSITIVE_PATTERNS:
            event_dict[key] = "[REDACTED]"
        elif isinstance(event_dict[key], str) and len(event_dict[key]) > 200:
            event_dict[key] = event_dict[key][:200] + "...[truncated]"
    return event_dict


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def _console_format(event_dict: Dict[str, Any]) -> str:
    """Human-readable colored console output."""
    level = event_dict.get("level", "info").upper()
    timestamp = event_dict.get("timestamp", "")
    event = event_dict.get("event", "")

    # Color codes
    colors = {
        "DEBUG": "\033[36m",    # cyan
        "INFO": "\033[32m",     # green
        "WARNING": "\033[33m",  # yellow
        "ERROR": "\033[31m",    # red
        "CRITICAL": "\033[35m", # magenta
    }
    reset = "\033[0m"
    color = colors.get(level, "")

    # Build extra fields string
    extras = []
    skip_keys = {"level", "timestamp", "event", "logger_name"}
    for k, v in event_dict.items():
        if k not in skip_keys:
            extras.append(f"{k}={v}")

    extra_str = " ".join(extras)
    msg = f"{color}{level:<8s}{reset} {timestamp} {event}"
    if extra_str:
        msg += f"  {extra_str}"
    return msg


def console_renderer(
    logger: Any, method_name: str, event_dict: Dict[str, Any],
) -> str:
    """structlog processor for colored console output."""
    return _console_format(event_dict)


# ---------------------------------------------------------------------------
# Module-level log levels
# ---------------------------------------------------------------------------

MODULE_LOG_LEVELS: Dict[str, LogLevel] = {
    "rcf.cli": LogLevel.INFO,
    "rcf.config": LogLevel.INFO,
    "rcf.export": LogLevel.INFO,
    "rcf.logging": LogLevel.INFO,
    "rcf.plugins.hunter": LogLevel.INFO,
    "rcf.plugins.apollo": LogLevel.INFO,
    "rcf.plugins.google_places": LogLevel.INFO,
    "rcf.plugins.linkedin": LogLevel.INFO,
    "rcf.plugins.bayt": LogLevel.INFO,
    "rcf.plugins.expatriates": LogLevel.INFO,
    "rcf.plugins.dubizzle": LogLevel.INFO,
    "rcf.plugins.dmcc_directory": LogLevel.INFO,
    "rcf.plugins.google_dorking": LogLevel.INFO,
    "spec.email_verifier": LogLevel.INFO,
    "spec.phone_validator": LogLevel.INFO,
    "uae_engine_spec.whatsapp_engine": LogLevel.INFO,
    "rcf.scoring": LogLevel.INFO,
    "rcf.rate_limiter": LogLevel.WARNING,
    "rcf.cache": LogLevel.WARNING,
    "rcf.db": LogLevel.INFO,
    "httpx": LogLevel.WARNING,
    "httpcore": LogLevel.WARNING,
    "playwright": LogLevel.WARNING,
    "sqlite3": LogLevel.WARNING,
}


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def setup_logging(
    log_level: LogLevel = LogLevel.INFO,
    log_file: str = "rcf.log",
) -> None:
    """
    Configure structlog with dual output:
      - Console: colored human-readable format
      - File: JSON format for machine parsing

    Args:
        log_level: Minimum log level for console output.
        log_file: Path to the JSON log file.
    """
    if structlog is None:
        # Fallback to stdlib logging if structlog not installed
        logging.basicConfig(
            level=getattr(logging, log_level.value),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        return

    # ── Standard library logging ───────────────────────────────────────
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.value),
    )

    # Apply per-module levels
    for module, level in MODULE_LOG_LEVELS.items():
        logging.getLogger(module).setLevel(getattr(logging, level.value))

    # ── File handler (JSON) ────────────────────────────────────────────
    log_path = Path(log_file)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # always capture everything to file
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    logging.root.addHandler(file_handler)

    # ── structlog configuration ────────────────────────────────────────
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        redact_processor,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Console: colored output
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=console_renderer,
    )
    # File: JSON output
    file_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
    )

    # Apply formatters to handlers
    for handler in logging.root.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.setFormatter(file_formatter)
        elif isinstance(handler, logging.StreamHandler) and handler.stream is sys.stdout:
            handler.setFormatter(console_formatter)


# ---------------------------------------------------------------------------
# Structured log event helpers
# ---------------------------------------------------------------------------

def get_logger(name: str = "rcf") -> Any:
    """Get a structlog logger for the given module name."""
    if structlog is not None:
        return structlog.get_logger(name)
    return logging.getLogger(name)


# Type-safe event logging helpers

def log_source_query(
    source: str,
    query: str,
    *,
    region: str = "",
    results_count: int = 0,
    latency_ms: float = 0.0,
    cached: bool = False,
) -> None:
    """Log a source query event."""
    logger = get_logger("rcf.sources")
    logger.info(
        "source_query",
        source=source,
        query=query[:100],  # truncate long queries
        region=region,
        results_count=results_count,
        latency_ms=round(latency_ms, 1),
        cached=cached,
    )


def log_rate_limit(
    source: str,
    *,
    wait_seconds: float = 0.0,
    requests_remaining: int = 0,
    reset_at: str = "",
) -> None:
    """Log a rate limit event."""
    logger = get_logger("rcf.rate_limiter")
    logger.warning(
        "rate_limited",
        source=source,
        wait_seconds=round(wait_seconds, 1),
        requests_remaining=requests_remaining,
        reset_at=reset_at,
    )


def log_verification_result(
    contact_id: str,
    *,
    field: str = "",  # "email" or "phone"
    tier: str = "",    # "syntax", "dns", "smtp", "api"
    passed: bool = False,
    provider: str = "",
) -> None:
    """Log a verification result (field values are redacted)."""
    logger = get_logger(f"rcf.verify.{field}")
    logger.info(
        "verification_result",
        contact_id=contact_id,
        field=field,
        tier=tier,
        passed=passed,
        provider=provider,
    )


def log_api_usage(
    source: str,
    *,
    credits_used: int = 0,
    credits_remaining: int = 0,
    reset_date: str = "",
) -> None:
    """Log API credit usage."""
    logger = get_logger("rcf.sources")
    logger.info(
        "api_usage",
        source=source,
        credits_used=credits_used,
        credits_remaining=credits_remaining,
        reset_date=reset_date,
    )


def log_error(
    message: str,
    *,
    source: str = "",
    error_type: str = "",
    recoverable: bool = True,
) -> None:
    """Log an error event."""
    logger = get_logger("rcf")
    logger.error(
        "error",
        message=message,
        source=source,
        error_type=error_type,
        recoverable=recoverable,
    )
