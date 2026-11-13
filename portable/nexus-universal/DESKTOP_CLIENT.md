# JARVIS NEXUS — desktop connectivity

A standard-library-only Python 3.10+ client for Windows, Linux and macOS.
This is a **read-only secure connection utility**, not a GUI application or
a universal USB autorun executable. It requires Python installed on the host.

Run from the `portable/nexus-universal` directory:

Windows:
`py -3 desktop_client.py --server https://YOUR-JARVIS-HOST:8765`

Linux/macOS:
`python3 desktop_client.py --server https://YOUR-JARVIS-HOST:8765`

For a private, self-signed LAN CA trusted by the user, supply
`--ca-file /path/to/trusted-ca.pem`. Do not bypass certificate verification.
The URL must be the HTTPS server root with no embedded credentials.

## Current capabilities
- Explicit user-started GET to `/api/state`
- Certificate and hostname validation
- Redirects are not followed
- One-megabyte response cap, timeout, no local secret storage
- No AI inference, paid API calls, remote shell, OS control or autorun

## Future work
A signed desktop GUI, secure device pairing transport, scoped authenticated
commands, audit log, reliable reconnection and actual platform adapters.
The Android prototype uses a different UI stack but will share the same
capability and command contract after integration.

No builds or runtime tests have been performed at this stage.
