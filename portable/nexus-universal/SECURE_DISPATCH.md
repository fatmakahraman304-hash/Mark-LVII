# Secure command dispatch foundation

`secure_dispatch.py` joins the existing credential store, registry,
transactional replay store, audit chain and allowlisted adapter contract.

Dispatch requires a scoped device credential, a live paired device, a matching
verified capability, a registered adapter, a fresh command ID, and an audit
record before any adapter action can execute. Unknown actions fail closed.
Errors from adapters are not returned verbatim to avoid leaking internals.

This module is **not** a network service. It does not prove the caller owns the
token or the device; authentication transport and pairing UX must be completed
before accepting remote commands. The registry currently uses in-memory
authorization state, so reconnect/rehydration and device-bound identity remain
release blockers. Audit and replay stores must be provisioned on durable
storage, with an external trusted audit-chain checkpoint.

Do not enable any non-read-only adapter until platform-specific permissions,
authentication, and user confirmation are integrated and reviewed.

The comprehensive build/test/security/hardware phase is deferred to final
acceptance as requested; no validation claim is made here.
