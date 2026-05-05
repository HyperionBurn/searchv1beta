"""
RCF Configuration — Pydantic models and YAML loading for config.yml.

Every config key is specified here with defaults, validation, and docs.
Loading order: config.yml → .env overrides → CLI flag overrides.
"""

from __future__ import annotations

import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)


# ---------------------------------------------------------------------------
# Enums — canonical definitions live in models.enums; re-exported here so
# that existing imports from rcf.config continue to work.
# ---------------------------------------------------------------------------

from models.enums import Region, ExportFormat, SourceType  # noqa: F401


class EmailVerificationTier(str, Enum):
    SYNTAX = "syntax"
    DNS = "dns"
    SMTP = "smtp"
    API = "api"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class PreferredContactMethod(str, Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    PHONE = "phone"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class GeneralConfig(BaseModel):
    """Top-level application settings."""

    default_region: Region = Region.UAE
    max_concurrent_requests: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of concurrent async HTTP requests.",
    )
    request_delay_seconds: float = Field(
        default=2.0,
        ge=0.0,
        le=60.0,
        description="Base delay between requests to the same source (seconds).",
    )
    user_agent_rotation: bool = Field(
        default=True,
        description="Rotate User-Agent strings across a pool of real browser UAs.",
    )
    cache_ttl_hours: int = Field(
        default=168,
        ge=1,
        description="Time-to-live for cached source responses (hours). 168 = 1 week.",
    )
    data_retention_days: int = Field(
        default=90,
        ge=1,
        description="Auto-delete contacts older than this (days). 0 = keep forever.",
    )
    log_level: LogLevel = LogLevel.INFO
    log_file: str = "rcf.log"
    database_path: str = "rcf_data.db"


class UAEConfig(BaseModel):
    """UAE / GCC–specific settings."""

    check_whatsapp: bool = Field(
        default=True,
        description="Check if phone numbers are WhatsApp-enabled via presence ping.",
    )
    dual_tld_check: bool = Field(
        default=True,
        description="Try both .ae and .com domains when resolving company websites.",
    )
    arabic_name_variants: bool = Field(
        default=True,
        description="Generate Arabic-name email permutations (Al, Bin, Mohammed compression).",
    )
    detect_ats: bool = Field(
        default=True,
        description="Detect ATS platforms (Taleo, SAP SF, PageUp) on company career pages.",
    )
    carrier_detection: bool = Field(
        default=True,
        description="Detect UAE mobile carrier (Etisalat, du, Virgin Mobile) from phone prefix.",
    )
    emirate_detection: bool = Field(
        default=True,
        description="Infer emirate from phone area code or address data.",
    )
    preferred_contact_method: PreferredContactMethod = PreferredContactMethod.WHATSAPP


class BrowserConfig(BaseModel):
    """Headless browser / anti-detection settings."""

    headless: bool = True
    stealth_mode: bool = Field(
        default=True,
        description="Apply playwright-stealth patches (webdriver flag, plugins, etc.).",
    )
    browser_pool_size: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of browser contexts to keep warm in the pool.",
    )
    context_reuse: bool = Field(
        default=True,
        description="Reuse browser contexts across requests instead of creating new ones.",
    )
    lightpanda_path: Optional[str] = Field(
        default=None,
        description="Path to Lightpanda binary. None = auto-detect or fall back to Chromium.",
    )
    camoufox_profile: Optional[str] = Field(
        default=None,
        description="Path to Camoufox Firefox profile for fingerprint randomisation.",
    )


class RateLimitConfig(BaseModel):
    """Per-source-type rate limits."""

    api: int = Field(
        default=10,
        description="Max API requests per minute per source.",
    )
    scrape: int = Field(
        default=6,
        description="Max scraping requests per minute per source.",
    )
    browser: int = Field(
        default=4,
        description="Max browser-page loads per minute per source.",
    )
    smtp: int = Field(
        default=3,
        description="Max SMTP verification connections per minute.",
    )


class EmailVerificationConfig(BaseModel):
    """Email verification pipeline settings."""

    enabled: bool = True
    tiers: List[EmailVerificationTier] = Field(
        default=[EmailVerificationTier.SYNTAX, EmailVerificationTier.DNS, EmailVerificationTier.SMTP, EmailVerificationTier.API],
        description="Verification tiers to execute in order. Stop on first definitive result.",
    )
    skip_smtp_for_m365: bool = Field(
        default=True,
        description="UAE-specific: M365 accepts all RCPT TO, producing false positives.",
    )
    use_hibp_fallback: bool = Field(
        default=True,
        description="Use HaveIBeenPwned breach DB as a verification signal.",
    )


class PhoneVerificationConfig(BaseModel):
    """Phone number verification settings."""

    enabled: bool = True
    libphonenumber: bool = Field(
        default=True,
        description="Validate and format with google-libphonenumber.",
    )
    whatsapp_check: bool = Field(
        default=True,
        description="Ping WhatsApp presence to confirm number is WA-enabled.",
    )
    carrier_detection: bool = Field(
        default=True,
        description="Detect carrier from number prefix (Etisalat/du/Virgin).",
    )


class VerificationConfig(BaseModel):
    """Umbrella verification settings."""

    email: EmailVerificationConfig = Field(default_factory=EmailVerificationConfig)
    phone: PhoneVerificationConfig = Field(default_factory=PhoneVerificationConfig)


class ScoringConfig(BaseModel):
    """Confidence scoring parameters."""

    minimum_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Discard contacts below this confidence threshold.",
    )
    prefer_phone_over_email: bool = Field(
        default=False,
        description="Boost confidence when a phone number is present.",
    )
    uae_regional_bonus: float = Field(
        default=0.05,
        ge=0.0,
        le=0.5,
        description="Confidence bonus for UAE-sourced data (regional accuracy premium).",
    )


class ExportConfig(BaseModel):
    """Default export behaviour."""

    default_format: ExportFormat = ExportFormat.CSV
    include_confidence: bool = True
    include_sources: bool = True
    include_verification_status: bool = True
    include_timestamps: bool = True
    deduplicate: bool = True


# ---------------------------------------------------------------------------
# Source configuration — each of the 30+ sources
# ---------------------------------------------------------------------------

class SourceDefinition(BaseModel):
    """Configuration for a single data source."""

    enabled: bool = True
    priority: int = Field(
        default=2,
        ge=1,
        le=5,
        description="1 = highest priority (tried first in waterfall).",
    )
    api_key_env: Optional[str] = Field(
        default=None,
        description="Environment variable name holding the API key.",
    )
    requires_browser: bool = False
    regions: List[Region] = Field(
        default_factory=lambda: list(Region),
        description="Regions this source covers. Default = all.",
    )
    type: SourceType = SourceType.API
    free_tier_limit: Optional[str] = Field(
        default=None,
        description="Human-readable free tier description, e.g. '50 credits/mo'.",
    )
    base_url: Optional[str] = None


# All 30+ sources — alphabetical by key
ALL_SOURCES: Dict[str, Dict[str, Any]] = {
    # ── Email Discovery APIs ──────────────────────────────────────────
    "hunter": {
        "enabled": True, "priority": 2, "type": "email",
        "api_key_env": "HUNTER_API_KEY",
        "free_tier_limit": "50 credits/mo",
        "base_url": "https://api.hunter.io/v2",
    },
    "apollo": {
        "enabled": True, "priority": 2, "type": "email",
        "api_key_env": "APOLLO_API_KEY",
        "free_tier_limit": "60 credits/mo",
        "base_url": "https://api.apollo.io/v1",
    },
    "snov": {
        "enabled": True, "priority": 2, "type": "email",
        "api_key_env": "SNOV_API_KEY",
        "free_tier_limit": "50 credits/mo",
        "base_url": "https://api.snov.io/v1",
    },
    "seamless_ai": {
        "enabled": True, "priority": 3, "type": "email",
        "api_key_env": "SEAMLESS_AI_KEY",
        "free_tier_limit": "50 lifetime credits",
        "base_url": "https://api.seamless.ai",
    },
    "tomba": {
        "enabled": False, "priority": 3, "type": "email",
        "api_key_env": "TOMBA_API_KEY",
        "free_tier_limit": "25 credits/mo",
        "base_url": "https://api.tomba.io/v1",
    },
    # ── Email Verification APIs ───────────────────────────────────────
    "zerobounce": {
        "enabled": True, "priority": 2, "type": "api",
        "api_key_env": "ZEROBOUNCE_API_KEY",
        "free_tier_limit": "100 credits/mo",
        "base_url": "https://api.zerobounce.net/v2",
    },
    "neverbounce": {
        "enabled": False, "priority": 3, "type": "api",
        "api_key_env": "NEVERBOUNCE_API_KEY",
        "free_tier_limit": "1000 one-time free",
        "base_url": "https://api.neverbounce.com/v4",
    },
    "kickbox": {
        "enabled": False, "priority": 3, "type": "api",
        "api_key_env": "KICKBOX_API_KEY",
        "free_tier_limit": "100 credits/mo",
        "base_url": "https://open.kickbox.com/v1",
    },
    # ── Phone & Location APIs ─────────────────────────────────────────
    "google_places": {
        "enabled": True, "priority": 1, "type": "api",
        "api_key_env": "GOOGLE_PLACES_API_KEY",
        "free_tier_limit": "$200/mo free credit",
        "base_url": "https://maps.googleapis.com/maps/api",
    },
    "abstract_api": {
        "enabled": False, "priority": 3, "type": "api",
        "api_key_env": "ABSTRACT_API_KEY",
        "free_tier_limit": "100 credits/mo",
        "base_url": "https://app.abstractapi.com/api",
    },
    # ── Social & OSINT ────────────────────────────────────────────────
    "hibp": {
        "enabled": False, "priority": 4, "type": "osint",
        "api_key_env": "HIBP_API_KEY",
        "free_tier_limit": "$3.50/mo — optional",
        "base_url": "https://haveibeenpwned.com/api/v3",
    },
    "maigret": {
        "enabled": False, "priority": 4, "type": "osint",
        "requires_browser": False,
        "free_tier_limit": "Unlimited (local tool)",
    },
    "github_email": {
        "enabled": False, "priority": 4, "type": "osint",
        "requires_browser": False,
        "free_tier_limit": "Unlimited (public commits)",
    },
    # ── Browser-based Sources ─────────────────────────────────────────
    "linkedin": {
        "enabled": True, "priority": 3, "type": "browser",
        "requires_browser": True,
        "regions": [Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT],
    },
    "google_dorking": {
        "enabled": True, "priority": 2, "type": "scrape",
        "free_tier_limit": "Unlimited (manual search)",
    },
    # ── GCC Job Boards ────────────────────────────────────────────────
    "bayt": {
        "enabled": True, "priority": 2, "type": "scrape",
        "base_url": "https://www.bayt.com",
        "regions": [Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT],
    },
    "naukri_gulf": {
        "enabled": True, "priority": 2, "type": "scrape",
        "base_url": "https://www.naukrigulf.com",
        "regions": [Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT],
    },
    "gulf_talent": {
        "enabled": True, "priority": 2, "type": "scrape",
        "base_url": "https://www.gulftalent.com",
        "regions": [Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN, Region.OMAN, Region.KUWAIT],
    },
    "laimoon": {
        "enabled": False, "priority": 3, "type": "scrape",
        "base_url": "https://www.laimoon.com",
        "regions": [Region.UAE, Region.SAUDI, Region.QATAR],
    },
    "foundit_gulf": {
        "enabled": False, "priority": 3, "type": "scrape",
        "base_url": "https://www.foundit.in/gulf",
        "regions": [Region.UAE, Region.SAUDI, Region.QATAR, Region.BAHRAIN],
    },
    # ── GCC Classifieds (phone-number goldmines) ──────────────────────
    "expatriates": {
        "enabled": True, "priority": 1, "type": "scrape",
        "base_url": "https://www.expatriates.com",
        "regions": [Region.UAE, Region.SAUDI, Region.QATAR, Region.KUWAIT, Region.BAHRAIN, Region.OMAN],
        "free_tier_limit": "Unlimited",
    },
    "dubizzle": {
        "enabled": True, "priority": 1, "type": "scrape",
        "base_url": "https://dubai.dubizzle.com",
        "regions": [Region.UAE],
        "free_tier_limit": "Unlimited",
    },
    # ── GCC Directories ───────────────────────────────────────────────
    "dmcc_directory": {
        "enabled": True, "priority": 2, "type": "directory",
        "base_url": "https://www.dmcc.ae",
        "regions": [Region.UAE],
        "free_tier_limit": "Unlimited",
    },
    "yellowpages_ae": {
        "enabled": True, "priority": 2, "type": "directory",
        "base_url": "https://www.yellowpages.ae",
        "regions": [Region.UAE],
        "free_tier_limit": "Unlimited",
    },
    "chamber_of_commerce": {
        "enabled": False, "priority": 3, "type": "directory",
        "regions": [Region.UAE, Region.SAUDI, Region.QATAR],
        "free_tier_limit": "Unlimited",
    },
    # ── Social / Community ────────────────────────────────────────────
    "facebook_groups": {
        "enabled": False, "priority": 3, "type": "social",
        "requires_browser": True,
        "regions": [Region.UAE, Region.SAUDI, Region.QATAR],
        "free_tier_limit": "Requires login session",
    },
    "telegram_groups": {
        "enabled": False, "priority": 4, "type": "social",
        "regions": [Region.UAE, Region.SAUDI],
        "free_tier_limit": "Unlimited",
    },
    # ── Event / Conference ────────────────────────────────────────────
    "hrse_speakers": {
        "enabled": False, "priority": 3, "type": "scrape",
        "base_url": "https://www.hrse.ae",
        "regions": [Region.UAE],
        "free_tier_limit": "Unlimited (public lists)",
    },
    "university_career_fairs": {
        "enabled": False, "priority": 4, "type": "scrape",
        "regions": [Region.UAE],
        "free_tier_limit": "Unlimited",
    },
    # ── Aggregators ───────────────────────────────────────────────────
    "indeed_uae": {
        "enabled": False, "priority": 3, "type": "scrape",
        "base_url": "https://ae.indeed.com",
        "regions": [Region.UAE],
    },
    # ── Email Permutation / Guessing ──────────────────────────────────
    "mailfoguess": {
        "enabled": False, "priority": 4, "type": "email",
        "free_tier_limit": "Unlimited (local tool)",
    },
    "name2email": {
        "enabled": False, "priority": 4, "type": "email",
        "base_url": "https://name2email.com",
        "free_tier_limit": "Unlimited",
    },
}


class SourcesConfig(BaseModel):
    """
    Dynamic source configuration.
    Keys must match ALL_SOURCES. Missing keys inherit defaults.
    """

    model_config = {"extra": "allow"}

    def get_source(self, name: str) -> SourceDefinition:
        """Get a source definition by name, falling back to ALL_SOURCES defaults."""
        raw = getattr(self, name, None)
        if raw is not None:
            return raw  # type: ignore[return-value]
        defaults = ALL_SOURCES.get(name, {})
        return SourceDefinition(**defaults)

    def enabled_sources(self, region: Optional[Region] = None) -> List[str]:
        """Return names of enabled sources, optionally filtered by region."""
        out: List[str] = []
        for name in {**ALL_SOURCES, **{k: {} for k in self.model_extra or {}}}:
            sd = self.get_source(name)
            if not sd.enabled:
                continue
            if region and sd.regions and region not in sd.regions and Region.GCC not in sd.regions:
                continue
            out.append(name)
        return sorted(out, key=lambda n: self.get_source(n).priority)


# ---------------------------------------------------------------------------
# Root configuration model
# ---------------------------------------------------------------------------

class RCFConfig(BaseModel):
    """Root configuration — mirrors config.yml exactly."""

    general: GeneralConfig = Field(default_factory=GeneralConfig)
    uae: UAEConfig = Field(default_factory=UAEConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    rate_limits: RateLimitConfig = Field(default_factory=RateLimitConfig)
    verification: VerificationConfig = Field(default_factory=VerificationConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    sources: SourcesConfig = Field(default_factory=SourcesConfig)

    # ── Loaders ────────────────────────────────────────────────────────

    @classmethod
    def from_yaml(cls, path: Path) -> "RCFConfig":
        """Load configuration from a YAML file, falling back to defaults for missing keys."""
        if not path.exists():
            return cls()
        with open(path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        # Build source sub-dicts into SourceDefinition instances
        if "sources" in raw and isinstance(raw["sources"], dict):
            src_defs: Dict[str, SourceDefinition] = {}
            for name, cfg in raw["sources"].items():
                merged = {**ALL_SOURCES.get(name, {}), **(cfg or {})}
                src_defs[name] = SourceDefinition(**merged)
            raw["sources"] = src_defs
        return cls(**raw)

    def resolve_api_key(self, source_name: str) -> Optional[str]:
        """Resolve the API key for a source from environment variables."""
        sd = self.sources.get_source(source_name)
        if not sd.api_key_env:
            return None
        return os.environ.get(sd.api_key_env)
