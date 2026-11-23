"""
X (Twitter) Platform Adapter.
Discovers verified public X profiles and handles.
"""
from typing import List
from app.platforms.base import BasePlatformAdapter
from app.schemas import QueryIntent


class XAdapter(BasePlatformAdapter):

    @property
    def platform_name(self) -> str:
        return "X"

    def generate_search_queries(self, intent: QueryIntent) -> List[str]:
        queries = []
        loc = intent.location.city or intent.location.to_formatted_string() or ""
        interest = intent.interest or intent.audience

        if loc:
            queries.append(f'site:x.com "{interest}" "{loc}" -inurl:status')
            queries.append(f'site:twitter.com "{interest}" "{loc}" -inurl:status')
        else:
            queries.append(f'site:x.com "{interest}" -inurl:status')
        return queries
