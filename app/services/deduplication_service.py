"""
Deduplication and profile consolidation service.
Leverages IdentityService for robust multi-factor identity matching.
Consolidates cross-platform profiles belonging to the same verified individual or entity.
"""
from typing import List, Dict, Set
import logging
from app.schemas import RawProfileCandidate, Prospect, SocialLink
from app.utils.normalizers import clean_prospect_name
from app.services.identity_service import identity_service
from app.services.contact_service import contact_service
from app.services.profile_extractor import profile_extractor

logger = logging.getLogger(__name__)


class DeduplicationService:
    def consolidate_candidates(self, candidates: List[RawProfileCandidate]) -> List[Prospect]:
        """
        Groups raw candidates across platforms by multi-factor identity resolution
        and consolidates them into unique Prospect records with combined social links.
        """
        if not candidates:
            return []

        clusters: List[List[RawProfileCandidate]] = []

        for candidate in candidates:
            merged = False
            for cluster in clusters:
                # Compare against all members or primary candidate of cluster
                is_match, confidence = identity_service.is_same_entity(candidate, cluster[0])
                if is_match:
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

    def _build_consolidated_prospect(self, cluster: List[RawProfileCandidate]) -> Prospect:
        """
        Combines a cluster of verified profiles into a single consolidated Prospect record.
        """
        # Select best cleaned name (prefer longer, non-abbreviated)
        names = [clean_prospect_name(c.name) for c in cluster if c.name and c.name != "Unknown Prospect"]
        best_name = max(names, key=len) if names else (cluster[0].name or "Unknown Prospect")

        # Select best location
        locations = [c.location for c in cluster if c.location]
        best_location = max(locations, key=len) if locations else None

        # Aggregate social links and contacts without duplicates
        all_social_links: List[SocialLink] = []
        seen_links: Set[str] = set()

        for candidate in cluster:
            candidate_links = profile_extractor.format_social_links(candidate)
            for sl in candidate_links:
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
