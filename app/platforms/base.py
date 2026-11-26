"""
Base Platform Adapter Abstract Class.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
import re
from app.schemas import QueryIntent, RawProfileCandidate
from app.utils.validators import (
    is_valid_platform_profile_url,
    normalize_profile_url,
    validate_and_normalize_email,
    validate_and_normalize_phone,
    validate_and_normalize_whatsapp
)
from app.utils.normalizers import clean_prospect_name, clean_location_string


EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
WHATSAPP_LINK_REGEX = re.compile(r"(?:https?://)?(?:wa\.me/|api\.whatsapp\.com/send\?phone=)(\+?\d+)", re.IGNORECASE)


class BasePlatformAdapter(ABC):
    """
    Abstract interface for platform-specific search and profile extraction.
    Ensures modularity: failure in one platform cannot break others.
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Name of the platform, e.g., 'LinkedIn', 'X'"""
        pass

    @abstractmethod
    def generate_search_queries(self, intent: QueryIntent) -> List[str]:
        """Generate targeted search queries/dorks for this platform."""
        pass

    def is_valid_url(self, url: str) -> bool:
        """Check whether the URL is a verified public profile on this platform."""
        return is_valid_platform_profile_url(self.platform_name, url)

    def normalize_url(self, url: str) -> str:
        """Canonicalize profile URL."""
        return normalize_profile_url(self.platform_name, url)

    def extract_candidate(self, title: str, snippet: str, url: str, intent: QueryIntent) -> Optional[RawProfileCandidate]:
        """
        Parses title, snippet, and URL to build a RawProfileCandidate.
        """
        if not self.is_valid_url(url):
            return None

        canonical_url = self.normalize_url(url)
        clean_name = clean_prospect_name(title)
        if not clean_name or clean_name.lower() in ("unknown", "unknown prospect", "login", "profile"):
            return None

        combined_text = f"{title} {snippet}"

        # Extract contacts
        emails: List[str] = []
        for raw_email in EMAIL_REGEX.findall(combined_text):
            norm_email = validate_and_normalize_email(raw_email)
            if norm_email and norm_email not in emails:
                emails.append(norm_email)

        phones: List[str] = []
        region = "US"
        if intent.location and intent.location.country:
            c = intent.location.country.upper()
            if "UK" in c or "BRITAIN" in c or "UNITED KINGDOM" in c:
                region = "GB"
            elif "INDIA" in c:
                region = "IN"
            elif "UAE" in c or "DUBAI" in c:
                region = "AE"

        for raw_phone in PHONE_REGEX.findall(combined_text):
            norm_phone = validate_and_normalize_phone(raw_phone, default_region=region)
            if norm_phone and norm_phone not in phones:
                phones.append(norm_phone)

        whatsapp_links: List[str] = []
        for raw_wa in WHATSAPP_LINK_REGEX.findall(combined_text):
            norm_wa = validate_and_normalize_whatsapp(raw_wa, default_region=region)
            if norm_wa and norm_wa not in whatsapp_links:
                whatsapp_links.append(norm_wa)

        # Only attach a location when the candidate's own title/snippet
        # contains evidence for it. Do not copy the query location onto every
        # result: that creates unsupported location claims and inflates scoring.
        detected_location = None
        if intent.location:
            loc_str = intent.location.to_formatted_string()
            candidate_text = combined_text.lower()
            city_match = (
                intent.location.city
                and intent.location.city.lower() in candidate_text
            )
            country_match = (
                intent.location.country
                and intent.location.country.lower() in candidate_text
            )
            if city_match and loc_str:
                detected_location = loc_str
            elif country_match:
                # Country evidence alone does not prove the requested city.
                detected_location = intent.location.country
            elif intent.location.city and "washington" in intent.location.city.lower() and "dc" in intent.location.city.lower():
                # Preserve the actually-mentioned suburb instead of claiming
                # that a nearby metro-area profile is located in Washington DC.
                metro_locations = [
                    ("silver spring", "Silver Spring, Maryland (Washington DC metro area)"),
                    ("bethesda", "Bethesda, Maryland (Washington DC metro area)"),
                    ("arlington virginia", "Arlington, Virginia (Washington DC metro area)"),
                    ("alexandria virginia", "Alexandria, Virginia (Washington DC metro area)"),
                    ("falls church virginia", "Falls Church, Virginia (Washington DC metro area)"),
                    ("hyattsville maryland", "Hyattsville, Maryland (Washington DC metro area)"),
                    ("college park maryland", "College Park, Maryland (Washington DC metro area)"),
                    ("rockville maryland", "Rockville, Maryland (Washington DC metro area)"),
                    ("takoma park maryland", "Takoma Park, Maryland (Washington DC metro area)"),
                ]
                normalized_text = re.sub(r"[^a-z0-9]+", " ", combined_text.lower())
                for location_token, formatted_location in metro_locations:
                    if location_token in normalized_text:
                        detected_location = formatted_location
                        break

        return RawProfileCandidate(
            platform=self.platform_name,
            url=canonical_url,
            name=clean_name,
            location=clean_location_string(detected_location),
            bio_snippet=snippet,
            emails=emails,
            phones=phones,
            whatsapp_links=whatsapp_links,
            relevance_score=0.0
        )
