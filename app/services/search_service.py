"""
Search service providing dynamic multi-source prospect discovery.
Provider waterfall:
Tavily API -> SerpAPI -> live DDGS search -> graceful empty response.

Searches are attempted directly with bounded timeouts. We do not use a
separate socket probe to decide whether outbound HTTPS search is available:
cloud hosts may block arbitrary DNS TCP probes while allowing HTTPS egress.
"""
import asyncio
import logging
from typing import List
import httpx

from app.config import settings
from app.schemas import QueryIntent, RawProfileCandidate
from app.platforms import get_all_platform_adapters, BasePlatformAdapter
from app.services.evidence_service import evidence_service

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self):
        self.adapters: List[BasePlatformAdapter] = get_all_platform_adapters()
        # Cloud-hosted search calls need more than a 1–2 second budget.
        self.timeout = max(8.0, float(settings.REQUEST_TIMEOUT_SECONDS))

    async def search_tavily(self, query: str, max_results: int = 5) -> List[dict]:
        """Tavily search API integration."""
        if not settings.TAVILY_API_KEY:
            return []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.TAVILY_API_KEY,
                        "query": query,
                        "max_results": max_results,
                        "search_depth": "basic"
                    }
                )
                res.raise_for_status()
                data = res.json()
                results = [
                    {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
                    for r in data.get("results", [])
                ]
                if results:
                    logger.info("Tavily returned %d results for query: %s", len(results), query)
                return results
        except Exception as exc:
            logger.warning("Tavily search failed for query '%s': %s", query, exc)
            return []

    async def search_serpapi(self, query: str, max_results: int = 5) -> List[dict]:
        """SerpAPI search integration."""
        if not settings.SERPAPI_API_KEY:
            return []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(
                    "https://serpapi.com/search.json",
                    params={
                        "api_key": settings.SERPAPI_API_KEY,
                        "q": query,
                        "num": max_results
                    }
                )
                res.raise_for_status()
                data = res.json()
                results = [
                    {"title": r.get("title", ""), "url": r.get("link", ""), "snippet": r.get("snippet", "")}
                    for r in data.get("organic_results", [])
                ]
                if results:
                    logger.info("SerpAPI returned %d results for query: %s", len(results), query)
                return results
        except Exception as exc:
            logger.warning("SerpAPI search failed for query '%s': %s", query, exc)
            return []

    async def search_live_web(self, query: str, max_results: int = 5) -> List[dict]:
        """Live web-search fallback through DDGS with a bounded timeout."""
        try:
            from ddgs import DDGS

            def _sync_query():
                try:
                    return list(DDGS(timeout=6.0).text(query, max_results=max_results))
                except Exception as exc:
                    logger.warning("DDGS search failed for query '%s': %s", query, exc)
                    return []

            loop = asyncio.get_running_loop()
            results = await asyncio.wait_for(
                loop.run_in_executor(None, _sync_query),
                timeout=7.0
            )
            parsed = [
                {
                    "title": item.get("title", ""),
                    "url": item.get("href", ""),
                    "snippet": item.get("body", "")
                }
                for item in results
            ]
            if parsed:
                logger.info("DDGS returned %d results for query: %s", len(parsed), query)
            return parsed
        except asyncio.TimeoutError:
            logger.warning("DDGS search timed out for query: %s", query)
            return []
        except Exception as exc:
            logger.warning("Live web search failed for query '%s': %s", query, exc)
            return []

    async def search_waterfall(self, query: str, max_results: int = 5) -> List[dict]:
        """
        Try configured search providers in order. Each provider is called directly;
        a failed provider falls through to the next one.
        """
        if settings.TAVILY_API_KEY:
            results = await self.search_tavily(query, max_results)
            if results:
                return results

        if settings.SERPAPI_API_KEY:
            results = await self.search_serpapi(query, max_results)
            if results:
                return results

        if not settings.TAVILY_API_KEY and not settings.SERPAPI_API_KEY:
            logger.warning(
                "No paid search provider is configured; using DDGS fallback. "
                "For reliable hosted discovery, configure TAVILY_API_KEY or SERPAPI_API_KEY."
            )
        results = await self.search_live_web(query, max_results)
        if not results:
            logger.warning("All configured search providers returned no results for query: %s", query)
        return results

    async def discover_candidates(self, intent: QueryIntent) -> List[RawProfileCandidate]:
        """
        Discover prospects across registered platform adapters.
        Try alternative query formulations when an adapter's first query yields
        no valid profile candidates.
        """
        candidates: List[RawProfileCandidate] = []
        search_tasks = []
        # Request-scoped limiter avoids overloading public search providers and
        # avoids binding a shared asyncio primitive to one pytest event loop.
        semaphore = asyncio.Semaphore(2)

        async def bounded_adapter_search(adapter, queries):
            async with semaphore:
                return await self._search_and_extract(adapter, queries, intent)

        for adapter in self.adapters:
            queries = adapter.generate_search_queries(intent)
            if queries:
                # Pass all generated alternatives; the adapter method will try
                # them sequentially and stop once enough candidates are collected.
                search_tasks.append(bounded_adapter_search(adapter, queries))

        results_by_adapter = await asyncio.gather(*search_tasks, return_exceptions=True)

        for adapter_result in results_by_adapter:
            if isinstance(adapter_result, Exception):
                logger.warning("A platform discovery task failed: %s", adapter_result)
                continue
            for candidate in adapter_result:
                evidence_service.record_evidence(candidate, intent)
                candidates.append(candidate)

        logger.info(
            "Discovery collected %d raw candidates across %d platform adapters",
            len(candidates),
            len(search_tasks)
        )
        return candidates

    async def _search_and_extract(
        self,
        adapter: BasePlatformAdapter,
        queries: List[str],
        intent: QueryIntent
    ) -> List[RawProfileCandidate]:
        """Try an adapter's query alternatives until candidates are found."""
        candidates: List[RawProfileCandidate] = []
        seen_urls = set()
        max_candidates = settings.MAX_SEARCH_RESULTS_PER_PLATFORM

        for query in queries:
            results = await self.search_waterfall(
                query,
                max_results=settings.MAX_SEARCH_RESULTS_PER_PLATFORM
            )
            logger.info(
                "%s search returned %d web results for query: %s",
                adapter.platform_name,
                len(results),
                query
            )

            for item in results:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                url = item.get("url", "")
                candidate = adapter.extract_candidate(title, snippet, url, intent)
                if candidate and candidate.url not in seen_urls:
                    candidates.append(candidate)
                    seen_urls.add(candidate.url)

            if len(candidates) >= max_candidates:
                break

            if candidates:
                # One query produced usable profiles. Avoid unnecessary requests
                # and search-provider rate limits.
                break

        logger.info(
            "%s adapter extracted %d valid profile candidates",
            adapter.platform_name,
            len(candidates)
        )
        return candidates


search_service = SearchService()
