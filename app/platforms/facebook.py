"""
Facebook Platform Adapter.
Discovers verified public Facebook profiles and community pages.
"""
from typing import List
from app.platforms.base import BasePlatformAdapter
from app.schemas import QueryIntent


class FacebookAdapter(BasePlatformAdapter):

    @property
    def platform_name(self) -> str:
        return "Facebook"

    def generate_search_queries(self, intent: QueryIntent) -> List[str]:
        queries = []
        loc = intent.location.city or intent.location.to_formatted_string() or ""
        audience = intent.audience or intent.interest

        if loc:
            queries.append(f'site:facebook.com "{audience}" "{loc}" -inurl:events -inurl:groups')
        else:
            queries.append(f'site:facebook.com "{audience}" -inurl:events -inurl:groups')
        return queries
