# JARVIS NEXUS — Gemini USB vault

1. Open \`KEY-SETUP.html\` on a trusted laptop in current Chrome/Edge.
2. Enter **your own** Gemini API key from Google AI Studio.
3. Make an ASCII passphrase (10–100 chars); this is **not** your Google password.
4. Download \`jarvis-key.enc.json\`; copy it to the USB drive.
5. On supported Android 11+ devices, **install** the separate JARVIS Gemini APK
   once, open it, choose the vault file from USB and unlock with passphrase.
6. Talk through an installed speech-recognition service or use text input;
   speech synthesis is optional and depends on Android services.

The encrypted file is portable, but the key **cannot be used without unlocking
it** on each new device. No app can safely read your encrypted secret and unlock
it automatically without carrying the unlock secret too. USB loss requires
rotating the API key if passphrase or vault confidentiality is compromised.

## Platform reality

- Android TV/projector, including suitable HY-320 Android 11 variants: APK
  may be side-loaded with owner permission; app/USB file picker and speech
  services must be available. USB insertion does **not** auto-launch apps.
- Samsung Tizen, LG webOS, generic media-only TVs: cannot run Android APK or
  arbitrary scripts from USB. A compatible native TV app, a supported web app
  served online, or an external Android TV stick is needed.
- No Qwen, Ollama, Python or laptop required for the Android Gemini APK.
- Requires internet and an API key with an active Gemini quota. Charges may
  occur depending on billing settings; no automatic paid fallback is configured.
- Google advises against distributing API keys in client software; a secure
  backend issuing scoped/short-lived session tokens is the production solution.
  This personal-use encrypted-vault method is **not** enterprise key protection.
- Never commit \`jarvis-key.enc.json\` to GitHub. Keep its passphrase private.

This is an Android app source prototype. A CI-built debug APK needs real-device
installation, voice-service, UI and API testing before being called supported.
