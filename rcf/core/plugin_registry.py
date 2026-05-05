"""
Plugin Registry — Discovers, registers, and manages all source plugins.

Responsibilities:
  - Load plugin classes from the plugins/ directory and the ALL_PLUGINS spec
  - Register instances keyed by plugin name
  - Filter plugins by region, source type, and query parameters
  - Sort by priority for waterfall execution
  - Track configuration status (API keys present, browser available, etc.)
  - Validate all plugins at startup and report issues

Usage:
    registry = PluginRegistry()
    await registry.discover_and_register()

    # Get all plugins that can serve a UAE recruiter query
    plugins = registry.get_for_query(query)

    # Get plugins sorted by priority (for waterfall)
    sorted_plugins = registry.get_by_priority()
"""

from __future__ import annotations

import asyncio
import importlib
import pkgutil
from pathlib import Path
from typing import Any

import structlog

from models.enums import Region, SourceType
from models.models import ContactQuery

from .base_plugin import (
    ALL_PLUGINS,
    PluginInfo,
    PluginSpec,
    PluginConfigError,
    RateLimitInfo,
    SourcePlugin,
)

logger = structlog.get_logger().bind(component="plugin_registry")


class PluginRegistry:
    """
    Central registry for all source plugins.

    Thread-safe for async usage — all mutations happen during init,
    reads are lock-free during pipeline execution.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, SourcePlugin] = {}
        self._specs: dict[str, PluginSpec] = dict(ALL_PLUGINS)
        self._config_cache: dict[str, bool] = {}  # name → is_configured

    # ── Registration ─────────────────────────────────────────────────

    def register(self, plugin: SourcePlugin) -> None:
        """
        Register a plugin instance.

        Args:
            plugin: Concrete SourcePlugin subclass instance.

        Raises:
            ValueError: If a plugin with the same name is already registered.
        """
        if plugin.name in self._plugins:
            raise ValueError(
                f"Plugin '{plugin.name}' is already registered. "
                f"Use unregister() first if replacing."
            )
        self._plugins[plugin.name] = plugin
        logger.info(
            "plugin_registered",
            plugin_name=plugin.name,
            source_type=plugin.source_type.value,
            priority=plugin.priority,
        )

    def unregister(self, name: str) -> None:
        """Remove a plugin by name."""
        if name in self._plugins:
            del self._plugins[name]
            self._config_cache.pop(name, None)
            logger.info("plugin_unregistered", plugin_name=name)

    # ── Lookup ───────────────────────────────────────────────────────

    def get(self, name: str) -> SourcePlugin:
        """
        Retrieve a plugin by exact name.

        Raises:
            KeyError: If no plugin with that name is registered.
        """
        if name not in self._plugins:
            raise KeyError(
                f"Plugin '{name}' not found. "
                f"Registered: {sorted(self._plugins.keys())}"
            )
        return self._plugins[name]

    def get_for_query(self, query: ContactQuery) -> list[SourcePlugin]:
        """
        Return plugins matching the query's region and source type filters.

        Filtering rules:
          1. Plugin must cover the query's region (or be GLOBAL)
          2. If query.sources is set, plugin's source_type must be in that list
          3. Plugin must be configured (API key present if required)
          4. Plugin must not be depleted (credits > 0 or unlimited)
          5. Results sorted by priority (ascending = highest priority first)
        """
        candidates: list[SourcePlugin] = []

        for plugin in self._plugins.values():
            spec = plugin.SPEC

            # Region filter: plugin must cover query region
            if query.region not in spec.regions and Region.GLOBAL not in spec.regions:
                continue

            # Source type filter: if query specifies types, plugin must match
            if query.sources is not None and spec.source_type not in query.sources:
                continue

            # Configuration check
            if not self._config_cache.get(plugin.name, True):
                continue

            candidates.append(plugin)

        # Sort by priority (1 = highest)
        candidates.sort(key=lambda p: p.priority)
        return candidates

    def get_by_priority(self) -> list[SourcePlugin]:
        """Return all registered plugins sorted by priority (ascending)."""
        return sorted(self._plugins.values(), key=lambda p: p.priority)

    def get_by_type(self, source_type: SourceType) -> list[SourcePlugin]:
        """Return all plugins of a given source type."""
        return [
            p for p in self._plugins.values()
            if p.source_type == source_type
        ]

    def get_by_region(self, region: Region) -> list[SourcePlugin]:
        """Return all plugins that cover a given region."""
        return [
            p for p in self._plugins.values()
            if region in p.regions or Region.GLOBAL in p.regions
        ]

    def get_browser_plugins(self) -> list[SourcePlugin]:
        """Return all plugins that require a browser."""
        return [p for p in self._plugins.values() if p.requires_browser]

    # ── Listing ──────────────────────────────────────────────────────

    def list_all(self) -> list[PluginInfo]:
        """Return metadata for all registered plugins."""
        infos: list[PluginInfo] = []
        for plugin in self._plugins.values():
            spec = plugin.SPEC
            infos.append(PluginInfo(
                name=spec.name,
                source_type=spec.source_type,
                regions=spec.regions,
                data_types=spec.data_types,
                priority=spec.priority,
                requires_browser=spec.requires_browser,
                api_key_env=spec.api_key_env,
                is_configured=self._config_cache.get(spec.name, True),
                rate_limit_rpm=spec.rate_limit_rpm,
                rate_limit_monthly=spec.rate_limit_monthly,
            ))
        return sorted(infos, key=lambda i: i.priority)

    def list_available(self, region: Region | None = None) -> list[PluginInfo]:
        """Return metadata for configured, non-depleted plugins."""
        infos = self.list_all()
        result = [i for i in infos if i.is_configured]
        if region is not None:
            result = [i for i in result if region in i.regions or Region.GLOBAL in i.regions]
        return result

    # ── Bulk operations ──────────────────────────────────────────────

    async def validate_all(self) -> dict[str, bool]:
        """
        Run validate_config() on all registered plugins concurrently.

        Returns:
            Dict mapping plugin name → is_valid (bool).
        """
        results: dict[str, bool] = {}

        async def _validate_one(name: str, plugin: SourcePlugin) -> None:
            try:
                is_valid = await plugin.validate_config()
                results[name] = is_valid
                self._config_cache[name] = is_valid
                if not is_valid:
                    logger.warning("plugin_config_invalid", plugin_name=name)
            except Exception as exc:
                results[name] = False
                self._config_cache[name] = False
                logger.error(
                    "plugin_validation_error",
                    plugin_name=name,
                    error=str(exc),
                )

        await asyncio.gather(*(
            _validate_one(name, plugin)
            for name, plugin in self._plugins.items()
        ))
        return results

    async def discover_and_register(
        self,
        plugins_package: str = "rcf.plugins",
        max_concurrency: int = 5,
    ) -> int:
        """
        Auto-discover plugin classes from the plugins package and register them.

        Scans the plugins/ directory for modules containing SourcePlugin subclasses,
        instantiates each with the configured concurrency, and registers them.

        Args:
            plugins_package: Python package path to scan for plugins.
            max_concurrency: Default concurrency limit per plugin.

        Returns:
            Number of plugins successfully registered.
        """
        registered_count = 0

        try:
            package = importlib.import_module(plugins_package)
        except ImportError:
            logger.error("plugins_package_not_found", package=plugins_package)
            return 0

        package_path = Path(package.__file__).parent  # type: ignore[arg-type]

        for module_info in pkgutil.iter_modules([str(package_path)]):
            if module_info.name.startswith("_"):
                continue

            try:
                module = importlib.import_module(f"{plugins_package}.{module_info.name}")
            except ImportError as exc:
                logger.warning(
                    "plugin_module_import_failed",
                    module=module_info.name,
                    error=str(exc),
                )
                continue

            # Find all SourcePlugin subclasses in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, SourcePlugin)
                    and attr is not SourcePlugin
                    and hasattr(attr, "SPEC")
                ):
                    try:
                        instance = attr(max_concurrency=max_concurrency)
                        self.register(instance)
                        registered_count += 1
                    except Exception as exc:
                        logger.error(
                            "plugin_instantiation_failed",
                            plugin_class=attr_name,
                            error=str(exc),
                        )

        # Validate all registered plugins
        await self.validate_all()

        logger.info(
            "plugin_discovery_complete",
            registered=registered_count,
            total_specs=len(self._specs),
        )
        return registered_count

    async def close_all(self) -> None:
        """Close all plugin resources (HTTP clients, browsers)."""
        await asyncio.gather(*(
            plugin.close()
            for plugin in self._plugins.values()
        ))

    # ── Properties ───────────────────────────────────────────────────

    @property
    def count(self) -> int:
        """Number of registered plugins."""
        return len(self._plugins)

    @property
    def names(self) -> list[str]:
        """Names of all registered plugins."""
        return sorted(self._plugins.keys())

    def has(self, name: str) -> bool:
        """Check if a plugin is registered."""
        return name in self._plugins

    def __len__(self) -> int:
        return len(self._plugins)

    def __contains__(self, name: str) -> bool:
        return name in self._plugins

    def __repr__(self) -> str:
        return (
            f"PluginRegistry(plugins={len(self._plugins)}, "
            f"configured={sum(1 for v in self._config_cache.values() if v)})"
        )
