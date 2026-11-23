"""
Prospect discovery master coordinator pipeline.
Coordinates query analysis, search, extraction, deduplication, and relevance scoring.
"""
import logging
from app.schemas import ProspectDiscoveryRequest, ProspectDiscoveryResponse
from app.services.query_service import query_service
from app.services.search_service import search_service
from app.services.relevance_service import relevance_service
from app.services.deduplication_service import deduplication_service

logger = logging.getLogger(__name__)


class ProspectService:
    async def discover_prospects(self, request: ProspectDiscoveryRequest) -> ProspectDiscoveryResponse:
        """
        Executes end-to-end prospect discovery workflow.
        """
        raw_query = request.query.strip()
        if not raw_query:
            return ProspectDiscoveryResponse(
                success=False,
                query=raw_query,
                total_prospects=0,
                prospects=[]
            )

        logger.info(f"Starting prospect discovery for query: '{raw_query}'")

        # 1. Natural Language Query Understanding
        intent = await query_service.analyze_query(raw_query)

        # 2. Multi-Platform Search & Profile Discovery
        raw_candidates = await search_service.discover_candidates(intent)

        # 3. Prospect Relevance Evaluation & Filtering
        filtered_candidates = relevance_service.filter_and_rank_candidates(raw_candidates, intent)

        # 4. Duplicate Detection & Cross-Platform Profile Consolidation
        consolidated_prospects = deduplication_service.consolidate_candidates(filtered_candidates)

        response = ProspectDiscoveryResponse(
            success=True,
            query=raw_query,
            total_prospects=len(consolidated_prospects),
            prospects=consolidated_prospects
        )

        logger.info(
            f"Discovery completed for '{raw_query}'. Found {response.total_prospects} consolidated prospects."
        )
        return response


prospect_service = ProspectService()
