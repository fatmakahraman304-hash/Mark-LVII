# Device sessions and explicit consent

`session_tokens.py` introduces short-lived per-device bearer sessions with
scope restrictions, expiry and revocation. Sessions are stored in memory only,
and must be invalidated on reconnect/restart and device revocation.

`device_consent.py` introduces one-time consent requests for individual
commands. A trusted local UI must show the actual device and action before
calling `approve(..., trusted_local_ui=True)`. Never accept this flag from
network JSON. Consumption is one-time and bound to device, command and action.

**Integration required:** the authenticated transport must establish the
identity before issuing a session; the dispatcher must require valid session
and consume local consent for state-changing actions. These are separate
foundations, not security guarantees until wired into the final execution path.

No microphone access, paid inference, remote execution or auto-installation.
No runtime or hardware tests have been performed yet.
