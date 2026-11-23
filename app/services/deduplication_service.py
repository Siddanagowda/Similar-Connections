"""
Deduplication and entity resolution service using RapidFuzz.
Consolidates cross-platform profiles belonging to the same individual or entity.
"""
from typing import List, Dict, Set
import logging
from rapidfuzz import fuzz
from app.schemas import RawProfileCandidate, Prospect, SocialLink
from app.utils.normalizers import extract_username_from_url, clean_prospect_name
from app.services.profile_extractor import profile_extractor

logger = logging.getLogger(__name__)


class DeduplicationService:
    def __init__(self, name_similarity_threshold: float = 88.0):
        self.name_similarity_threshold = name_similarity_threshold

    def consolidate_candidates(self, candidates: List[RawProfileCandidate]) -> List[Prospect]:
        """
        Groups raw candidates across platforms by identity and consolidates them
        into unique Prospect records with combined social links.
        """
        if not candidates:
            return []

        clusters: List[List[RawProfileCandidate]] = []

        for candidate in candidates:
            merged = False
            for cluster in clusters:
                if self._is_same_entity(candidate, cluster[0]):
                    cluster.append(candidate)
                    merged = True
                    break
            if not merged:
                clusters.append([candidate])

        # Build final Prospect records
        prospects: List[Prospect] = []
        for cluster in clusters:
            prospect = self._build_consolidated_prospect(cluster)
            prospects.append(prospect)

        logger.info(f"Consolidated {len(candidates)} raw candidates into {len(prospects)} unique prospects")
        return prospects

    def _is_same_entity(self, a: RawProfileCandidate, b: RawProfileCandidate) -> bool:
        """
        Evaluates whether candidate A and candidate B represent the same person or business.
        """
        # 1. Exact or shared verified contact info is a definitive match
        shared_emails = set(a.emails).intersection(set(b.emails))
        if shared_emails:
            return True

        shared_phones = set(a.phones).intersection(set(b.phones))
        if shared_phones:
            return True

        # 2. Check location conflict (e.g. London UK vs Tokyo Japan with common name)
        if a.location and b.location:
            loc_a = a.location.lower()
            loc_b = b.location.lower()
            # If countries are distinctly different and neither is contained in the other
            major_countries = ["usa", "uk", "india", "uae", "canada", "australia", "japan"]
            country_a = next((c for c in major_countries if c in loc_a), None)
            country_b = next((c for c in major_countries if c in loc_b), None)
            if country_a and country_b and country_a != country_b:
                return False

        # 3. Check username/handle match across platforms
        user_a = extract_username_from_url(a.platform, a.url)
        user_b = extract_username_from_url(b.platform, b.url)
        if user_a and user_b and len(user_a) >= 3 and len(user_b) >= 3:
            handle_ratio = fuzz.ratio(user_a, user_b)
            if handle_ratio >= 92:
                # Same handle across different platforms (e.g. @garyvee on X and Instagram)
                name_ratio = fuzz.token_sort_ratio(a.name.lower(), b.name.lower())
                if name_ratio >= 70:
                    return True

        # 4. Compare full names using RapidFuzz
        clean_a = clean_prospect_name(a.name).lower().strip()
        clean_b = clean_prospect_name(b.name).lower().strip()

        token_sort = fuzz.token_sort_ratio(clean_a, clean_b)
        token_set = fuzz.token_set_ratio(clean_a, clean_b)

        if token_sort >= self.name_similarity_threshold or token_set >= 95:
            return True

        return False

    def _build_consolidated_prospect(self, cluster: List[RawProfileCandidate]) -> Prospect:
        """
        Combines a cluster of candidates into a single Prospect record.
        """
        # Select best name (prefer longer, non-abbreviated, cleaned)
        names = [clean_prospect_name(c.name) for c in cluster if c.name and c.name != "Unknown Prospect"]
        best_name = max(names, key=len) if names else (cluster[0].name or "Unknown Prospect")

        # Select best location
        locations = [c.location for c in cluster if c.location]
        best_location = max(locations, key=len) if locations else None

        # Aggregate social links without duplicates
        all_social_links: List[SocialLink] = []
        seen_links: Set[str] = set()

        for candidate in cluster:
            candidate_links = profile_extractor.format_social_links(candidate)
            for sl in candidate_links:
                # Unique key: platform + link
                key = f"{sl.platform}:{sl.link.lower()}"
                if key not in seen_links:
                    seen_links.add(key)
                    all_social_links.append(sl)

        return Prospect(
            name=best_name,
            location=best_location,
            social_link=all_social_links
        )


deduplication_service = DeduplicationService()
