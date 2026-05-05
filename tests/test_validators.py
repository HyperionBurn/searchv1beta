"""
Tests for validator functions (models/validators.py).

Covers:
  - validate_email (valid, invalid, edge cases)
  - validate_uae_phone (various UAE formats: 050, 055, +97150, etc.)
  - validate_gcc_phone (other GCC countries)
  - is_m365_domain (mocked DNS)
  - Arabic name normalization functions
"""

import pytest
from unittest.mock import patch, MagicMock

from models.validators import (
    ArabicNameNormalizer,
    MOHAMMED_VARIANTS,
    generate_email_permutations,
    generate_name_variants,
    infer_uae_carrier,
    infer_uae_emirate,
    is_uae_domain,
    is_uae_mobile,
    is_uae_whatsapp_likely,
    normalize_arabic_name,
    validate_email,
    validate_gcc_phone,
    validate_linkedin_url,
    validate_saudi_phone,
    validate_uae_phone,
)


# ===========================================================================
# validate_email
# ===========================================================================


class TestValidateEmail:
    def test_valid_email(self):
        assert validate_email("ahmed@example.com") == "ahmed@example.com"

    def test_uppercase_lowered(self):
        assert validate_email("Ahmed@Example.COM") == "ahmed@example.com"

    def test_whitespace_stripped(self):
        assert validate_email("  test@example.com  ") == "test@example.com"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_email("")

    def test_no_at_sign_raises(self):
        with pytest.raises(ValueError, match="Invalid email"):
            validate_email("noemail")

    def test_double_at_raises(self):
        with pytest.raises(ValueError, match="Invalid email"):
            validate_email("bad@@example.com")

    def test_plus_tagging_valid(self):
        assert validate_email("user+tag@gmail.com") == "user+tag@gmail.com"

    def test_dots_in_local_part(self):
        assert validate_email("first.last@company.co.uk") == "first.last@company.co.uk"


# ===========================================================================
# validate_uae_phone
# ===========================================================================


class TestValidateUAEPhone:
    # --- Valid mobile formats ---

    @pytest.mark.parametrize("input_phone,expected", [
        ("+971501234567", "+971501234567"),
        ("+971551234567", "+971551234567"),
        ("+971521234567", "+971521234567"),
        ("+971541234567", "+971541234567"),
        ("+971561234567", "+971561234567"),
        ("+971581234567", "+971581234567"),
    ])
    def test_valid_e164_mobile(self, input_phone, expected):
        assert validate_uae_phone(input_phone) == expected

    def test_local_format_05x(self):
        assert validate_uae_phone("0501234567") == "+971501234567"

    def test_local_format_055(self):
        assert validate_uae_phone("0551234567") == "+971551234567"

    def test_with_dashes(self):
        assert validate_uae_phone("+971-50-123-4567") == "+971501234567"

    def test_with_spaces(self):
        assert validate_uae_phone("+971 50 123 4567") == "+971501234567"

    def test_without_plus(self):
        assert validate_uae_phone("971501234567") == "+971501234567"

    # --- Valid landline ---

    def test_dubai_landline(self):
        assert validate_uae_phone("+97141234567") == "+97141234567"

    def test_abu_dhabi_landline(self):
        assert validate_uae_phone("+97121234567") == "+97121234567"

    # --- Valid toll-free ---

    def test_tollfree_800(self):
        assert validate_uae_phone("+971800123456") == "+971800123456"

    def test_local_800(self):
        assert validate_uae_phone("800123456") == "+971800123456"

    # --- Invalid ---

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_uae_phone("")

    def test_invalid_prefix_raises(self):
        with pytest.raises(ValueError, match="Invalid UAE mobile prefix"):
            validate_uae_phone("+971591234567")

    def test_invalid_length_raises(self):
        with pytest.raises(ValueError):
            validate_uae_phone("+97150123456")  # too short

    def test_random_string_raises(self):
        with pytest.raises(ValueError, match="Invalid UAE phone"):
            validate_uae_phone("not-a-phone")


# ===========================================================================
# validate_saudi_phone
# ===========================================================================


class TestValidateSaudiPhone:
    def test_valid_e164(self):
        assert validate_saudi_phone("+966501234567") == "+966501234567"

    def test_local_format(self):
        assert validate_saudi_phone("0501234567") == "+966501234567"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_saudi_phone("")


# ===========================================================================
# validate_gcc_phone
# ===========================================================================


class TestValidateGCCPhone:
    def test_uae_dispatches_correctly(self):
        assert validate_gcc_phone("+971501234567") == "+971501234567"

    def test_saudi_dispatches_correctly(self):
        assert validate_gcc_phone("+966501234567") == "+966501234567"

    def test_qatar_valid(self):
        assert validate_gcc_phone("+97433123456") == "+97433123456"

    def test_bahrain_valid(self):
        assert validate_gcc_phone("+97331234567") == "+97331234567"

    def test_oman_valid(self):
        assert validate_gcc_phone("+96891234567") == "+96891234567"

    def test_kuwait_valid(self):
        assert validate_gcc_phone("+96551234567") == "+96551234567"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_gcc_phone("")

    def test_unrecognised_country_raises(self):
        with pytest.raises(ValueError, match="Unrecognised GCC"):
            validate_gcc_phone("+442071234567")


# ===========================================================================
# Carrier & emirate inference
# ===========================================================================


class TestInferUAECarrier:
    def test_etisalat_50(self):
        assert infer_uae_carrier("+971501234567") == "etisalat"

    def test_etisalat_54(self):
        assert infer_uae_carrier("+971541234567") == "etisalat"

    def test_du_55(self):
        assert infer_uae_carrier("+971551234567") == "du"

    def test_shared_52_unknown(self):
        assert infer_uae_carrier("+971521234567") == "unknown"

    def test_landline_etisalat(self):
        assert infer_uae_carrier("+97141234567") == "etisalat"

    def test_non_uae_unknown(self):
        assert infer_uae_carrier("+14155552671") == "unknown"


class TestInferUAEEmirate:
    def test_dubai(self):
        assert infer_uae_emirate("+97141234567") == "Dubai"

    def test_abu_dhabi(self):
        assert infer_uae_emirate("+97121234567") == "Abu Dhabi"

    def test_sharjah(self):
        assert infer_uae_emirate("+97161234567") == "Sharjah"

    def test_mobile_returns_none(self):
        assert infer_uae_emirate("+971501234567") is None

    def test_non_uae_returns_none(self):
        assert infer_uae_emirate("+14155552671") is None


class TestIsUAEMobile:
    def test_mobile_true(self):
        assert is_uae_mobile("+971501234567") is True

    def test_landline_false(self):
        assert is_uae_mobile("+97141234567") is False


class TestIsUAEWhatsAppLikely:
    def test_mobile_likely(self):
        assert is_uae_whatsapp_likely("+971501234567") is True

    def test_landline_unlikely(self):
        assert is_uae_whatsapp_likely("+97141234567") is False


# ===========================================================================
# LinkedIn URL validator
# ===========================================================================


class TestValidateLinkedInURL:
    def test_valid_url(self):
        assert validate_linkedin_url("https://linkedin.com/in/test-user") == "https://linkedin.com/in/test-user"

    def test_trailing_slash_removed(self):
        assert validate_linkedin_url("https://linkedin.com/in/test-user/") == "https://linkedin.com/in/test-user"

    def test_www_accepted(self):
        assert validate_linkedin_url("https://www.linkedin.com/in/test-user") == "https://www.linkedin.com/in/test-user"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_linkedin_url("")

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Invalid LinkedIn"):
            validate_linkedin_url("https://facebook.com/test")


# ===========================================================================
# UAE domain checks
# ===========================================================================


class TestIsUAEDomain:
    def test_dot_ae(self):
        assert is_uae_domain("example.ae") is True

    def test_co_dot_ae(self):
        assert is_uae_domain("example.co.ae") is True

    def test_com_not_uae(self):
        assert is_uae_domain("example.com") is False

    def test_gov_ae(self):
        assert is_uae_domain("portal.gov.ae") is True


# ===========================================================================
# is_m365_domain (mocked DNS)
# ===========================================================================


class TestIsM365Domain:
    """Test M365 detection with mocked DNS lookups."""

    @pytest.mark.network
    def test_real_lookup_returns_bool(self):
        """Network test — just checks it returns bool, doesn't assert True/False."""
        from models.validators import is_m365_domain
        result = is_m365_domain("microsoft.com")
        assert isinstance(result, bool)

    def test_m365_detected(self):
        """Mock DNS to simulate M365 MX record."""
        import models.validators as mod
        with patch.dict("sys.modules", {"dns": MagicMock(), "dns.resolver": MagicMock()}):
            # Re-import to get mocked dns
            mock_resolver = MagicMock()
            mock_record = MagicMock()
            mock_record.exchange = "example-com.mail.protection.outlook.com."
            mock_resolver.resolve.return_value = [mock_record]

            with patch.object(mod, "is_m365_domain", wraps=None) as mock_fn:
                # Just test the logic directly by patching dns.resolver inside the function
                pass

        # Instead, test by mocking at the function level
        # The function does `import dns.resolver` inside, so we mock the import
        import dns.resolver as real_resolver
        mock_record = MagicMock()
        mock_record.exchange = "example-com.mail.protection.outlook.com."
        with patch.object(real_resolver, "resolve", return_value=[mock_record]):
            from models.validators import is_m365_domain
            assert is_m365_domain("example.com") is True

    def test_non_m365_domain(self):
        """Mock DNS to simulate non-M365 MX record."""
        import dns.resolver as real_resolver
        mock_record = MagicMock()
        mock_record.exchange = "mail.example.com."
        with patch.object(real_resolver, "resolve", return_value=[mock_record]):
            from models.validators import is_m365_domain
            assert is_m365_domain("example.com") is False

    def test_dns_failure_returns_false(self):
        """Network error should return False, not raise."""
        import dns.resolver as real_resolver
        with patch.object(real_resolver, "resolve", side_effect=Exception("DNS timeout")):
            from models.validators import is_m365_domain
            assert is_m365_domain("example.com") is False


# ===========================================================================
# Arabic name normalization
# ===========================================================================


class TestNormalizeArabicName:
    def test_lowercase(self):
        assert normalize_arabic_name("AHMED AL-RASHID") == "ahmed al-rashid"

    def test_whitespace_collapsed(self):
        assert normalize_arabic_name("  Ahmed   Al   Rashid  ") == "ahmed al rashid"

    def test_diacritics_stripped(self):
        assert normalize_arabic_name("Ahméd") == "ahmed"


class TestGenerateNameVariants:
    def test_mohammed_variant_generation(self):
        variants = generate_name_variants("Mohammed Ahmed")
        assert any("m " in v for v in variants)

    def test_al_prefix_stripped(self):
        variants = generate_name_variants("Ahmed Al Rashid")
        assert any("rashid" in v and "al" not in v for v in variants)

    def test_returns_list(self):
        result = generate_name_variants("Ahmed Ali")
        assert isinstance(result, list)
        assert len(result) >= 1


class TestGenerateEmailPermutations:
    def test_basic_permutations(self):
        emails = generate_email_permutations("ahmed", "rashid", "example.com")
        assert "ahmed.rashid@example.com" in emails
        assert "ahmedrashid@example.com" in emails
        assert "arashid@example.com" in emails

    def test_mohammed_compression(self):
        emails = generate_email_permutations("mohammed", "ali", "example.com")
        assert any(e.startswith("m.") for e in emails)
        assert any(e.startswith("mohd") for e in emails)

    def test_deduplication(self):
        emails = generate_email_permutations("ali", "khan", "example.com")
        assert len(emails) == len(set(emails))


class TestArabicNameNormalizer:
    def test_normalize(self):
        assert ArabicNameNormalizer.normalize("MOHAMMED Ahmed") == "mohammed ahmed"

    def test_strip_prefixes(self):
        result = ArabicNameNormalizer.strip_prefixes("Ahmed Al Rashid")
        assert "al" not in result.split()
        assert "ahmed" in result

    def test_variants(self):
        variants = ArabicNameNormalizer.variants("Mohammed Ali")
        assert isinstance(variants, list)
        assert len(variants) >= 1

    def test_email_permutations(self):
        emails = ArabicNameNormalizer.email_permutations("saeed", "khan", "test.com")
        assert "saeed.khan@test.com" in emails
