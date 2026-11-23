"""
YouTube Platform Adapter.
Discovers verified public creator channels and profiles.
"""
from typing import List
from app.platforms.base import BasePlatformAdapter
from app.schemas import QueryIntent


class YouTubeAdapter(BasePlatformAdapter):

    @property
    def platform_name(self) -> str:
        return "YouTube"

    def generate_search_queries(self, intent: QueryIntent) -> List[str]:
        queries = []
        loc = intent.location.city or intent.location.to_formatted_string() or ""
        audience = intent.audience or intent.interest

        if loc:
            queries.append(f'site:youtube.com/@ "{audience}" "{loc}"')
            queries.append(f'site:youtube.com/channel "{audience}" "{loc}"')
        else:
            queries.append(f'site:youtube.com/@ "{audience}"')
        return queries
