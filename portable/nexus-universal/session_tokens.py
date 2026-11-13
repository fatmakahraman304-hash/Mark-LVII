"""Short-lived, scoped session tokens derived after verified device authentication.

This library is transport-agnostic. Never expose issue() directly to untrusted
HTTP callers; authenticate the device credential and TLS channel first.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass

SESSION_TTL = 900
MAX_SESSIONS = 1000


@dataclass(frozen=True)
class SessionGrant:
    session_id: str
    bearer: str
    device_id: str
    expires_at: int
    scopes: frozenset[str]


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, tuple[bytes, str, int, frozenset[str]]] = {}

    def issue(self, device_id: str, scopes: frozenset[str], *, authenticated: bool) -> SessionGrant:
        if authenticated is not True:
            raise PermissionError("Verified device authentication required")
        from pairing_store import DEVICE_ID, ALLOWED_SCOPES
        if not isinstance(device_id, str) or not DEVICE_ID.fullmatch(device_id):
            raise ValueError("Invalid device ID")
        if not scopes or not scopes.issubset(ALLOWED_SCOPES):
            raise ValueError("Invalid scopes")
        now = int(time.time())
        self.expire(now=now)
        if len(self._sessions) >= MAX_SESSIONS:
            raise RuntimeError("Session capacity reached")
        session_id = secrets.token_hex(16)
        bearer = secrets.token_urlsafe(32)
        expiry = now + SESSION_TTL
        self._sessions[session_id] = (
            hashlib.sha256(bearer.encode("ascii")).digest(), device_id, expiry, scopes
        )
        return SessionGrant(session_id, bearer, device_id, expiry, scopes)

    def verify(self, session_id: str, bearer: str, device_id: str, scope: str) -> bool:
        if not isinstance(session_id, str) or not isinstance(bearer, str) or len(bearer) > 256:
            return False
        record = self._sessions.get(session_id)
        if record is None:
            return False
        token_hash, bound_device, expiry, scopes = record
        if int(time.time()) >= expiry or bound_device != device_id or scope not in scopes:
            return False
        return hmac.compare_digest(token_hash, hashlib.sha256(bearer.encode("utf-8")).digest())

    def revoke_device(self, device_id: str) -> int:
        ids = [sid for sid, record in self._sessions.items() if record[1] == device_id]
        for sid in ids:
            del self._sessions[sid]
        return len(ids)

    def expire(self, *, now: int | None = None) -> int:
        now = int(time.time()) if now is None else now
        ids = [sid for sid, record in self._sessions.items() if record[2] <= now]
        for sid in ids:
            del self._sessions[sid]
        return len(ids)
