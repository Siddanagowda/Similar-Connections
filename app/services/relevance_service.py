"""
Relevance scoring and ranking service.
Evaluates query-to-profile relevance based strictly on topical and geographic alignment.
Separates relevance from contact presence.
"""
from typing import List, Tuple
import logging
from app.config import settings
from app.schemas import RawProfileCandidate, QueryIntent

logger = logging.getLogger(__name__)


class RelevanceService:
    def __init__(self, threshold: float = None):
        self.threshold = threshold if threshold is not None else settings.RELEVANCE_THRESHOLD

    def score_candidate(self, candidate: RawProfileCandidate, intent: QueryIntent) -> float:
        """
        Calculates a relevance score from 0.0 to 1.0 strictly based on query alignment.
        Weighted components:
          - Interest relevance: 50%
          - Location relevance: 35%
          - Audience / persona alignment: 15%
        (Contact presence is NOT included in relevance scoring).
        """
        score = 0.0
        text_corpus = f"{candidate.name} {candidate.bio_snippet} {candidate.location or ''} {candidate.url}".lower()

        # 1. Interest Match (Weight: 0.50)
        interest = (intent.interest or "").lower()
        if interest:
            if interest in text_corpus:
                score += 0.50
            else:
                for kw in intent.search_keywords:
                    if kw.lower() in text_corpus:
                        score += 0.30
                        break

        # 2. Location Match (Weight: 0.35)
        city = (intent.location.city or "").lower()
        country = (intent.location.country or "").lower()

        if city and city in text_corpus:
            score += 0.25
        if country and country in text_corpus:
            score += 0.10
        elif not city and not country:
            # If query had no geographic constraints, grant full location credit
            score += 0.35

        # 3. Audience / Persona alignment (Weight: 0.15)
        audience = (intent.audience or "").lower()
        if audience and audience in text_corpus:
            score += 0.15
        else:
            role_indicators = ["founder", "owner", "ceo", "director", "lover", "enthusiast", "agency", "creator", "player", "chef"]
            if any(r in text_corpus for r in role_indicators):
                score += 0.10

        return round(min(score, 1.0), 3)

    def filter_and_rank_candidates(
        self, candidates: List[RawProfileCandidate], intent: QueryIntent
    ) -> List[RawProfileCandidate]:
        """
        Scores all candidates, filters out irrelevant results below the threshold,
        and ranks them by descending score.
        """
        scored_candidates: List[Tuple[float, RawProfileCandidate]] = []

        for cand in candidates:
            score = self.score_candidate(cand, intent)
            cand.relevance_score = score
            if score >= self.threshold:
                scored_candidates.append((score, cand))
            else:
                logger.debug(f"Filtered out low-relevance candidate '{cand.name}' (score: {score})")

        # Sort descending by score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored_candidates]


relevance_service = RelevanceService()
