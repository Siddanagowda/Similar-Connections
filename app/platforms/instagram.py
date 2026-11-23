"""
Instagram Platform Adapter.
Discovers verified public Instagram profiles.
"""
from typing import List
from app.platforms.base import BasePlatformAdapter
from app.schemas import QueryIntent


class InstagramAdapter(BasePlatformAdapter):

    @property
    def platform_name(self) -> str:
        return "Instagram"

    def generate_search_queries(self, intent: QueryIntent) -> List[str]:
        queries = []
        loc = intent.location.city or intent.location.to_formatted_string() or ""
        audience = intent.audience or intent.interest

        if loc:
            queries.append(f'site:instagram.com "{audience}" "{loc}" -inurl:p -inurl:reel -inurl:explore')
        else:
            queries.append(f'site:instagram.com "{audience}" -inurl:p -inurl:reel -inurl:explore')
        return queries
