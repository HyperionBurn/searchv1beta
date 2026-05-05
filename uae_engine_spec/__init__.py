"""
UAE/GCC Recruiter Contact Finder Engine — Complete Specification Package.

Modules:
    arabic_name_engine  — Arabic name normalization and email pattern generation
    uae_phone_engine    — UAE/GCC phone validation, carrier detection, classification
    uae_domain_engine   — UAE employer domain resolution and email format lookup
    whatsapp_engine     — WhatsApp number detection and enrichment
    uae_google_dork     — UAE-specific Google dork query builder
    uae_ats             — ATS detection and recruiter metadata extraction
    uae_compliance      — Legal compliance, rate limiting, and data retention

Usage:
    from uae_engine_spec import (
        ArabicNameEngine,
        UAEPhoneEngine,
        UAEDomainEngine,
        WhatsAppEngine,
        UAEGoogleDorkEngine,
        UAEATSEngine,
        UAEComplianceEngine,
    )
"""

from .arabic_name_engine import ArabicNameEngine, NormalizedName, EXAMPLES
from .uae_phone_engine import (
    UAEPhoneEngine,
    UAEPhoneInfo,
    PhoneType,
    Carrier,
    Emirate,
)
from .uae_domain_engine import UAEDomainEngine, EmployerEmailInfo, EMPLOYER_DATABASE
from .whatsapp_engine import (
    WhatsAppEngine,
    WhatsAppInfo,
    WhatsAppBusinessProfile,
    LEGAL_DISCLAIMER as WHATSAPP_LEGAL_DISCLAIMER,
)
from .uae_google_dork import UAEGoogleDorkEngine, QUERY_TEMPLATES
from .uae_ats import UAEATSEngine, ATSInfo, RecruiterMetadata
from .uae_compliance import UAEComplianceEngine, ComplianceReport

__all__ = [
    "ArabicNameEngine",
    "NormalizedName",
    "UAEPhoneEngine",
    "UAEPhoneInfo",
    "PhoneType",
    "Carrier",
    "Emirate",
    "UAEDomainEngine",
    "EmployerEmailInfo",
    "EMPLOYER_DATABASE",
    "WhatsAppEngine",
    "WhatsAppInfo",
    "WhatsAppBusinessProfile",
    "UAEGoogleDorkEngine",
    "QUERY_TEMPLATES",
    "UAEATSEngine",
    "ATSInfo",
    "RecruiterMetadata",
    "UAEComplianceEngine",
    "ComplianceReport",
    "EXAMPLES",
]
