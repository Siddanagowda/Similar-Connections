"""
X (Twitter) Platform Adapter.
Discovers public X profiles using person-oriented search phrases when the
query targets individuals.
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
        audience = intent.audience or interest

        if intent.target_type == "individual":
            # Avoid broad interest-only queries that commonly surface teams,
            # clubs, and organizations instead of individual people.
            person_phrases = []
            if audience:
                person_phrases.append(audience)
            if interest:
                person_phrases.extend([
                    f"{interest} fan",
                    f"{interest} enthusiast",
                    f"{interest} supporter"
                ])

            seen = set()
            for phrase in person_phrases:
                phrase_key = phrase.casefold()
                if phrase_key in seen:
                    continue
                seen.add(phrase_key)
                if loc:
                    queries.append(
                        f'site:x.com "{phrase}" "{loc}" -inurl:status '
                        f'-team -club -"official account"'
                    )
                else:
                    queries.append(
                        f'site:x.com "{phrase}" -inurl:status '
                        f'-team -club -"official account"'
                    )
            return queries

        if loc:
            queries.append(f'site:x.com "{interest}" "{loc}" -inurl:status')
            queries.append(f'site:twitter.com "{interest}" "{loc}" -inurl:status')
        else:
            queries.append(f'site:x.com "{interest}" -inurl:status')
        return queries
