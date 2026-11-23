"""
LinkedIn Platform Adapter.
Discovers verified public LinkedIn member and organization profiles.
"""
from typing import List
from app.platforms.base import BasePlatformAdapter
from app.schemas import QueryIntent


class LinkedInAdapter(BasePlatformAdapter):

    @property
    def platform_name(self) -> str:
        return "LinkedIn"

    def generate_search_queries(self, intent: QueryIntent) -> List[str]:
        queries = []
        loc = intent.location.to_formatted_string() or ""
        audience = intent.audience or intent.interest

        # 1. Individual profile dork
        if loc:
            queries.append(f'site:linkedin.com/in "{audience}" "{loc}"')
            if intent.location.city:
                queries.append(f'site:linkedin.com/in "{intent.interest}" "{intent.location.city}"')
        else:
            queries.append(f'site:linkedin.com/in "{audience}"')

        # 2. Company/organization profile dork if business target
        if intent.target_type == "business" or "agency" in audience.lower() or "owner" in audience.lower():
            if loc:
                queries.append(f'site:linkedin.com/company "{audience}" "{loc}"')
            else:
                queries.append(f'site:linkedin.com/company "{audience}"')

        return queries
