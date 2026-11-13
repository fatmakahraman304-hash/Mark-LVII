"""Durable platform metadata linked to a paired credential.

Separate DBs cannot guarantee a cross-store atomic commit. Store metadata
in the SAME SQLite database as PairingStore and reconcile on startup.
"""
from __future__ import annotations
import sqlite3
from pairing_store import PairingStore
from platform_manifest import PLATFORMS


class DeviceMetadata:
    def __init__(self, pairing: PairingStore):
        self.pairing = pairing
        self.db = pairing.db
        self.db.execute("""CREATE TABLE IF NOT EXISTS device_metadata(
            device_id TEXT PRIMARY KEY REFERENCES devices(id) ON DELETE CASCADE,
            platform TEXT NOT NULL,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
        )""")

    def set_platform(self, device_id: str, platform: str) -> None:
        if platform not in PLATFORMS:
            raise ValueError("Unsupported platform")
        # PairingStore uses autocommit. Host must coordinate pairing and metadata
        # creation as one transaction in a future consolidated pairing operation.
        cursor = self.db.execute(
            "INSERT INTO device_metadata(device_id,platform) "
            "SELECT id,? FROM devices WHERE id=? AND revoked=0 "
            "ON CONFLICT(device_id) DO UPDATE SET platform=excluded.platform",
            (platform, device_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("Unknown or revoked device")

    def trusted_mapping(self) -> dict[str, str]:
        return dict(self.db.execute(
            "SELECT m.device_id,m.platform FROM device_metadata m "
            "JOIN devices d ON d.id=m.device_id WHERE d.revoked=0"
        ))

    def delete_orphans(self) -> int:
        cursor = self.db.execute(
            "DELETE FROM device_metadata WHERE device_id NOT IN "
            "(SELECT id FROM devices WHERE revoked=0)"
        )
        return cursor.rowcount
