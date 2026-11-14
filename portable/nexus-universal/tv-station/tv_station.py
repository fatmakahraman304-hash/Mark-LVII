"""JARVIS NEXUS TV Station: laptop-independent local AI host.

Run on a separately powered Windows/Linux/macOS mini-PC plugged into a TV by
HDMI. Requires local Ollama and a pre-downloaded qwen3:8b model ON THAT HOST.
No cloud providers, LAN exposure, TV USB auto-execution or device control.
Python 3.10+, standard library only.
"""
from __future__ import annotations

import argparse
import hmac
import http.client
import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"
DEFAULT_PORT = 18767
OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
MODEL = "qwen3:8b"
MAX_REQUEST_BYTES = 16000
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_PROMPT = 2000
MAX_HISTORY = 8
MAX_HISTORY_CHARS = 8000
FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; "
       "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; "
       "form-action 'none'")


class InputError(ValueError):
    pass


def unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    out = {}
    for key, value in pairs:
        if key in out:
            raise InputError("Duplicate JSON field")
        out[key] = value
    return out


def checked_chat(obj: object) -> list[dict[str, str]]:
    """Only user/assistant plain text; no system prompts or tool instructions."""
    if type(obj) is not dict or set(obj) != {"prompt", "history"}:
        raise InputError("Invalid chat payload")
    prompt, history = obj["prompt"], obj["history"]
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= MAX_PROMPT:
        raise InputError("Prompt must contain 1-2000 characters")
    if not isinstance(history, list) or len(history) > MAX_HISTORY:
        raise InputError("Too much history")
    messages = [{
        "role": "system",
        "content": ("Sen J.A.R.V.I.S. TV Station adlı yerel bir yardımcı asistansın. "
                    "Türkçe ve açık cevap ver. Bilgisayarı, televizyonu veya USB'yi "
                    "kontrol edebildiğini iddia etme. Donanım durumunu doğrulamadan "
                    "çalışıyor deme. Ağ veya ücretli hizmet kullanmıyorsun.")
    }]
    total = 0
    for item in history:
        if (type(item) is not dict or set(item) != {"role", "content"} or
                item["role"] not in ("user", "assistant") or
                not isinstance(item["content"], str) or
                len(item["content"]) > MAX_PROMPT):
            raise InputError("Invalid history entry")
        total += len(item["content"])
        messages.append({"role": item["role"], "content": item["content"]})
    if total > MAX_HISTORY_CHARS:
        raise InputError("History too long")
    messages.append({"role": "user", "content": prompt.strip()})
    return messages


def ollama_json(method: str, path: str, payload: dict | None = None,
                timeout: float = 5.0) -> dict:
    """Direct loopback HTTP; bypasses proxy environment and cannot call a LAN host."""
    conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=timeout)
    try:
        body = None if payload is None else json.dumps(
            payload, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        if response.status != 200:
            raise RuntimeError("Ollama HTTP error")
        if response.length is not None and response.length > MAX_RESPONSE_BYTES:
            raise RuntimeError("Ollama response too large")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise RuntimeError("Ollama response too large")
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs)
        if type(result) is not dict:
            raise RuntimeError("Invalid Ollama response")
        return result
    finally:
        conn.close()


def model_available() -> bool:
    result = ollama_json("GET", "/api/tags", timeout=3.0)
    models = result.get("models", [])
    return isinstance(models, list) and any(
        type(item) is dict and item.get("name") == MODEL for item in models
    )


def answer(messages: list[dict[str, str]]) -> str:
    result = ollama_json("POST", "/api/chat", {
        "model": MODEL, "stream": False, "think": False,
        "messages": messages,
        "options": {"num_predict": 384, "num_ctx": 4096}
    }, timeout=100.0)
    msg = result.get("message")
    content = msg.get("content") if type(msg) is dict else None
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Ollama returned no answer")
    return content[:10000]


class TVServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, port: int = DEFAULT_PORT):
        super().__init__((HOST, port), TVHandler)
        self.token = secrets.token_urlsafe(32)
        self.inference_gate = threading.BoundedSemaphore(1)


class TVHandler(BaseHTTPRequestHandler):
    server_version = "NEXUS-TV/0.1"
    sys_version = ""

    def log_message(self, *args) -> None:
        # No URL, message, token or prompt logs.
        pass

    def _allowed_host(self) -> bool:
        hosts = self.headers.get_all("Host", [])
        return len(hosts) == 1 and hosts[0] in (
            "127.0.0.1:" + str(self.server.server_port),
            "localhost:" + str(self.server.server_port),
        ) and self.client_address[0] == HOST

    def _headers(self, code: int, content_type: str, length: int) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", CSP)
        self.end_headers()

    def _json(self, code: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self._headers(code, "application/json; charset=utf-8", len(data))
        self.wfile.write(data)

    def do_GET(self) -> None:
        if not self._allowed_host():
            self._json(403, {"error": "forbidden"})
            return
        if self.path == "/api/token":
            self._json(200, {"token": self.server.token})
            return
        if self.path == "/api/health":
            try:
                has_model = model_available()
            except (OSError, ValueError, RuntimeError, http.client.HTTPException):
                self._json(503, {"ready": False, "reason": "ollama_unavailable",
                                 "model": MODEL, "local_only": True})
                return
            self._json(200 if has_model else 503, {
                "ready": has_model,
                "reason": "ready" if has_model else "model_missing",
                "model": MODEL, "local_only": True
            })
            return
        if self.path not in FILES:
            self._json(404, {"error": "not_found"})
            return
        name, mime = FILES[self.path]
        try:
            data = (Path(__file__).resolve().parent / name).read_bytes()
        except OSError:
            self._json(503, {"error": "station_files_missing"})
            return
        self._headers(200, mime, len(data))
        self.wfile.write(data)

    def do_POST(self) -> None:
        if not self._allowed_host():
            self._json(403, {"error": "forbidden"})
            return
        host = self.headers["Host"]
        origins = self.headers.get_all("Origin", [])
        tokens = self.headers.get_all("X-Nexus-Token", [])
        try:
            valid_token = (len(tokens) == 1 and len(tokens[0]) <= 256 and
                           hmac.compare_digest(tokens[0].encode("ascii"),
                                               self.server.token.encode("ascii")))
        except UnicodeEncodeError:
            valid_token = False
        if (self.path != "/api/chat" or len(origins) != 1 or
                origins[0] != "http://" + host or not valid_token):
            self._json(403, {"error": "request_not_authorized"})
            return
        if self.headers.get("Transfer-Encoding"):
            self._json(400, {"error": "chunked_request_not_supported"})
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            self._json(415, {"error": "json_required"})
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if not 0 < length <= MAX_REQUEST_BYTES:
                raise InputError("Invalid body size")
            raw = self.rfile.read(length)
            messages = checked_chat(json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs,
                                              parse_constant=lambda _: (_ for _ in ()).throw(InputError("Invalid number"))))
        except (InputError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
            self._json(400, {"error": "invalid_chat_request"})
            return
        if not self.server.inference_gate.acquire(blocking=False):
            self._json(429, {"error": "model_busy"})
            return
        try:
            try:
                if not model_available():
                    self._json(503, {"error": "model_missing", "model": MODEL})
                    return
                response = answer(messages)
                self._json(200, {"answer": response, "model": MODEL})
            except (OSError, ValueError, RuntimeError, http.client.HTTPException):
                self._json(503, {"error": "ollama_unavailable"})
        finally:
            self.server.inference_gate.release()

    def do_OPTIONS(self) -> None:
        self._json(405, {"error": "method_not_allowed"})

    def do_PUT(self) -> None:
        self._json(405, {"error": "method_not_allowed"})

    def do_DELETE(self) -> None:
        self._json(405, {"error": "method_not_allowed"})


def main() -> int:
    parser = argparse.ArgumentParser(description="TV Station: local HDMI AI host, no cloud")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be 1024..65535")
    try:
        server = TVServer(args.port)
    except OSError as exc:
        print("NEXUS TV: cannot open local port: " + str(exc))
        return 2
    url = "http://127.0.0.1:" + str(server.server_port) + "/"
    print("JARVIS TV Station: " + url, flush=True)
    print("Local-only. Requires Ollama + qwen3:8b on THIS computer.", flush=True)
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
