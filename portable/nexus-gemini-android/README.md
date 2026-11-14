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
5. Type questions or use optional Android speech recognition & TTS services.

## Android voice: v0.3 push-to-talk (not Gemini Live)

- **🎤 Konuş** explicitly requests Android RECORD_AUDIO permission and listens
  for a **single** Turkish utterance via Android SpeechRecognizer. Partial
  text is shown while listening; the final text is sent to Gemini REST.
- **⏹ Dinlemeyi Durdur** cancels recognition. A 20-second timeout also closes
  the microphone; navigating away closes it too. No continuous hot mic,
  background listening, wake word or microphone file recording.
- **🔊 SES TESTİ** speaks a short Turkish sentence through Android
  TextToSpeech. **🔇 Sesi Kapat / 🔊 Sesi Aç** mutes or enables spoken replies.
- Gemini response text is spoken through Android TTS when available.
  This is NOT the upstream FatihMakes Gemini Live bidirectional audio model.
- Android's speech recognition service may send your voice to its provider
  over the Internet. The app itself sends only transcribed text to Gemini REST.
- HY-320 and many TVs lack a microphone, Turkish TTS or Android speech
  recognizer. In that case connect a compatible USB/Bluetooth microphone and
  install/enable Android speech recognition and TTS if the device supports it.
  If neither recognition service nor a supporting recognizer Activity exists,
  this prototype cannot understand speech on that device.
- If an older GitHub debug APK was installed, updating may fail because
  separate CI runs use distinct debug signing keys. In that case uninstall
  the older JARVIS Gemini test app, install the new v0.3 APK, and re-import
  jarvis-gemini-key.json. Uninstall clears its device-local saved key.
- No Gemini Live streaming, continuous wake word or hands-free voice loop.

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
