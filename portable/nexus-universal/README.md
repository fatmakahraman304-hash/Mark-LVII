# JARVIS NEXUS UNIVERSAL

Cross-device portable client architecture. This repository folder contains an initial
capability catalog and device-selection page; **not** a universal executable, firmware
exploit, auto-run USB, or finished multi-platform release.

## Platforms
- Windows: portable client launcher (future); no administrator privileges by default.
- Linux: portable browser/client (future); desktop environment and permissions vary.
- Android phones, Android TV and Android projectors: opt-in Android APK prototype
  in `../nexus-android`, subject to installation and user consent.
- macOS: signed/notarized client is future work.
- iOS/iPadOS: ordinary USB storage cannot install or launch an app; an approved
  app or web client is required.
- Samsung Tizen / LG webOS: ordinary USB storage cannot run arbitrary Android APKs;
  vendor-supported apps or authenticated network APIs only.
- Generic projectors: USB often supports media files only; external host or
  supported built-in browser/app needed.
- Microcontrollers: requires firmware/protocol-specific integration and explicit permission.

## Design
A device-independent capability catalog feeds a UI that reports supported,
requires-setup, or unsupported features. Each adapter must negotiate capabilities
rather than assume control. Authentication uses pairing, least-privilege credentials,
and server-side revocation (future). No paid AI calls without user opt-in.

## Acceptance gates
1. Cross-platform capability catalog and offline validation.
2. Per-platform signed packages with reproducible builds and tests.
3. Pairing, revocation, certificate validation and no stored USB secrets.
4. Per-platform voice/UI and explicitly authorized control adapters.
5. Hardware verification before claiming support.

Current status: catalog and selector prototype committed. Device tests pending.
