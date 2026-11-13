"""Conservative, offline Turkish/English intent parser.

Parsing text does NOT authorize actions. The secure dispatcher and device OS
must separately enforce pairing, scopes, confirmation and actual capabilities.
No microphone access, speech recognition or paid AI calls occur here.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class VoiceIntent:
    action: str
    params: dict
    requires_confirmation: bool


def _normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


_SIMPLE = {
    "duraklat": "media.pause",
    "pause": "media.pause",
    "oynat": "media.play",
    "play": "media.play",
    "durdur": "media.stop",
    "stop": "media.stop",
    "geri": "display.back",
    "back": "display.back",
    "ana ekran": "display.home",
    "home": "display.home",
    "durum": "status.read",
    "status": "status.read",
}


def parse_intent(text: str) -> VoiceIntent | None:
    if not isinstance(text, str) or len(text) > 256:
        return None
    normalized = _normalize(text)
    action = _SIMPLE.get(normalized)
    if action:
        return VoiceIntent(action, {}, action != "status.read")
    match = re.fullmatch(r"(?:ses|volume)\s+(\d{1,3})", normalized)
    if match:
        level = int(match.group(1))
        if 0 <= level <= 100:
            return VoiceIntent("media.volume", {"level": level}, True)
    return None
