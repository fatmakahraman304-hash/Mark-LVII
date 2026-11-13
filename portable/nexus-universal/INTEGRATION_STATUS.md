# NEXUS integration status — source stage

The project now includes:
- Cross-platform device capability catalog
- Strict command protocol and scope mapping
- One-time invitation and revocable credential store
- Durable replay reservations and metadata audit chain
- Offline secure dispatch orchestration
- Loopback-only read-only gateway
- Python desktop HTTPS status client
- Android WebView client source
- Transport-neutral connection state machine
- Offline Turkish/English text-to-intent parser

**These components are not yet a fully integrated product.**
ConnectionManager transitions are driven by a future authenticated transport.
VoiceIntent is text parsing, not speech recognition. Neither component grants
device control or makes network calls.

Remaining high-priority implementation:
- Authenticated owner pairing UI, network API and TLS credential lifecycle
- Shared Android/desktop client protocol and native platform adapters
- Actual microphone consent and speech-to-text pipeline
- End-user UI, signed packaging, persistent recovery, release automation
- Final security, build and real-device tests

User requested comprehensive tests at the end. Do not describe any source
module as tested or production-ready before the final acceptance gates pass.
