# NEXUS local gateway (source-only)

This development gateway intentionally exposes **only read-only metadata** on
the same computer, and cannot pair or control devices.

Start manually from this directory:
```
python local_gateway.py --host 127.0.0.1 --port 18765
```

Read-only endpoints:
- `GET /v1/health`
- `GET /v1/platforms`

The server binds only to loopback, checks the Host header to reduce DNS-rebinding
risk, does not set CORS headers, and rejects all mutation requests. Never forward
port 18765 to a LAN or the internet. It is **not** a replacement for the main
JARVIS server at port 8765.

`scope_policy.py` defines the action-to-scope contract for future authenticated
command handling. It does not itself authorize a command.

## Not yet implemented
- Authenticated pairing API, owner verification, rate limits and CSRF protection
- Device proof-of-possession, signed messages and durable replay storage
- HTTPS/mTLS LAN transport and Android/desktop protocol integration
- Real platform control adapters and full auditing
- Packaging, runtime tests, security review and hardware validation

Do not enable write endpoints until the above security gates are met.
