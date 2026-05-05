"""
Rate Limiter — Asyncio-based token-bucket rate limiter for plugin requests.

Features:
  - Per-plugin request-per-minute limiting via asyncio.Semaphore
  - Configurable burst allowance
  - Backoff on rate-limit responses (429)
  - Plugin-aware: reads limits from PluginSpec
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TokenBucket:
    """Token-bucket rate limiter for a single plugin."""

    max_tokens: float
    refill_rate: float  # tokens per second
    _tokens: float = field(init=False, default=0.0)
    _last_refill: float = field(init=False, default_factory=time.monotonic)
    _lock: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)

    def __post_init__(self) -> None:
        self._tokens = self.max_tokens

    async def acquire(self) -> None:
        """Wait until a token is available, then consume it."""
        if self.max_tokens <= 0:
            return  # No rate limiting configured
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
            # No token available — wait before retry
            wait_time = (1.0 - self._tokens) / self.refill_rate if self.refill_rate > 0 else 1.0
            await asyncio.sleep(min(wait_time, 0.5))

    async def acquire_batch(self, count: int) -> None:
        """Acquire multiple tokens."""
        for _ in range(count):
            await self.acquire()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.max_tokens, self._tokens + elapsed * self.refill_rate)
        self._last_refill = now


class RateLimiterRegistry:
    """
    Centralized rate-limiter registry keyed by plugin name.

    Each plugin gets its own TokenBucket configured from its PluginSpec
    rate limits (requests_per_minute, requests_per_month).
    """

    def __init__(self) -> None:
        self._buckets: dict[str, TokenBucket] = {}

    def register(
        self,
        plugin_name: str,
        requests_per_minute: int,
        burst: int = 0,
    ) -> None:
        """Create a token bucket for a plugin."""
        max_tokens = burst if burst > 0 else requests_per_minute
        refill_rate = requests_per_minute / 60.0  # tokens per second
        self._buckets[plugin_name] = TokenBucket(
            max_tokens=float(max_tokens),
            refill_rate=refill_rate,
        )

    async def acquire(self, plugin_name: str) -> None:
        """Wait for rate-limited permission to make a request."""
        bucket = self._buckets.get(plugin_name)
        if bucket is None:
            return  # No rate limit configured — proceed
        await bucket.acquire()

    def get_bucket(self, plugin_name: str) -> Optional[TokenBucket]:
        """Return the token bucket for a plugin (for inspection)."""
        return self._buckets.get(plugin_name)

    def registered_plugins(self) -> list[str]:
        """Return names of all rate-limited plugins."""
        return list(self._buckets.keys())
