"""
Free Tier API Tracker — Usage Tracking & Graceful Degradation
=============================================================
Tracks API credit usage across all free verification tiers with
SQLite persistence, reset logic, warning thresholds, and graceful
degradation when limits are hit.

APIs tracked:
  - ZeroBounce:     100/mo
  - NeverBounce:    1000 one-time
  - Kickbox:        100/mo
  - Twilio Lookup:  Pay-per-use ($0.01/query)
  - Abstract API:   100/mo
  - HIBP:           Rate-limited (1 req/1.5s)
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Warning threshold: 80% of credits used
WARNING_THRESHOLD_PCT: float = 0.80

# Hard stop: 100% of credits used
HARD_STOP_PCT: float = 1.00

# Default database path
DEFAULT_DB_PATH: str = str(Path.home() / ".gcc-recruiter" / "api_usage.db")


# ---------------------------------------------------------------------------
# Provider Configuration
# ---------------------------------------------------------------------------

class ResetType:
    MONTHLY = "monthly"
    DAILY = "daily"
    ONE_TIME = "one_time"
    UNLIMITED = "unlimited"


@dataclass
class ProviderConfig:
    """Configuration for a single API provider's free tier."""
    name: str
    credits_limit: int
    reset_type: str
    reset_day: int = 1  # Day of month for monthly reset (1 = 1st)
    rate_limit_per_second: float = 0.0  # 0 = no rate limit


# Pre-configured provider defaults
DEFAULT_PROVIDERS: dict[str, ProviderConfig] = {
    "zerobounce": ProviderConfig(
        name="zerobounce",
        credits_limit=100,
        reset_type=ResetType.MONTHLY,
        reset_day=1,
    ),
    "neverbounce": ProviderConfig(
        name="neverbounce",
        credits_limit=1000,
        reset_type=ResetType.ONE_TIME,
    ),
    "kickbox": ProviderConfig(
        name="kickbox",
        credits_limit=100,
        reset_type=ResetType.MONTHLY,
        reset_day=1,
    ),
    "twilio_lookup": ProviderConfig(
        name="twilio_lookup",
        credits_limit=0,  # Pay-per-use, no free limit
        reset_type=ResetType.UNLIMITED,
    ),
    "abstract_api": ProviderConfig(
        name="abstract_api",
        credits_limit=100,
        reset_type=ResetType.MONTHLY,
        reset_day=1,
    ),
    "hibp": ProviderConfig(
        name="hibp",
        credits_limit=0,  # Rate-limited, not credit-limited
        reset_type=ResetType.UNLIMITED,
        rate_limit_per_second=1.0 / 1.5,  # 1 request per 1.5 seconds
    ),
}


# ---------------------------------------------------------------------------
# Usage Record
# ---------------------------------------------------------------------------

@dataclass
class UsageRecord:
    """Single API usage record."""
    provider: str
    credits_used: int
    credits_limit: int
    reset_type: str
    last_used: float = field(default_factory=time.time)
    last_reset: float = field(default_factory=time.time)
    period_start: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# FreeTierTracker
# ---------------------------------------------------------------------------

class FreeTierTracker:
    """
    Track and manage free API tier usage across all providers.

    Features:
      - Per-provider credit tracking with SQLite persistence
      - Monthly/daily/one-time reset logic
      - Warning at 80% usage
      - Hard stop at 100% usage
      - Graceful degradation: skip depleted providers
      - Thread-safe via SQLite transactions

    Usage:
        tracker = FreeTierTracker()

        # Check before making an API call
        if not tracker.is_depleted("zerobounce"):
            result = await call_zerobounce(email)
            tracker.record_usage("zerobounce", 1, 100)

        # Check warnings
        warnings = tracker.get_warnings()
        for w in warnings:
            print(f"WARNING: {w}")
    """

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        providers: dict[str, ProviderConfig] | None = None,
    ) -> None:
        self.db_path = db_path
        self.providers = providers or DEFAULT_PROVIDERS
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Initialize SQLite database and create tables if needed."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_usage (
                    provider TEXT PRIMARY KEY,
                    credits_used INTEGER NOT NULL DEFAULT 0,
                    credits_limit INTEGER NOT NULL DEFAULT 0,
                    reset_type TEXT NOT NULL DEFAULT 'monthly',
                    last_used REAL NOT NULL DEFAULT 0,
                    last_reset REAL NOT NULL DEFAULT 0,
                    period_start REAL NOT NULL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    credits INTEGER NOT NULL,
                    timestamp REAL NOT NULL DEFAULT (strftime('%s', 'now'))
                )
            """)
            conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _check_reset(self, provider: str, conn: sqlite3.Connection) -> None:
        """
        Check if the usage period has expired and reset if needed.

        Reset logic:
          - MONTHLY: Reset on the 1st of each month
          - DAILY: Reset at midnight UTC
          - ONE_TIME: Never reset
          - UNLIMITED: Never reset (no credits to track)
        """
        now = time.time()
        now_dt = datetime.fromtimestamp(now, tz=timezone.utc)

        row = conn.execute(
            "SELECT reset_type, last_reset, credits_limit FROM api_usage WHERE provider = ?",
            (provider,),
        ).fetchone()

        if not row:
            return

        reset_type, last_reset, credits_limit = row
        last_reset_dt = datetime.fromtimestamp(last_reset, tz=timezone.utc)

        should_reset = False

        if reset_type == ResetType.MONTHLY:
            # Reset if we're in a new month
            if (now_dt.year > last_reset_dt.year or
                    now_dt.month > last_reset_dt.month):
                should_reset = True

        elif reset_type == ResetType.DAILY:
            # Reset if we're on a new day
            if now_dt.date() > last_reset_dt.date():
                should_reset = True

        if should_reset:
            conn.execute(
                "UPDATE api_usage SET credits_used = 0, last_reset = ?, period_start = ? WHERE provider = ?",
                (now, now, provider),
            )
            conn.commit()

    def get_usage(self, provider: str) -> UsageRecord:
        """Get current usage record for a provider."""
        with self._get_conn() as conn:
            self._check_reset(provider, conn)

            row = conn.execute(
                "SELECT provider, credits_used, credits_limit, reset_type, last_used, last_reset, period_start FROM api_usage WHERE provider = ?",
                (provider,),
            ).fetchone()

            if not row:
                # Initialize from config
                config = self.providers.get(provider)
                if config:
                    now = time.time()
                    conn.execute(
                        "INSERT INTO api_usage (provider, credits_used, credits_limit, reset_type, last_used, last_reset, period_start) VALUES (?, 0, ?, ?, 0, ?, ?)",
                        (provider, config.credits_limit, config.reset_type, now, now),
                    )
                    conn.commit()
                    return UsageRecord(
                        provider=provider,
                        credits_used=0,
                        credits_limit=config.credits_limit,
                        reset_type=config.reset_type,
                        last_used=0,
                        last_reset=now,
                        period_start=now,
                    )
                return UsageRecord(
                    provider=provider,
                    credits_used=0,
                    credits_limit=0,
                    reset_type=ResetType.UNLIMITED,
                )

            return UsageRecord(
                provider=row[0],
                credits_used=row[1],
                credits_limit=row[2],
                reset_type=row[3],
                last_used=row[4],
                last_reset=row[5],
                period_start=row[6],
            )

    def record_usage(
        self, provider: str, credits: int, limit: int | None = None
    ) -> None:
        """
        Record usage of `credits` for a provider.

        Args:
            provider: API provider name
            credits: Number of credits consumed
            limit: Override credits limit (if known at call time)
        """
        now = time.time()

        with self._get_conn() as conn:
            self._check_reset(provider, conn)

            # Check if provider exists
            exists = conn.execute(
                "SELECT 1 FROM api_usage WHERE provider = ?", (provider,)
            ).fetchone()

            if exists:
                if limit is not None:
                    conn.execute(
                        "UPDATE api_usage SET credits_used = credits_used + ?, credits_limit = ?, last_used = ? WHERE provider = ?",
                        (credits, limit, now, provider),
                    )
                else:
                    conn.execute(
                        "UPDATE api_usage SET credits_used = credits_used + ?, last_used = ? WHERE provider = ?",
                        (credits, now, provider),
                    )
            else:
                config = self.providers.get(provider)
                actual_limit = limit or (config.credits_limit if config else 0)
                reset_type = config.reset_type if config else ResetType.MONTHLY

                conn.execute(
                    "INSERT INTO api_usage (provider, credits_used, credits_limit, reset_type, last_used, last_reset, period_start) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (provider, credits, actual_limit, reset_type, now, now, now),
                )

            # Log the usage
            conn.execute(
                "INSERT INTO usage_log (provider, credits, timestamp) VALUES (?, ?, ?)",
                (provider, credits, now),
            )
            conn.commit()

    def is_depleted(self, provider: str) -> bool:
        """
        Check if a provider's credits are fully depleted.

        Returns True if credits_used >= credits_limit (hard stop).
        Unlimited providers always return False.
        """
        usage = self.get_usage(provider)

        if usage.reset_type == ResetType.UNLIMITED:
            return False

        if usage.credits_limit <= 0:
            return False

        return usage.credits_used >= usage.credits_limit

    def is_near_limit(self, provider: str) -> bool:
        """
        Check if a provider is near its limit (≥ 80% used).

        Returns True if usage is at or above the warning threshold.
        """
        usage = self.get_usage(provider)

        if usage.credits_limit <= 0:
            return False

        return (usage.credits_used / usage.credits_limit) >= WARNING_THRESHOLD_PCT

    def remaining_credits(self, provider: str) -> int:
        """Get remaining credits for a provider."""
        usage = self.get_usage(provider)
        if usage.credits_limit <= 0:
            return -1  # Unlimited
        return max(0, usage.credits_limit - usage.credits_used)

    def usage_percentage(self, provider: str) -> float:
        """Get usage percentage (0.0 to 1.0) for a provider."""
        usage = self.get_usage(provider)
        if usage.credits_limit <= 0:
            return 0.0
        return min(1.0, usage.credits_used / usage.credits_limit)

    def get_warnings(self) -> list[str]:
        """
        Get all active warnings for near-limit or depleted providers.

        Returns list of warning messages.
        """
        warnings: list[str] = []

        for provider_name in self.providers:
            usage = self.get_usage(provider_name)

            if usage.credits_limit <= 0:
                continue

            pct = usage.credits_used / usage.credits_limit

            if pct >= HARD_STOP_PCT:
                warnings.append(
                    f"🛑 {provider_name}: DEPLETED "
                    f"({usage.credits_used}/{usage.credits_limit} credits used). "
                    f"Reset: {usage.reset_type}"
                )
            elif pct >= WARNING_THRESHOLD_PCT:
                warnings.append(
                    f"⚠️ {provider_name}: {pct:.0%} used "
                    f"({usage.credits_used}/{usage.credits_limit} credits). "
                    f"Reset: {usage.reset_type}"
                )

        return warnings

    def get_available_providers(self) -> list[str]:
        """Get list of providers that still have credits available."""
        available: list[str] = []
        for provider_name in self.providers:
            if not self.is_depleted(provider_name):
                available.append(provider_name)
        return available

    def get_depleted_providers(self) -> list[str]:
        """Get list of providers that are fully depleted."""
        return [
            name for name in self.providers
            if self.is_depleted(name)
        ]

    def get_status_report(self) -> dict:
        """
        Get full status report for all tracked providers.

        Returns dict with provider name → status info.
        """
        report: dict = {}
        for provider_name, config in self.providers.items():
            usage = self.get_usage(provider_name)
            report[provider_name] = {
                "credits_used": usage.credits_used,
                "credits_limit": usage.credits_limit,
                "remaining": self.remaining_credits(provider_name),
                "usage_pct": round(self.usage_percentage(provider_name), 3),
                "is_depleted": self.is_depleted(provider_name),
                "is_near_limit": self.is_near_limit(provider_name),
                "reset_type": usage.reset_type,
                "last_used": datetime.fromtimestamp(
                    usage.last_used, tz=timezone.utc
                ).isoformat() if usage.last_used > 0 else "never",
                "last_reset": datetime.fromtimestamp(
                    usage.last_reset, tz=timezone.utc
                ).isoformat() if usage.last_reset > 0 else "never",
            }
        return report

    def reset_provider(self, provider: str) -> None:
        """Manually reset a provider's usage counter."""
        now = time.time()
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE api_usage SET credits_used = 0, last_reset = ?, period_start = ? WHERE provider = ?",
                (now, now, provider),
            )
            conn.commit()

    def reset_all(self) -> None:
        """Manually reset all providers' usage counters."""
        now = time.time()
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE api_usage SET credits_used = 0, last_reset = ?, period_start = ?",
                (now, now),
            )
            conn.commit()

    def get_usage_log(
        self, provider: str | None = None, limit: int = 100
    ) -> list[dict]:
        """
        Get usage log entries.

        Args:
            provider: Filter by provider (None = all)
            limit: Max entries to return
        """
        with self._get_conn() as conn:
            if provider:
                rows = conn.execute(
                    "SELECT provider, credits, timestamp FROM usage_log WHERE provider = ? ORDER BY timestamp DESC LIMIT ?",
                    (provider, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT provider, credits, timestamp FROM usage_log ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                ).fetchall()

        return [
            {
                "provider": row[0],
                "credits": row[1],
                "timestamp": datetime.fromtimestamp(
                    row[2], tz=timezone.utc
                ).isoformat(),
            }
            for row in rows
        ]


# ---------------------------------------------------------------------------
# Graceful Degradation Helper
# ---------------------------------------------------------------------------

class APIProviderSelector:
    """
    Select the best available API provider for a given operation.

    Implements graceful degradation:
      1. Filter out depleted providers
      2. Sort by priority (credits remaining / reliability)
      3. Fall through to next provider if current fails

    Usage:
        selector = APIProviderSelector(tracker)
        for provider in selector.get_available("email_verify"):
            result = await call_provider(provider, email)
            if result:
                break
    """

    # Provider priority by operation type
    EMAIL_VERIFY_PRIORITY: list[str] = [
        "zerobounce",   # 100/mo, best accuracy
        "neverbounce",  # 1000 one-time, good backup
        "kickbox",      # 100/mo, decent accuracy
    ]

    PHONE_VERIFY_PRIORITY: list[str] = [
        "twilio_lookup",  # Pay-per-use, most accurate
        "abstract_api",   # 100/mo, decent backup
    ]

    ALT_VERIFY_PRIORITY: list[str] = [
        "hibp",  # Rate-limited but free
    ]

    def __init__(self, tracker: FreeTierTracker) -> None:
        self.tracker = tracker

    def get_available(
        self, operation: str = "email_verify"
    ) -> list[str]:
        """
        Get ordered list of available providers for an operation.

        Skips depleted providers, returns only those with remaining credits.
        """
        priority_map = {
            "email_verify": self.EMAIL_VERIFY_PRIORITY,
            "phone_verify": self.PHONE_VERIFY_PRIORITY,
            "alt_verify": self.ALT_VERIFY_PRIORITY,
        }

        priorities = priority_map.get(operation, self.EMAIL_VERIFY_PRIORITY)

        return [
            p for p in priorities
            if not self.tracker.is_depleted(p)
        ]

    def select_best(self, operation: str = "email_verify") -> Optional[str]:
        """
        Select the single best available provider.

        Returns None if all providers are depleted.
        """
        available = self.get_available(operation)
        return available[0] if available else None
