import pytest

from app.config import settings
from app.schemas import LocationDetail, QueryIntent, RawProfileCandidate
from app.services.search_service import SearchService


@pytest.mark.asyncio
async def test_search_waterfall_uses_live_fallback_without_api_keys(monkeypatch):
    service = SearchService()
    monkeypatch.setattr(settings, "TAVILY_API_KEY", None)
    monkeypatch.setattr(settings, "SERPAPI_API_KEY", None)

    async def fake_live_search(query, max_results=5):
        return [{"title": "Result", "url": "https://example.org/profile", "snippet": "startup founder"}]

    monkeypatch.setattr(service, "search_live_web", fake_live_search)

    results = await service.search_waterfall("startup founder London", max_results=5)

    assert len(results) == 1
    assert results[0]["title"] == "Result"


@pytest.mark.asyncio
async def test_adapter_tries_next_query_when_first_has_no_candidates(monkeypatch):
    service = SearchService()
    calls = []

    class DummyAdapter:
        platform_name = "LinkedIn"

        def extract_candidate(self, title, snippet, url, intent):
            if "linkedin.com/in/" not in url:
                return None
            return RawProfileCandidate(
                platform="LinkedIn",
                url=url,
                name=title,
                location="London, UK",
                bio_snippet=snippet
            )

    async def fake_search_waterfall(query, max_results=5):
        calls.append(query)
        if query == "first query":
            return []
        return [{
            "title": "Alex Founder",
            "url": "https://www.linkedin.com/in/alex-founder",
            "snippet": "Startup founder based in London"
        }]

    monkeypatch.setattr(service, "search_waterfall", fake_search_waterfall)

    intent = QueryIntent(
        interest="Startup",
        audience="Startup founders",
        location=LocationDetail(city="London", country="UK"),
        search_keywords=["Startup", "Startup founders"]
    )
    candidates = await service._search_and_extract(
        DummyAdapter(),
        ["first query", "second query"],
        intent
    )

    assert calls == ["first query", "second query"]
    assert len(candidates) == 1
    assert candidates[0].name == "Alex Founder"
