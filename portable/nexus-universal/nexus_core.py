"""Portable, dependency-free capability negotiation for authorized JARVIS clients.

This module does not probe, exploit, install software or execute device commands.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import FrozenSet

KNOWN_CAPABILITIES = frozenset({"browser-ui", "wifi-connection"})
SUPPORTED_STATUSES = frozenset({"planned", "prototype", "source-only", "research"})


@dataclass(frozen=True)
class DeviceProfile:
    id: str
    name: str
    status: str
    capabilities: FrozenSet[str]
    usb_launch: str


@dataclass(frozen=True)
class Negotiation:
    platform: str
    available: FrozenSet[str]
    unavailable: FrozenSet[str]
    reason: str


def load_catalog(path: str | Path) -> dict[str, DeviceProfile]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1:
        raise ValueError("Unsupported catalog schema")
    profiles: dict[str, DeviceProfile] = {}
    for entry in raw["device_profiles"]:
        identifier = entry["id"]
        if not isinstance(identifier, str) or not identifier or identifier in profiles:
            raise ValueError("Invalid or duplicate device ID")
        capabilities = entry["capabilities"]
        if not isinstance(capabilities, list) or any(
            not isinstance(c, str) or c not in KNOWN_CAPABILITIES for c in capabilities
        ):
            raise ValueError("Unknown capability")
        if entry["status"] not in SUPPORTED_STATUSES:
            raise ValueError("Unknown status")
        profiles[identifier] = DeviceProfile(
            id=identifier, name=entry["name"], status=entry["status"],
            capabilities=frozenset(capabilities), usb_launch=entry["usb_launch"],
        )
    return profiles


def negotiate(
    profiles: dict[str, DeviceProfile],
    platform: str,
    requested: set[str],
    *,
    user_authorized: bool = False,
) -> Negotiation:
    """Return declared capabilities, never infer control rights from USB presence."""
    if not requested.issubset(KNOWN_CAPABILITIES):
        raise ValueError("Unknown requested capability")
    profile = profiles.get(platform)
    if profile is None:
        return Negotiation(platform, frozenset(), frozenset(requested), "Unknown platform")
    if not user_authorized:
        return Negotiation(platform, frozenset(), frozenset(requested), "User authorization required")
    # Catalog entries are design-level declarations. No feature is considered
    # operational until its platform implementation is verified.
    return Negotiation(
        platform, frozenset(), frozenset(requested),
        "Catalog is informational; platform integration not verified",
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Inspect NEXUS capabilities; no device control")
    parser.add_argument("--catalog", default=str(Path(__file__).with_name("capabilities.json")))
    parser.add_argument("--platform", required=True)
    args = parser.parse_args()
    catalog = load_catalog(args.catalog)
    profile = catalog.get(args.platform)
    print(json.dumps(
        {"platform": args.platform, "status": profile.status if profile else "unknown",
         "declared": sorted(profile.capabilities) if profile else [],
         "verified_operational": [], "auto_usb_execution": False},
        ensure_ascii=False, indent=2,
    ))
