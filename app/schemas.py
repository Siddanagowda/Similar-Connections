"""
Pydantic Schemas for Request, Response, and Internal Data Models.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


# -------------------------------------------------------------
# Public API Request & Response Schemas
# -------------------------------------------------------------

class ProspectDiscoveryRequest(BaseModel):
    query: str = Field(
        ...,
        description="Natural language query describing desired prospects, audience, and location.",
        examples=["Football lovers in Washington DC in USA"]
    )


class SocialLink(BaseModel):
    platform: str = Field(
        ...,
        description="Platform name, e.g., LinkedIn, X, YouTube, Instagram, Facebook, Threads, WhatsApp, Email, Google"
    )
    link: str = Field(
        ...,
        description="Verified public profile URL or validated contact link (e.g. mailto:..., https://wa.me/...)"
    )


class Prospect(BaseModel):
    name: str = Field(
        ...,
        description="Full name or business title of the discovered prospect"
    )
    location: Optional[str] = Field(
        default=None,
        description="Geographical location (e.g., City, State, Country)"
    )
    social_link: List[SocialLink] = Field(
        default_factory=list,
        description="List of verified public profile links and contact methods"
    )


class ProspectDiscoveryResponse(BaseModel):
    success: bool = Field(
        default=True,
        description="Indicates whether the request was processed successfully"
    )
    query: str = Field(
        ...,
        description="The original user search query"
    )
    total_prospects: int = Field(
        ...,
        description="Total number of unique prospects discovered and consolidated"
    )
    prospects: List[Prospect] = Field(
        default_factory=list,
        description="Consolidated list of matching prospects"
    )


# -------------------------------------------------------------
# Internal Pipeline Schemas
# -------------------------------------------------------------

class LocationDetail(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None

    def to_formatted_string(self) -> Optional[str]:
        parts = [p for p in [self.city, self.state, self.country] if p]
        return ", ".join(parts) if parts else None


class QueryIntent(BaseModel):
    interest: str = Field(default="", description="Core subject or interest, e.g., Football")
    audience: str = Field(default="", description="Target persona, e.g., Football lovers")
    location: LocationDetail = Field(default_factory=LocationDetail)
    target_type: str = Field(default="individual", description="'individual' or 'business'")
    search_keywords: List[str] = Field(default_factory=list)


class RawProfileCandidate(BaseModel):
    platform: str
    url: str
    name: str
    location: Optional[str] = None
    bio_snippet: str = ""
    emails: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    whatsapp_links: List[str] = Field(default_factory=list)
    relevance_score: float = 0.0
