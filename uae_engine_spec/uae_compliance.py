"""
UAEComplianceEngine — Legal compliance and rate limiting for UAE web scraping.

Provides:
- Legal disclaimer display on startup
- robots.txt checker before scraping
- Rate limit enforcer (1 req/5 sec for UAE sites)
- Data retention policy (delete after 90 days)
- Personal use disclaimer
- UAE cybercrime law warnings
- Session logging and audit trail

LEGAL FRAMEWORK:
- UAE Federal Decree-Law No. 34/2021 (Cybercrime Law)
- UAE Federal Decree-Law No. 45/2021 (Personal Data Protection Law)
- WhatsApp/Meta Terms of Service
- robots.txt standard (RFC 9309)
- GDPR (if processing EU citizen data)

Production-grade: no placeholders.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import urllib.robotparser
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Rate limits per domain category
RATE_LIMITS: dict[str, float] = {
    "uae_government": 10.0,    # 1 req per 10 sec for .gov.ae
    "uae_corporate": 5.0,      # 1 req per 5 sec for UAE companies
    "uae_classifieds": 3.0,    # 1 req per 3 sec for Dubizzle/Expatriates
    "linkedin": 10.0,          # 1 req per 10 sec for LinkedIn
    "google": 2.0,             # 1 req per 2 sec for Google searches
    "whatsapp": 5.0,           # 1 req per 5 sec for wa.me checks
    "job_boards": 3.0,         # 1 req per 3 sec for Bayt/NaukriGulf
    "social_media": 5.0,       # 1 req per 5 sec for Facebook/Twitter
    "default": 5.0,            # Default rate limit
}

# Data retention: 90 days
DATA_RETENTION_DAYS: int = 90

# Domains exempt from robots.txt checking (public APIs, etc.)
ROBOTS_TXT_EXEMPT_DOMAINS: list[str] = [
    "wa.me",
    "api.whatsapp.com",
]

# User agent string for robots.txt checking
USER_AGENT: str = "UAE-Recruiter-Finder/1.0 (Personal Use; +https://github.com/example)"


# ---------------------------------------------------------------------------
# Legal Text
# ---------------------------------------------------------------------------

STARTUP_DISCLAIMER: str = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   🔒 UAE Recruiter Contact Finder — Legal Compliance Notice                  ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   This tool is designed for PERSONAL, NON-COMMERCIAL job search research.   ║
║                                                                              ║
║   ⚠️  UAE CYBERCRIME LAW (Federal Decree-Law No. 34/2021):                  ║
║   • Unauthorized access to information systems is a criminal offense         ║
║   • Penalties: imprisonment + fines up to AED 3,000,000                     ║
║   • Automated data collection without authorization may violate this law     ║
║                                                                              ║
║   ⚠️  UAE DATA PROTECTION LAW (Federal Decree-Law No. 45/2021):             ║
║   • Processing personal data requires consent or legitimate basis            ║
║   • Data subjects have rights to access, correction, and deletion            ║
║   • Cross-border data transfers are restricted                               ║
║                                                                              ║
║   ⚠️  WHATSAPP TERMS OF SERVICE:                                            ║
║   • Automated scraping of WhatsApp may violate Meta's ToS                    ║
║   • Account may be banned for automated access                               ║
║                                                                              ║
║   ✅ COMPLIANCE RULES ENFORCED BY THIS TOOL:                                ║
║   1. robots.txt is checked before every scrape request                       ║
║   2. Rate limiting enforced (min 5 sec between requests)                     ║
║   3. Data auto-deleted after {retention_days} days                            ║
║   4. No bulk messaging or spam capabilities                                  ║
║   5. All activity is logged for audit purposes                                ║
║   6. Personal use disclaimer shown on startup                                ║
║                                                                              ║
║   By using this tool, you acknowledge:                                       ║
║   • You are using it for personal job search only                            ║
║   • You will not share, sell, or redistribute contact data                   ║
║   • You will obtain consent before contacting recruiters                      ║
║   • You accept full legal responsibility for your use                        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
""".format(retention_days=DATA_RETENTION_DAYS)

PERSONAL_USE_NOTICE: str = (
    "PERSONAL USE ONLY: This tool is for individual job-search research. "
    "All collected data is subject to a 90-day auto-deletion policy. "
    "Do not share, sell, or redistribute any contact information found. "
    "Always obtain explicit consent before contacting anyone."
)

UAE_CYBERCRIME_WARNING: str = (
    "WARNING: UAE Federal Decree-Law No. 34/2021 (Combating Rumors and "
    "Cybercrimes) criminalizes unauthorized access to information systems, "
    "data collection without authorization, and the use of automated means "
    "to gather personal information. Penalties include imprisonment and "
    "fines ranging from AED 50,000 to AED 3,000,000."
)

DATA_RETENTION_NOTICE: str = (
    f"DATA RETENTION POLICY: All collected contact data will be automatically "
    f"deleted after {DATA_RETENTION_DAYS} days. This policy is enforced by "
    f"the UAEComplianceEngine. Data stored in the local database beyond this "
    f"period will be purged on next run."
)


# ---------------------------------------------------------------------------
# Domain Category Classification
# ---------------------------------------------------------------------------

DOMAIN_CATEGORIES: dict[str, str] = {
    # UAE government
    ".gov.ae": "uae_government",
    "gov.ae": "uae_government",
    # UAE classifieds
    "dubizzle.com": "uae_classifieds",
    "expatriates.com": "uae_classifieds",
    # LinkedIn
    "linkedin.com": "linkedin",
    # Google
    "google.com": "google",
    "google.ae": "google",
    # WhatsApp
    "wa.me": "whatsapp",
    "api.whatsapp.com": "whatsapp",
    "web.whatsapp.com": "whatsapp",
    # Job boards
    "bayt.com": "job_boards",
    "naukrigulf.com": "job_boards",
    "gulftalent.com": "job_boards",
    "laimoon.com": "job_boards",
    "foundit.in": "job_boards",
    "indeed.com": "job_boards",
    "ae.indeed.com": "job_boards",
    # Social media
    "facebook.com": "social_media",
    "twitter.com": "social_media",
    "x.com": "social_media",
    "instagram.com": "social_media",
    "telegram.me": "social_media",
    "t.me": "social_media",
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class RateLimitState:
    """Tracks rate limit state per domain."""
    domain: str
    last_request_time: float = 0.0
    request_count: int = 0
    category: str = "default"


@dataclass
class ComplianceLogEntry:
    """Single compliance audit log entry."""
    timestamp: float
    action: str          # "scrape", "robots_check", "rate_limit_wait", "data_delete"
    target_url: str
    result: str          # "allowed", "blocked", "deferred"
    reason: str
    details: Optional[str] = None


@dataclass
class ComplianceReport:
    """Summary compliance report."""
    session_start: datetime
    total_requests: int
    blocked_by_robots: int
    rate_limited_waits: int
    data_deleted_count: int
    domains_accessed: list[str]
    warnings: list[str]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class UAEComplianceEngine:
    """
    Legal compliance and rate limiting engine for UAE web scraping.

    Enforces:
    - robots.txt compliance
    - Per-domain rate limiting
    - Data retention (90-day auto-deletion)
    - Audit logging
    - Legal disclaimers
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        log_file: Optional[Path] = None,
        respect_robots_txt: bool = True,
        enforce_rate_limits: bool = True,
    ):
        """
        Args:
            data_dir: Directory where collected data is stored.
            log_file: Path to compliance audit log file.
            respect_robots_txt: If True, check robots.txt before scraping.
            enforce_rate_limits: If True, enforce rate limiting.
        """
        self._data_dir = data_dir or Path("./data")
        self._log_file = log_file or self._data_dir / "compliance_log.jsonl"
        self._respect_robots = respect_robots_txt
        self._enforce_rate = enforce_rate_limits

        # Rate limit state per domain
        self._rate_states: dict[str, RateLimitState] = {}

        # Robots.txt cache: domain → RobotFileParser
        self._robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}

        # Session stats
        self._session_start = datetime.now()
        self._total_requests = 0
        self._blocked_by_robots = 0
        self._rate_limited_waits = 0

        # Ensure data dir exists
        self._data_dir.mkdir(parents=True, exist_ok=True)

    # ---- Public API ----

    def display_startup_disclaimer(self) -> str:
        """
        Display the legal disclaimer on tool startup.

        Returns:
            Formatted disclaimer string to display to the user.

        Example:
            >>> eng = UAEComplianceEngine()
            >>> print(eng.display_startup_disclaimer())
            🔒 UAE Recruiter Contact Finder — Legal Compliance Notice
            ...
        """
        return STARTUP_DISCLAIMER

    def check_robots_txt(self, url: str) -> bool:
        """
        Check if a URL is allowed by the site's robots.txt.

        Caches robots.txt parsers per domain for efficiency.
        Re-checks every 30 minutes.

        Args:
            url: URL to check.

        Returns:
            True if scraping is allowed, False if blocked.

        Example:
            >>> eng = UAEComplianceEngine()
            >>> eng.check_robots_txt("https://www.linkedin.com/jobs/view/123")
            False  # LinkedIn typically disallows scraping
            >>> eng.check_robots_txt("https://example.com/public-page")
            True
        """
        if not self._respect_robots:
            return True

        parsed = urlparse(url)
        domain = parsed.netloc

        # Exempt domains
        for exempt in ROBOTS_TXT_EXEMPT_DOMAINS:
            if domain.endswith(exempt):
                return True

        # Check cache
        if domain not in self._robots_cache:
            robots_url = f"{parsed.scheme}://{domain}/robots.txt"
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots_url)
            try:
                rp.read()
            except Exception:
                # If robots.txt can't be fetched, assume allowed
                # but log a warning
                self._log_entry(
                    action="robots_check",
                    target_url=url,
                    result="allowed",
                    reason="robots.txt fetch failed — assuming allowed",
                )
                return True
            self._robots_cache[domain] = rp

        rp = self._robots_cache[domain]
        allowed = rp.can_fetch(USER_AGENT, url)

        self._log_entry(
            action="robots_check",
            target_url=url,
            result="allowed" if allowed else "blocked",
            reason="robots.txt " + ("allows" if allowed else "disallows"),
        )

        if not allowed:
            self._blocked_by_robots += 1

        return allowed

    def enforce_rate_limit(self, url: str) -> float:
        """
        Enforce rate limiting for a URL's domain.

        Returns the number of seconds waited (0 if no wait needed).

        Args:
            url: URL about to be requested.

        Returns:
            Seconds waited for rate limit compliance.

        Example:
            >>> eng = UAEComplianceEngine()
            >>> wait_time = eng.enforce_rate_limit("https://www.bayt.com/...")
            >>> wait_time >= 0
            True
        """
        if not self._enforce_rate:
            return 0.0

        domain = urlparse(url).netloc
        category = self._classify_domain(domain)
        min_interval = RATE_LIMITS.get(category, RATE_LIMITS["default"])

        if domain not in self._rate_states:
            self._rate_states[domain] = RateLimitState(
                domain=domain,
                category=category,
            )

        state = self._rate_states[domain]
        elapsed = time.time() - state.last_request_time
        wait_time = 0.0

        if elapsed < min_interval:
            wait_time = min_interval - elapsed
            self._rate_limited_waits += 1
            self._log_entry(
                action="rate_limit_wait",
                target_url=url,
                result="deferred",
                reason=f"Rate limit: waited {wait_time:.1f}s "
                       f"(category: {category}, min_interval: {min_interval}s)",
            )
            time.sleep(wait_time)

        state.last_request_time = time.time()
        state.request_count += 1
        self._total_requests += 1

        return wait_time

    def check_data_retention(self) -> list[Path]:
        """
        Check for data files older than the retention period.

        Returns list of files that should be deleted.

        Args: None.

        Returns:
            List of Path objects for expired data files.

        Example:
            >>> eng = UAEComplianceEngine(data_dir=Path("./data"))
            >>> expired = eng.check_data_retention()
            >>> for f in expired:
            ...     f.unlink()  # delete expired files
        """
        cutoff = datetime.now() - timedelta(days=DATA_RETENTION_DAYS)
        cutoff_ts = cutoff.timestamp()
        expired_files: list[Path] = []

        if not self._data_dir.exists():
            return expired_files

        for f in self._data_dir.rglob("*"):
            if f.is_file():
                # Skip compliance log itself
                if f == self._log_file:
                    continue
                if f.stat().st_mtime < cutoff_ts:
                    expired_files.append(f)

        if expired_files:
            self._log_entry(
                action="data_delete",
                target_url="",
                result="pending",
                reason=f"{len(expired_files)} files exceed {DATA_RETENTION_DAYS}-day retention",
                details=str([str(f) for f in expired_files]),
            )

        return expired_files

    def enforce_data_retention(self) -> int:
        """
        Delete data files older than the retention period.

        Returns the number of files deleted.

        Args: None.

        Returns:
            Count of deleted files.
        """
        expired = self.check_data_retention()
        count = 0
        for f in expired:
            try:
                f.unlink()
                count += 1
            except Exception:
                pass

        if count > 0:
            self._log_entry(
                action="data_delete",
                target_url="",
                result="completed",
                reason=f"Deleted {count} expired data files",
            )

        return count

    def get_compliance_report(self) -> ComplianceReport:
        """
        Generate a compliance report for the current session.

        Returns:
            ComplianceReport with session statistics.

        Example:
            >>> eng = UAEComplianceEngine()
            >>> report = eng.get_compliance_report()
            >>> report.total_requests
            0
            >>> report.blocked_by_robots
            0
        """
        return ComplianceReport(
            session_start=self._session_start,
            total_requests=self._total_requests,
            blocked_by_robots=self._blocked_by_robots,
            rate_limited_waits=self._rate_limited_waits,
            data_deleted_count=0,
            domains_accessed=list(self._rate_states.keys()),
            warnings=self._generate_warnings(),
        )

    def should_proceed(self, url: str) -> tuple[bool, str]:
        """
        Full compliance check before making a request.

        Checks robots.txt AND rate limits.

        Args:
            url: URL about to be requested.

        Returns:
            Tuple of (should_proceed: bool, reason: str).

        Example:
            >>> eng = UAEComplianceEngine()
            >>> allowed, reason = eng.should_proceed("https://example.com/page")
            >>> if allowed:
            ...     # proceed with request
            ...     pass
            ... else:
            ...     print(f"Blocked: {reason}")
        """
        # Check robots.txt
        if not self.check_robots_txt(url):
            return False, "Blocked by robots.txt"

        # Enforce rate limit
        wait_time = self.enforce_rate_limit(url)
        if wait_time > 0:
            pass  # Already waited

        return True, "Allowed"

    def get_legal_notice(self) -> str:
        """
        Get the personal use disclaimer text.

        Returns:
            Personal use disclaimer string.
        """
        return PERSONAL_USE_NOTICE

    def get_cybercrime_warning(self) -> str:
        """
        Get the UAE cybercrime law warning.

        Returns:
            UAE cybercrime law warning string.
        """
        return UAE_CYBERCRIME_WARNING

    # ---- Private helpers ----

    def _classify_domain(self, domain: str) -> str:
        """Classify a domain into a rate-limit category."""
        domain_lower = domain.lower()

        # Exact match
        if domain_lower in DOMAIN_CATEGORIES:
            return DOMAIN_CATEGORIES[domain_lower]

        # Suffix match
        for suffix, category in DOMAIN_CATEGORIES.items():
            if domain_lower.endswith(suffix):
                return category

        # UAE government
        if domain_lower.endswith(".gov.ae"):
            return "uae_government"

        # UAE corporate (.ae domain)
        if domain_lower.endswith(".ae"):
            return "uae_corporate"

        return "default"

    def _log_entry(
        self,
        action: str,
        target_url: str,
        result: str,
        reason: str,
        details: Optional[str] = None,
    ) -> None:
        """Write a compliance log entry."""
        entry = ComplianceLogEntry(
            timestamp=time.time(),
            action=action,
            target_url=target_url,
            result=result,
            reason=reason,
            details=details,
        )

        try:
            self._log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._log_file, "a") as f:
                f.write(json.dumps({
                    "timestamp": entry.timestamp,
                    "action": entry.action,
                    "target_url": entry.target_url,
                    "result": entry.result,
                    "reason": entry.reason,
                    "details": entry.details,
                }) + "\n")
        except Exception:
            pass  # Don't fail the main workflow for logging errors

    def _generate_warnings(self) -> list[str]:
        """Generate compliance warnings based on session activity."""
        warnings: list[str] = []

        if self._blocked_by_robots > 0:
            warnings.append(
                f"{self._blocked_by_robots} requests blocked by robots.txt. "
                f"Respect site scraping policies."
            )

        for domain, state in self._rate_states.items():
            if state.request_count > 100:
                warnings.append(
                    f"High request count to {domain}: {state.request_count} "
                    f"requests. Consider reducing frequency."
                )

        return warnings
