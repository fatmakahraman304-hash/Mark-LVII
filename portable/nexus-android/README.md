# JARVIS NEXUS Android client (prototype)

Native Android Java/Gradle starter for HY-320 Android 11 (1 GB RAM).
This is **source code**, not a compiled/tested APK.

## Build
Open this folder as an Android Studio project (JDK 17, Android SDK 35).
Use Android Gradle Plugin 8.6.1 and Gradle 8.7 (install compatible Gradle locally; wrapper not yet committed).
Build a debug APK with `gradle assembleDebug` using an appropriately configured Android SDK.
Do not install unverified binaries on devices.

## Behavior
- User manually opens the installed app and enters an authorized HTTPS JARVIS server URL.
- A single WebView displays the server UI, with no JavaScript-to-native bridge.
- HTTPS certificate errors are rejected. Off-origin navigation and mixed content are blocked.
- No auto-run on USB insertion, no elevated privileges, no arbitrary device control.
- Back/logout clears WebView cookies/cache. Server-side session revocation is not yet integrated.
- No microphone capture or voice command support in this prototype.
- APK install is still subject to Android user consent and device policy.

## Required next work
Build verification, Android 11 projector installation test, trusted LAN TLS certificate provisioning, auth pairing and server-side revocation, voice permission design, RAM profiling, and UI tests. Consider modernizing targetSdk after assessing Android TV compatibility and runtime permission behavior.
