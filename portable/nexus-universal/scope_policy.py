"""Central allowlisted command-to-scope policy, no wildcard privileges."""
from __future__ import annotations

from command_protocol import ACTIONS

ACTION_SCOPES = {
    "status.read": "status.read",
    "media.play": "media.control",
    "media.pause": "media.control",
    "media.stop": "media.control",
    "media.volume": "media.control",
    "display.open_url": "display.control",
    "display.back": "display.control",
    "display.home": "display.control",
}
if set(ACTION_SCOPES) != ACTIONS:
    raise RuntimeError("Scope mapping must cover every command action")


def required_scope(action: str) -> str:
    if action not in ACTION_SCOPES:
        raise ValueError("Action not allowlisted")
    return ACTION_SCOPES[action]
