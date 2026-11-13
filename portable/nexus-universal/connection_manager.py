"""Transport-neutral NEXUS connection lifecycle.

No background discovery, port scanning, remote command execution or network I/O.
The host application drives transitions after authenticated transport events.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import time


class ConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    REVOKED = "revoked"


@dataclass
class Session:
    device_id: str
    state: ConnectionState = ConnectionState.DISCONNECTED
    last_heartbeat: float = 0.0
    failures: int = 0
    next_retry: float = 0.0


class ConnectionManager:
    def __init__(self, *, heartbeat_timeout: float = 90.0, max_backoff: float = 60.0):
        if heartbeat_timeout <= 0 or max_backoff <= 0:
            raise ValueError("Timeouts must be positive")
        self.heartbeat_timeout = heartbeat_timeout
        self.max_backoff = max_backoff
        self.sessions: dict[str, Session] = {}

    def session(self, device_id: str) -> Session:
        if not device_id or len(device_id) > 128:
            raise ValueError("Invalid device ID")
        return self.sessions.setdefault(device_id, Session(device_id))

    def connecting(self, device_id: str, *, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        session = self.session(device_id)
        if session.state == ConnectionState.REVOKED or now < session.next_retry:
            return False
        session.state = ConnectionState.CONNECTING
        return True

    def authenticating(self, device_id: str) -> None:
        session = self.session(device_id)
        if session.state != ConnectionState.CONNECTING:
            raise ValueError("Invalid transition")
        session.state = ConnectionState.AUTHENTICATING

    def authenticated(self, device_id: str, *, now: float | None = None) -> None:
        """Only call after the transport has cryptographically authenticated the device."""
        session = self.session(device_id)
        if session.state != ConnectionState.AUTHENTICATING:
            raise ValueError("Invalid transition")
        session.state = ConnectionState.CONNECTED
        session.last_heartbeat = time.monotonic() if now is None else now
        session.failures = 0
        session.next_retry = 0.0

    def heartbeat(self, device_id: str, *, now: float | None = None) -> bool:
        session = self.session(device_id)
        if session.state not in (ConnectionState.CONNECTED, ConnectionState.DEGRADED):
            return False
        session.last_heartbeat = time.monotonic() if now is None else now
        session.state = ConnectionState.CONNECTED
        return True

    def tick(self, *, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        for session in self.sessions.values():
            if (session.state == ConnectionState.CONNECTED and
                now - session.last_heartbeat > self.heartbeat_timeout):
                session.state = ConnectionState.DEGRADED

    def disconnected(self, device_id: str, *, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        session = self.session(device_id)
        if session.state == ConnectionState.REVOKED:
            return
        session.failures = min(session.failures + 1, 30)
        delay = min(self.max_backoff, float(2 ** min(session.failures - 1, 16)))
        session.next_retry = now + delay
        session.state = ConnectionState.DISCONNECTED

    def revoke(self, device_id: str) -> None:
        session = self.session(device_id)
        session.state = ConnectionState.REVOKED
        session.next_retry = float("inf")
        session.last_heartbeat = 0.0
