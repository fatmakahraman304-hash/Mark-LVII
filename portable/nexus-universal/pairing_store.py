"""Local pairing credential store for JARVIS NEXUS.

No network endpoints. The caller MUST authenticate the owner and obtain explicit
on-device approval before invoking begin_pairing. Tokens are shown only once.
SQLite contains SHA-256 digests of high-entropy secrets, never raw credentials.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

DEVICE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
ALLOWED_SCOPES = frozenset({"status.read", "media.control", "display.control"})
PAIRING_TTL = 120
TOKEN_BYTES = 32


class PairingError(Exception):
    pass


@dataclass(frozen=True)
class PairingInvitation:
    invitation_id: str
    secret: str
    expires_at: int


@dataclass(frozen=True)
class DeviceCredential:
    device_id: str
    token: str
    scopes: frozenset[str]


class PairingStore:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.execute("PRAGMA busy_timeout = 10000")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS invitations(
                id TEXT PRIMARY KEY, secret_hash BLOB NOT NULL,
                expires_at INTEGER NOT NULL, consumed INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS devices(
                id TEXT PRIMARY KEY, token_hash BLOB NOT NULL,
                scopes TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL, last_seen INTEGER
            );
        """)

    @staticmethod
    def _digest(secret: str) -> bytes:
        return hashlib.sha256(secret.encode("ascii")).digest()

    def begin_pairing(self, *, owner_approved: bool) -> PairingInvitation:
        if owner_approved is not True:
            raise PermissionError("Explicit authenticated owner approval required")
        now = int(time.time())
        invitation_id = secrets.token_hex(16)
        secret = secrets.token_urlsafe(TOKEN_BYTES)
        self.db.execute("DELETE FROM invitations WHERE expires_at < ? OR consumed = 1", (now,))
        self.db.execute(
            "INSERT INTO invitations(id, secret_hash, expires_at) VALUES(?,?,?)",
            (invitation_id, self._digest(secret), now + PAIRING_TTL),
        )
        return PairingInvitation(invitation_id, secret, now + PAIRING_TTL)

    def redeem(self, invitation_id: str, secret: str, device_id: str,
               scopes: set[str] | frozenset[str]) -> DeviceCredential:
        if not DEVICE_ID.fullmatch(device_id):
            raise PairingError("Invalid device identifier")
        if not scopes or not set(scopes).issubset(ALLOWED_SCOPES):
            raise PairingError("Invalid scopes")
        if not isinstance(secret, str) or len(secret) > 256:
            raise PairingError("Invalid secret")
        now = int(time.time())
        token = secrets.token_urlsafe(TOKEN_BYTES)
        scope_text = ",".join(sorted(scopes))
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute(
                "SELECT secret_hash,expires_at,consumed FROM invitations WHERE id=?",
                (invitation_id,),
            ).fetchone()
            if (row is None or row[2] or row[1] < now or
                not hmac.compare_digest(row[0], self._digest(secret))):
                raise PairingError("Invalid or expired invitation")
            if self.db.execute("SELECT 1 FROM devices WHERE id=?", (device_id,)).fetchone():
                raise PairingError("Device ID already registered")
            self.db.execute(
                "INSERT INTO devices(id,token_hash,scopes,created_at) VALUES(?,?,?,?)",
                (device_id, self._digest(token), scope_text, now),
            )
            self.db.execute("UPDATE invitations SET consumed=1 WHERE id=?", (invitation_id,))
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return DeviceCredential(device_id, token, frozenset(scopes))

    def authenticate(self, device_id: str, token: str, required_scope: str) -> bool:
        if required_scope not in ALLOWED_SCOPES or not isinstance(token, str) or len(token) > 256:
            return False
        row = self.db.execute(
            "SELECT token_hash,scopes,revoked FROM devices WHERE id=?", (device_id,),
        ).fetchone()
        if not row or row[2] or required_scope not in row[1].split(","):
            return False
        if not hmac.compare_digest(row[0], self._digest(token)):
            return False
        self.db.execute("UPDATE devices SET last_seen=? WHERE id=?", (int(time.time()), device_id))
        return True

    def revoke(self, device_id: str, *, owner_approved: bool) -> bool:
        if owner_approved is not True:
            raise PermissionError("Authenticated owner approval required")
        cursor = self.db.execute("UPDATE devices SET revoked=1 WHERE id=?", (device_id,))
        return cursor.rowcount == 1

    def close(self) -> None:
        self.db.close()
