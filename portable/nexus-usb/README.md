# JARVIS NEXUS — USB browser prototype

This is a **working static UI prototype**, not an Android APK and not a device-control agent.

## Try it
1. Copy `index.html` to a standard USB stick.
2. On a device that permits opening local HTML files, open it in a browser.
3. Enter the URL of an explicitly authorized JARVIS server, e.g. an HTTPS LAN endpoint.
4. Use **Bağlantıyı kontrol et** for a read-only `GET /api/state` probe, then **JARVIS'i aç** to navigate to its existing UI.

## Important limits
- HY-320 USB-to-browser HTML support has **not** been verified. Android may not offer an HTML opener for USB files.
- File-origin CORS rules may block the probe even when the JARVIS server is reachable. Do not disable browser security to work around this.
- Self-signed HTTPS certificates may require trusted certificate provisioning.
- No installation, automatic USB execution, device takeover, voice commands, or OS control is provided by this prototype.
- This page stores no secrets and uses no paid inference.
- A future signed Android app with user-granted permissions is the preferred reliable HY-320 path.

## Next tests
Verify HY-320 USB mount and local HTML opener; validate browser network connectivity, then build and test an Android client.
