"""
Unit tests for validator utilities: emails, phones, whatsapp, and profile URLs.
"""
import pytest
from app.utils.validators import (
    validate_and_normalize_email,
    validate_and_normalize_phone,
    validate_and_normalize_whatsapp,
    is_valid_platform_profile_url,
    normalize_profile_url,
    clean_tracking_params
)


def test_email_validation():
    # Valid emails
    assert validate_and_normalize_email("john.smith@vaynermedia.com") == "john.smith@vaynermedia.com"
    assert validate_and_normalize_email("mailto:contact@dxora.com") == "contact@dxora.com"
    assert validate_and_normalize_email("INFO@COMPANY.CO.UK") == "info@company.co.uk"

    # Invalid or dummy emails
    assert validate_and_normalize_email("invalid-email") is None
    assert validate_and_normalize_email("someone@example.com") is None
    assert validate_and_normalize_email("test@sample.com") is None
    assert validate_and_normalize_email("") is None
    assert validate_and_normalize_email(None) is None


def test_phone_validation():
    # Valid US numbers
    assert validate_and_normalize_phone("+1 202-555-0199", default_region="US") == "+12025550199"
    assert validate_and_normalize_phone("2025550199", default_region="US") == "+12025550199"

    # Valid UK numbers
    assert validate_and_normalize_phone("+44 7700 900077", default_region="GB") == "+447700900077"

    # Valid India numbers
    assert validate_and_normalize_phone("+91 98250 01234", default_region="IN") == "+919825001234"

    # Invalid / repetitive numbers
    assert validate_and_normalize_phone("1111111") is None
    assert validate_and_normalize_phone("123") is None
    assert validate_and_normalize_phone("") is None
    assert validate_and_normalize_phone(None) is None


def test_whatsapp_validation():
    assert validate_and_normalize_whatsapp("https://wa.me/12025550199") == "https://wa.me/12025550199"
    assert validate_and_normalize_whatsapp("https://api.whatsapp.com/send?phone=447700900077") == "https://wa.me/447700900077"
    assert validate_and_normalize_whatsapp("+12025550199") == "https://wa.me/12025550199"
    assert validate_and_normalize_whatsapp("invalid_link") is None


def test_profile_url_validation():
    # LinkedIn
    assert is_valid_platform_profile_url("LinkedIn", "https://www.linkedin.com/in/jasonsmith") is True
    assert is_valid_platform_profile_url("LinkedIn", "https://linkedin.com/company/dxora") is True
    assert is_valid_platform_profile_url("LinkedIn", "https://linkedin.com/feed") is False
    assert is_valid_platform_profile_url("LinkedIn", "https://linkedin.com/login") is False

    # X / Twitter
    assert is_valid_platform_profile_url("X", "https://x.com/garyvee") is True
    assert is_valid_platform_profile_url("X", "https://twitter.com/garyvee") is True
    assert is_valid_platform_profile_url("X", "https://x.com/home") is False
    assert is_valid_platform_profile_url("X", "https://x.com/explore") is False

    # Instagram
    assert is_valid_platform_profile_url("Instagram", "https://www.instagram.com/whoisjwright") is True
    assert is_valid_platform_profile_url("Instagram", "https://instagram.com/explore") is False
    assert is_valid_platform_profile_url("Instagram", "https://instagram.com/p/B3k4l5m") is False

    # YouTube
    assert is_valid_platform_profile_url("YouTube", "https://www.youtube.com/@garyvee") is True
    assert is_valid_platform_profile_url("YouTube", "https://www.youtube.com/channel/UC123456789") is True
    assert is_valid_platform_profile_url("YouTube", "https://www.youtube.com/watch") is False

    # Threads
    assert is_valid_platform_profile_url("Threads", "https://www.threads.net/@garyvee") is True
    assert is_valid_platform_profile_url("Threads", "https://threads.net/login") is False

    # Search engines often append query parameters to otherwise valid profile URLs.
    assert is_valid_platform_profile_url("LinkedIn", "https://www.linkedin.com/in/jasonsmith?trk=public_profile") is True
    assert is_valid_platform_profile_url("X", "https://x.com/garyvee?s=20") is True
    assert is_valid_platform_profile_url("Instagram", "https://instagram.com/whoisjwright/?hl=en") is True
    assert is_valid_platform_profile_url("YouTube", "https://www.youtube.com/@garyvee?si=abc123") is True
    assert normalize_profile_url("LinkedIn", "https://www.linkedin.com/in/jasonsmith?trk=public_profile") == "https://www.linkedin.com/in/jasonsmith"


def test_clean_tracking_params():
    url = "https://x.com/garyvee?utm_source=twitter&utm_medium=social&ref=share"
    cleaned = clean_tracking_params(url)
    assert cleaned == "https://x.com/garyvee"
