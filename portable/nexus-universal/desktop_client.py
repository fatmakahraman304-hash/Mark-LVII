"""Cross-platform desktop client foundation (Windows/Linux/macOS).

No background services, autorun, privilege escalation or system control.
Only explicit HTTPS requests to an owner-configured JARVIS server.
"""
from __future__ import annotations

import argparse
import getpass
import http.client
import json
import ssl
import sys
from dataclasses import dataclass
from urllib.parse import urlsplit

MAX_RESPONSE = 1024 * 1024


class ClientError(Exception):
    pass


def normalize_origin(value: str) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise ClientError("Invalid server URL")
    try:
        parsed = urlsplit(value.strip())
        if (parsed.scheme != "https" or not parsed.hostname or
            parsed.username is not None or parsed.password is not None or
            parsed.path not in ("", "/") or parsed.query or parsed.fragment or
            parsed.port == 0):
            raise ClientError("A HTTPS server root URL is required")
        port = parsed.port
        host = parsed.hostname.lower()
        if ":" in host:
            host = "[" + host + "]"
        return "https://" + host + (f":{port}" if port is not None else "")
    except ValueError as exc:
        raise ClientError("Invalid server URL") from exc


@dataclass(frozen=True)
class ServerState:
    version: str
    connected: bool


class JarvisClient:
    """Read-only health/state client; no inference or device command calls."""

    def __init__(self, origin: str, *, cafile: str | None = None, timeout: float = 8.0):
        self.origin = normalize_origin(origin)
        if not 0 < timeout <= 30:
            raise ClientError("Invalid timeout")
        self.timeout = timeout
        try:
            self.context = ssl.create_default_context(cafile=cafile)
        except (OSError, ssl.SSLError) as exc:
            raise ClientError("Unable to load trusted CA") from exc
        self.context.check_hostname = True
        self.context.verify_mode = ssl.CERT_REQUIRED

    def state(self) -> ServerState:
        parsed = urlsplit(self.origin)
        connection = http.client.HTTPSConnection(
            parsed.hostname, parsed.port or 443, timeout=self.timeout,
            context=self.context,
        )
        try:
            connection.request("GET", "/api/state", headers={
                "Accept": "application/json",
                "User-Agent": "JARVIS-NEXUS/0.1",
                "Cache-Control": "no-store",
            })
            response = connection.getresponse()
            # Deliberately do not follow redirects, including off-origin redirects.
            if response.status != 200:
                raise ClientError(f"State endpoint returned HTTP {response.status}")
            if response.length is not None and response.length > MAX_RESPONSE:
                raise ClientError("Response too large")
            raw = response.read(MAX_RESPONSE + 1)
            if len(raw) > MAX_RESPONSE:
                raise ClientError("Response too large")
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ClientError("Invalid state response")
            version = payload.get("version", "unknown")
            if not isinstance(version, (str, int, float)) or isinstance(version, bool):
                version = "unknown"
            return ServerState(str(version)[:64], True)
        except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
            raise ClientError("Secure state request failed") from exc
        finally:
            connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="JARVIS NEXUS read-only HTTPS desktop client")
    parser.add_argument("--server", required=True, help="Trusted HTTPS JARVIS origin")
    parser.add_argument("--ca-file", help="Trusted LAN CA certificate (PEM); never disable TLS verification")
    args = parser.parse_args(argv)
    try:
        client = JarvisClient(args.server, cafile=args.ca_file)
        state = client.state()
        print(json.dumps({"connected": state.connected, "version": state.version}, ensure_ascii=False))
        return 0
    except ClientError as exc:
        print(f"NEXUS: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
