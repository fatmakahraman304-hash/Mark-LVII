"""Explicit, per-command local consent state.

This is a library used by a trusted UI; it does not display prompts itself.
"""
from __future__ import annotations
from dataclasses import dataclass
import secrets
import time

MAX_PENDING = 128
CONSENT_TTL = 60


@dataclass(frozen=True)
class ConsentRequest:
    consent_id: str
    device_id: str
    command_id: str
    action: str
    expires_at: int


class ConsentManager:
    def __init__(self):
        self._pending: dict[str, ConsentRequest] = {}
        self._approved: set[str] = set()

    def request(self, device_id: str, command_id: str, action: str) -> ConsentRequest:
        from command_protocol import ID_RE, ACTIONS
        if (not isinstance(device_id, str) or not ID_RE.fullmatch(device_id)
            or not isinstance(command_id, str) or not ID_RE.fullmatch(command_id)
            or action not in ACTIONS):
            raise ValueError("Invalid consent request")
        self.expire()
        if len(self._pending) >= MAX_PENDING:
            raise RuntimeError("Too many pending consent requests")
        consent = ConsentRequest(secrets.token_hex(16), device_id, command_id,
                                 action, int(time.time()) + CONSENT_TTL)
        self._pending[consent.consent_id] = consent
        return consent

    def approve(self, consent_id: str, *, trusted_local_ui: bool) -> bool:
        if trusted_local_ui is not True:
            raise PermissionError("Trusted local UI confirmation required")
        request = self._pending.get(consent_id)
        if request is None or int(time.time()) >= request.expires_at:
            return False
        self._approved.add(consent_id)
        return True

    def consume(self, consent_id: str, device_id: str, command_id: str, action: str) -> bool:
        request = self._pending.pop(consent_id, None)
        approved = consent_id in self._approved
        self._approved.discard(consent_id)
        return bool(approved and request and int(time.time()) < request.expires_at
                    and request.device_id == device_id
                    and request.command_id == command_id and request.action == action)

    def expire(self) -> None:
        now = int(time.time())
        for key, request in list(self._pending.items()):
            if request.expires_at <= now:
                del self._pending[key]
                self._approved.discard(key)
