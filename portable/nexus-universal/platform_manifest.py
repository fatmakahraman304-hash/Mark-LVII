"""Strict local platform adapter manifest; declarations never grant permissions."""
from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
from command_protocol import ACTIONS

PLATFORMS = frozenset({"windows", "linux", "macos", "android", "android_tv",
                       "tizen", "webos", "ios", "generic_projector"})


@dataclass(frozen=True)
class AdapterManifest:
    platform: str
    adapter_id: str
    actions: frozenset[str]
    requires_local_consent: bool


def load_manifest(path: str | Path) -> AdapterManifest:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != {
        "schema_version", "platform", "adapter_id", "actions", "requires_local_consent"
    }:
        raise ValueError("Invalid manifest shape")
    if type(raw["schema_version"]) is not int or raw["schema_version"] != 1:
        raise ValueError("Unsupported manifest version")
    if not isinstance(raw["platform"], str) or raw["platform"] not in PLATFORMS:
        raise ValueError("Unsupported platform")
    adapter_id = raw["adapter_id"]
    if not isinstance(adapter_id, str) or not 1 <= len(adapter_id) <= 80:
        raise ValueError("Invalid adapter ID")
    actions = raw["actions"]
    if (not isinstance(actions, list) or
        not all(isinstance(a, str) and a in ACTIONS for a in actions) or
        len(actions) != len(set(actions))):
        raise ValueError("Invalid action declarations")
    if type(raw["requires_local_consent"]) is not bool:
        raise ValueError("Invalid consent policy")
    if not raw["requires_local_consent"] and any(a != "status.read" for a in actions):
        raise ValueError("Mutating actions always require local consent")
    return AdapterManifest(raw["platform"], adapter_id, frozenset(actions),
                           raw["requires_local_consent"])


def verified_actions(manifest: AdapterManifest, *, platform_verified: bool,
                     user_granted: frozenset[str]) -> frozenset[str]:
    """A manifest alone never activates capabilities."""
    if platform_verified is not True:
        return frozenset()
    return manifest.actions.intersection(user_granted)
