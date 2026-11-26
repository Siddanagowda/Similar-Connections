"""
Unit tests for IdentityService: multi-factor identity resolution and false-positive prevention.
"""
import pytest
from app.services.identity_service import identity_service
from app.schemas import RawProfileCandidate


def test_geographic_conflict_prevents_merge():
    # Two people with exact same name in different countries must NEVER merge
    c1 = RawProfileCandidate(
        platform="LinkedIn",
        url="https://www.linkedin.com/in/john-smith-ny",
        name="John Smith",
        location="New York, USA",
        bio_snippet="Marketing director in New York"
    )
    c2 = RawProfileCandidate(
        platform="X",
        url="https://x.com/johnsmith_uk",
        name="John Smith",
        location="London, UK",
        bio_snippet="Digital strategist in London"
    )

    is_match, conf = identity_service.is_same_entity(c1, c2)
    assert is_match is False
    assert conf == 0.0


def test_shared_verified_contact_triggers_merge():
    # Candidates with shared verified email are 100% the same entity
    c1 = RawProfileCandidate(
        platform="LinkedIn",
        url="https://www.linkedin.com/in/jason-wright",
        name="Jason Wright",
        location="Washington DC, USA",
        bio_snippet="NFL player and Washington football executive",
        emails=["contact@jasonwrightdc.com"]
    )
    c2 = RawProfileCandidate(
        platform="X",
        url="https://x.com/whoisjwright",
        name="Jason Wright",
        location="Washington DC, USA",
        bio_snippet="Business executive",
        emails=["contact@jasonwrightdc.com"]
    )

    is_match, conf = identity_service.is_same_entity(c1, c2)
    assert is_match is True
    assert conf == 1.0


def test_matching_cross_platform_handles_trigger_merge():
    # Same handle across X and Instagram with high name similarity
    c1 = RawProfileCandidate(
        platform="X",
        url="https://x.com/garyvee",
        name="Gary Vaynerchuk",
        location="New York, USA",
        bio_snippet="CEO of VaynerMedia"
    )
    c2 = RawProfileCandidate(
        platform="Instagram",
        url="https://www.instagram.com/garyvee",
        name="Gary Vaynerchuk",
        location="New York, USA",
        bio_snippet="Chairman of VaynerX"
    )

    is_match, conf = identity_service.is_same_entity(c1, c2)
    assert is_match is True
    assert conf >= 0.90


def test_common_names_without_corroborating_evidence_do_not_merge():
    # John Smith without matching location or handle
    c1 = RawProfileCandidate(
        platform="LinkedIn",
        url="https://www.linkedin.com/in/john-smith-1",
        name="John Smith",
        location=None,
        bio_snippet="Software developer"
    )
    c2 = RawProfileCandidate(
        platform="X",
        url="https://x.com/jsmith99",
        name="John Smith",
        location=None,
        bio_snippet="Football fan"
    )

    is_match, conf = identity_service.is_same_entity(c1, c2)
    assert is_match is False
