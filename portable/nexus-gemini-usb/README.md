# JARVIS NEXUS — Passwordless Gemini USB

1. Open KEY-SETUP.html on your trusted laptop.
2. Enter the Google AI Studio Gemini API key once; no password.
3. Download jarvis-gemini-key.json and copy it to the USB.
4. On every compatible Android TV/projector, manually install the APK once.
5. Launch the app and select jarvis-gemini-key.json from USB **once**.
6. On later launches **that Android device** reads its encrypted saved key
   automatically, without any password. Clearing app data requires reimport.

## Important security trade-off

The cross-device USB file contains your API key in **plaintext**.
Anyone with access to that USB file can use your key and possibly incur costs.
Never share/upload the file, and rotate/revoke the key if the USB is lost.
The Android app encrypts only its *device-local copy* using Android Keystore.
Do not commit the USB key file to GitHub or paste it in chat.

A user-authenticated cloud broker with short-lived credentials is the better
production solution; it is not implemented here.

Android USB insertion cannot reliably autoinstall/autostart apps. Samsung
Tizen, LG webOS and media-only TVs cannot run this APK; Android devices
must offer a compatible APK installer/file picker. Microphone recognition
and TTS depend on Android device services. Gemini requires internet and
may consume billable quota. HY-320 hardware remains untested.
