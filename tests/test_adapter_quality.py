from app.platforms.base import BasePlatformAdapter
from app.platforms.x_platform import XAdapter
from app.schemas import LocationDetail, QueryIntent


def football_intent():
    return QueryIntent(
        interest="Football",
        audience="Football lovers",
        location=LocationDetail(city="Washington DC", state="District of Columbia", country="USA"),
        target_type="individual",
        search_keywords=["Football", "Football lovers", "Washington DC", "USA"]
    )


def test_x_individual_queries_include_person_oriented_phrases():
    queries = XAdapter().generate_search_queries(football_intent())

    assert any('"Football fan"' in query for query in queries)
    assert any('"Football enthusiast"' in query for query in queries)
    assert all("-inurl:status" in query for query in queries)


def test_candidate_location_is_not_copied_from_query_without_evidence():
    adapter = XAdapter()
    candidate = adapter.extract_candidate(
        title="Mike Engelberg",
        snippet="Enjoys watching football on weekends",
        url="https://x.com/frogfootball",
        intent=football_intent()
    )

    assert candidate is not None
    assert candidate.location is None


def test_country_evidence_does_not_infer_city():
    adapter = XAdapter()
    candidate = adapter.extract_candidate(
        title="Mike Engelberg",
        snippet="Football fan based in the USA",
        url="https://x.com/frogfootball",
        intent=football_intent()
    )

    assert candidate is not None
    assert candidate.location == "USA"
