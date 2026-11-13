# JARVIS NEXUS — Portable USB (v1 design)

Status: design only; not implemented or device-tested.
Base: feature/osiris-world-command. Target test device: HY-320 Android 11, 1 GB RAM, Wi-Fi.

## Goal
Use a conventional USB storage stick to carry a lightweight JARVIS client for compatible, user-authorized devices. On HY-320, launch a supported Android client or web UI, connect over Wi-Fi to an explicitly paired JARVIS backend, show the JARVIS interface, and accept commands. No local LLM inference on the projector.

## Physical and OS limits
A conventional USB mass-storage stick cannot execute programs by itself, emulate Flipper Zero hardware, or force arbitrary TVs/projectors to run code. Android 11 generally requires a user-mediated first-time install/launch; USB insertion alone does not grant execution or privileged device control. If the Android client must be installed, unplugging USB does not uninstall it. Explicitly offer uninstall/clear-session instructions; do not promise zero persistence.

## Architecture
- USB: versioned Android APK (only if installable), optional static web client, signed manifest with SHA-256 checksums, setup instructions.
- Projector: low-memory Android launcher/client or browser-based UI. Avoid always-on background processes.
- Transport: Wi-Fi to paired JARVIS service with TLS, short-lived scoped session tokens, device revocation, reconnect with backoff, no secrets stored on removable media.
- Commands: allowlisted actions via OS-supported intents/APIs; capability negotiation and explicit confirmation for sensitive actions.
- Voice: detect usable microphone, ask permission; offer text/remote input fallback.
- Network: backend availability check; no silent paid-model fallback. Require explicit user opt-in before paid API inference.
- Session: logout, token revocation and no sensitive cached data on USB.

## Milestones and acceptance gates
1. HY-320 USB detection: verify filesystem mount, read-only manifest access and APK install capability; capture firmware/build and available browser. No installation before explicit consent.
2. Minimal client: render dashboard on 1 GB RAM Android 11, avoid crashes/ANRs; display offline/unpaired status.
3. Pairing: user confirms a one-time code; verify TLS and least-privilege token, revoke and expiry tests.
4. Commands: user-authorized open-web-page, media play/pause where supported; unavailable actions report unsupported rather than claiming success.
5. Voice: microphone permission, end-to-end command test, text fallback.
6. USB removal: close session when detectable; verify revocation/logout and document app persistence.
7. Security: malicious USB files not executed, unsigned package rejected, no arbitrary shell execution, no device exploitation, no CSRF regression, guest data isolated.
8. Cross-device support only after HY-320 passes actual hardware tests.

## Open questions for physical test
USB storage mount behavior; APK installation policy; launcher and browser versions; microphone availability; available RAM under load; connectivity to existing JARVIS host or authorized gateway.

No claims of completed functionality until tested on real hardware.
