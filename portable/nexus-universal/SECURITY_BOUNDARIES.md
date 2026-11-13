# NEXUS security boundaries and release blockers

## Implemented foundations
- All command actions explicitly allowlisted and parameter validated.
- Per-device token hashes and revocation stored in SQLite.
- One-time pairing invitations with a 120-second expiry.
- Loopback-only, read-only development gateway.
- Persistent transactional command replay reservation in `replay_store.py`.
- HMAC-chained metadata audit log in `audit_store.py`.

## Critical caveats
These are independent building blocks, **not a completed secure network service**.
The current `DeviceRegistry` still has its own in-memory replay tracking;
`ReplayStore` must be integrated into the final authenticated dispatcher.
Likewise `AuditStore` is not yet wired into every authorization decision.
An audit chain detects edits only if its signing key and a trusted chain head
are protected externally; it does not prevent file deletion or rollback.
Do not expose owner-approved boolean flags as user-controlled HTTP parameters.

## Required before LAN/Internet exposure
- Trusted owner login, anti-CSRF and device-local consent UX.
- Pairing challenge exchange over verified TLS with rate limits.
- Scoped token authentication on every request and secure credential lifecycle.
- Network transport with request size limits, origin policy, timeout and audit.
- Persistent replay guard integrated before adapter execution.
- Per-platform OS permissions and capability proof; fail closed by default.
- Certificate rotation, signed installers and supply-chain verification.
- Real security review and comprehensive tests at final acceptance phase.

Never turn a USB insertion into permission to execute software or control a
device. The user's request to defer tests does not waive these release gates.
