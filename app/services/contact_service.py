"""
Contact discovery and verification service.
Extracts, validates, and standardizes publicly published emails, phone numbers, and WhatsApp links.
Strictly disallows guessed or fabricated contact information.
"""
import re
from typing import List, Optional, Tuple
from app.schemas import SocialLink, RawProfileCandidate
from app.utils.validators import (
    validate_and_normalize_email,
    validate_and_normalize_phone,
    validate_and_normalize_whatsapp
)

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
WHATSAPP_LINK_REGEX = re.compile(r"(?:https?://)?(?:wa\.me/|api\.whatsapp\.com/send\?phone=)(\+?\d+)", re.IGNORECASE)


class ContactService:
    def extract_contacts_from_text(
        self, text: str, default_region: Optional[str] = "US"
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Extracts validated emails, phones, and whatsapp links directly from public text/snippet.
        Returns (emails, phones, whatsapp_links).
        """
        if not text:
            return [], [], []

        emails: List[str] = []
        for raw_email in EMAIL_REGEX.findall(text):
            norm_em = validate_and_normalize_email(raw_email)
            if norm_em and norm_em not in emails:
                emails.append(norm_em)

        phones: List[str] = []
        for raw_phone in PHONE_REGEX.findall(text):
            norm_ph = validate_and_normalize_phone(raw_phone, default_region=default_region)
            if norm_ph and norm_ph not in phones:
                phones.append(norm_ph)

        whatsapp_links: List[str] = []
        for raw_wa in WHATSAPP_LINK_REGEX.findall(text):
            norm_wa = validate_and_normalize_whatsapp(raw_wa, default_region=default_region)
            if norm_wa and norm_wa not in whatsapp_links:
                whatsapp_links.append(norm_wa)

        return emails, phones, whatsapp_links

    def create_social_contact_links(
        self,
        emails: List[str],
        phones: List[str],
        whatsapp_links: List[str]
    ) -> List[SocialLink]:
        """
        Converts verified contacts into SocialLink format per Rule 6:
        - Email -> mailto:<email>
        - WhatsApp -> https://wa.me/<digits>
        - Phone -> tel:<e164>
        """
        links: List[SocialLink] = []
        seen = set()

        for em in emails:
            norm = validate_and_normalize_email(em)
            if norm:
                item = f"mailto:{norm}"
                if item not in seen:
                    links.append(SocialLink(platform="Email", link=item))
                    seen.add(item)

        for wa in whatsapp_links:
            norm_wa = validate_and_normalize_whatsapp(wa)
            if norm_wa:
                if norm_wa not in seen:
                    links.append(SocialLink(platform="WhatsApp", link=norm_wa))
                    seen.add(norm_wa)

        for ph in phones:
            norm_ph = validate_and_normalize_phone(ph)
            if norm_ph:
                # If WhatsApp isn't present, make a WhatsApp link from mobile number
                wa_link = f"https://wa.me/{norm_ph.lstrip('+')}"
                if wa_link not in seen and not whatsapp_links:
                    links.append(SocialLink(platform="WhatsApp", link=wa_link))
                    seen.add(wa_link)
                tel_link = f"tel:{norm_ph}"
                if tel_link not in seen:
                    links.append(SocialLink(platform="Phone", link=tel_link))
                    seen.add(tel_link)

        return links


contact_service = ContactService()
