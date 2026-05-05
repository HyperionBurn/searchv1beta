"""
Enumerations for the UAE/GCC Recruiter Contact Finder.

Every enum is typed with str + lower-case auto values so JSON serialisation
produces human-readable strings and CLI flags map directly.
"""

from __future__ import annotations

from enum import Enum, unique


class _LowerStrEnum(str, Enum):
    """Base: serialises to lower-case string value."""

    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list) -> str:  # type: ignore[override]
        return name.lower()


# ---------------------------------------------------------------------------
# Geographic / regional
# ---------------------------------------------------------------------------

@unique
class Region(_LowerStrEnum):
    """Geographic region for search scoping and result tagging."""
    UAE = "uae"
    SAUDI = "saudi"
    QATAR = "qatar"
    BAHRAIN = "bahrain"
    OMAN = "oman"
    KUWAIT = "kuwait"
    GCC = "gcc"
    GLOBAL = "global"


@unique
class GCSCountry(_LowerStrEnum):
    """ISO-style GCC country codes used for phone validation dispatch."""
    AE = "ae"   # United Arab Emirates   +971
    SA = "sa"   # Saudi Arabia            +966
    QA = "qa"   # Qatar                   +974
    BH = "bh"   # Bahrain                 +973
    OM = "om"   # Oman                    +968
    KW = "kw"   # Kuwait                  +965


# ---------------------------------------------------------------------------
# Contact / person
# ---------------------------------------------------------------------------

@unique
class ContactType(_LowerStrEnum):
    """Role category of the recruiter contact."""
    RECRUITER = "recruiter"
    HR_MANAGER = "hr_manager"
    TALENT_ACQUISITION = "talent_acquisition"
    HEADHUNTER = "headhunter"
    AGENCY = "agency"


# ---------------------------------------------------------------------------
# Source
# ---------------------------------------------------------------------------

@unique
class SourceType(_LowerStrEnum):
    """Origin category of a data point."""
    API = "api"
    SCRAPE = "scrape"
    PERMUTATION = "permutation"
    DIRECTORY = "directory"
    CLASSIFIED = "classified"
    SOCIAL = "social"
    EVENT = "event"
    BROWSER = "browser"
    OSINT = "osint"
    EMAIL = "email"


@unique
class APIProvider(_LowerStrEnum):
    """External APIs the tool integrates with."""
    HUNTER = "hunter"
    SNOV = "snov"
    CLEARBIT = "clearbit"
    ROCKETREACH = "rocketreach"
    PROXYCURL = "proxycurl"
    GOOGLE_MAPS = "google_maps"
    LINKEDIN = "linkedin"
    BAYT = "bayt"
    NAUKRIGULF = "naukrigulf"
    GULFTAENT = "gulftalent"
    EXPATRIATES = "expatriates"
    DUBIZZLE = "dubizzle"
    DMCC = "dmcc"
    YELLOWPAGES_AE = "yellowpages_ae"
    INTERNAL = "internal"


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

@unique
class VerificationStatus(_LowerStrEnum):
    """Email / phone verification state machine."""
    UNVERIFIED = "unverified"
    SYNTAX_VALID = "syntax_valid"
    DNS_VALID = "dns_valid"
    SMTP_VALID = "smtp_valid"
    API_VALID = "api_valid"
    BOUNCE = "bounce"
    INVALID = "invalid"


@unique
class VerificationMethod(_LowerStrEnum):
    """How verification was performed."""
    REGEX = "regex"
    MX_LOOKUP = "mx_lookup"
    SMTP_RCPT = "smtp_rcpt"
    API_CHECK = "api_check"
    BREACH_DB = "breach_db"
    MANUAL = "manual"
    WEB_CONFIRM = "web_confirm"


# ---------------------------------------------------------------------------
# Phone
# ---------------------------------------------------------------------------

@unique
class PhoneType(_LowerStrEnum):
    """Type of telephone number."""
    MOBILE = "mobile"
    LANDLINE = "landline"
    TOLLFREE = "tollfree"
    PREMIUM = "premium"
    UNKNOWN = "unknown"


@unique
class UAECarrier(_LowerStrEnum):
    """UAE mobile network operator."""
    ETISALAT = "etisalat"
    DU = "du"
    VIRGIN_MOBILE = "virgin_mobile"
    UNKNOWN = "unknown"


@unique
class UAEPhoneCategory(_LowerStrEnum):
    """Categorises UAE number prefix ranges."""
    ETISALAT_MOBILE = "etisalat_mobile"     # 50, 52, 54, 56, 58
    DU_MOBILE = "du_mobile"                 # 52, 55, 56, 58 (shared ranges)
    VIRGIN_MOBILE = "virgin_mobile"         # MVNO on du network
    ETISALAT_LANDLINE = "etisalat_landline" # 02, 03, 04, 06, 07, 09
    DU_LANDLINE = "du_landline"             # 04 (shared)
    TOLLFREE = "tollfree"                   # 800, 900
    PREMIUM = "premium"                     # 700
    UNKNOWN = "unknown"


@unique
class UAECarrierPrefix(_LowerStrEnum):
    """Maps UAE mobile prefixes to their known carrier.

    NOTE: Due to MNP (Mobile Number Portability) since 2019, prefix is
    only a *hint*, not a guarantee.  Use carrier lookup API for accuracy.
    """
    ETISALAT_50 = "etisalat_50"
    SHARED_52 = "shared_52"  # Ambiguous post-MNP
    ETISALAT_54 = "etisalat_54"
    ETISALAT_56 = "etisalat_56"
    ETISALAT_58 = "etisalat_58"
    DU_55 = "du_55"
    DU_56 = "du_56"  # Originally Etisalat, now ambiguous post-MNP
    DU_58 = "du_58"  # Originally Etisalat, now ambiguous post-MNP
    VIRGIN_55 = "virgin_55"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# UAE specifics
# ---------------------------------------------------------------------------

@unique
class UAEFreeZone(_LowerStrEnum):
    """Major UAE free zones — useful for company profiling."""
    DMCC = "dmcc"
    DIFC = "difc"
    DSO = "dso"              # Dubai Silicon Oasis
    DAFZA = "dafza"          # Dubai Airport Free Zone
    JAFZA = "jafza"          # Jabel Ali Free Zone
    ADGM = "adgm"            # Abu Dhabi Global Market
    KIZAD = "kizad"          # Khalifa Industrial Zone
    TWOFOUR54 = "twofour54"  # Abu Dhabi media zone
    SHAMS = "shams"          # Sharjah Media City
    SAIF_ZONE = "saif_zone"  # Sharjah Airport Free Zone
    HAMRIYAH = "hamriyah"    # Hamriyah Free Zone
    RAKEZ = "rakez"          # Ras Al Khaimah FTZ
    FUJAIRAH_FTZ = "fujairah_ftz"
    AJMAN_FTZ = "ajman_ftz"
    UMM_AL_QUWAIN_FTZ = "uaq_ftz"
    NONE = "none"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

@unique
class SessionStatus(_LowerStrEnum):
    """Lifecycle state of a search session."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@unique
class ExportFormat(_LowerStrEnum):
    """Supported export formats."""
    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"
    HTML = "html"
    EXCEL = "excel"  # backward-compat alias for XLSX
    VCARD = "vcard"
    MARKDOWN = "markdown"
