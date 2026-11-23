"""
WhatsApp Platform Adapter.
Discovers verified public WhatsApp direct contact links (https://wa.me/...).
"""
from typing import List
from app.platforms.base import BasePlatformAdapter
from app.schemas import QueryIntent


class WhatsAppAdapter(BasePlatformAdapter):

    @property
    def platform_name(self) -> str:
        return "WhatsApp"

    def generate_search_queries(self, intent: QueryIntent) -> List[str]:
        queries = []
        loc = intent.location.city or intent.location.to_formatted_string() or ""
        audience = intent.audience or intent.interest

        if loc:
            queries.append(f'"wa.me" "{audience}" "{loc}"')
        else:
            queries.append(f'"wa.me" "{audience}"')
        return queries

    def is_valid_url(self, url: str) -> bool:
        if not url:
            return False
        return "wa.me/" in url.lower() or "whatsapp.com/send" in url.lower()

    def normalize_url(self, url: str) -> str:
        from app.utils.validators import validate_and_normalize_whatsapp
        res = validate_and_normalize_whatsapp(url)
        return res if res else url
