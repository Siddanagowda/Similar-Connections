"""
Validation utilities for emails, phone numbers, WhatsApp links, and platform profile URLs.
"""
import re
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from email_validator import validate_email, EmailNotValidError
import phonenumbers


# Disallowed/dummy email domains and local parts
DISALLOWED_EMAIL_DOMAINS = {
    "example.com", "sample.com", "domain.com", "test.com", "email.com",
    "sentry.io", "wixpress.com", "schema.org", "github.com", "gravatar.com"
}
DISALLOWED_EMAIL_NAMES = {"user", "test", "name", "email", "admin", "info", "contact", "support", "noreply", "no-reply"}


def validate_and_normalize_email(email: str) -> Optional[str]:
    """
    Validates and normalizes an email address.
    Returns normalized email in lowercase or None if invalid.
    """
    if not email or not isinstance(email, str):
        return None
    email = email.strip().lower()
    # Strip mailto: prefix if present
    if email.startswith("mailto:"):
        email = email[7:].strip()

    try:
        validated = validate_email(email, check_deliverability=False)
        norm_email = validated.normalized
        domain = norm_email.split("@")[-1]
        local = norm_email.split("@")[0]

        if domain in DISALLOWED_EMAIL_DOMAINS:
            return None
        if local in DISALLOWED_EMAIL_NAMES and domain.count(".") < 1:
            return None
        return norm_email
    except EmailNotValidError:
        return None
    except Exception:
        return None


def validate_and_normalize_phone(phone: str, default_region: Optional[str] = "US") -> Optional[str]:
    """
    Validates and normalizes a phone number to E.164 format.
    Returns E.164 string (+12025550199) or None if invalid.
    """
    if not phone or not isinstance(phone, str):
        return None
    phone_clean = phone.strip()
    if phone_clean.startswith("tel:"):
        phone_clean = phone_clean[4:].strip()

    # Reject if too short or purely repetitive
    digits_only = re.sub(r"\D", "", phone_clean)
    if len(digits_only) < 7 or len(digits_only) > 15:
        return None
    if len(set(digits_only)) <= 1:
        return None

    # Handle international prefixes directly if phone starts with country code without '+'
    for prefix in ("971", "44", "91", "1"):
        if digits_only.startswith(prefix) and len(digits_only) >= 10:
            try:
                p = phonenumbers.parse("+" + digits_only, None)
                if phonenumbers.is_valid_number(p) or (phonenumbers.is_possible_number(p) and len(digits_only) >= 10):
                    return phonenumbers.format_number(p, phonenumbers.PhoneNumberFormat.E164)
            except Exception:
                pass

    for region in [default_region, "US", "GB", "IN", "AE", None]:
        try:
            parsed = phonenumbers.parse(phone_clean, region)
            if phonenumbers.is_valid_number(parsed) or (phonenumbers.is_possible_number(parsed) and len(digits_only) >= 10):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except Exception:
            continue
    return None


def validate_and_normalize_whatsapp(link_or_phone: str, default_region: Optional[str] = "US") -> Optional[str]:
    """
    Validates WhatsApp contact link or raw phone number.
    Returns canonical https://wa.me/<digits> link or None.
    """
    if not link_or_phone or not isinstance(link_or_phone, str):
        return None
    link_clean = link_or_phone.strip()

    # Extract digits from wa.me/ or api.whatsapp.com/send?phone=
    match = re.search(r"(?:wa\.me/|whatsapp\.com/send\?(?:[^&]*&)?phone=)(\+?\d+)", link_clean, re.IGNORECASE)
    if match:
        raw_num = match.group(1)
    else:
        # If it's a URL like wa.me/?text=... without phone digits, reject it
        if "wa.me" in link_clean or "whatsapp.com" in link_clean:
            return None
        raw_num = link_clean

    validated_phone = validate_and_normalize_phone(raw_num, default_region=default_region)
    if validated_phone:
        clean_digits = re.sub(r"\D", "", validated_phone)
        return f"https://wa.me/{clean_digits}"
    return None


def clean_tracking_params(url: str) -> str:
    """
    Removes analytics/tracking parameters (utm_*, ref, fbclid, etc.) from a URL.
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        query_dict = parse_qs(parsed.query, keep_blank_values=False)
        # Drop tracking keys
        filtered_query = {
            k: v for k, v in query_dict.items()
            if not k.startswith("utm_") and k not in {"ref", "fbclid", "gclid", "source", "s", "t"}
        }
        clean_query = urlencode(filtered_query, doseq=True)
        return urlunparse((
            parsed.scheme or "https",
            parsed.netloc,
            parsed.path.rstrip("/"),
            parsed.params,
            clean_query,
            ""  # drop fragments
        ))
    except Exception:
        return url


# Platform Profile URL regex rules
PLATFORM_URL_PATTERNS = {
    "LinkedIn": re.compile(
        r"^https?://([a-z]{2,3}\.)?linkedin\.com/(in|company)/[a-zA-Z0-9%_-]+/?$", re.IGNORECASE
    ),
    "X": re.compile(
        r"^https?://(www\.)?(x\.com|twitter\.com)/([a-zA-Z0-9_]{1,30})/?$", re.IGNORECASE
    ),
    "YouTube": re.compile(
        r"^https?://(www\.)?youtube\.com/(@[a-zA-Z0-9_.-]+|channel/[a-zA-Z0-9_-]+|c/[a-zA-Z0-9_-]+|user/[a-zA-Z0-9_-]+)/?$", re.IGNORECASE
    ),
    "Instagram": re.compile(
        r"^https?://(www\.)?instagram\.com/([a-zA-Z0-9_.-]{1,30})/?$", re.IGNORECASE
    ),
    "Facebook": re.compile(
        r"^https?://(www\.)?facebook\.com/([a-zA-Z0-9_.-]+)/?$", re.IGNORECASE
    ),
    "Threads": re.compile(
        r"^https?://(www\.)?threads\.net/(@[a-zA-Z0-9_.-]+)/?$", re.IGNORECASE
    ),
}

# Generic non-profile paths that should NOT be considered profile URLs
NON_PROFILE_PATHS = {
    "home", "feed", "login", "signup", "explore", "search", "terms", "privacy",
    "settings", "help", "about", "jobs", "press", "legal", "notifications",
    "messages", "i", "hashtag", "share", "watch", "post", "reel", "stories", "p"
}


def is_valid_platform_profile_url(platform: str, url: str) -> bool:
    """
    Checks if a URL is a genuine personal/business public profile link on the given platform.
    """
    if not url or not isinstance(url, str):
        return False
    clean_url = clean_tracking_params(url)
    # Search engines commonly append non-identity query parameters to profile
    # URLs (trk, originalSubdomain, hl, si, etc.). They are not part of the
    # profile path and must not cause an otherwise valid URL to be rejected.
    parsed_input = urlparse(clean_url)
    profile_url = urlunparse((
        parsed_input.scheme or "https",
        parsed_input.netloc,
        parsed_input.path.rstrip("/"),
        "",
        "",
        ""
    ))
    pattern = PLATFORM_URL_PATTERNS.get(platform)
    if not pattern:
        # For platforms without strict regex (e.g. Google indexed sites), ensure valid HTTP(S) URL
        try:
            parsed = urlparse(profile_url)
            return bool(parsed.scheme in ("http", "https") and parsed.netloc)
        except Exception:
            return False

    if not pattern.match(profile_url):
        return False

    # Check for reserved non-profile words in path
    parsed = urlparse(clean_url)
    path_segments = [seg for seg in parsed.path.strip("/").split("/") if seg]
    if not path_segments:
        return False

    last_segment = path_segments[-1].lower()
    first_segment = path_segments[0].lower()
    if last_segment in NON_PROFILE_PATHS or first_segment in NON_PROFILE_PATHS:
        return False

    return True


def normalize_profile_url(platform: str, url: str) -> str:
    """
    Normalizes a profile URL to its canonical form.
    E.g., twitter.com -> x.com, ensuring https.
    """
    cleaned = clean_tracking_params(url)
    if not cleaned.startswith("http://") and not cleaned.startswith("https://"):
        cleaned = "https://" + cleaned

    parsed = urlparse(cleaned)
    netloc = parsed.netloc.lower()

    if platform == "X" and "twitter.com" in netloc:
        netloc = netloc.replace("twitter.com", "x.com")

    # Query parameters and fragments are not needed in canonical profile links.
    path = parsed.path.rstrip("/")
    return urlunparse(("https", netloc, path, "", "", ""))
