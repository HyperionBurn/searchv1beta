"""
UAEGoogleDorkEngine — UAE/GCC-specific Google dork query builder.

Provides:
- Email dorking for UAE companies
- Phone number dorking (+971 patterns)
- WhatsApp number dorking
- Walk-in interview dorking
- Recruiter-specific dorking
- 30+ complete query templates
- UAE-specific operators: site:ae, +971, Dubai/AbuDhabi/Sharjah

Production-grade: no placeholders, all templates complete.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# UAE Location Keywords
# ---------------------------------------------------------------------------

UAE_LOCATIONS: list[str] = [
    "dubai",
    "abu dhabi",
    "sharjah",
    "ajman",
    "ras al khaimah",
    "rak",
    "umm al quwain",
    "fujairah",
    "al ain",
    "jebel ali",
    "jlt",
    "jumeirah lakes towers",
    "difc",
    "dubai marina",
    "business bay",
    "dubai internet city",
    "dubai media city",
    "dubai silicon oasis",
    "karama",
    "deira",
    "bur dubai",
    "barsha",
    "sheikh zayed road",
    "uae",
    "gcc",
    "gulf",
    "middle east",
]

# Abu Dhabi area keywords (for location-specific dorking)
ABU_DHABI_AREAS: list[str] = [
    "abu dhabi island",
    "al reem island",
    "al maryah island",
    "khalifa city",
    "mussafah",
    "mbz city",
    "al ain",
    "madinat zayed",
    "ruwais",
    "ghayathi",
]

# Dubai area keywords
DUBAI_AREAS: list[str] = [
    "downtown dubai",
    "dubai marina",
    "jbr",
    "business bay",
    "difc",
    "jlt",
    "jumeirah lakes towers",
    "dubai internet city",
    "dubai media city",
    "dubai silicon oasis",
    "dubai festival city",
    "deira",
    "bur dubai",
    "karama",
    "al qusais",
    "al nahda",
    "barsha",
    "al barsha",
    "tecom",
    "sheikh zayed road",
    "emirates road",
    "al quoz",
    "jebel ali",
    "dubai investment park",
    "dip",
]

# Emiratisation keywords
EMIRATISATION_KEYWORDS: list[str] = [
    "emiratisation",
    "emiratization",
    "uae national",
    "uae nationals",
    "emirati",
    "tawteen",
    "nafis",
    "nationalization",
    "uae citizen",
    "khaleeji",
]

# Recruitment agency keywords
RECRUITMENT_KEYWORDS: list[str] = [
    "recruitment agency",
    "recruitment consultancy",
    "hr consultancy",
    "staffing agency",
    "manpower",
    "talent acquisition",
    "executive search",
    "headhunter",
    "recruiter",
    "hr manager",
    "hiring",
    "recruitment",
    "sourcing",
    "placement",
    "outplacement",
    "temp staffing",
]

# Recruiter job title keywords
RECRUITER_TITLES: list[str] = [
    "recruiter",
    "talent acquisition",
    "hr manager",
    "hr director",
    "recruitment consultant",
    "recruitment manager",
    "resourcer",
    "sourcer",
    "people partner",
    "hiring manager",
    "emiratisation officer",
    "emiratisation manager",
    "nationalization manager",
    "gcc recruiter",
    "gulf recruiter",
]


# ---------------------------------------------------------------------------
# Query Template Library (30+ templates)
# ---------------------------------------------------------------------------

QUERY_TEMPLATES: dict[str, str] = {
    # ---- Email finding ----
    "email_by_company": (
        '"{company}" "@{domain}" '
        '(site:linkedin.com OR site:linkedin.com/in/ OR site:bayt.com)'
    ),
    "email_by_company_uae": (
        '"{company}" "@{domain}" '
        '"uae" OR "dubai" OR "abu dhabi"'
    ),
    "email_recruiter_title": (
        '"{company}" ("recruiter" OR "talent acquisition" OR "hr manager") '
        '"@"'
    ),
    "email_with_phone": (
        '"{company}" "@" "+971"'
    ),
    "email_gmail_recruiter": (
        '"{company}" ("recruiter" OR "hr") '
        '("@gmail.com" OR "@hotmail.com" OR "@outlook.com")'
    ),

    # ---- Phone finding ----
    "phone_by_company": (
        '"{company}" "+971" '
        '("recruiter" OR "hr" OR "recruitment")'
    ),
    "phone_mobile_uae": (
        '"{company}" "+971 5" OR "+971-5" OR "050" OR "052" OR "054" OR "055"'
    ),
    "phone_whatsapp_format": (
        '"{company}" "whatsapp" "+971"'
    ),
    "phone_recruiter_specific": (
        '"{name}" "{company}" "+971"'
    ),

    # ---- WhatsApp specific ----
    "whatsapp_recruiter": (
        '"{company}" "whatsapp" ("+971" OR "050" OR "052") '
        '("recruiter" OR "hr" OR "hiring")'
    ),
    "whatsapp_number_direct": (
        '"{company}" "wa.me" OR "whatsapp" "+9715"'
    ),
    "whatsapp_contact_card": (
        '"{company}" "contact" "whatsapp" '
        '("dubai" OR "uae")'
    ),

    # ---- Walk-in interviews ----
    "walkin_general": (
        '"walk in interview" "{location}" '
        '("recruitment" OR "hiring" OR "vacancy")'
    ),
    "walkin_company": (
        '"walk in interview" "{company}" '
        '"{location}"'
    ),
    "walkin_with_phone": (
        '"walk in interview" "{location}" "+971"'
    ),
    "walkin_date_range": (
        '"walk in interview" "{location}" '
        '("today" OR "tomorrow" OR "this week") '
        '("+971" OR "@" OR "contact")'
    ),
    "walkin_specific_role": (
        '"walk in interview" "{location}" "{role}" '
        '("+971" OR "@" OR "whatsapp")'
    ),

    # ---- Recruiter-specific ----
    "recruiter_by_name_company": (
        '"{name}" "{company}" '
        '("recruiter" OR "talent acquisition" OR "hr") '
        '(site:linkedin.com OR site:bayt.com)'
    ),
    "recruiter_by_name_uae": (
        '"{name}" ("uae" OR "dubai" OR "gcc") '
        '("recruiter" OR "recruitment")'
    ),
    "recruiter_linkedin_uae": (
        'site:linkedin.com/in/ "{company}" '
        '"recruiter" OR "talent acquisition" '
        '"uae" OR "dubai" OR "abu dhabi"'
    ),
    "recruiter_email_linkedin": (
        'site:linkedin.com/in/ "{name}" '
        '"@" OR "email" OR "contact"'
    ),
    "recruiter_bayt": (
        'site:bayt.com "{company}" '
        '"recruiter" OR "hr manager"'
    ),

    # ---- Company intelligence ----
    "company_careers_page": (
        '"{company}" "careers" '
        '(site:{domain} OR "hiring" OR "jobs") '
        '"uae"'
    ),
    "company_ats_page": (
        '"{company}" '
        '("taleo" OR "successfactors" OR "pageup" OR "workday" OR "icims") '
        '"careers"'
    ),
    "company_hiring_signal": (
        '"{company}" "hiring" "uae" '
        '("recruiter" OR "hr" OR "talent") '
        '(2024 OR 2025 OR 2026)'
    ),

    # ---- Expatriates / Dubizzle ----
    "expatriates_recruiter": (
        'site:expatriates.com "{location}" '
        '("recruitment" OR "hiring" OR "staff required") '
        '"+971"'
    ),
    "dubizzle_recruiter": (
        'site:dubizzle.com "{location}" '
        '("recruitment agency" OR "hiring") '
        '("050" OR "052" OR "054" OR "055")'
    ),

    # ---- Government / free zone ----
    "gov_recruiter": (
        '"{entity}" site:gov.ae '
        '("hr" OR "recruitment" OR "careers") '
        '"@"'
    ),
    "free_zone_agencies": (
        'site:dmcc.ae "recruitment" OR "hr consultancy" '
        '"{location}"'
    ),

    # ---- Emiratisation ----
    "emiratisation_recruiter": (
        '"emiratisation" OR "emiratization" '
        '"{company}" '
        '("officer" OR "manager" OR "specialist") '
        '(site:linkedin.com OR "@")'
    ),

    # ---- Cross-reference ----
    "name_phone_crossref": (
        '"{name}" "+971" '
        '("recruiter" OR "hr") '
        '"{company}"'
    ),
    "email_phone_combo": (
        '"{company}" '
        '("@" OR "+971") '
        '"{name}" '
        '("recruiter" OR "hr")'
    ),

    # ---- GCC-wide ----
    "gcc_recruiter_by_company": (
        '"{company}" ("recruiter" OR "hr") '
        '("uae" OR "saudi" OR "qatar" OR "bahrain" OR "oman" OR "kuwait") '
        '"+"'
    ),
}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class UAEGoogleDorkEngine:
    """UAE/GCC-specific Google dork query builder."""

    def build_email_query(self, company: str) -> str:
        """
        Build UAE-specific email dork for a company.

        Tries to find recruiter email addresses by searching for:
        - Company name + @ symbol
        - Company domain (if known)
        - Recruiter/HR title keywords
        - UAE location keywords

        Args:
            company: Company name (e.g., "Emirates Group").

        Returns:
            Google dork query string.

        Example:
            >>> eng = UAEGoogleDorkEngine()
            >>> query = eng.build_email_query("Emirates Group")
            >>> "@emirates.com" in query
            True
        """
        from uae_domain_engine import UAEDomainEngine

        domain_eng = UAEDomainEngine()
        domains = domain_eng.resolve_domains(company)
        primary_domain = domains[0] if domains else "example.com"

        parts: list[str] = []

        # Primary: company + domain + recruiter keywords
        parts.append(
            f'"{company}" "@{primary_domain}" '
            f'("recruiter" OR "talent acquisition" OR "hr manager")'
        )

        # LinkedIn-specific
        parts.append(
            f'site:linkedin.com/in/ "{company}" '
            f'"recruiter" "@"'
        )

        # Bayt-specific
        parts.append(
            f'site:bayt.com "{company}" '
            f'"recruiter" OR "hr"'
        )

        # Generic with phone
        parts.append(
            f'"{company}" "@" "+971" '
            f'"recruiter"'
        )

        # Personal email addresses
        parts.append(
            f'"{company}" "recruiter" '
            f'("@gmail.com" OR "@hotmail.com" OR "@outlook.com")'
        )

        return " | ".join(parts)

    def build_phone_query(self, company: str) -> str:
        """
        Build UAE phone number dork for a company.

        Searches for +971 mobile patterns associated with the company.

        Args:
            company: Company name.

        Returns:
            Google dork query string.

        Example:
            >>> eng = UAEGoogleDorkEngine()
            >>> query = eng.build_phone_query("ABC Recruitment")
            >>> "+971" in query
            True
        """
        parts: list[str] = []

        # Company + phone + recruiter keywords
        parts.append(
            f'"{company}" "+971" '
            f'("recruiter" OR "hr" OR "recruitment")'
        )

        # Specific mobile prefixes
        parts.append(
            f'"{company}" '
            f'("+971 50" OR "+971 52" OR "+971 54" OR "+971 55" '
            f'OR "+971 56" OR "+971 58" OR "050" OR "052" OR "054" '
            f'OR "055" OR "056" OR "058")'
        )

        # Expatriates.com (known to have phone numbers)
        parts.append(
            f'site:expatriates.com "{company}" "+971"'
        )

        # Dubizzle (known to have phone numbers)
        parts.append(
            f'site:dubizzle.com "{company}" '
            f'("050" OR "052" OR "054" OR "055")'
        )

        return " | ".join(parts)

    def build_whatsapp_query(self, company: str) -> str:
        """
        Build WhatsApp number dork for a company.

        Searches for WhatsApp-enabled numbers associated with recruiters
        at the specified company.

        Args:
            company: Company name.

        Returns:
            Google dork query string.

        Example:
            >>> eng = UAEGoogleDorkEngine()
            >>> query = eng.build_whatsapp_query("ABC Recruitment")
            >>> "whatsapp" in query.lower()
            True
        """
        parts: list[str] = []

        # Direct WhatsApp mentions
        parts.append(
            f'"{company}" "whatsapp" "+971" '
            f'("recruiter" OR "hr" OR "hiring" OR "contact")'
        )

        # wa.me links
        parts.append(
            f'"{company}" "wa.me" "+971"'
        )

        # Phone + WhatsApp keyword
        parts.append(
            f'"{company}" '
            f'("whatsapp" OR "wa.me" OR "call" OR "contact") '
            f'("+971 5" OR "050" OR "052" OR "054" OR "055" OR "056" OR "058")'
        )

        # Facebook groups (rich source of WhatsApp numbers)
        parts.append(
            f'site:facebook.com "{company}" '
            f'"whatsapp" "+971"'
        )

        return " | ".join(parts)

    def build_walkin_query(self, location: str) -> str:
        """
        Build walk-in interview dork for a UAE location.

        Walk-in interview posts in UAE almost always include phone numbers
        and email addresses — they are one of the richest sources of
        recruiter contact info.

        Args:
            location: UAE location (e.g., "Dubai", "Sharjah").

        Returns:
            Google dork query string.

        Example:
            >>> eng = UAEGoogleDorkEngine()
            >>> query = eng.build_walkin_query("Dubai")
            >>> "walk in interview" in query.lower()
            True
        """
        parts: list[str] = []

        # General walk-in with phone
        parts.append(
            f'"walk in interview" "{location}" '
            f'("+971" OR "@" OR "whatsapp" OR "contact")'
        )

        # Walk-in on classifieds sites
        parts.append(
            f'site:expatriates.com "walk in interview" "{location}" '
            f'"+971"'
        )

        parts.append(
            f'site:dubizzle.com "walk in interview" "{location}"'
        )

        # Date-specific (current/recent)
        parts.append(
            f'"walk in interview" "{location}" '
            f'("today" OR "tomorrow" OR "this week" OR "urgent") '
            f'("+971" OR "@" OR "whatsapp")'
        )

        # Specific roles at walk-ins
        parts.append(
            f'"walk in interview" "{location}" '
            f'("recruitment" OR "hr" OR "admin" OR "accountant" OR "engineer") '
            f'"+971"'
        )

        return " | ".join(parts)

    def build_recruiter_query(self, name: str, company: str) -> str:
        """
        Build recruiter-specific dork using name and company.

        Cross-references recruiter name + company across LinkedIn,
        Bayt, and general web results.

        Args:
            name: Recruiter's name.
            company: Company name.

        Returns:
            Google dork query string.

        Example:
            >>> eng = UAEGoogleDorkEngine()
            >>> query = eng.build_recruiter_query("Ahmed Al Rashid", "ADNOC")
            >>> "Ahmed Al Rashid" in query
            True
            >>> "ADNOC" in query
            True
        """
        parts: list[str] = []

        # LinkedIn profile
        parts.append(
            f'site:linkedin.com/in/ "{name}" "{company}"'
        )

        # Name + company + contact info
        parts.append(
            f'"{name}" "{company}" '
            f'("@" OR "+971" OR "email" OR "phone" OR "contact")'
        )

        # Name + recruiter keywords
        parts.append(
            f'"{name}" "{company}" '
            f'("recruiter" OR "hr" OR "talent acquisition")'
        )

        # Name + phone specifically
        parts.append(
            f'"{name}" "+971" "{company}"'
        )

        # Name + email specifically
        parts.append(
            f'"{name}" "@" "{company}" '
            f'("uae" OR "dubai" OR "gcc")'
        )

        # Bayt.com profile
        parts.append(
            f'site:bayt.com "{name}" "{company}"'
        )

        return " | ".join(parts)

    def build_custom_query(self, template_name: str, **kwargs) -> str:
        """
        Build a query from a named template with variable substitution.

        Args:
            template_name: Key from QUERY_TEMPLATES.
            **kwargs: Template variables (company, name, location, domain, etc.)

        Returns:
            Formatted query string.

        Example:
            >>> eng = UAEGoogleDorkEngine()
            >>> query = eng.build_custom_query(
            ...     "email_by_company",
            ...     company="ADNOC",
            ...     domain="adnoc.ae",
            ... )
        """
        if template_name not in QUERY_TEMPLATES:
            raise ValueError(
                f"Unknown template: {template_name}. "
                f"Available: {list(QUERY_TEMPLATES.keys())}"
            )
        return QUERY_TEMPLATES[template_name].format(**kwargs)

    def list_templates(self) -> dict[str, str]:
        """Return all available query templates with their descriptions."""
        return dict(QUERY_TEMPLATES)
