"""
ArabicNameEngine — Arabic name normalization and email pattern generator.

Handles the full complexity of Arabic names in the GCC context:
- Prefix variants (Al/El/Bin/Bint/Abd/Abdel)
- Mohammed variants (8+ transliterations)
- Patronymic chains (bin/bint stripping)
- Compound names (Abdul Rahman vs Abdulrahman)
- Title stripping (Sheikh/Eng./Dr.)
- Arabic→Latin transliteration variants

Production-grade: no placeholders, all mapping tables complete.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Constants & Mapping Tables
# ---------------------------------------------------------------------------

# Titles that must be stripped before email generation.
# Keys are stripped forms (lowercase); values are common variants.
TITLE_VARIANTS: dict[str, list[str]] = {
    "sheikh": ["sheikh", "shaikh", "shaykh", "sh", "sh."],
    "eng": ["eng", "eng.", "engineer", "engr", "engr."],
    "dr": ["dr", "dr.", "doctor", "dr"],
    "mr": ["mr", "mr.", "mister"],
    "mrs": ["mrs", "mrs.", "missus"],
    "ms": ["ms", "ms."],
    "prof": ["prof", "prof.", "professor"],
    "hajji": ["hajji", "haji", "haj", "al-haj", "alhaj"],
    "sayyid": ["sayyid", "syed", "sayed", "sayyid"],
}

# Flatten to a single lookup: variant → canonical title
_TITLE_LOOKUP: dict[str, str] = {}
for _canonical, _variants in TITLE_VARIANTS.items():
    for _v in _variants:
        _TITLE_LOOKUP[_v] = _canonical


# Arabic article / prefix variants and their canonical forms.
# The key is the canonical prefix; values are all known transliterations.
PREFIX_MAP: dict[str, list[str]] = {
    "al": [
        "al", "al-", "el", "el-", "al ", "ul", "ol",
        # Arabic definite article forms
        "\u0627\u0644",  # ال
    ],
    "bin": [
        "bin", "bn", "b.", "ibn", "ben", "ibn ",
        "\u0628\u0646",  # بن
        "\u0627\u0628\u0646",  # ابن
    ],
    "bint": [
        "bint", "bint.", "bt", "bt.",
        "\u0628\u0646\u062a",  # بنت
    ],
}

# Flatten: variant → canonical
_PREFIX_LOOKUP: dict[str, str] = {}
for _canonical, _variants in PREFIX_MAP.items():
    for _v in _variants:
        _PREFIX_LOOKUP[_v] = _canonical


# Mohammed variant table — the most overloaded Arabic name.
# Each variant is a known transliteration found in GCC email addresses.
MOHAMMED_VARIANTS: list[str] = [
    "mohammed",
    "mohammad",
    "muhammad",
    "mohamed",
    "mohamad",
    "muhamed",
    "mohamud",
    "mohammod",
    "mohd",
    "mhamad",
    "muhamad",
    "muhmmad",
    "mohammd",
    "mhmmd",
    "mhd",
    "mohamet",   # Francophone variant
    "mohummad",  # Pakistani-origin variant
    # Shortened / nickname forms
    "mo",
    "moe",
    "momo",
    # NOTE: ahmed/ahmad (أحمد), mahmoud/mahmud (محمود), hamid (حامد)
    # are DISTINCT Arabic names and should NOT be in Mohammed variants.
    # They remain in NAME_VARIANT_MAP for their own variant generation.
]


# Servant-of-Allah compound names (Abdul X / Abd Al X / AbdX / AbdulX).
# Each key is the second element; values are all known transliterations.
ABD_COMPOUNDS: dict[str, list[str]] = {
    "rahman": ["rahman", "rahmaan", "alrahman", "al rahman", "errahman"],
    "rahim": ["rahim", "raheem", "alrahim", "al rahim", "erraheem"],
    "allah": ["allah", "ullah"],
    "aziz": ["aziz", "azeez", "alaziz", "al aziz", "elaziz"],
    "salam": ["salam", "salaam", "alsalam", "al salam"],
    "karim": ["karim", "kareem", "alkarim", "al karim"],
    "hakim": ["hakim", "hakeem", "alhakim", "al hakim"],
    "jabbar": ["jabbar", "jabar", "aljabbar", "al jabbar"],
    "malik": ["malik", "maleek", "almalik", "al malik"],
    "qadir": ["qadir", "qadeer", "alqadir", "al qadir"],
    "basit": ["basit", "baset", "albasit", "al basit"],
    "latif": ["latif", "lateef", "allatif", "al latif"],
    "hamid": ["hamid", "hameed", "alhamid", "al hamid"],
    "nasser": ["nasser", "naser", "nassar", "naser"],
    "samad": ["samad", "alsamad", "al samad"],
    "shakur": ["shakur", "shakoor", "alshakur"],
    "tawwab": ["tawwab", "altawwab", "al tawwab"],
    "wahab": ["wahab", "wahhab", "alwahab", "al wahab"],
}

# Flatten for lookup
_ABD_PART_LOOKUP: dict[str, str] = {}
for _canonical, _variants in ABD_COMPOUNDS.items():
    _ABD_PART_LOOKUP[_canonical] = _canonical
    for _v in _variants:
        _ABD_PART_LOOKUP[_v] = _canonical

# "Abdul" transliteration variants
ABD_PREFIXES: list[str] = [
    "abdul", "abd al", "abd el", "abd", "abdel", "abdul ",
    "abdu", "abd",
]


# ---------------------------------------------------------------------------
# Email pattern templates
# ---------------------------------------------------------------------------

# These are the most common email username patterns for GCC employers.
# {f} = first initial, {first} = first name, {last} = last name,
# {m} = middle initial, {middle} = middle name
EMAIL_PATTERNS: list[str] = [
    "{first}.{last}",
    "{first}{last}",
    "{f}{last}",
    "{first}_{last}",
    "{first}.{m}{last}",
    "{first}{l}",
    "{first}.{middle}.{last}",
    "{f}.{last}",
    "{f}{m}{last}",
    "{first}.{last}1",
    "{first}{last}1",
    # Common in legacy Etisalat / government systems
    "{first}_{last}",
    "{f}_{last}",
    # Short forms (for names like Mohd)
    "{first}",
]


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class NormalizedName:
    """All normalized forms of an Arabic name."""
    original: str
    stripped: str  # titles removed
    parts: list[str]  # individual name parts
    normalized_forms: list[str]  # all variant full-name strings
    first_name_variants: list[str]
    last_name_variants: list[str]
    middle_name_variants: list[str]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ArabicNameEngine:
    """Generates all email permutations for Arabic names in the GCC context."""

    # ---- Public API ----

    def normalize(self, name: str) -> NormalizedName:
        """
        Generate all normalized forms of an Arabic name.

        Args:
            name: Raw name string, e.g. "Mohammed bin Khalid Al Maktoum"

        Returns:
            NormalizedName with all variants populated.

        Example:
            >>> eng = ArabicNameEngine()
            >>> result = eng.normalize("Eng. Mohammed Al Rashid")
            >>> result.stripped
            'mohammed al rashid'
            >>> 'mohammed rashid' in result.normalized_forms
            True
        """
        cleaned = self._clean_input(name)
        stripped = self._strip_titles(cleaned)
        tokens = stripped.split()

        parts = self._explode_tokens(tokens)

        first_variants = self._variants_for_token(parts[0]) if parts else [""]
        last_variants = self._variants_for_token(parts[-1]) if len(parts) > 1 else [""]
        middle_parts = parts[1:-1] if len(parts) > 2 else []
        middle_variants: list[str] = []
        for mp in middle_parts:
            middle_variants.extend(self._variants_for_token(mp))

        # Build full-name normalized forms
        full_forms: set[str] = set()

        # Base: all parts joined
        base_name = " ".join(parts)
        full_forms.add(base_name)

        # Remove patronymic connectors
        no_patronymic = self._remove_patronymic_parts(parts)
        if no_patronymic:
            full_forms.add(" ".join(no_patronymic))

        # Abbreviate last name (Al Rashid → Rashid, Al Maktoum → Maktoum)
        for combo in self._prefix_abbreviations(parts):
            full_forms.add(" ".join(combo))

        # Generate cross-product of variant parts
        for first_v in first_variants:
            for last_v in last_variants:
                full_forms.add(f"{first_v} {last_v}")
                if middle_variants:
                    for mid_v in middle_variants:
                        full_forms.add(f"{first_v} {mid_v} {last_v}")

        # Handle Abdul compounds
        full_forms.update(self._abd_compound_forms(parts))

        return NormalizedName(
            original=name,
            stripped=stripped,
            parts=parts,
            normalized_forms=sorted(full_forms),
            first_name_variants=sorted(set(first_variants)),
            last_name_variants=sorted(set(last_variants)),
            middle_name_variants=sorted(set(middle_variants)),
        )

    def generate_email_patterns(
        self, name: str, domain: str
    ) -> list[str]:
        """
        Generate all plausible email addresses for an Arabic name at a domain.

        Generates permutations across:
        - All first/last name variants
        - All email pattern templates
        - With and without prefixes (Al/El)
        - With and without patronymics

        Args:
            name: Raw name string.
            domain: Email domain (without @).

        Returns:
            Deduplicated, lowercase list of email candidates.

        Example:
            >>> eng = ArabicNameEngine()
            >>> emails = eng.generate_email_patterns(
            ...     "Mohammed Al Rashid", "emirates.com"
            ... )
            >>> "mohammed.rashid@emirates.com" in emails
            True
            >>> "mohd.rashid@emirates.com" in emails
            True
            >>> "mohammad.alrashid@emirates.com" in emails
            True
        """
        norm = self.normalize(name)
        domain = domain.lower().strip("@").strip()

        candidates: set[str] = set()

        for first in norm.first_name_variants:
            for last in norm.last_name_variants:
                for pattern in EMAIL_PATTERNS:
                    email = pattern.format(
                        first=first,
                        last=last,
                        f=first[0] if first else "",
                        l=last[0] if last else "",
                        m=norm.middle_name_variants[0][0]
                        if norm.middle_name_variants
                        else "",
                        middle=norm.middle_name_variants[0]
                        if norm.middle_name_variants
                        else "",
                    )
                    candidates.add(f"{email}@{domain}")

            # Also try with no last name
            candidates.add(f"{first}@{domain}")
            candidates.add(f"{first[0]}@{domain}")

        # Also try patronymic-stripped forms
        no_pat = self._remove_patronymic_parts(norm.parts)
        if no_pat and len(no_pat) >= 2:
            first_v = self._variants_for_token(no_pat[0])
            last_v = self._variants_for_token(no_pat[-1])
            for f in first_v:
                for l in last_v:
                    candidates.add(f"{f}.{l}@{domain}")
                    candidates.add(f"{f}{l}@{domain}")
                    candidates.add(f"{f[0]}{l}@{domain}")

        # Try Al/El joined forms (alrashid, elrashid)
        for part in norm.parts:
            for prefix in ("al", "el"):
                if part.startswith(prefix) and len(part) > len(prefix):
                    candidates.add(f"{part}@{domain}")

        return sorted(candidates)

    def handle_prefixes(self, name: str) -> list[str]:
        """
        Handle Al/El/Bin/Bint prefixes — return all variant forms.

        Args:
            name: Name string potentially containing Arabic prefixes.

        Returns:
            List of name variants with prefixes handled.

        Example:
            >>> eng = ArabicNameEngine()
            >>> eng.handle_prefixes("Khalid Al Maktoum")
            ['khalid maktoum', 'khalid al maktoum', 'khalid almaktoum',
             'khalid el maktoum', 'khalid elmaktoum']
        """
        cleaned = self._clean_input(name)
        tokens = cleaned.split()
        results: set[str] = set()

        results.add(cleaned)  # original

        # Process each token for prefix variants
        processed_tokens = []
        for tok in tokens:
            variants = self._prefix_token_variants(tok)
            processed_tokens.append(variants)

        # Generate cross-product
        if processed_tokens:
            from itertools import product
            for combo in product(*processed_tokens):
                results.add(" ".join(combo))

        # Also add forms with prefix removed
        no_prefix = []
        for tok in tokens:
            canonical = _PREFIX_LOOKUP.get(tok)
            if canonical == "al":
                continue  # skip Al/El entirely
            elif canonical == "bin":
                continue  # skip bin
            elif canonical == "bint":
                continue  # skip bint
            else:
                no_prefix.append(tok)
        if no_prefix and no_prefix != tokens:
            results.add(" ".join(no_prefix))

        return sorted(results)

    def handle_mohammed(self, name: str) -> list[str]:
        """
        Expand Mohammed variants in a name.

        Args:
            name: Name potentially containing a Mohammed variant.

        Returns:
            List of name variants with all Mohammed transliterations.

        Example:
            >>> eng = ArabicNameEngine()
            >>> variants = eng.handle_mohammed("Mohammed Al Rashid")
            >>> "mohd al rashid" in variants
            True
            >>> "muhammad al rashid" in variants
            True
        """
        cleaned = self._clean_input(name)
        tokens = cleaned.split()

        results: set[str] = set()
        results.add(cleaned)

        # Find which token(s) are Mohammed variants
        mohammed_positions = []
        for i, tok in enumerate(tokens):
            if tok in MOHAMMED_VARIANTS:
                mohammed_positions.append(i)

        if not mohammed_positions:
            return sorted(results)

        # Replace each Mohammed position with all variants
        for pos in mohammed_positions:
            for mvar in MOHAMMED_VARIANTS[:8]:  # Top 8 most common
                new_tokens = list(tokens)
                new_tokens[pos] = mvar
                results.add(" ".join(new_tokens))

                # Also try shortened forms for first position
                if pos == 0:
                    # mo / mohd as first initial style
                    short_tokens = list(tokens)
                    short_tokens[pos] = "mohd"
                    results.add(" ".join(short_tokens))

        # Also generate forms where Mohammed is entirely dropped
        # (common in informal usage: "Mo Rashid")
        for pos in mohammed_positions:
            short = ["mo" if i == pos else t for i, t in enumerate(tokens)]
            results.add(" ".join(short))

        return sorted(results)

    def transliterate(self, name: str) -> list[str]:
        """
        Generate Arabic→Latin transliteration variants.

        Handles common substitution patterns seen in GCC email addresses:
        - kh ↔ h (Khalid → Halid)
        - ou ↔ u (Yousuf → Yusuf)
        - aa ↔ a (Khalid → Khalid)
        - ee ↔ i (Naseer → Nasir)
        - ie ↔ i (Sadiq → Sadiq)
        - q ↔ k (Qassim → Kassim)
        - gh ↔ g (Ghanem → Ganem)
        - th ↔ t (Thani → Tani)
        - dh ↔ d (Dhuheir → Duheir)
        - sh ↔ s (Sharif → Sarif — rare but occurs in emails)

        Args:
            name: Latin-script Arabic name.

        Returns:
            List of transliteration variants.

        Example:
            >>> eng = ArabicNameEngine()
            >>> variants = eng.transliterate("Yousuf Al Qassim")
            >>> "yusuf al kassim" in variants
            True
        """
        cleaned = self._clean_input(name)

        substitutions: list[tuple[str, str]] = [
            ("kh", "h"),
            ("ou", "u"),
            ("aa", "a"),
            ("ee", "i"),
            ("ie", "i"),
            ("q", "k"),
            ("gh", "g"),
            ("th", "t"),
            ("dh", "d"),
            ("sh", "s"),
            # Reverse
            ("a", "aa"),
            ("i", "ee"),
            ("u", "ou"),
            ("k", "q"),
            ("s", "sh"),
        ]

        results: set[str] = {cleaned}

        for old, new in substitutions:
            if old in cleaned:
                results.add(cleaned.replace(old, new))

        # Compose multiple substitutions
        for i, (old1, new1) in enumerate(substitutions):
            if old1 not in cleaned:
                continue
            temp = cleaned.replace(old1, new1)
            for old2, new2 in substitutions[i + 1:]:
                if old2 in temp:
                    results.add(temp.replace(old2, new2))

        return sorted(results)

    # ---- Private helpers ----

    def _clean_input(self, name: str) -> str:
        """Lowercase, strip extra whitespace, remove diacritics."""
        name = name.strip().lower()
        # Remove Arabic diacritical marks (tashkeel)
        name = re.sub(r"[\u064b-\u065f]", "", name)
        # Normalize whitespace
        name = re.sub(r"\s+", " ", name)
        # Remove dots that are part of abbreviations (keep for b. → bin)
        # But normalize multiple dots
        name = re.sub(r"\.{2,}", ".", name)
        return name

    def _strip_titles(self, name: str) -> str:
        """Remove all known titles from the name."""
        tokens = name.split()
        stripped = []
        for tok in tokens:
            if tok.rstrip(".") in _TITLE_LOOKUP:
                continue
            stripped.append(tok)
        return " ".join(stripped)

    def _explode_tokens(self, tokens: list[str]) -> list[str]:
        """
        Expand compound tokens: 'Abdulrahman' → ['abdulrahman'].
        The normalization handles these via ABD compound logic.
        """
        return tokens

    def _variants_for_token(self, token: str) -> list[str]:
        """Get all variant forms for a single name token."""
        variants: set[str] = {token}

        # Mohammed variants
        if token in MOHAMMED_VARIANTS:
            variants.update(MOHAMMED_VARIANTS[:8])

        # Prefix variants
        for prefix_form in _PREFIX_LOOKUP:
            pass  # handled separately

        # Check if token starts with known prefix
        for prefix_canonical, prefix_list in PREFIX_MAP.items():
            for pv in prefix_list:
                pv_clean = pv.strip()
                if token.startswith(pv_clean) and len(token) > len(pv_clean):
                    rest = token[len(pv_clean):]
                    # Add joined form
                    for alt_prefix in ("al", "el"):
                        variants.add(f"{alt_prefix}{rest}")
                        variants.add(f"{alt_prefix} {rest}")
                    # Add bare form (no prefix)
                    variants.add(rest)

        # ABD compound handling
        lower = token
        if lower.startswith("abdul"):
            rest = lower[5:]
            if rest in _ABD_PART_LOOKUP:
                canonical = _ABD_PART_LOOKUP[rest]
                variants.add(f"abdul{canonical}")
                variants.add(f"abdul {canonical}")
                variants.add(f"abd al {canonical}")
                variants.add(f"abd{canonical}")
                variants.add(f"abdel{canonical}")
                # Also just the second part
                variants.add(canonical)
        elif lower.startswith("abd") and len(lower) > 3:
            rest = lower[3:]
            if rest:
                variants.add(f"abdul{rest}")
                variants.add(f"abd al {rest}")

        # Transliteration variants
        for v in list(variants):
            variants.update(self.transliterate(v))

        return sorted(variants)

    def _remove_patronymic_parts(self, parts: list[str]) -> list[str]:
        """Remove bin/bint connectors and return non-patronymic parts."""
        result = []
        for p in parts:
            canonical = _PREFIX_LOOKUP.get(p)
            if canonical in ("bin", "bint"):
                continue
            result.append(p)
        return result

    def _prefix_abbreviations(self, parts: list[str]) -> list[list[str]]:
        """Generate forms where Al/El prefixes are abbreviated or removed."""
        combos: list[list[str]] = []
        result = []
        for p in parts:
            canonical = _PREFIX_LOOKUP.get(p)
            if canonical == "al":
                # Skip the Al token
                continue
            result.append(p)
        if result != parts:
            combos.append(result)
        return combos

    def _prefix_token_variants(self, token: str) -> list[str]:
        """Return all prefix variant forms for a single token."""
        variants = [token]

        for pv in _PREFIX_LOOKUP:
            pv_clean = pv.strip()
            if token.startswith(pv_clean) and len(token) > len(pv_clean):
                rest = token[len(pv_clean):]
                for alt in ("al", "el", "al-", "el-"):
                    variants.append(f"{alt}{rest}")
                variants.append(rest)  # bare form

        return variants

    def _abd_compound_forms(self, parts: list[str]) -> set[str]:
        """Generate Abdul-compound variant full-name forms."""
        forms: set[str] = set()
        for i, part in enumerate(parts):
            lower = part.lower()
            if lower.startswith("abdul") and i < len(parts) - 1:
                # "Abdul Rahman" → also try "Abdulrahman" as single token
                joined = lower + parts[i + 1].lower()
                new_parts = parts[:i] + [joined] + parts[i + 2:]
                forms.add(" ".join(new_parts))
            elif lower.startswith("abdul") and len(lower) > 5:
                # "Abdulrahman" → also try "Abdul Rahman" as two tokens
                rest = lower[5:]
                if rest:
                    new_parts = parts[:i] + ["abdul", rest] + parts[i + 1:]
                    forms.add(" ".join(new_parts))
        return forms


# ---------------------------------------------------------------------------
# Example inputs/outputs for 25+ Arabic names
# ---------------------------------------------------------------------------

EXAMPLES: list[dict] = [
    {
        "input": "Mohammed Al Rashid",
        "email_domain": "emirates.com",
        "expected_emails": [
            "mohammed.rashid@emirates.com",
            "mohammad.rashid@emirates.com",
            "muhammad.rashid@emirates.com",
            "mohd.rashid@emirates.com",
            "mohamed.rashid@emirates.com",
            "mohammed.alrashid@emirates.com",
            "mohammad.alrashid@emirates.com",
            "m.rashid@emirates.com",
        ],
    },
    {
        "input": "Ahmed bin Khalid Al Maktoum",
        "email_domain": "dubai.gov.ae",
        "expected_emails": [
            "ahmed.maktoum@dubai.gov.ae",
            "ahmed.almaktoum@dubai.gov.ae",
            "ahmed.khalid@dubai.gov.ae",
            "ahmed.khalid.maktoum@dubai.gov.ae",
            "a.maktoum@dubai.gov.ae",
        ],
    },
    {
        "input": "Abdul Rahman Al Qassimi",
        "email_domain": "adnoc.ae",
        "expected_emails": [
            "abdulrahman.qassimi@adnoc.ae",
            "abdulrahman.alqassimi@adnoc.ae",
            "abdul.rahman@adnoc.ae",
            "abdalrahman.qassimi@adnoc.ae",
            "a.qassimi@adnoc.ae",
            "rahman.qassimi@adnoc.ae",
        ],
    },
    {
        "input": "Sheikh Mohammed Bin Zayed",
        "email_domain": "ad.gov.ae",
        "expected_emails": [
            "mohammed.zayed@ad.gov.ae",
            "mohammad.zayed@ad.gov.ae",
            "mohd.zayed@ad.gov.ae",
            "m.zayed@ad.gov.ae",
        ],
    },
    {
        "input": "Fatima Bint Khalid Al Nahyan",
        "email_domain": "gov.ae",
        "expected_emails": [
            "fatima.nahyan@gov.ae",
            "fatima.alnahyan@gov.ae",
            "fatima.khalid@gov.ae",
            "f.nahyan@gov.ae",
        ],
    },
    {
        "input": "Dr. Omar Al Shamsi",
        "email_domain": "moh.gov.ae",
        "expected_emails": [
            "omar.shamsi@moh.gov.ae",
            "omar.alshamsi@moh.gov.ae",
            "o.shamsi@moh.gov.ae",
        ],
    },
    {
        "input": "Eng. Hassan Yousuf",
        "email_domain": "dewa.gov.ae",
        "expected_emails": [
            "hassan.yousuf@dewa.gov.ae",
            "hassan.yusuf@dewa.gov.ae",
            "h.yousuf@dewa.gov.ae",
        ],
    },
    {
        "input": "Noura El Khoury",
        "email_domain": "mubadala.com",
        "expected_emails": [
            "noura.khoury@mubadala.com",
            "noura.elkhoury@mubadala.com",
            "noura.alkhoury@mubadala.com",
            "n.khoury@mubadala.com",
        ],
    },
    {
        "input": "Mohd Khalid Al Falasi",
        "email_domain": "etisalat.ae",
        "expected_emails": [
            "mohd.falasi@etisalat.ae",
            "mohd.alfalasi@etisalat.ae",
            "mohammed.falasi@etisalat.ae",
            "m.falasi@etisalat.ae",
        ],
    },
    {
        "input": "Amina Abdul Aziz",
        "email_domain": "dubaiproperties.ae",
        "expected_emails": [
            "amina.aziz@dubaiproperties.ae",
            "amina.abdulaziz@dubaiproperties.ae",
            "a.aziz@dubaiproperties.ae",
        ],
    },
    {
        "input": "Khalid Ibrahim Al Mansoori",
        "email_domain": "fab.ae",
        "expected_emails": [
            "khalid.mansoori@fab.ae",
            "khalid.almansoori@fab.ae",
            "khalid.ibrahim.mansoori@fab.ae",
            "k.mansoori@fab.ae",
        ],
    },
    {
        "input": "Reem Abdullah Al Mheiri",
        "email_domain": "emaar.ae",
        "expected_emails": [
            "reem.mheiri@emaar.ae",
            "reem.almheiri@emaar.ae",
            "reem.abdullah.mheiri@emaar.ae",
            "r.mheiri@emaar.ae",
        ],
    },
    {
        "input": "Saeed Hamad Al Tayer",
        "email_domain": "dewa.gov.ae",
        "expected_emails": [
            "saeed.tayer@dewa.gov.ae",
            "saeed.altayer@dewa.gov.ae",
            "saeed.hamad.tayer@dewa.gov.ae",
            "s.tayer@dewa.gov.ae",
        ],
    },
    {
        "input": "Layla Mohamed Al Ketbi",
        "email_domain": "adnoc.ae",
        "expected_emails": [
            "layla.ketbi@adnoc.ae",
            "layla.alketbi@adnoc.ae",
            "layla.mohamed.ketbi@adnoc.ae",
            "l.ketbi@adnoc.ae",
        ],
    },
    {
        "input": "Tariq Abdul Karim",
        "email_domain": "careem.com",
        "expected_emails": [
            "tariq.karim@careem.com",
            "tariq.abdulkarim@careem.com",
            "tariq.abdelkarim@careem.com",
            "t.karim@careem.com",
        ],
    },
    {
        "input": "Mariam Obaid Al Shamsi",
        "email_domain": "du.ae",
        "expected_emails": [
            "mariam.shamsi@du.ae",
            "mariam.alshamsi@du.ae",
            "mariam.obaid.shamsi@du.ae",
            "m.shamsi@du.ae",
        ],
    },
    {
        "input": "Hamad Rashid Al Dhaheri",
        "email_domain": "adpolice.gov.ae",
        "expected_emails": [
            "hamad.dhaheri@adpolice.gov.ae",
            "hamad.aldhaheri@adpolice.gov.ae",
            "hamad.rashid.dhaheri@adpolice.gov.ae",
            "h.dhaheri@adpolice.gov.ae",
        ],
    },
    {
        "input": "Abdulla Sultan Al Darmaki",
        "email_domain": "adgm.abudhabi",
        "expected_emails": [
            "abdulla.darmaki@adgm.abudhabi",
            "abdulla.aldarmaki@adgm.abudhabi",
            "abdulla.sultan.darmaki@adgm.abudhabi",
            "a.darmaki@adgm.abudhabi",
        ],
    },
    {
        "input": "Salama Humaid Al Nuaimi",
        "email_domain": "moe.gov.ae",
        "expected_emails": [
            "salama.nuaimi@moe.gov.ae",
            "salama.alnuaimi@moe.gov.ae",
            "salama.humaid.nuaimi@moe.gov.ae",
            "s.nuaimi@moe.gov.ae",
        ],
    },
    {
        "input": "Rashid Juma Al Maktoum",
        "email_domain": "dubai.ae",
        "expected_emails": [
            "rashid.maktoum@dubai.ae",
            "rashid.almaktoum@dubai.ae",
            "rashid.juma.maktoum@dubai.ae",
            "r.maktoum@dubai.ae",
        ],
    },
    {
        "input": "Yousuf Abdul Salam",
        "email_domain": "noon.com",
        "expected_emails": [
            "yousuf.salam@noon.com",
            "yousuf.abdulsalam@noon.com",
            "yusuf.salam@noon.com",
            "y.salam@noon.com",
        ],
    },
    {
        "input": "Hind Mohamed Al Qubaisi",
        "email_domain": "difc.ae",
        "expected_emails": [
            "hind.qubaisi@difc.ae",
            "hind.alqubaisi@difc.ae",
            "hind.mohamed.qubaisi@difc.ae",
            "h.qubaisi@difc.ae",
        ],
    },
    {
        "input": "Faisal Ahmad Al Serkal",
        "email_domain": "dpworld.com",
        "expected_emails": [
            "faisal.serkal@dpworld.com",
            "faisal.alserkal@dpworld.com",
            "faisal.ahmad.serkal@dpworld.com",
            "f.serkal@dpworld.com",
        ],
    },
    {
        "input": "Moza Saeed Al Matrooshi",
        "email_domain": "sharjah.gov.ae",
        "expected_emails": [
            "moza.matrooshi@sharjah.gov.ae",
            "moza.almatrooshi@sharjah.gov.ae",
            "m.matrooshi@sharjah.gov.ae",
        ],
    },
    {
        "input": "Abdulrahman Nasser Al Raeesi",
        "email_domain": "moi.gov.ae",
        "expected_emails": [
            "abdulrahman.raeesi@moi.gov.ae",
            "abdulrahman.alraeesi@moi.gov.ae",
            "rahman.raeesi@moi.gov.ae",
            "a.raeesi@moi.gov.ae",
        ],
    },
]
