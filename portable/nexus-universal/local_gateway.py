"""Loopback-only NEXUS development gateway.

This is a deliberately restricted coordination service, not a remotely exposed
pairing endpoint or a bridge into JARVIS's paid model APIs. Python 3.10+.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import secrets
import threading
from urllib.parse import urlsplit

from nexus_core import load_catalog

MAX_REQUEST_BYTES = 4096


class Gateway(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, address, catalog):
        if not ipaddress.ip_address(address[0]).is_loopback:
            raise ValueError("Gateway must bind to loopback only")
        super().__init__(address, GatewayHandler)
        self.catalog = catalog
        self.started = datetime.now(timezone.utc).isoformat()


class GatewayHandler(BaseHTTPRequestHandler):
    server_version = "NEXUS-Local/0.1"
    sys_version = ""

    def _send(self, code: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _trusted_request(self) -> bool:
        # Loopback binding is the primary boundary; reject non-loopback peers
        # and unexpected Host headers as defense against DNS rebinding.
        try:
            if not ipaddress.ip_address(self.client_address[0]).is_loopback:
                return False
            host = self.headers.get("Host", "")
            if not host or "@" in host or "/" in host or "\\" in host:
                return False
            parsed = urlsplit("http://" + host)
            if parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
                return False
            return parsed.port == self.server.server_port
        except ValueError:
            return False

    def do_GET(self):
        if not self._trusted_request():
            self._send(403, {"error": "forbidden"})
            return
        if self.path == "/v1/health":
            self._send(200, {"service": "jarvis-nexus-local", "ready": True,
                             "remote_control": False, "pairing_enabled": False})
        elif self.path == "/v1/platforms":
            self._send(200, {"schema_version": 1, "profiles": [
                {"id": p.id, "name": p.name, "status": p.status,
                 "declared_capabilities": sorted(p.capabilities),
                 "verified_capabilities": []}
                for p in self.server.catalog.values()
            ]})
        else:
            self._send(404, {"error": "not_found"})

    def do_POST(self):
        # All mutation paths disabled until authenticated pairing, CSRF and
        # per-device authorization are implemented and reviewed.
        self._send(405, {"error": "mutation_disabled"})

    def do_PUT(self):
        self.do_POST()

    def do_DELETE(self):
        self.do_POST()

    def do_PATCH(self):
        self.do_POST()

    def log_message(self, format, *args):
        # Avoid recording URL paths or future credentials in access logs.
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="NEXUS read-only local gateway")
    parser.add_argument("--host", default="127.0.0.1", choices=("127.0.0.1", "::1"))
    parser.add_argument("--port", type=int, default=18765)
    parser.add_argument("--catalog", default=None)
    args = parser.parse_args()
    from pathlib import Path
    catalog = load_catalog(args.catalog or Path(__file__).with_name("capabilities.json"))
    gateway = Gateway((args.host, args.port), catalog)
    print(f"NEXUS local gateway on {args.host}:{gateway.server_port} (read-only)")
    try:
        gateway.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        gateway.server_close()


if __name__ == "__main__":
    main()
