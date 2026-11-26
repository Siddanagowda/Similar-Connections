"""
Evidence tracking and provenance service.
Records source URLs, snippets, and matched keywords for every candidate and prospect.
"""
from typing import Dict, List, Set, Optional
from pydantic import BaseModel, Field
from app.schemas import RawProfileCandidate, QueryIntent


class EvidenceRecord(BaseModel):
    source_url: str
    platform: str
    snippet: str
    matched_keywords: List[str] = Field(default_factory=list)


class EvidenceTrail(BaseModel):
    prospect_name: str
    records: List[EvidenceRecord] = Field(default_factory=list)

    def summary(self) -> str:
        sources = [r.source_url for r in self.records]
        return f"Evidence collected from {len(sources)} source(s): {', '.join(sources)}"


class EvidenceService:
    def __init__(self):
        self._trails: Dict[str, EvidenceTrail] = {}

    def record_evidence(
        self,
        candidate: RawProfileCandidate,
        intent: QueryIntent
    ) -> EvidenceRecord:
        """
        Extracts matched keywords and stores an evidence record for a candidate.
        """
        matched = []
        text_corpus = f"{candidate.name} {candidate.bio_snippet} {candidate.location or ''}".lower()

        if intent.interest and intent.interest.lower() in text_corpus:
            matched.append(intent.interest)
        if intent.audience and intent.audience.lower() in text_corpus:
            matched.append(intent.audience)
        if intent.location.city and intent.location.city.lower() in text_corpus:
            matched.append(intent.location.city)
        if intent.location.country and intent.location.country.lower() in text_corpus:
            matched.append(intent.location.country)

        record = EvidenceRecord(
            source_url=candidate.url,
            platform=candidate.platform,
            snippet=candidate.bio_snippet,
            matched_keywords=matched
        )

        name_key = candidate.name.lower().strip()
        if name_key not in self._trails:
            self._trails[name_key] = EvidenceTrail(prospect_name=candidate.name)
        self._trails[name_key].records.append(record)

        return record

    def get_trail_for_prospect(self, prospect_name: str) -> Optional[EvidenceTrail]:
        return self._trails.get(prospect_name.lower().strip())

    def clear(self):
        self._trails.clear()


evidence_service = EvidenceService()
