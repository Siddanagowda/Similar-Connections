"""
Data cleaning and normalization utilities for names, locations, and usernames.
"""
import re
from typing import Optional
from urllib.parse import urlparse


PLATFORM_SUFFIXES = [
    r"\s*\|\s*LinkedIn.*$",
    r"\s*-\s*LinkedIn.*$",
    r"\s*•\s*Instagram.*$",
    r"\s*\|\s*Instagram.*$",
    r"\s*-\s*YouTube.*$",
    r"\s*\|\s*Facebook.*$",
    r"\s*-\s*Facebook.*$",
    r"\s*on\s+X:\s*.*$",
    r"\s*on\s+Twitter:\s*.*$",
    r"\s*/\s*X.*$",
    r"\s*•\s*Threads.*$",
    r"\s*\|\s*Threads.*$",
]

LOCATION_CLEAN_PATTERNS = [
    (r"\bGreater\s+", ""),
    (r"\bMetropolitan\s+Area\b", ""),
    (r"\bArea\b", ""),
    (r"\bLocation:\s*", ""),
    (r"\s+", " "),
]


def clean_prospect_name(raw_name: str) -> str:
    """
    Cleans raw title or scraped text into a canonical person or company name.
    Strips platform suffixes, social handles, and trailing descriptors.
    """
    if not raw_name or not isinstance(raw_name, str):
        return "Unknown Prospect"

    name = raw_name.strip()

    # 1. Remove platform title branding
    for pat in PLATFORM_SUFFIXES:
        name = re.sub(pat, "", name, flags=re.IGNORECASE)

    # 2. If title contains handle like "John Doe (@johndoe)", extract John Doe
    handle_match = re.search(r"^(.*?)\s*\(@[a-zA-Z0-9_.-]+\)", name)
    if handle_match and len(handle_match.group(1).strip()) > 1:
        name = handle_match.group(1).strip()

    # 3. If title is formatted as "Name - Headline/Company" or "Name | Title"
    # Take the first segment if it looks like a person's name (1-4 words)
    split_chars = [" - ", " – ", " — ", " | "]
    for sc in split_chars:
        if sc in name:
            parts = name.split(sc)
            first_part = parts[0].strip()
            # If the first part looks like a realistic name (<= 4 words, >= 2 chars)
            if 1 <= len(first_part.split()) <= 4 and len(first_part) >= 2:
                name = first_part
                break

    # 4. Remove leading/trailing non-alphanumeric characters (except typical title punctuation like dots)
    name = re.sub(r"^[^\w\s\.]+", "", name)
    name = re.sub(r"[^\w\s\.]+$", "", name)

    # 5. Collapse spaces
    name = re.sub(r"\s+", " ", name).strip()

    # 6. Reject generic site navigation or listicle titles
    disallowed_generic = {
        "home", "welcome", "whatsapp", "login", "signup", "contact us", "about us",
        "terms", "privacy", "cookie policy", "unknown", "unknown prospect"
    }
    if name.lower() in disallowed_generic:
        return "Unknown Prospect"
    if re.search(r"^(how to|top \d+|best \d+|guide to|list of)\b", name, re.IGNORECASE):
        return "Unknown Prospect"

    # 7. Fallback if empty
    return name if name else "Unknown Prospect"


def clean_location_string(raw_location: Optional[str]) -> Optional[str]:
    """
    Standardizes location string. E.g. "Washington, DC Area" -> "Washington, DC, USA"
    """
    if not raw_location or not isinstance(raw_location, str):
        return None

    loc = raw_location.strip()
    for pattern, replacement in LOCATION_CLEAN_PATTERNS:
        loc = re.sub(pattern, replacement, loc, flags=re.IGNORECASE)

    loc = loc.strip(" ,.-")
    return loc if loc else None


def extract_username_from_url(platform: str, url: str) -> Optional[str]:
    """
    Extracts canonical username/handle from profile URL for identity matching.
    """
    if not url:
        return None
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        parts = [p for p in path.split("/") if p]
        if not parts:
            return None

        if platform == "LinkedIn":
            # linkedin.com/in/username
            if len(parts) >= 2 and parts[0] == "in":
                return parts[1].lower()
            return parts[-1].lower()

        if platform in ("X", "Instagram", "Facebook"):
            # x.com/username
            return parts[0].lstrip("@").lower()

        if platform in ("YouTube", "Threads"):
            # youtube.com/@username or threads.net/@username
            user = parts[0]
            if user.startswith("@"):
                return user[1:].lower()
            if len(parts) >= 2 and parts[0] in ("channel", "c", "user"):
                return parts[1].lower()
            return user.lower()

        return parts[-1].lower()
    except Exception:
        return None
