from app.schemas import LocationDetail, QueryIntent, RawProfileCandidate
from app.services.relevance_service import RelevanceService


def football_dc_intent():
    return QueryIntent(
        interest="Football",
        audience="Football lovers",
        location=LocationDetail(
            city="Washington DC",
            state="District of Columbia",
            country="USA"
        ),
        search_keywords=["Football", "Football lovers", "Washington DC", "USA"]
    )


def candidate(name, url, location, snippet):
    return RawProfileCandidate(
        platform="LinkedIn",
        url=url,
        name=name,
        location=location,
        bio_snippet=snippet
    )


def test_accepts_local_person_with_explicit_football_fan_evidence():
    relevance = RelevanceService(threshold=0.35)
    person = candidate(
        "Rich Daniel",
        "https://www.linkedin.com/in/rich-daniel-89936b2",
        None,
        "Silver Spring Maryland. D.C. Divas Football. A true fan of the game."
    )

    assert relevance.score_candidate(person, football_dc_intent()) >= 0.35


def test_rejects_person_with_football_role_but_no_fan_evidence():
    relevance = RelevanceService(threshold=0.35)
    coach = candidate(
        "Ramal Faunteroy",
        "https://www.linkedin.com/in/ramal-faunteroy-33565071",
        "USA",
        "Defensive line football coach based in the DMV."
    )

    assert relevance.score_candidate(coach, football_dc_intent()) == 0.0


def test_rejects_profile_from_other_country_even_if_football_fan():
    relevance = RelevanceService(threshold=0.35)
    profile = candidate(
        "Mario Coker",
        "https://uk.linkedin.com/in/mario-coker-82abb1198",
        "London, England, UK",
        "Football fan and enthusiast based in London, UK."
    )

    assert relevance.score_candidate(profile, football_dc_intent()) == 0.0


def test_rejects_country_only_evidence_when_city_was_requested():
    relevance = RelevanceService(threshold=0.35)
    profile = candidate(
        "Peter Sellers",
        "https://bh.linkedin.com/in/petersellers",
        "USA",
        "Football fan and enthusiast."
    )

    assert relevance.score_candidate(profile, football_dc_intent()) == 0.0
