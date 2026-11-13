# Trusted controller integration boundary

`trusted_controller.py` assembles pairing, short-lived sessions, consent and
revocation behind a local orchestration class. It is not an HTTP service.
A host must authenticate the owner and obtain a genuine UI confirmation before
minting a `VerifiedOwner` approval. **Passing booleans is not proof**; do not
expose `owner_approval()` or any other owner method to untrusted clients.

A paired device can request a scoped session after presenting its credential.
The final network implementation must bind that authentication to a verified
TLS channel, rate limit failures, and require owner approval of scopes before
pairing. The current `pair()` accepts scopes from its trusted caller and
must not be wired to arbitrary client-supplied scope requests.

Important release blockers:
- Pairing and audit changes span multiple stores without a global transaction.
  A crash can leave an incomplete registration and must be reconciled.
- The device registry and session store are in-memory and require trusted
  restoration after restart.
- Owner consent needs a real local UI and must display the precise command.
- Device capability activation must come from verified platform adapters.
- A production network server requires TLS, CSRF protections, throttling and
  independent security review.

No paid inference or device-control operations are triggered by this module.
