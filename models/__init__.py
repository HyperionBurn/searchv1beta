"""
UAE/GCC Recruiter Contact Finder — Data Model Package.

All Pydantic V2 models, enums, validators, and type aliases for the CLI tool.
"""

from .enums import (
    APIProvider,
    ContactType,
    ExportFormat,
    GCSCountry,
    PhoneType,
    Region,
    SessionStatus,
    SourceType,
    UAECarrier,
    UAECarrierPrefix,
    UAEFreeZone,
    UAEPhoneCategory,
    VerificationMethod,
    VerificationStatus,
)
from .validators import (
    ArabicNameNormalizer,
    GCCTelecomDB,
    UAEDomainValidator,
    normalize_arabic_name,
    validate_email,
    validate_gcc_phone,
    validate_linkedin_url,
    validate_saudi_phone,
    validate_uae_phone,
)
from .models import (
    APIUsageTracker,
    ArabicName,
    CompanyProfile,
    ConfidenceScore,
    ContactQuery,
    EmailRecord,
    ExportRecord,
    PhoneRecord,
    RecruiterContact,
    SearchSession,
    SourceResult,
    UAEPhoneInfo,
)

__all__ = [
    # Enums
    "APIProvider",
    "ContactType",
    "ExportFormat",
    "GCSCountry",
    "PhoneType",
    "Region",
    "SessionStatus",
    "SourceType",
    "UAECarrier",
    "UAECarrierPrefix",
    "UAEFreeZone",
    "UAEPhoneCategory",
    "VerificationMethod",
    "VerificationStatus",
    # Validators
    "ArabicNameNormalizer",
    "GCCTelecomDB",
    "UAEDomainValidator",
    "normalize_arabic_name",
    "validate_email",
    "validate_gcc_phone",
    "validate_linkedin_url",
    "validate_saudi_phone",
    "validate_uae_phone",
    # Models
    "APIUsageTracker",
    "ArabicName",
    "CompanyProfile",
    "ConfidenceScore",
    "ContactQuery",
    "EmailRecord",
    "ExportRecord",
    "PhoneRecord",
    "RecruiterContact",
    "SearchSession",
    "SourceResult",
    "UAEPhoneInfo",
]
