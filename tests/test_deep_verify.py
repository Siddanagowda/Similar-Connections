"""
Deep verification script testing edge cases, schema constraints, and arbitrary queries.
"""
import pytest
from app.schemas import ProspectDiscoveryRequest
from app.services.prospect_service import prospect_service


@pytest.mark.asyncio
async def test_all_benchmarks_and_edge_cases():
    benchmarks = [
        "Football lovers in Washington DC in USA",
        "Digital marketing agency owners in New York USA",
        "Startup founders in London UK",
        "Cricket lovers in Ahmedabad India",
        "Restaurant owners in Dubai UAE",
    ]
    arbitrary = [
        "AI researchers in San Francisco USA",
    ]

    for q in benchmarks:
        req = ProspectDiscoveryRequest(query=q)
        res = await prospect_service.discover_prospects(req)
        assert res.success is True
        assert res.query == q
        assert res.total_prospects == len(res.prospects)
        assert res.total_prospects >= 1

        for p in res.prospects:
            assert isinstance(p.name, str) and len(p.name) > 0
            assert isinstance(p.social_link, list)
            assert len(p.social_link) >= 1

            for sl in p.social_link:
                assert sl.platform in [
                    "Google", "LinkedIn", "X", "YouTube", "Instagram",
                    "WhatsApp", "Facebook", "Email", "Threads", "Phone"
                ]
                assert sl.link.startswith("http://") or sl.link.startswith("https://") or sl.link.startswith("mailto:") or sl.link.startswith("tel:")
                assert "google.com/search" not in sl.link

    for q in arbitrary:
        req = ProspectDiscoveryRequest(query=q)
        res = await prospect_service.discover_prospects(req)
        assert res.success is True
        assert res.query == q
        assert res.total_prospects == len(res.prospects)
        assert res.total_prospects >= 0

        for p in res.prospects:
            assert isinstance(p.name, str) and len(p.name) > 0
            assert isinstance(p.social_link, list)
            assert len(p.social_link) >= 1

            for sl in p.social_link:
                assert sl.platform in [
                    "Google", "LinkedIn", "X", "YouTube", "Instagram",
                    "WhatsApp", "Facebook", "Email", "Threads", "Phone"
                ]
                assert sl.link.startswith("http://") or sl.link.startswith("https://") or sl.link.startswith("mailto:") or sl.link.startswith("tel:")
                assert "google.com/search" not in sl.link


@pytest.mark.asyncio
async def test_whitespace_and_empty_queries():
    for empty in ["", "   ", "\t\n"]:
        req = ProspectDiscoveryRequest(query=empty)
        res = await prospect_service.discover_prospects(req)
        assert res.success is False
        assert res.total_prospects == 0
        assert res.prospects == []
