"""
Profile extraction and contact consolidation service.
"""
from typing import List
from app.schemas import RawProfileCandidate, SocialLink
from app.utils.validators import (
    validate_and_normalize_email,
    validate_and_normalize_phone,
    validate_and_normalize_whatsapp
)


class ProfileExtractor:
    def format_social_links(self, candidate: RawProfileCandidate) -> List[SocialLink]:
        """
        Extracts and converts all candidate profiles, emails, and phone/WhatsApp contacts
        into the required List[SocialLink] schema.
        Rule 6: "Email and phone information must also be included inside the social_link array."
        """
        links: List[SocialLink] = []
        seen_links = set()

        # 1. Main profile URL
        if candidate.url and candidate.url not in seen_links:
            links.append(SocialLink(platform=candidate.platform, link=candidate.url))
            seen_links.add(candidate.url)

        # 2. Email contacts formatted with mailto:
        for em in candidate.emails:
            norm_em = validate_and_normalize_email(em)
            if norm_em:
                mailto_link = f"mailto:{norm_em}"
                if mailto_link not in seen_links:
                    links.append(SocialLink(platform="Email", link=mailto_link))
                    seen_links.add(mailto_link)

        # 3. WhatsApp contact links
        for wa in candidate.whatsapp_links:
            norm_wa = validate_and_normalize_whatsapp(wa)
            if norm_wa and norm_wa not in seen_links:
                links.append(SocialLink(platform="WhatsApp", link=norm_wa))
                seen_links.add(norm_wa)

        # 4. Standalone Phone numbers formatted with tel:
        for ph in candidate.phones:
            norm_ph = validate_and_normalize_phone(ph)
            if norm_ph:
                tel_link = f"tel:{norm_ph}"
                # If no WhatsApp link exists yet, also offer WhatsApp
                wa_candidate = f"https://wa.me/{norm_ph.lstrip('+')}"
                if wa_candidate not in seen_links and not candidate.whatsapp_links:
                    links.append(SocialLink(platform="WhatsApp", link=wa_candidate))
                    seen_links.add(wa_candidate)
                elif tel_link not in seen_links:
                    links.append(SocialLink(platform="Phone", link=tel_link))
                    seen_links.add(tel_link)

        return links


profile_extractor = ProfileExtractor()
