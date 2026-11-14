"""Official destinations and explicit commands for the embedded social panel."""

import re

SITES = {
    "instagram": ("Instagram", "https://www.instagram.com/", {"instagram.com", "www.instagram.com"}),
    "tiktok": ("TikTok", "https://www.tiktok.com/", {"tiktok.com", "www.tiktok.com"}),
    "whatsapp": ("WhatsApp", "https://web.whatsapp.com/", {"web.whatsapp.com"}),
}


def site_for_name(name: str) -> str | None:
    key = re.sub(r"[\s.'’\-]", "", name.replace("İ", "i").casefold())
    if key == "whatsab":
        key = "whatsapp"
    return key if key in SITES else None


def site_for_command(text: str) -> str | None:
    words = " ".join(text.strip().replace("İ", "i").casefold().split()).rstrip(".!")
    match = re.fullmatch(
        r"(instagram|tik\s*tok|whats\s*app|whatsab)(?:['’]?[ıiuü])?"
        r"(?: (?:ortada|jarvis'te|jarvis içinde))? aç",
        words,
    )
    return site_for_name(match[1]) if match else None
