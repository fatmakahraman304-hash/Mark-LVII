# Secure pairing integration — implementation boundary

`pairing_store.py` is a local credential store, not a complete pairing server.
Its `owner_approved=True` flag is a **trust boundary**, not proof of identity.
Never let a remote caller choose that flag. Only trusted server code should set it
after authenticating the owner and recording a physical/local UI confirmation.

## Proposed workflow
1. Owner signs into JARVIS and presses **Add device** on a trusted screen.
2. Trusted server invokes `begin_pairing(owner_approved=True)` and displays
   invitation ID + 256-bit random secret through a protected channel.
3. New client connects via verified HTTPS, submits invitation ID and secret,
   a unique device ID and the **owner-approved** scopes.
4. Trusted server calls `redeem()` once and returns a per-device token only
   to the newly paired client over HTTPS.
5. Every subsequent device request authenticates the token and checks the
   specific action scope. Revocation invalidates it.
6. Owner can revoke the device through an authenticated management interface.

## Required before network exposure
- Real owner authentication and UI approval; never trust request booleans.
- Client-side TLS validation, authenticated transport, CSRF protections.
- Pairing attempt throttling, request size limits, abuse logging without secrets.
- Device-bound proof-of-possession if threat model requires it.
- Atomic persistent replay protection and auditable command authorization.
- Storage permissions / encrypted backup policy and credential rotation.
- Mapping from protocol actions to scopes and trusted platform adapters.
- Security review and final-stage tests.

**Not production-ready:** do not publish an endpoint that directly invokes
`begin_pairing`, `redeem`, or `revoke` without the safeguards above.
