"""Tests for rate limiter edge cases.

Bug: TokenBucket with max_tokens=0 and refill_rate=0 would loop forever
in acquire() because the while-True loop never found a token and the
wait_time calculation divided by zero refill_rate.

Fix: Early return when both max_tokens and refill_rate are zero, treating
the bucket as "unlimited / no rate limiting configured".
"""

import asyncio

import pytest

from rcf.utils.rate_limiter import TokenBucket, RateLimiterRegistry


class TestRateLimiterEdgeCases:
    """TokenBucket edge cases — especially zero-capacity buckets."""

    @pytest.mark.asyncio
    async def test_zero_max_tokens_returns_immediately(self):
        """A bucket with max_tokens=0 and refill_rate=0 must not hang."""
        bucket = TokenBucket(max_tokens=0, refill_rate=0)
        # Should complete almost instantly (no hang)
        await asyncio.wait_for(bucket.acquire(), timeout=0.5)

    @pytest.mark.asyncio
    async def test_zero_max_tokens_with_positive_refill(self):
        """A bucket with max_tokens=0 but positive refill_rate will eventually refill."""
        bucket = TokenBucket(max_tokens=0, refill_rate=1000)
        # With a high refill rate, a token should appear quickly
        await asyncio.wait_for(bucket.acquire(), timeout=1.0)

    @pytest.mark.asyncio
    async def test_normal_acquire_works(self):
        """Normal bucket with tokens available should acquire immediately."""
        bucket = TokenBucket(max_tokens=5, refill_rate=10)
        await asyncio.wait_for(bucket.acquire(), timeout=0.5)

    @pytest.mark.asyncio
    async def test_acquire_drains_tokens(self):
        """Acquiring should reduce available tokens."""
        bucket = TokenBucket(max_tokens=2, refill_rate=0)
        await bucket.acquire()
        await bucket.acquire()
        # Third acquire with refill_rate=0 should hang or timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(bucket.acquire(), timeout=0.3)

    @pytest.mark.asyncio
    async def test_acquire_batch_zero_bucket(self):
        """Batch acquire on a zero-capacity bucket should not hang."""
        bucket = TokenBucket(max_tokens=0, refill_rate=0)
        await asyncio.wait_for(bucket.acquire_batch(3), timeout=1.0)


class TestRateLimiterRegistryEdgeCases:
    """Registry-level edge cases."""

    def test_acquire_unregistered_plugin_no_error(self):
        """Acquiring for a plugin with no bucket should succeed immediately."""
        registry = RateLimiterRegistry()
        # Should not raise or hang
        result = asyncio.get_event_loop().run_until_complete(
            registry.acquire("nonexistent_plugin")
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_acquire_unregistered_plugin_async(self):
        """Async version: unregistered plugins bypass rate limiting."""
        registry = RateLimiterRegistry()
        await registry.acquire("unknown")

    def test_registered_plugins_empty(self):
        registry = RateLimiterRegistry()
        assert registry.registered_plugins() == []

    def test_get_bucket_unregistered(self):
        registry = RateLimiterRegistry()
        assert registry.get_bucket("missing") is None
