"""
Unit tests for ContactService: contact extraction, validation, and SocialLink formatting.
"""
import pytest
from app.services.contact_service import contact_service


def test_extract_contacts_from_text():
    text = (
        "Reach out at contact@vaynermedia.com or call +1 212-555-0192. "
        "Also available on WhatsApp at https://wa.me/12125550192 for direct messaging. "
        "Ignore dummy support@example.com and noreply@domain.com."
    )
    emails, phones, whatsapp_links = contact_service.extract_contacts_from_text(text, default_region="US")

    assert "contact@vaynermedia.com" in emails
    assert "support@example.com" not in emails  # filtered disallowed domain
    assert "+12125550192" in phones
    assert "https://wa.me/12125550192" in whatsapp_links


def test_create_social_contact_links():
    emails = ["contact@npdigital.com"]
    phones = ["+12025550199"]
    whatsapp = ["https://wa.me/12025550199"]

    links = contact_service.create_social_contact_links(emails, phones, whatsapp)
    platforms = [sl.platform for sl in links]
    urls = [sl.link for sl in links]

    assert "Email" in platforms
    assert "mailto:contact@npdigital.com" in urls
    assert "WhatsApp" in platforms
    assert "https://wa.me/12025550199" in urls
