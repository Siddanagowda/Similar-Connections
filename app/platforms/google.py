"""
Google Discovery Platform Adapter.
Serves as discovery source and extracts public web presences and personal domains.
Strictly excludes generic search result URLs (google.com/search) per Rule 79.
"""
from typing import List, Optional
from urllib.parse import urlparse
from app.platforms.base import BasePlatformAdapter
from app.schemas import QueryIntent, RawProfileCandidate


class GoogleDiscoveryAdapter(BasePlatformAdapter):

    @property
    def platform_name(self) -> str:
        return "Google"

    def generate_search_queries(self, intent: QueryIntent) -> List[str]:
        queries = []
        loc = intent.location.city or intent.location.to_formatted_string() or ""
        audience = intent.audience or intent.interest

        if loc:
            queries.append(f'"{audience}" "{loc}" (contact OR email OR founder OR owner)')
        else:
            queries.append(f'"{audience}" (contact OR email OR founder OR owner)')
        return queries

    def is_valid_url(self, url: str) -> bool:
        if not url:
            return False
        try:
            parsed = urlparse(url)
            # Never allow google search or accounts pages as prospect URLs
            if "google." in parsed.netloc.lower():
                return False
            # Exclude major social platforms (handled by dedicated adapters) and generic aggregators
            excluded_domains = [
                "linkedin.com", "x.com", "twitter.com", "instagram.com",
                "youtube.com", "facebook.com", "threads.net", "whatsapp.com",
                "meetup.com", "aeroleads.com", "wikipedia.org", "yelp.com",
                "tripadvisor.com", "yellowpages.com", "quora.com", "reddit.com"
            ]
            if any(dom in parsed.netloc.lower() for dom in excluded_domains):
                return False
            return bool(parsed.scheme in ("http", "https") and parsed.netloc)
        except Exception:
            return False

    def normalize_url(self, url: str) -> str:
        from app.utils.validators import clean_tracking_params
        return clean_tracking_params(url)
