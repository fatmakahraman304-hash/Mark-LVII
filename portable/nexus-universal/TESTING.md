# NEXUS Universal — verification gates

Run `python -m unittest -v test_nexus_core.py` in this folder (Python 3.10+).

The catalog is informational. No device-control adapter is enabled until hardware
tests prove the relevant capability, user permission, and safe failure behavior.

## Integration contract (future)
Each adapter must expose a stable platform identifier, report actual detected
capabilities, require explicit device pairing/authorization, and return structured
unsupported errors for unknown actions. No generic shell-command endpoint.
No auto-execution from USB or permission bypass.

## Known gaps
No verified platform adapters, signed packages, microphone handling, pairing,
revocation, or Android hardware test yet. A test passing for the catalog does not
mean an APK works on a projector or that a TV can be controlled.
