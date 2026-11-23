"""
Query understanding and search query generation service.
"""
from typing import Dict, List
import logging
from app.schemas import QueryIntent
from app.services.llm_service import llm_service
from app.platforms import get_all_platform_adapters

logger = logging.getLogger(__name__)


class QueryService:
    def __init__(self):
        self.llm = llm_service
        self.adapters = get_all_platform_adapters()

    async def analyze_query(self, raw_query: str) -> QueryIntent:
        """
        Extracts structured search parameters from natural language query.
        """
        logger.info(f"Analyzing query: '{raw_query}'")
        intent = await self.llm.extract_query_intent(raw_query)
        logger.info(
            f"Extracted Intent -> Interest: '{intent.interest}', Audience: '{intent.audience}', "
            f"Location: '{intent.location.to_formatted_string()}', Target Type: '{intent.target_type}'"
        )
        return intent

    def generate_platform_queries(self, intent: QueryIntent) -> Dict[str, List[str]]:
        """
        Generates platform-specific search dorks across all supported platforms.
        """
        platform_queries: Dict[str, List[str]] = {}
        for adapter in self.adapters:
            queries = adapter.generate_search_queries(intent)
            platform_queries[adapter.platform_name] = queries
        return platform_queries


query_service = QueryService()
