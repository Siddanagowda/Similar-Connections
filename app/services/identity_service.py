"""
Identity Resolution and Entity Matching Service.
Prevents false-positive merges of distinct individuals sharing similar names.
Uses multi-factor signals: exact contacts, cross-platform handles, geographic verification, and bio context.
"""
import logging
from typing import Optional, Tuple
from rapidfuzz import fuzz
from app.schemas import RawProfileCandidate
from app.utils.normalizers import extract_username_from_url, clean_prospect_name

logger = logging.getLogger(__name__)

# List of common names requiring higher scrutiny
COMMON_NAMES = {"john smith", "michael johnson", "david smith", "chris brown", "alex jones", "mohammed ali"}


class IdentityService:
    def __init__(self, high_name_threshold: float = 90.0):
        self.high_name_threshold = high_name_threshold

    def is_same_entity(self, a: RawProfileCandidate, b: RawProfileCandidate) -> Tuple[bool, float]:
        """
        Determines whether Candidate A and Candidate B represent the same individual or entity.
        Returns (is_match: bool, confidence: float between 0.0 and 1.0).
        """
        # Rule 1: Shared verified contact details (Definitive Match)
        if a.emails and b.emails:
            shared_emails = set(a.emails).intersection(set(b.emails))
            if shared_emails:
                return True, 1.0

        if a.phones and b.phones:
            shared_phones = set(a.phones).intersection(set(b.phones))
            if shared_phones:
                return True, 1.0

        # Rule 2: Strict Geographic Conflict Check (Negative Veto)
        if a.location and b.location:
            loc_a = a.location.lower()
            loc_b = b.location.lower()

            major_regions = ["usa", "uk", "india", "uae", "canada", "australia", "germany", "japan", "france"]
            region_a = next((r for r in major_regions if r in loc_a), None)
            region_b = next((r for r in major_regions if r in loc_b), None)

            if region_a and region_b and region_a != region_b:
                # Conflicting countries -> strictly reject merge
                return False, 0.0

        # Rule 3: Cross-Platform Handle Match
        user_a = extract_username_from_url(a.platform, a.url)
        user_b = extract_username_from_url(b.platform, b.url)

        clean_name_a = clean_prospect_name(a.name).lower().strip()
        clean_name_b = clean_prospect_name(b.name).lower().strip()

        if user_a and user_b and len(user_a) >= 4 and len(user_b) >= 4:
            handle_sim = fuzz.ratio(user_a, user_b)
            if handle_sim >= 92:
                name_sim = fuzz.token_sort_ratio(clean_name_a, clean_name_b)
                if name_sim >= 65:
                    return True, 0.95

        # Rule 4: Multi-Factor Name + Location + Context Verification
        # Never merge on name similarity alone!
        token_sort = fuzz.token_sort_ratio(clean_name_a, clean_name_b)
        token_set = fuzz.token_set_ratio(clean_name_a, clean_name_b)

        if token_sort >= self.high_name_threshold or token_set >= 95:
            # Common name guard
            if clean_name_a in COMMON_NAMES or clean_name_b in COMMON_NAMES:
                # Common names strictly require matching handle or matching verified city
                if not (a.location and b.location and a.location.lower() == b.location.lower()):
                    return False, 0.0

            # Verify location corroboration if locations are present
            if a.location and b.location:
                loc_sim = fuzz.partial_ratio(a.location.lower(), b.location.lower())
                if loc_sim >= 80:
                    return True, 0.88

            # Check shared professional context in bio
            words_a = set(a.bio_snippet.lower().split())
            words_b = set(b.bio_snippet.lower().split())
            # meaningful word overlap (excluding stopwords)
            stopwords = {"the", "a", "an", "in", "and", "or", "of", "to", "for", "at", "by", "from", "with", "is", "on"}
            overlap = (words_a.intersection(words_b)) - stopwords

            if len(overlap) >= 3:
                return True, 0.82

            # If locations are identical or compatible and name matches strongly
            if a.location and b.location:
                if a.location.lower() in b.location.lower() or b.location.lower() in a.location.lower():
                    return True, 0.80

        return False, 0.0


identity_service = IdentityService()
