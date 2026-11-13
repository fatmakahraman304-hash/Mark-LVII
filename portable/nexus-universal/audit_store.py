"""Tamper-evident append-only audit chain for NEXUS decisions.

Records contain metadata only; never tokens, secrets, prompts or raw URLs.
HMAC signing with an externally provisioned key is required for authenticity.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import re
import sqlite3
import time
from dataclasses import dataclass

SAFE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
EVENTS = frozenset({"pair.created", "pair.redeemed", "device.revoked",
                    "command.allowed", "command.denied", "device.connected",
                    "device.disconnected"})
ZERO = "0" * 64


class AuditError(ValueError):
    pass


@dataclass(frozen=True)
class AuditEntry:
    seq: int
    timestamp: int
    event: str
    device_id: str
    prev_mac: str
    mac: str


class AuditStore:
    def __init__(self, path: str, signing_key: bytes):
        if not isinstance(signing_key, bytes) or len(signing_key) < 32:
            raise AuditError("A separate secret audit key of at least 32 bytes is required")
        self.key = signing_key
        self.db = sqlite3.connect(path, isolation_level=None, timeout=10)
        self.db.execute("PRAGMA busy_timeout=10000")
        self.db.execute("""CREATE TABLE IF NOT EXISTS audit(
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            event TEXT NOT NULL,
            device_id TEXT NOT NULL,
            prev_mac TEXT NOT NULL,
            mac TEXT NOT NULL
        )""")

    def _mac(self, seq: int, ts: int, event: str, device: str, prev: str) -> str:
        payload = json.dumps([seq, ts, event, device, prev], separators=(",", ":"))
        return hmac.new(self.key, payload.encode(), hashlib.sha256).hexdigest()

    def append(self, event: str, device_id: str) -> AuditEntry:
        if event not in EVENTS or not isinstance(device_id, str) or not SAFE.fullmatch(device_id):
            raise AuditError("Invalid audit metadata")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute("SELECT seq,mac FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
            seq, prev = (row[0] + 1, row[1]) if row else (1, ZERO)
            ts = int(time.time())
            mac = self._mac(seq, ts, event, device_id, prev)
            self.db.execute("INSERT INTO audit(seq,timestamp,event,device_id,prev_mac,mac) VALUES(?,?,?,?,?,?)",
                            (seq, ts, event, device_id, prev, mac))
            self.db.execute("COMMIT")
            return AuditEntry(seq, ts, event, device_id, prev, mac)
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def verify(self) -> bool:
        prev, expected_seq = ZERO, 1
        for seq, ts, event, device, prev_mac, mac in self.db.execute(
            "SELECT seq,timestamp,event,device_id,prev_mac,mac FROM audit ORDER BY seq"
        ):
            if seq != expected_seq or not hmac.compare_digest(prev, prev_mac):
                return False
            if not hmac.compare_digest(self._mac(seq, ts, event, device, prev), mac):
                return False
            prev = mac
            expected_seq += 1
        return True

    def close(self):
        self.db.close()
