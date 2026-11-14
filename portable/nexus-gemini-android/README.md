# JARVIS NEXUS Gemini Android TV/Projector (passwordless test build)

Android 8+ APK using the Gemini REST API. Does not need laptop, Ollama or Qwen.

## Set up once on laptop
1. Open ../nexus-gemini-usb/KEY-SETUP.html in Chrome/Edge.
2. Paste the Gemini API key and download jarvis-gemini-key.json.
3. Copy this JSON and the current debug APK to USB.

## On each compatible Android TV/projector
1. Manually install APK from USB with owner permission.
2. Open J.A.R.V.I.S. Gemini from Apps.
3. Select jarvis-gemini-key.json from USB once. **No password**.
4. The app encrypts a copy in Android Keystore (AES/GCM) and automatically
   loads it on subsequent launches. Uninstall/data wipe requires re-import.
5. App speaks its welcome message if Turkish TTS is installed, requests microphone
   permission once, and starts listening while the app is in the foreground.
   No microphone buttons are needed; a text field remains for unsupported TVs.

## Android voice: v0.4 button-free foreground mode (NOT Gemini Live)

- On app launch, after the first-time Android microphone permission and initial
  API key import, JARVIS greets the user using Android Turkish TTS and starts
  best-effort recognition. No talk/mute/stop/test buttons are shown.
- Saying exactly **"sus"** or **"Jarvis sus"** immediately disables spoken
  replies and stops current TTS when the speech engine recognizes it.
- Saying exactly **"konuş"** or **"Jarvis konuş"** re-enables spoken replies,
  responds "Dinliyorum", and keeps recognizing. Voice command recognition
  remains active while muted.
- Other finished recognized utterances are sent as text to Gemini REST; Gemini
  answers are read aloud using Android TextToSpeech when available.
- Recognition is **foreground-only**, explicit Android RECORD_AUDIO permission
  is required, microphone status is shown prominently, and the microphone
  closes when the user exits the app or the activity stops.
- Android SpeechRecognizer is not designed for sustained, continuous speech
  recognition. This version restarts short 20-second sessions while visible
  and stops retrying after repeated service errors. Therefore it cannot
  guarantee true always-on, zero-gap wake-word recognition, especially on
  Android 11 projectors with limited microphone/service support.
- Android speech recognition may send audio to its own remote provider. This
  app sends only transcribed text to Gemini REST. No app-side recording files,
  background service, wake word engine, or Gemini Live audio streaming.
- When the assistant is talking, the recognizer filters non-command audio
  to avoid its own speech triggering an infinite conversation. Exact "sus"
  commands may still be affected by speaker echo, device drivers, and OS
  recognition limits. Headphones or echo cancellation may improve this.
- Hardware prerequisites: microphone (built-in or compatible USB/Bluetooth),
  working Android speech recognition service and Turkish TTS. If missing,
  typed Enter-to-send fallback remains available; buttons are not required.
- Updating a debug APK may fail because debug build signing keys may differ
  across build environments. If Android reports an incompatible signature,
  uninstall the old test APK, install v0.4, and re-import the existing USB
  `jarvis-gemini-key.json`. It has no vault password.

## Security
**The USB JSON contains the API key in PLAINTEXT.** Anybody who copies it
can use Google Gemini quota and potentially cause charges. Keep your USB
private. If lost, rotate/revoke the key in Google AI Studio. Never upload
the JSON to GitHub or send it in chat. Android Keystore secures only the
device-local copy, not the removable USB file. Production-grade shared
credentials need a user-authenticated backend that issues short-lived tokens.

## Models and limits
Upstream FatihMakes/Mark-LVII uses Gemini Live
gemini-3.1-flash-live-preview and a Gemini native-audio fallback.
This app currently uses REST text Flash models:
gemini-3.5-flash-lite, gemini-3.5-flash, gemini-3.8-flash.
It does NOT implement Gemini Live continuous two-way audio.
Voice input and reply speech require Android OS services.

Internet is necessary. Gemini usage may be billed according to account
settings; no automatic paid model fallback is implemented.
APK builds on CI require real HY-320 voice, installer, performance, and
remote control testing. Android APK cannot run on Samsung Tizen, LG webOS
or arbitrary media-only USB TVs. USB insertion does not autorun apps.
