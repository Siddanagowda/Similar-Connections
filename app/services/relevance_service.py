"""
Relevance scoring and ranking service.

Candidates must demonstrate evidence for the requested geography and audience
before weighted scoring is applied. This prevents a generic topic mention from
being treated as a locally relevant prospect.
"""
from typing import List, Tuple
import logging
import re

from app.config import settings
from app.schemas import RawProfileCandidate, QueryIntent

logger = logging.getLogger(__name__)


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


class RelevanceService:
    def __init__(self, threshold: float = None):
        self.threshold = threshold if threshold is not None else settings.RELEVANCE_THRESHOLD

    def _candidate_text(self, candidate: RawProfileCandidate) -> str:
        return " ".join([
            candidate.name or "",
            candidate.bio_snippet or "",
            candidate.location or "",
            candidate.url or ""
        ])

    def _matches_location(self, candidate: RawProfileCandidate, intent: QueryIntent, corpus: str) -> bool:
        """Require candidate-side evidence for the requested city or country."""
        normalized = f" {_normalize_text(corpus)} "
        city = intent.location.city
        country = intent.location.country

        if city:
            city_normalized = _normalize_text(city)
            if city_normalized and f" {city_normalized} " in normalized:
                return True

            # The Washington DC region is commonly described as DC, DMV,
            # District of Columbia, or by nearby Maryland/Virginia suburbs.
            if "washington" in city_normalized and "dc" in city_normalized:
                dc_aliases = [
                    "district of columbia",
                    "washington d c",
                    "washington dc metro area",
                    "washington metropolitan area",
                    "dmv",
                    "silver spring",
                    "bethesda",
                    "arlington",
                    "alexandria",
                    "falls church",
                    "hyattsville",
                    "college park",
                    "rockville",
                    "takoma park",
                ]
                if any(f" {_normalize_text(alias)} " in normalized for alias in dc_aliases):
                    return True

            # Do not treat country-only evidence as proof of a city match.
            return False

        if country:
            aliases = {
                "usa": ["usa", "united states", "united states of america", "america"],
                "uk": ["uk", "united kingdom", "great britain", "england", "scotland", "wales"],
                "uae": ["uae", "united arab emirates"],
            }
            country_normalized = _normalize_text(country)
            options = aliases.get(country_normalized, [country])
            return any(
                f" {_normalize_text(option)} " in normalized
                for option in options
            )

        return True

    def _matches_audience(self, intent: QueryIntent, corpus: str) -> bool:
        """Require a role/persona signal when the query names a specific audience."""
        audience = (intent.audience or "").lower()
        normalized = f" {_normalize_text(corpus)} "
        interest = _normalize_text(intent.interest)

        # Audience descriptions such as 'football lovers' or 'cricket fans'
        # require an explicit fan/enthusiast/supporter signal, not just the
        # presence of the sport keyword or a coaching/team affiliation.
        if re.search(r"\b(lovers?|fans?|enthusiasts?|supporters?)\b", audience):
            fan_terms = [
                f"{interest} fan",
                f"fan of {interest}",
                f"{interest} fans",
                f"{interest} enthusiast",
                f"enthusiast for {interest}",
                f"{interest} supporter",
                f"supporter of {interest}",
                f"{interest} lover",
                f"lover of {interest}",
                f"passionate about {interest}",
                f"love {interest}",
                f"loves {interest}",
                f"follows {interest}",
                f"{interest} follower",
                f"{interest} followers",
                "fan of the game",
                "loves the game",
                "love the game",
                "passionate about the game",
                "fan of the sport",
                "loves the sport",
                "love the sport",
            ]
            has_fan_signal = bool(interest) and any(
                f" {_normalize_text(term)} " in normalized
                for term in fan_terms
            )
            has_interest = bool(interest and interest in normalized)
            return has_fan_signal and has_interest

        # Professional/business audiences need role evidence.
        if re.search(r"\b(founders?|owners?|ceos?|proprietors?|directors?)\b", audience):
            role_terms = [
                "founder", "co founder", "owner", "ceo", "proprietor", "director"
            ]
            return any(f" {term} " in normalized for term in role_terms)

        # For other audiences, require the audience phrase or topic plus an
        # audience-specific token to be present in the candidate text.
        audience_normalized = _normalize_text(audience)
        if audience_normalized and f" {audience_normalized} " in normalized:
            return True
        return bool(interest and interest in normalized)

    def score_candidate(self, candidate: RawProfileCandidate, intent: QueryIntent) -> float:
        """
        Calculate a 0.0–1.0 score using:
        interest (50%), location (35%), audience/persona (15%).
        """
        raw_corpus = self._candidate_text(candidate)
        corpus = _normalize_text(raw_corpus)

        # Hard evidence gates: a topic match alone is not a local prospect match.
        if not self._matches_location(candidate, intent, raw_corpus):
            return 0.0
        if not self._matches_audience(intent, raw_corpus):
            return 0.0

        score = 0.0

        interest = _normalize_text(intent.interest)
        if interest and interest in corpus:
            score += 0.50
        elif any(
            _normalize_text(keyword) in corpus
            for keyword in intent.search_keywords
            if keyword
        ):
            score += 0.30

        city = _normalize_text(intent.location.city or "")
        country = _normalize_text(intent.location.country or "")
        if city:
            score += 0.25
            # A verified city/metro-area match implies the requested location
            # context; country text adds corroboration where available.
            score += 0.10
        elif country:
            score += 0.35

        score += 0.15
        return round(min(score, 1.0), 3)

    def filter_and_rank_candidates(
        self, candidates: List[RawProfileCandidate], intent: QueryIntent
    ) -> List[RawProfileCandidate]:
        """Filter candidates against the configured threshold and rank by score."""
        scored_candidates: List[Tuple[float, RawProfileCandidate]] = []

        for candidate in candidates:
            score = self.score_candidate(candidate, intent)
            candidate.relevance_score = score
            if score >= self.threshold:
                scored_candidates.append((score, candidate))
            else:
                logger.debug(
                    "Filtered candidate '%s' (score=%.3f, location=%s, audience=%s)",
                    candidate.name,
                    score,
                    self._matches_location(candidate, intent, self._candidate_text(candidate)),
                    self._matches_audience(intent, self._candidate_text(candidate))
                )

        scored_candidates.sort(key=lambda item: item[0], reverse=True)
        return [candidate for _, candidate in scored_candidates]


relevance_service = RelevanceService()
