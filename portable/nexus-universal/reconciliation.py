"""Conservative recovery after crashes or partial device pairing."""
from __future__ import annotations
from dataclasses import dataclass
from device_metadata import DeviceMetadata
from device_registry import DeviceRegistry
from device_recovery import restore_devices
from pairing_store import PairingStore
from session_tokens import SessionManager


@dataclass(frozen=True)
class RecoveryReport:
    restored: int
    missing_metadata: tuple[str, ...]
    stale_metadata_removed: int


def reconcile(pairing: PairingStore, metadata: DeviceMetadata,
              registry: DeviceRegistry, sessions: SessionManager) -> RecoveryReport:
    """Restore only devices with trusted metadata; never mark them online."""
    mapping = metadata.trusted_mapping()
    active_ids = {row[0] for row in pairing.db.execute(
        "SELECT id FROM devices WHERE revoked=0"
    )}
    missing = tuple(sorted(active_ids - set(mapping)))
    removed = metadata.delete_orphans()
    # Session tokens are process-local; ensure any caller-provided manager has
    # no live grants for an untrusted/unrestored device.
    for device_id in missing:
        sessions.revoke_device(device_id)
    restored = restore_devices(pairing, registry, mapping)
    return RecoveryReport(restored, missing, removed)
