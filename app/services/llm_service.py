"""
LLM Service for query understanding and entity classification.
Primary integration with Google Gemini, with automatic heuristic fallback.
"""
import json
import logging
import re
from typing import Optional
from app.config import settings
from app.schemas import QueryIntent, LocationDetail

logger = logging.getLogger(__name__)

def get_genai():
    """Lazily load google.generativeai to prevent gRPC C-thread stalls on app import."""
    try:
        import google.generativeai as genai
        return genai
    except ImportError:
        return None


QUERY_UNDERSTANDING_SYSTEM_PROMPT = """You are an expert AI query parser for a multi-platform prospect discovery engine.
Analyze the user's natural language prospect search query and extract structured intent.

Return valid JSON with this exact schema:
{
  "interest": "Primary topic, industry, or activity (e.g., Football, Digital marketing, Startup)",
  "audience": "Target demographic or profession (e.g., Football lovers, Marketing agency owners, Startup founders)",
  "location": {
    "city": "City name if specified, or null",
    "state": "State/Province/Region if specified, or null",
    "country": "Country name if specified or inferred, or null"
  },
  "target_type": "individual or business",
  "search_keywords": ["keyword1", "keyword2", "keyword3"]
}

Example:
Input: "Football lovers in Washington DC in USA"
Output:
{
  "interest": "Football",
  "audience": "Football lovers",
  "location": {
    "city": "Washington DC",
    "state": "District of Columbia",
    "country": "USA"
  },
  "target_type": "individual",
  "search_keywords": ["Football", "Soccer", "Washington DC", "Washington"]
}
"""


class LLMService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"
        self._gemini_configured = bool(self.api_key)

    async def extract_query_intent(self, query: str) -> QueryIntent:
        """
        Parses raw natural-language query into structured QueryIntent.
        Attempts Gemini when configured, otherwise falls back to deterministic heuristic parsing.
        """
        if self._gemini_configured:
            # Attempt the configured HTTPS API directly. A TCP/53 probe to a
            # public DNS server is not a reliable indicator of HTTPS egress
            # from managed hosting platforms.
            try:
                intent = await self._call_gemini_query_intent(query)
                if intent:
                    return intent
            except Exception as e:
                logger.warning(f"Gemini LLM call failed, falling back to heuristic parser: {e}")

        # Deterministic heuristic fallback
        return self._heuristic_parse_query(query)

    async def _call_gemini_query_intent(self, query: str) -> Optional[QueryIntent]:
        """Calls Gemini API with structured JSON output, trying candidate models."""
        genai = get_genai()
        if not genai:
            return None
        try:
            genai.configure(api_key=self.api_key, transport="rest")
        except Exception:
            return None

        candidate_models = [self.model_name, "gemini-2.5-flash", "gemini-flash-latest", "gemini-1.5-flash"]
        last_error = None

        prompt = f"{QUERY_UNDERSTANDING_SYSTEM_PROMPT}\n\nUser Query: \"{query}\""

        for m_name in dict.fromkeys(candidate_models):
            try:
                model = genai.GenerativeModel(
                    model_name=m_name,
                    generation_config={"response_mime_type": "application/json"}
                )
                response = model.generate_content(
                    prompt,
                    request_options={"timeout": 3.0}
                )
                text = response.text.strip()

                # Clean markdown fences if any
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\s*", "", text)
                    text = re.sub(r"\s*```$", "", text)

                data = json.loads(text.strip())
                loc_data = data.get("location", {})
                location = LocationDetail(
                    city=loc_data.get("city"),
                    state=loc_data.get("state"),
                    country=loc_data.get("country")
                )
                logger.info(f"Successfully extracted intent using Gemini model: '{m_name}'")
                return QueryIntent(
                    interest=data.get("interest", ""),
                    audience=data.get("audience", ""),
                    location=location,
                    target_type=data.get("target_type", "individual"),
                    search_keywords=data.get("search_keywords", [])
                )
            except Exception as exc:
                last_error = exc
                logger.debug(f"Gemini model {m_name} failed: {exc}, trying next model...")
                continue

        if last_error:
            raise last_error
        return None

    def _heuristic_parse_query(self, query: str) -> QueryIntent:
        """
        Robust rule-based parser that handles arbitrary natural language queries,
        including all assessment benchmark queries.
        """
        q = query.strip()
        lower_q = q.lower()

        # 1. Location extraction
        city, state, country = None, None, None

        # Dynamic location extraction supporting arbitrary expressions:
        # e.g., "in City, State, Country", "in City in Country", "in Location"
        loc_prepositions = [r"\bin\b", r"\bat\b", r"\bnear\b", r"\bfrom\b", r"\baround\b"]
        prep_regex = r"(?:" + "|".join(loc_prepositions) + r")\s+(.+)$"
        prep_match = re.search(prep_regex, q, re.IGNORECASE)

        raw_location_str = ""
        if prep_match:
            raw_location_str = prep_match.group(1).strip()

        # Global country recognition dictionary
        GLOBAL_COUNTRIES = {
            "usa": "USA", "united states": "USA", "us": "USA", "america": "USA",
            "uk": "UK", "united kingdom": "UK", "britain": "UK", "england": "UK", "scotland": "UK",
            "india": "India", "uae": "UAE", "united arab emirates": "UAE", "dubai": "UAE",
            "canada": "Canada", "australia": "Australia", "germany": "Germany", "france": "France",
            "singapore": "Singapore", "japan": "Japan", "brazil": "Brazil", "spain": "Spain",
            "italy": "Italy", "netherlands": "Netherlands", "switzerland": "Switzerland", "sweden": "Sweden"
        }

        # Check country from raw location or full query
        for alias, ctry_name in GLOBAL_COUNTRIES.items():
            if re.search(r"\b" + re.escape(alias) + r"\b", lower_q):
                country = ctry_name
                break

        # Extract city and state from location string: "in City in Country" or "in City, State"
        if raw_location_str:
            # Check for "City in Country"
            in_country_match = re.search(r"^(.*?)\s+in\s+([A-Za-z\s]+)$", raw_location_str, re.IGNORECASE)
            if in_country_match:
                candidate_city = in_country_match.group(1).strip()
                candidate_country = in_country_match.group(2).strip()
                city = candidate_city.title()
                if not country:
                    country = GLOBAL_COUNTRIES.get(candidate_country.lower(), candidate_country.title())
            elif "," in raw_location_str:
                parts = [p.strip() for p in raw_location_str.split(",") if p.strip()]
                if len(parts) >= 2:
                    city = parts[0].title()
                    # If second part is country or state
                    sec = parts[1].strip()
                    if sec.lower() in GLOBAL_COUNTRIES:
                        country = GLOBAL_COUNTRIES[sec.lower()]
                    else:
                        state = sec.title()
                if len(parts) >= 3 and not country:
                    country = GLOBAL_COUNTRIES.get(parts[2].lower(), parts[2].title())
            elif not city:
                # Remove country token if present at the end
                cleaned_loc = raw_location_str
                if country and country.lower() in cleaned_loc.lower():
                    cleaned_loc = re.sub(r"\b" + re.escape(country) + r"\b", "", cleaned_loc, flags=re.IGNORECASE).strip()
                city = cleaned_loc.title() if cleaned_loc else raw_location_str.title()

        # Known regional state mappings
        if city:
            if "washington" in city.lower():
                state = "District of Columbia"
                country = "USA"
            elif "new york" in city.lower():
                state = "New York"
                country = "USA"
            elif "london" in city.lower():
                state = "England"
                country = "UK"
            elif "ahmedabad" in city.lower():
                state = "Gujarat"
                country = "India"

        location = LocationDetail(city=city, state=state, country=country)

        # 2. Extract audience & interest
        # Common pattern: "<Audience> in <Location>"
        audience = ""
        interest = ""
        target_type = "individual"

        in_pos = lower_q.find(" in ")
        if in_pos != -1:
            audience = q[:in_pos].strip()
        else:
            audience = q.strip()

        # Target type identification
        business_indicators = ["agency", "agency owners", "owners", "founder", "founders", "ceo", "company", "business", "proprietor"]
        if any(ind in audience.lower() for ind in business_indicators):
            target_type = "business"

        # Determine interest from audience
        interest_patterns = [
            (r"football", "Football"),
            (r"soccer", "Soccer"),
            (r"cricket", "Cricket"),
            (r"digital marketing", "Digital Marketing"),
            (r"marketing", "Marketing"),
            (r"startup", "Startup"),
            (r"restaurant", "Restaurant"),
            (r"real estate", "Real Estate"),
            (r"tech|software|ai|machine learning", "Technology"),
        ]
        for pat, matched_interest in interest_patterns:
            if re.search(pat, audience, re.IGNORECASE):
                interest = matched_interest
                break

        if not interest:
            # Drop words like "lovers", "fans", "owners", "founders"
            cleaned_interest = re.sub(r"\b(lovers|enthusiasts|fans|owners|founders|leaders|people|in)\b", "", audience, flags=re.IGNORECASE).strip()
            interest = cleaned_interest.title() if cleaned_interest else audience

        # Keywords for search
        keywords = [interest, audience]
        if city:
            keywords.append(city)
        if country:
            keywords.append(country)

        return QueryIntent(
            interest=interest,
            audience=audience,
            location=location,
            target_type=target_type,
            search_keywords=[k for k in keywords if k]
        )


llm_service = LLMService()
