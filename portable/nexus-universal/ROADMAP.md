# JARVIS NEXUS UNIVERSAL — product completion roadmap

## Phase A — shared foundations (source code in progress)
- [x] Device catalog and offline selector
- [x] Allowlisted JSON command schema and TTL validation
- [x] In-memory device registry and adapter interface
- [x] SQLite-backed one-time invitation and revocable token store
- [ ] Real authenticated owner approval and pairing HTTP interface
- [ ] Persisted command replay prevention and audit records
- [ ] Capability negotiation from verified device adapters

## Phase B — real clients
- [ ] Windows signed portable client
- [ ] Android phone/TV signed and installable APK
- [ ] Linux desktop client
- [ ] macOS notarized client
- [ ] Vendor-supported Tizen/webOS control integrations
- [ ] Web-only fallbacks for platforms that prohibit USB execution

## Phase C — unified experience
- [ ] Shared responsive UI and accessible TV remote navigation
- [ ] Voice pipeline with explicit microphone consent
- [ ] JARVIS/FRIDAY backend session handoff
- [ ] Opt-in device actions with granular permissions
- [ ] Offline discovery, reconnect, token rotation, lost-device revocation
- [ ] Rate limits, audit logs and paid-inference guardrails

## Phase D — final verification (deferred at user request)
- [ ] Automated builds and unit/integration tests
- [ ] Cross-platform security review, fuzzing and failure tests
- [ ] Real Windows/Android TV/projector/phone and supported TV API trials
- [ ] RAM, battery and accessibility profiling
- [ ] Release signing, rollback, installation and upgrade verification

**Completion definition:** no feature is called complete until its platform
implementation, permission model, build and hardware acceptance gate pass.
Ordinary USB sticks do not run arbitrary code on insertion.
