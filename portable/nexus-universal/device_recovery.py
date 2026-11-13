"""Fail-closed restoration of paired devices from the persistent credential DB.

Rehydration does not mark devices online or assign control capabilities.
Only verified platform adapters may advertise executable actions.
"""
from __future__ import annotations
import re
from device_registry import Device, DeviceRegistry
from pairing_store import PairingStore

PLATFORMS = frozenset({"windows", "linux", "macos", "android", "android_tv",
                       "tizen", "webos", "ios", "generic_projector"})


def restore_devices(pairing: PairingStore, registry: DeviceRegistry,
                    platform_by_device: dict[str, str]) -> int:
    """Restore identity only, without trusting persisted runtime state."""
    restored = 0
    for device_id, platform in platform_by_device.items():
        if platform not in PLATFORMS:
            continue
        row = pairing.db.execute(
            "SELECT revoked FROM devices WHERE id=?", (device_id,)
        ).fetchone()
        if row is None or row[0]:
            continue
        if registry.get(device_id) is not None:
            continue
        registry.register(Device(device_id=device_id, platform=platform,
                                 capabilities=set(), paired=True,
                                 revoked=False, online=False))
        restored += 1
    return restored
