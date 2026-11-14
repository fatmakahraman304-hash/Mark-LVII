# JARVIS NEXUS Gemini Android TV / Projector client (prototype)

This is the **Gemini API** alternative to the local Ollama TV Station.
It does **not** require Qwen, Ollama, a laptop or a mini PC after installation.

## Build

Android Studio (JDK 17, Android SDK 35) or GitHub Actions:
\`gradle -p portable/nexus-gemini-android assembleDebug\`

A CI-produced **debug** APK is intended for owner-authorized manual testing,
not a signed production release. The APK can be installed once from USB on a
compatible Android 8+ device with sideload permission (Android 11 HY-320 is a
target, but not yet verified).

## Set up once on laptop
1. Open \`../nexus-gemini-usb/KEY-SETUP.html\` with a current Chrome/Edge.
2. Enter your Google AI Studio Gemini API key and a new vault passphrase.
3. Download \`jarvis-key.enc.json\`; copy it to the USB stick. It is
   **AES-256-GCM encrypted** with PBKDF2-SHA256 (250,000 iterations).
4. Put the APK on the USB. On the Android device, **install** it using a
   trusted file manager and owner-approved unknown-app installation.
5. Launch **J.A.R.V.I.S. Gemini** from the Android Apps screen. USB insertion
   alone does not launch or install an APK.
6. Select the encrypted file using Android's document picker and type the
   vault password. The encrypted file is cached locally for future launches;
   the unlocked API key is **only kept in app memory**.
7. Use TV remote/keyboard for text. Voice input uses the system speech
   recognition intent, and TTS uses system TextToSpeech; these may be absent
   on low-cost projectors or TVs.

## Gemini models

The upstream FatihMakes/Mark-LVII main source uses
\`gemini-3.1-flash-live-preview\` as its default **Live** model and
\`gemini-2.5-flash-native-audio-preview-12-2025\` as its Live fallback.
It also defines Gemini Flash REST model ladders. This prototype currently
implements **REST generateContent**, not Gemini Live streaming:
- \`gemini-3.5-flash-lite\` (default)
- \`gemini-3.5-flash\`
- \`gemini-3.8-flash\`

Microphone + TTS are Android OS services, not Gemini Live streaming. Real-time
interruptible Live voice would require a separate authenticated Live API
integration and testing. Do not claim that feature is implemented.

## Known limits
- Not compatible with arbitrary Samsung Tizen, LG webOS or media-only TV USB
  playback; those need vendor-specific apps, a supported hosted browser app
  or a user-approved Android TV dongle.
- Android must be able to install/open the APK and offer a document picker.
  HY-320 Android versions, microphones, storage permissions and TV remote
  behavior vary; hardware test still pending.
- A device WITHOUT an Android speech recognizer or microphone still supports
  text input; TTS voice availability varies.
- Gemini calls cost tokens and may incur charges depending on the Google
  account's plan. There is **no paid fallback** or implicit other provider.
- Google's official guidance discourages putting API keys in client software.
  The encrypted portable vault avoids plaintext *at rest*, but once unlocked,
  a compromised device can extract the key from memory. For high-security
  deployment, use a backend/token broker with device authentication.
- Do not store or commit \`jarvis-key.enc.json\`, any real key, or passwords in GitHub.
- APK needs compile/automated tests, real API + Android 11 installation and
  end-to-end USB/TV tests before release claims.
