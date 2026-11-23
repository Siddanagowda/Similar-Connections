"""
Unit tests for name cleaning, identity resolution, and deduplication.
"""
import pytest
from app.utils.normalizers import clean_prospect_name, extract_username_from_url
from app.services.deduplication_service import deduplication_service
from app.schemas import RawProfileCandidate


def test_clean_prospect_name():
    # Suffix stripping
    assert clean_prospect_name("Gary Vaynerchuk | LinkedIn") == "Gary Vaynerchuk"
    assert clean_prospect_name("Jason Wright - President & CEO - Washington Football") == "Jason Wright"
    assert clean_prospect_name("Hardik Pandya (@hardikpandya93) • Instagram photos") == "Hardik Pandya"
    assert clean_prospect_name("Neil Patel - YouTube") == "Neil Patel"
    assert clean_prospect_name("Vineet Bhatia - Home | Facebook") == "Vineet Bhatia"
    assert clean_prospect_name("Dan Snyder on X: \"Excited for the game\"") == "Dan Snyder"


def test_extract_username_from_url():
    assert extract_username_from_url("LinkedIn", "https://www.linkedin.com/in/jason-wright") == "jason-wright"
    assert extract_username_from_url("X", "https://x.com/whoisjwright") == "whoisjwright"
    assert extract_username_from_url("Instagram", "https://instagram.com/whoisjwright") == "whoisjwright"
    assert extract_username_from_url("YouTube", "https://youtube.com/@garyvee") == "garyvee"
    assert extract_username_from_url("Threads", "https://threads.net/@garyvee") == "garyvee"


def test_deduplication_merges_same_entity():
    # Two candidates representing the same person across platforms
    c1 = RawProfileCandidate(
        platform="LinkedIn",
        url="https://www.linkedin.com/in/jason-wright",
        name="Jason Wright",
        location="Washington DC, USA",
        bio_snippet="NFL player and Washington football executive",
        emails=["contact@jasonwrightdc.com"],
        phones=["+12025550184"],
        whatsapp_links=["https://wa.me/12025550184"]
    )
    c2 = RawProfileCandidate(
        platform="X",
        url="https://x.com/whoisjwright",
        name="Jason Wright | NFL",
        location="Washington DC, USA",
        bio_snippet="Former Washington football president",
        emails=[],
        phones=[],
        whatsapp_links=[]
    )

    prospects = deduplication_service.consolidate_candidates([c1, c2])

    assert len(prospects) == 1
    prospect = prospects[0]
    assert prospect.name == "Jason Wright"
    assert prospect.location == "Washington DC, USA"

    # Social links should contain LinkedIn, X, Email, and WhatsApp
    platforms = [sl.platform for sl in prospect.social_link]
    assert "LinkedIn" in platforms
    assert "X" in platforms
    assert "Email" in platforms
    assert "WhatsApp" in platforms


def test_deduplication_keeps_distinct_people_separate():
    c1 = RawProfileCandidate(
        platform="LinkedIn",
        url="https://www.linkedin.com/in/jason-wright-dc",
        name="Jason Wright",
        location="Washington DC, USA",
        bio_snippet="Washington DC football"
    )
    c2 = RawProfileCandidate(
        platform="LinkedIn",
        url="https://www.linkedin.com/in/gary-vaynerchuk-ny",
        name="Gary Vaynerchuk",
        location="New York, USA",
        bio_snippet="Marketing agency owner"
    )

    prospects = deduplication_service.consolidate_candidates([c1, c2])
    assert len(prospects) == 2
    names = {p.name for p in prospects}
    assert "Jason Wright" in names
    assert "Gary Vaynerchuk" in names
