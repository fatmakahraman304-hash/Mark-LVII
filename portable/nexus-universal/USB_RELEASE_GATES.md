# USB reliability gates — not yet passed

A normal flash drive cannot automatically execute on every Windows, Mac, Linux,
Android or TV device. USB insertion is not authorization. No universal
zero-error guarantee is technically possible across all hardware.

The Windows launcher now checks for Python 3.10+ and prints a clear error
instead of launching with an unsupported interpreter. `usb_preflight.py`
performs a local offline check of required files, Python version and catalog
schema. It does not make network calls, install software or run paid models.

## Before labeling USB release-ready
1. Package self-contained signed Windows executable (no Python dependency).
2. Package signed macOS and Linux variants; no silent execution.
3. Build and sign Android/Android TV APK; confirm TV remote navigation.
4. Implement certificate onboarding and authenticated device pairing.
5. Check read-only connection, session consent, reconnection and revocation.
6. Test on actual Windows hosts, macOS, Linux, Android and supported TVs.
7. Verify offline behavior, corrupt USB files, missing runtimes, expired
   certificates, network outages, low RAM and failed upgrades.
8. Validate installer signatures, rollback, malware scan and permissions.

Current preflight covers only source prerequisites. It does **not** certify
the hardware, network, executable packaging or full JARVIS integration.
