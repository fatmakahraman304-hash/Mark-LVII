"""Shared, strict NEXUS wire-format validation for future clients.

Only data envelopes; no HTTP server, permissions, or device control.
"""
from __future__ import annotations
import json
import re

MAX_MESSAGE = 8192
IDENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
KINDS = frozenset({"hello", "hello_ack", "heartbeat", "command_result", "error"})


class ProtocolError(ValueError):
    pass


def _unique_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ProtocolError("Duplicate JSON key")
        obj[key] = value
    return obj


def parse_envelope(raw: bytes | str) -> dict:
    if not isinstance(raw, (bytes, str)):
        raise ProtocolError("Invalid payload")
    try:
        encoded = raw.encode("utf-8") if isinstance(raw, str) else raw
        if len(encoded) > MAX_MESSAGE:
            raise ProtocolError("Payload too large")
        data = json.loads(encoded, object_pairs_hook=_unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ProtocolError("Invalid number")))
    except (UnicodeError, json.JSONDecodeError, TypeError) as exc:
        raise ProtocolError("Invalid JSON") from exc
    if type(data) is not dict or set(data) != {"version", "kind", "request_id", "payload"}:
        raise ProtocolError("Invalid envelope shape")
    if type(data["version"]) is not int or data["version"] != 1:
        raise ProtocolError("Unsupported version")
    if not isinstance(data["kind"], str) or data["kind"] not in KINDS:
        raise ProtocolError("Unsupported message kind")
    if not isinstance(data["request_id"], str) or not IDENT.fullmatch(data["request_id"]):
        raise ProtocolError("Invalid request identifier")
    if type(data["payload"]) is not dict:
        raise ProtocolError("Invalid payload object")
    return data


def make_envelope(kind: str, request_id: str, payload: dict) -> bytes:
    data = {"version": 1, "kind": kind, "request_id": request_id, "payload": payload}
    try:
        encoded = json.dumps(data, ensure_ascii=False, allow_nan=False,
                             separators=(",", ":")).encode("utf-8")
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ProtocolError("Invalid envelope content") from exc
    parse_envelope(encoded)
    return encoded
