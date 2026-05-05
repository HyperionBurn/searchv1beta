"""
API Tracker — Thin adapter around spec/api_tracker.py for the orchestrator.

Tracks per-provider API credit usage, detects depletion, and provides
graceful degradation when limits are hit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import structlog

logger = structlog.get_logger().bind(component="api_tracker")


@dataclass
class TrackerReport:
    """Summary of API usage across all providers."""
    provider: str
    used: int
    limit: Optional[int]
    remaining: Optional[int]
    is_depleted: bool


class APITracker:
    """
    API credit tracker that wraps spec/api_tracker.py FreeTierTracker.

    Used by PipelineOrchestrator to:
      - Check if a provider is depleted before calling it
      - Record usage after each API call
      - Report aggregate usage for session summaries
    """

    def __init__(self) -> None:
        from spec.api_tracker import FreeTierTracker
        self._tracker = FreeTierTracker()

    def is_depleted(self, provider: str) -> bool:
        """Check if a provider has used all its free-tier credits."""
        return self._tracker.is_depleted(provider)

    def record_usage(self, provider: str, credits: int = 1, limit: int = 100) -> None:
        """Record that a provider consumed credits."""
        self._tracker.record_usage(provider, credits, limit)

    def get_usage(self, provider: str) -> Optional[TrackerReport]:
        """Get usage stats for a provider."""
        usage = self._tracker.get_usage(provider)
        if usage is None:
            return None
        return TrackerReport(
            provider=usage.provider,
            used=usage.credits_used,
            limit=usage.credits_limit if usage.credits_limit > 0 else None,
            remaining=usage.credits_limit - usage.credits_used if usage.credits_limit > 0 else None,
            is_depleted=self.is_depleted(provider),
        )

    def get_all_usage(self) -> dict[str, TrackerReport]:
        """Get usage stats for all tracked providers."""
        from spec.api_tracker import DEFAULT_PROVIDERS
        reports: dict[str, TrackerReport] = {}
        for name in DEFAULT_PROVIDERS:
            report = self.get_usage(name)
            if report:
                reports[name] = report
        return reports

    def get_warnings(self) -> list[str]:
        """Get warnings for providers approaching their limit."""
        return self._tracker.get_warnings()
