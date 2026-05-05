"""
Pydantic V2 Models for the UAE/GCC Recruiter Contact Finder.

All models use Pydantic V2's `model_config = ConfigDict(...)` style.
Every field has explicit types, constraints, descriptions, and validators.
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

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
    UAEFreeZone,
    VerificationMethod,
    VerificationStatus,
)
from .validators import (
    infer_uae_carrier,
    infer_uae_emirate,
    is_uae_mobile,
    validate_email,
    validate_gcc_phone,
    validate_linkedin_url,
    validate_uae_phone,
)


# =====================================================================
# Helper: UTC now factory
# =====================================================================

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


# =====================================================================
# MODELS
# =====================================================================


class ContactQuery(BaseModel):
    """User input parameters for a recruiter contact search."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "description": "Search query parameters for finding recruiter contacts.",
            "examples": [
                {
                    "company_names": ["DMCC", "Michael Page"],
                    "industry": "recruitment",
                    "region": "uae",
                    "contact_types": ["recruiter", "headhunter"],
                    "max_results": 50,
                    "min_confidence": 0.6,
                }
            ],
        },
    )

    company_names: list[str] = Field(
        default_factory=list,
        description="Target company names to search recruiters for.",
        examples=[["DMCC", "Michael Page", "Hays"]],
    )
    industry: str | None = Field(
        default=None,
        max_length=100,
        description="Industry filter (e.g. 'recruitment', 'oil & gas', 'fintech').",
    )
    region: Region = Field(
        default=Region.UAE,
        description="Geographic region to scope the search.",
    )
    contact_types: list[ContactType] = Field(
        default_factory=lambda: [ContactType.RECRUITER],
        description="Types of contacts to search for.",
    )
    max_results: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum number of results to return.",
    )
    min_confidence: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score threshold (0.0-1.0).",
    )
    keywords: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Additional keywords (e.g. 'tech hiring', 'executive search').",
    )
    include_unverified: bool = Field(
        default=False,
        description="Include contacts with no email/phone verification.",
    )
    sources: list[SourceType] | None = Field(
        default=None,
        description="Specific source types to query. None = all available.",
    )

    @field_validator("company_names")
    @classmethod
    def _validate_company_names(cls, v: list[str]) -> list[str]:
        cleaned = [name.strip() for name in v if name.strip()]
        if len(cleaned) != len(v):
            raise ValueError("Company names cannot contain blank entries")
        return cleaned

    @field_validator("keywords")
    @classmethod
    def _validate_keywords(cls, v: list[str]) -> list[str]:
        return [kw.strip().lower() for kw in v if kw.strip()]


# -------------------------------------------------------------------
# EmailRecord
# -------------------------------------------------------------------

class EmailRecord(BaseModel):
    """A single email address with verification metadata."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(
        description="Email address (lowercased, trimmed).",
    )
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED,
        description="Current verification state.",
    )
    verification_method: VerificationMethod | None = Field(
        default=None,
        description="Method used for verification.",
    )
    verification_date: datetime | None = Field(
        default=None,
        description="When verification was last performed.",
    )
    is_primary: bool = Field(
        default=False,
        description="Whether this is the primary/corporate email.",
    )
    source: SourceType | None = Field(
        default=None,
        description="Where this email was found.",
    )
    bounce_count: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Number of times an email to this address bounced.",
    )
    last_bounce_date: datetime | None = Field(
        default=None,
        description="Date of last bounce, if any.",
    )

    @field_validator("email")
    @classmethod
    def _validate_email_field(cls, v: str) -> str:
        return validate_email(v)

    @field_validator("verification_method")
    @classmethod
    def _validate_method_when_verified(cls, v: VerificationMethod | None, info) -> VerificationMethod | None:
        status = info.data.get("verification_status")
        if status in (
            VerificationStatus.DNS_VALID,
            VerificationStatus.SMTP_VALID,
            VerificationStatus.API_VALID,
        ) and v is None:
            raise ValueError("verification_method is required when verification_status indicates verified")
        return v


# -------------------------------------------------------------------
# PhoneRecord
# -------------------------------------------------------------------

class PhoneRecord(BaseModel):
    """A single phone number with validation and carrier metadata."""

    model_config = ConfigDict(str_strip_whitespace=True)

    phone: str = Field(
        description="Phone number in E.164 format (+971XXXXXXXXX).",
    )
    validation_status: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED,
        description="Current phone validation state.",
    )
    country_code: str = Field(
        default="AE",
        min_length=2,
        max_length=2,
        description="ISO 3166-1 alpha-2 country code.",
    )
    carrier: str | None = Field(
        default=None,
        description="Mobile network operator (etisalat, du, virgin_mobile).",
    )
    line_type: PhoneType = Field(
        default=PhoneType.UNKNOWN,
        description="Type of phone line.",
    )
    is_whatsapp: bool = Field(
        default=False,
        description="Whether this number has an active WhatsApp account.",
    )
    whatsapp_business: bool = Field(
        default=False,
        description="Whether the WhatsApp account is a Business account.",
    )
    is_primary: bool = Field(
        default=False,
        description="Whether this is the primary contact number.",
    )
    source: SourceType | None = Field(
        default=None,
        description="Where this phone was found.",
    )

    @field_validator("phone")
    @classmethod
    def _validate_phone_field(cls, v: str) -> str:
        """Attempt GCC-wide validation; fall back to basic format check."""
        try:
            return validate_gcc_phone(v)
        except ValueError:
            # Allow non-GCC numbers if they look like valid E.164
            if re.match(r"^\+\d{7,15}$", v):
                return v
            raise

    @model_validator(mode="after")
    def _infer_carrier_if_uae(self) -> "PhoneRecord":
        """Auto-populate carrier for UAE mobile numbers."""
        if self.phone.startswith("+971") and self.carrier is None:
            carrier = infer_uae_carrier(self.phone)
            if carrier != "unknown":
                self.carrier = carrier
            if is_uae_mobile(self.phone):
                if self.line_type == PhoneType.UNKNOWN:
                    self.line_type = PhoneType.MOBILE
        return self


# =====================================================================
# UAE-SPECIFIC MODELS
# =====================================================================


class UAEPhoneInfo(BaseModel):
    """UAE-specific phone metadata: carrier, emirate, number type."""

    model_config = ConfigDict(str_strip_whitespace=True)

    phone_e164: str = Field(
        description="Phone number in E.164 format.",
    )
    carrier: UAECarrier = Field(
        default=UAECarrier.UNKNOWN,
        description="UAE mobile carrier.",
    )
    emirate: str | None = Field(
        default=None,
        description="Inferred emirate for landline numbers.",
    )
    number_type: PhoneType = Field(
        default=PhoneType.UNKNOWN,
        description="Mobile / landline / tollfree / premium.",
    )
    mnp_note: str | None = Field(
        default="Post-MNP (2019): prefix is hint only, use carrier lookup API for accuracy.",
        description="Note about Mobile Number Portability implications.",
    )
    is_whatsapp_likely: bool = Field(
        default=False,
        description="Heuristic: UAE mobile → very likely WhatsApp.",
    )

    @field_validator("phone_e164")
    @classmethod
    def _must_be_uae(cls, v: str) -> str:
        return validate_uae_phone(v)

    @model_validator(mode="after")
    def _populate_uae_fields(self) -> "UAEPhoneInfo":
        """Auto-populate carrier, emirate, and type from the number."""
        carrier_str = infer_uae_carrier(self.phone_e164)
        try:
            self.carrier = UAECarrier(carrier_str)
        except ValueError:
            self.carrier = UAECarrier.UNKNOWN

        self.emirate = infer_uae_emirate(self.phone_e164)

        if self.phone_e164.startswith("+9715"):
            self.number_type = PhoneType.MOBILE
            self.is_whatsapp_likely = True
        elif self.phone_e164.startswith("+971800") or self.phone_e164.startswith("+971900"):
            self.number_type = PhoneType.TOLLFREE
        elif self.phone_e164.startswith("+971700"):
            self.number_type = PhoneType.PREMIUM
        elif any(
            self.phone_e164.startswith(f"+971{ac}")
            for ac in ("2", "3", "4", "6", "7", "9")
        ):
            self.number_type = PhoneType.LANDLINE

        return self


# -------------------------------------------------------------------
# ArabicName
# -------------------------------------------------------------------

class ArabicName(BaseModel):
    """Arabic name with normalised forms and email permutations."""

    model_config = ConfigDict(str_strip_whitespace=True)

    original_name: str = Field(
        min_length=1,
        max_length=300,
        description="Original name as found in source data.",
    )
    normalized_form: str = Field(
        default="",
        min_length=0,
        description="Canonical lowercase normalised form.",
    )
    normalized_forms: list[str] = Field(
        default_factory=list,
        description="All known spelling variants.",
    )
    email_permutations: list[str] = Field(
        default_factory=list,
        description="Generated email local-part permutations (without domain).",
    )
    al_el_bin_removed: str = Field(
        default="",
        description="Name with Al/El/Bin/Bint prefixes stripped.",
    )
    mohammed_variants: list[str] = Field(
        default_factory=list,
        description="If name contains Mohammed, list of variant spellings.",
    )
    first_name: str = Field(
        default="",
        max_length=100,
        description="Extracted first name.",
    )
    last_name: str = Field(
        default="",
        max_length=100,
        description="Extracted last / family name.",
    )
    middle_name: str | None = Field(
        default=None,
        max_length=100,
        description="Middle name if present.",
    )

    @field_validator("original_name")
    @classmethod
    def _original_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("original_name cannot be blank")
        return v

    @model_validator(mode="after")
    def _auto_populate(self) -> "ArabicName":
        """Auto-generate normalised forms and permutations if not provided."""
        from .validators import (
            ArabicNameNormalizer,
            MOHAMMED_VARIANTS,
            generate_email_permutations,
            generate_name_variants,
            normalize_arabic_name,
        )

        norm = normalize_arabic_name(self.original_name)
        if not self.normalized_form:
            self.normalized_form = norm

        if not self.normalized_forms:
            self.normalized_forms = generate_name_variants(self.original_name)

        if not self.al_el_bin_removed:
            self.al_el_bin_removed = ArabicNameNormalizer.strip_prefixes(self.original_name)

        # Mohammed variant detection
        parts = norm.split()
        if not self.mohammed_variants:
            for part in parts:
                if part in MOHAMMED_VARIANTS:
                    self.mohammed_variants = sorted(MOHAMMED_VARIANTS)
                    break

        # Simple name splitting: first = first word, last = last word
        if not self.first_name and parts:
            self.first_name = parts[0]
        if not self.last_name and len(parts) > 1:
            self.last_name = parts[-1]
        if not self.middle_name and len(parts) > 2:
            self.middle_name = " ".join(parts[1:-1])

        return self


# -------------------------------------------------------------------
# CompanyProfile
# -------------------------------------------------------------------

class CompanyProfile(BaseModel):
    """Company metadata for email pattern inference and ATS detection."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(
        min_length=1,
        max_length=300,
        description="Company display name.",
    )
    domain_ae: str | None = Field(
        default=None,
        max_length=253,
        description="Company .ae domain (if known).",
    )
    domain_com: str | None = Field(
        default=None,
        max_length=253,
        description="Company .com domain (if known).",
    )
    industry: str | None = Field(
        default=None,
        max_length=100,
        description="Industry sector.",
    )
    ats_platform: str | None = Field(
        default=None,
        max_length=100,
        description="Detected ATS (e.g. 'taleo', 'sap_successfactors', 'pageup').",
    )
    email_format_pattern: str | None = Field(
        default=None,
        max_length=50,
        description="Inferred email local-part pattern (e.g. 'firstname.lastname').",
    )
    known_emails: list[str] = Field(
        default_factory=list,
        description="Known email addresses used for pattern inference.",
    )
    is_uae_free_zone: bool = Field(
        default=False,
        description="Whether the company operates in a UAE free zone.",
    )
    free_zone_name: UAEFreeZone | None = Field(
        default=None,
        description="Which free zone, if applicable.",
    )
    linkedin_company_url: str | None = Field(
        default=None,
        description="LinkedIn company page URL.",
    )
    country: str = Field(
        default="AE",
        min_length=2,
        max_length=2,
        description="ISO country code.",
    )
    region: Region = Field(
        default=Region.UAE,
        description="Geographic region.",
    )
    employee_count_range: str | None = Field(
        default=None,
        description="Employee count bucket (e.g. '51-200', '1001-5000').",
    )
    created_at: datetime = Field(
        default_factory=_utcnow,
        description="When this profile was first created.",
    )
    updated_at: datetime = Field(
        default_factory=_utcnow,
        description="When this profile was last updated.",
    )

    @field_validator("known_emails")
    @classmethod
    def _validate_known_emails(cls, v: list[str]) -> list[str]:
        return [validate_email(e) for e in v]

    @field_validator("domain_ae", "domain_com")
    @classmethod
    def _validate_domains(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.lower().strip()
        if v.startswith("http://") or v.startswith("https://"):
            raise ValueError("Domain should not include protocol (http/https)")
        if "/" in v:
            raise ValueError("Domain should not include path segments")
        return v

    @model_validator(mode="after")
    def _infer_email_pattern(self) -> "CompanyProfile":
        """Auto-infer email pattern from known emails."""
        if not self.email_format_pattern and self.known_emails:
            from .validators import infer_email_pattern
            self.email_format_pattern = infer_email_pattern(self.known_emails)
        return self


# -------------------------------------------------------------------
# SourceResult
# -------------------------------------------------------------------

class SourceResult(BaseModel):
    """Raw result from a single source before merging/dedup."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "description": "A single raw extraction from one data source.",
        },
    )

    source_name: str = Field(
        min_length=1,
        max_length=100,
        description="Name of the source (e.g. 'linkedin', 'google_maps', 'expatriates').",
    )
    source_type: SourceType = Field(
        description="Category of the source.",
    )
    raw_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw extracted data from the source (unprocessed).",
    )
    extracted_name: str | None = Field(
        default=None,
        description="Name extracted from this source.",
    )
    extracted_email: str | None = Field(
        default=None,
        description="Email extracted from this source.",
    )
    extracted_phone: str | None = Field(
        default=None,
        description="Phone extracted from this source.",
    )
    extracted_company: str | None = Field(
        default=None,
        description="Company name extracted from this source.",
    )
    extracted_title: str | None = Field(
        default=None,
        description="Job title extracted from this source.",
    )
    extracted_linkedin: str | None = Field(
        default=None,
        description="LinkedIn URL extracted from this source.",
    )
    source_url: str | None = Field(
        default=None,
        max_length=2048,
        description="URL of the page/data this was extracted from.",
    )
    confidence_contribution: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Confidence score contribution from this source alone.",
    )
    extracted_at: datetime = Field(
        default_factory=_utcnow,
        description="When this data was extracted.",
    )
    request_id: str | None = Field(
        default=None,
        description="API request ID or scrape session ID for tracing.",
    )

    @field_validator("extracted_email")
    @classmethod
    def _validate_extracted_email(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_email(v)

    @field_validator("extracted_phone")
    @classmethod
    def _validate_extracted_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            return validate_gcc_phone(v)
        except ValueError:
            return v  # Store as-is; validation happens at merge time


# -------------------------------------------------------------------
# ConfidenceScore
# -------------------------------------------------------------------

class ConfidenceScore(BaseModel):
    """Multi-factor confidence score for a merged recruiter contact."""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Composite confidence score broken down by contributing factors.",
        },
    )

    value: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence score (0.0 = uncertain, 1.0 = verified).",
    )
    source_count: int = Field(
        default=0,
        ge=0,
        description="Number of independent sources confirming this contact.",
    )
    email_verified: bool = Field(
        default=False,
        description="Whether at least one email is DNS/API verified.",
    )
    phone_verified: bool = Field(
        default=False,
        description="Whether at least one phone is validated.",
    )
    data_freshness_days: int | None = Field(
        default=None,
        ge=0,
        description="Days since the most recent source data was extracted.",
    )
    linkedin_found: bool = Field(
        default=False,
        description="Whether a LinkedIn profile was found.",
    )
    whatsapp_found: bool = Field(
        default=False,
        description="Whether a WhatsApp account was detected.",
    )
    name_match_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How well the name matches across sources (1.0 = exact).",
    )
    company_match_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How well the company matches across sources.",
    )
    calculation_details: dict[str, float] = Field(
        default_factory=dict,
        description="Breakdown of how the score was calculated (factor → weight × value).",
    )

    @model_validator(mode="after")
    def _compute_score(self) -> "ConfidenceScore":
        """Compute composite score from factors if not explicitly set."""
        if self.value > 0:
            return self  # Already set explicitly

        score = 0.0
        details: dict[str, float] = {}

        # Source corroboration (0-30 points → 0.0-0.30)
        source_factor = min(self.source_count / 5.0, 1.0) * 0.30
        score += source_factor
        details["source_corroboration"] = round(source_factor, 3)

        # Email verification (0-20 points)
        email_factor = 0.20 if self.email_verified else 0.0
        score += email_factor
        details["email_verification"] = round(email_factor, 3)

        # Phone verification (0-15 points)
        phone_factor = 0.15 if self.phone_verified else 0.0
        score += phone_factor
        details["phone_verification"] = round(phone_factor, 3)

        # LinkedIn (0-15 points)
        linkedin_factor = 0.15 if self.linkedin_found else 0.0
        score += linkedin_factor
        details["linkedin_found"] = round(linkedin_factor, 3)

        # WhatsApp (0-10 points — high value in GCC)
        whatsapp_factor = 0.10 if self.whatsapp_found else 0.0
        score += whatsapp_factor
        details["whatsapp_found"] = round(whatsapp_factor, 3)

        # Data freshness (0-10 points, decays over 90 days)
        if self.data_freshness_days is not None:
            freshness_factor = max(0.0, 1.0 - (self.data_freshness_days / 90.0)) * 0.10
        else:
            freshness_factor = 0.0
        score += freshness_factor
        details["data_freshness"] = round(freshness_factor, 3)

        # Name match (0-5 bonus)
        name_bonus = self.name_match_score * 0.05
        score += name_bonus
        details["name_match"] = round(name_bonus, 3)

        # Company match (0-5 bonus)
        company_bonus = self.company_match_score * 0.05
        score += company_bonus
        details["company_match"] = round(company_bonus, 3)

        self.value = round(min(score, 1.0), 4)
        self.calculation_details = details
        return self


# -------------------------------------------------------------------
# RecruiterContact (THE CORE RECORD)
# -------------------------------------------------------------------

class RecruiterContact(BaseModel):
    """Merged, deduplicated recruiter contact — the core domain record."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "description": "A fully merged recruiter contact from all available sources.",
        },
    )

    id: str = Field(
        default_factory=_new_uuid,
        description="Unique contact identifier (UUID v4).",
    )
    name: str = Field(
        min_length=1,
        max_length=300,
        description="Display name of the recruiter.",
    )
    arabic_name: ArabicName | None = Field(
        default=None,
        description="Parsed Arabic name with variants and permutations.",
    )
    emails: list[EmailRecord] = Field(
        default_factory=list,
        description="All known email addresses.",
    )
    phones: list[PhoneRecord] = Field(
        default_factory=list,
        description="All known phone numbers.",
    )
    company: str | None = Field(
        default=None,
        max_length=300,
        description="Current company / agency.",
    )
    company_profile: CompanyProfile | None = Field(
        default=None,
        description="Resolved company profile (if matched).",
    )
    title: str | None = Field(
        default=None,
        max_length=200,
        description="Job title (e.g. 'Senior Recruitment Consultant').",
    )
    contact_type: ContactType = Field(
        default=ContactType.RECRUITER,
        description="Role category.",
    )
    linkedin_url: str | None = Field(
        default=None,
        description="LinkedIn profile URL.",
    )
    whatsapp_number: str | None = Field(
        default=None,
        description="WhatsApp number in E.164 (if different from primary phone).",
    )
    confidence: ConfidenceScore = Field(
        default_factory=ConfidenceScore,
        description="Composite confidence score.",
    )
    sources: list[SourceResult] = Field(
        default_factory=list,
        description="All source extractions that contributed to this record.",
    )
    region: Region = Field(
        default=Region.UAE,
        description="Primary geographic region.",
    )
    country: str = Field(
        default="AE",
        min_length=2,
        max_length=2,
        description="ISO 3166-1 alpha-2 country code.",
    )
    notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Free-text notes about this contact.",
    )
    tags: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="User-defined tags (e.g. ['tech', 'uae-freezone', 'walkin']).",
    )
    is_active: bool = Field(
        default=True,
        description="Whether the contact is still active/current.",
    )
    created_at: datetime = Field(
        default_factory=_utcnow,
        description="When this record was first created.",
    )
    updated_at: datetime = Field(
        default_factory=_utcnow,
        description="When this record was last modified.",
    )

    @field_validator("linkedin_url")
    @classmethod
    def _validate_linkedin(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_linkedin_url(v)

    @field_validator("whatsapp_number")
    @classmethod
    def _validate_whatsapp(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_gcc_phone(v)

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, v: list[str]) -> list[str]:
        cleaned = [t.strip().lower() for t in v if t.strip()]
        if len(cleaned) != len(v):
            raise ValueError("Tags cannot contain blank entries")
        return cleaned

    @field_serializer("created_at", "updated_at")
    def _serialize_datetimes(self, v: datetime) -> str:
        return v.isoformat()


# -------------------------------------------------------------------
# SearchSession
# -------------------------------------------------------------------

class SearchSession(BaseModel):
    """A single CLI invocation / search session."""

    model_config = ConfigDict(str_strip_whitespace=True)

    session_id: str = Field(
        default_factory=_new_uuid,
        description="Unique session identifier.",
    )
    queries: list[ContactQuery] = Field(
        default_factory=list,
        description="All queries executed in this session.",
    )
    results: list[str] = Field(
        default_factory=list,
        description="List of RecruiterContact IDs returned.",
    )
    results_count: int = Field(
        default=0,
        ge=0,
        description="Total number of contacts found.",
    )
    api_usage: dict[str, int] = Field(
        default_factory=dict,
        description="Credits used per source: {source_name: credits_consumed}.",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Error messages encountered during the session.",
    )
    started_at: datetime = Field(
        default_factory=_utcnow,
        description="Session start time.",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Session end time (null if still running).",
    )
    status: SessionStatus = Field(
        default=SessionStatus.RUNNING,
        description="Current session lifecycle state.",
    )
    total_duration_seconds: float | None = Field(
        default=None,
        ge=0.0,
        description="Total wall-clock time in seconds.",
    )


# -------------------------------------------------------------------
# APIUsageTracker
# -------------------------------------------------------------------

class APIUsageTracker(BaseModel):
    """Per-source API credit tracking."""

    model_config = ConfigDict(str_strip_whitespace=True)

    source_name: str = Field(
        min_length=1,
        max_length=100,
        description="API source name.",
    )
    source_type: SourceType = Field(
        default=SourceType.API,
        description="Category of the source.",
    )
    credits_used: int = Field(
        default=0,
        ge=0,
        description="Credits consumed this billing period.",
    )
    credits_limit: int | None = Field(
        default=None,
        ge=0,
        description="Credit limit per billing period (None = unlimited).",
    )
    credits_remaining: int | None = Field(
        default=None,
        ge=0,
        description="Credits remaining this billing period.",
    )
    reset_date: date | None = Field(
        default=None,
        description="When credits reset.",
    )
    last_used: datetime | None = Field(
        default=None,
        description="When this API was last called.",
    )
    api_key_env_var: str | None = Field(
        default=None,
        description="Environment variable name holding the API key.",
    )

    @model_validator(mode="after")
    def _validate_credits(self) -> "APIUsageTracker":
        if (
            self.credits_limit is not None
            and self.credits_remaining is not None
            and self.credits_remaining > self.credits_limit
        ):
            raise ValueError("credits_remaining cannot exceed credits_limit")
        return self


# -------------------------------------------------------------------
# ExportRecord
# -------------------------------------------------------------------

class ExportRecord(BaseModel):
    """Record of a data export operation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    format: ExportFormat = Field(
        description="Export file format.",
    )
    filename: str = Field(
        min_length=1,
        max_length=500,
        description="Output filename.",
    )
    row_count: int = Field(
        default=0,
        ge=0,
        description="Number of rows exported.",
    )
    filters_applied: dict[str, Any] = Field(
        default_factory=dict,
        description="Query filters that were applied.",
    )
    deduped_count: int = Field(
        default=0,
        ge=0,
        description="Number of duplicates removed before export.",
    )
    confidence_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum confidence filter applied.",
    )
    export_date: datetime = Field(
        default_factory=_utcnow,
        description="When the export was generated.",
    )
    file_size_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Size of the exported file in bytes.",
    )
    session_id: str | None = Field(
        default=None,
        description="Associated search session ID.",
    )
