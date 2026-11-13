# JARVIS NEXUS UNIVERSAL — Target architecture

## Scope
One user-authorized personal AI interface across multiple operating systems and
device types, with separate platform adapters. This is a target architecture,
not a claim of completed platform integration.

## Layers
1. **Portable distribution**: USB directory with platform-specific signed installers
   or browser client. No automatic USB execution or hidden persistence.
2. **Client UI**: responsive web interface; native wrappers only where needed.
3. **Identity & pairing**: short-lived one-time pairing challenge, authenticated
   TLS, per-device scoped credentials, explicit revocation and audit logs.
   **Not yet implemented** in this branch.
4. **Protocol**: strict JSON command schema with action allowlist, TTL, command IDs,
   parameter validation and replay checks.
5. **Registry**: device inventory and runtime capability negotiation.
6. **Adapters**: opt-in Android, Windows, Linux, macOS, vendor TV and smart-home
   integrations; platform APIs only, no arbitrary remote shell.
7. **JARVIS backend**: existing Ollama/Abacus routing; no paid calls without
   explicit user authorization. Integration not yet wired.

## Implemented in this phase
`command_protocol.py`, `device_registry.py`, `adapters.py` are source-only
core components. The registry is ephemeral, and its `authorize()` method must
only be invoked by a trusted pairing server after cryptographic verification.
**Do not expose these classes directly as a network API.**

## Safety and privacy
Never assume plugging in USB grants control. Avoid silently activating microphones,
cameras, external URLs, or paid inference. Each adapter must validate local user
permission and expose only explicitly supported actions. Deny unknown commands.
Never log pairing tokens or send secrets to the USB.

## Remaining implementation
Authenticated transport, durable encrypted identity store, replay persistence,
audit trail, adapter sandboxing, permission UX, platform packaging, voice pipeline,
screen awareness, device-specific media control, firmware/vendor API research,
real-hardware validation and end-to-end tests.

## Final-stage test gates (deferred by project decision)
Unit tests; protocol fuzzing; auth/revocation/replay tests; cross-origin/TLS tests;
APK and desktop builds; device matrix; memory/CPU profiling; security review;
manual Windows/Android TV/TV vendor tests; paid API budget guard verification.
No production release until these gates pass.
