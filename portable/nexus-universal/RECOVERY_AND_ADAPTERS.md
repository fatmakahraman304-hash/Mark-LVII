# Device recovery and adapter manifests

`device_recovery.py` restores non-revoked paired identities from SQLite
**only when** the trusted host supplies a device-to-platform mapping. Restored
devices are always offline and have zero executable capabilities. They must
authenticate again and undergo platform adapter verification before use.

`platform_manifest.py` validates local action declarations. Manifests are
informational; they are not signatures, platform attestation or authorization.
`verified_actions()` returns an empty set unless the trusted host explicitly
reports platform verification and user-granted actions. Do not derive either
argument from an untrusted HTTP payload.

`manifests/desktop-status.json` is an illustrative Windows read-only
adapter declaration, not a shipped Windows executable.

Before release: persist device platform metadata transactionally alongside
pairing, signed adapter distribution, revocation reconciliation, trusted
platform permission checks, real client implementations and end-stage tests.
