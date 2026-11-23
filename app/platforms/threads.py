"""
Threads Platform Adapter.
Discovers verified public Threads profiles.
"""
from typing import List
from app.platforms.base import BasePlatformAdapter
from app.schemas import QueryIntent


class ThreadsAdapter(BasePlatformAdapter):

    @property
    def platform_name(self) -> str:
        return "Threads"

    def generate_search_queries(self, intent: QueryIntent) -> List[str]:
        queries = []
        loc = intent.location.city or intent.location.to_formatted_string() or ""
        audience = intent.audience or intent.interest

        if loc:
            queries.append(f'site:threads.net/@ "{audience}" "{loc}"')
        else:
            queries.append(f'site:threads.net/@ "{audience}"')
        return queries
