"""JARVIS NEXUS command contract. Standard-library only; no remote shell execution."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
import json
import re
import time
import uuid

MAX_BYTES = 8192
ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}$")
ACTIONS = frozenset({"status.read", "media.play", "media.pause", "media.stop",
                     "media.volume", "display.open_url", "display.back", "display.home"})

class CommandError(ValueError):
    pass

class ResultCode(str, Enum):
    OK = "ok"
    DENIED = "denied"
    UNSUPPORTED = "unsupported"
    INVALID = "invalid"
    EXPIRED = "expired"
    OFFLINE = "offline"
    FAILED = "failed"

@dataclass(frozen=True)
class Command:
    version: int
    command_id: str
    device_id: str
    action: str
    params: dict
    issued_at: int
    expires_at: int

    @classmethod
    def create(cls, device_id: str, action: str, params: dict | None = None,
               ttl_seconds: int = 30) -> "Command":
        if not 1 <= ttl_seconds <= 300:
            raise CommandError("TTL out of range")
        now = int(time.time())
        return cls(1, str(uuid.uuid4()), device_id, action, params or {}, now, now + ttl_seconds).validate()

    @classmethod
    def parse(cls, raw: str | bytes) -> "Command":
        if len(raw.encode("utf-8") if isinstance(raw, str) else raw) > MAX_BYTES:
            raise CommandError("Command too large")
        try:
            obj = json.loads(raw)
            if not isinstance(obj, dict) or set(obj) != set(cls.__dataclass_fields__):
                raise CommandError("Unexpected command fields")
            return cls(**obj).validate()
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CommandError("Invalid JSON command") from exc

    def validate(self) -> "Command":
        if type(self.version) is not int or self.version != 1:
            raise CommandError("Unsupported protocol version")
        if not isinstance(self.command_id, str) or not ID_RE.fullmatch(self.command_id):
            raise CommandError("Invalid command ID")
        if not isinstance(self.device_id, str) or not ID_RE.fullmatch(self.device_id):
            raise CommandError("Invalid device ID")
        if self.action not in ACTIONS:
            raise CommandError("Action not allowlisted")
        if type(self.issued_at) is not int or type(self.expires_at) is not int:
            raise CommandError("Invalid timestamps")
        if self.expires_at <= self.issued_at or self.expires_at - self.issued_at > 300:
            raise CommandError("Invalid expiry")
        if not isinstance(self.params, dict):
            raise CommandError("Invalid params")
        expected = {"media.volume": {"level"}, "display.open_url": {"url"}}
        if set(self.params) != expected.get(self.action, set()):
            raise CommandError("Invalid action parameters")
        if self.action == "media.volume":
            level = self.params["level"]
            if type(level) is not int or not 0 <= level <= 100:
                raise CommandError("Invalid volume")
        if self.action == "display.open_url":
            from urllib.parse import urlsplit
            url = self.params["url"]
            if not isinstance(url, str) or len(url) > 2048:
                raise CommandError("Invalid URL")
            try:
                parsed = urlsplit(url)
                if (parsed.scheme != "https" or not parsed.hostname or
                    parsed.username is not None or parsed.password is not None or
                    parsed.port == 0):
                    raise CommandError("Only HTTPS URLs without credentials allowed")
            except ValueError as exc:
                raise CommandError("Invalid URL") from exc
        if len(json.dumps(asdict(self), ensure_ascii=False).encode("utf-8")) > MAX_BYTES:
            raise CommandError("Command too large")
        return self

    def is_expired(self, now: int | None = None) -> bool:
        now = int(time.time()) if now is None else now
        return now > self.expires_at or now < self.issued_at - 30

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"), ensure_ascii=False)

@dataclass(frozen=True)
class CommandResult:
    command_id: str
    code: ResultCode
    message: str

    def to_dict(self) -> dict:
        return {"command_id": self.command_id, "code": self.code.value, "message": self.message}
