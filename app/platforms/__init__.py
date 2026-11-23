"""
Platform adapter registry.
"""
from typing import Dict, List
from app.platforms.base import BasePlatformAdapter
from app.platforms.linkedin import LinkedInAdapter
from app.platforms.x_platform import XAdapter
from app.platforms.youtube import YouTubeAdapter
from app.platforms.instagram import InstagramAdapter
from app.platforms.facebook import FacebookAdapter
from app.platforms.threads import ThreadsAdapter
from app.platforms.whatsapp import WhatsAppAdapter
from app.platforms.google import GoogleDiscoveryAdapter


def get_all_platform_adapters() -> List[BasePlatformAdapter]:
    """Returns instances of all registered platform adapters."""
    return [
        LinkedInAdapter(),
        XAdapter(),
        YouTubeAdapter(),
        InstagramAdapter(),
        FacebookAdapter(),
        ThreadsAdapter(),
        WhatsAppAdapter(),
        GoogleDiscoveryAdapter(),
    ]


def get_adapter_by_name(name: str) -> BasePlatformAdapter:
    """Finds an adapter by platform name."""
    adapters = {a.platform_name.lower(): a for a in get_all_platform_adapters()}
    adapter = adapters.get(name.lower())
    if not adapter:
        raise ValueError(f"Unsupported platform: {name}")
    return adapter
