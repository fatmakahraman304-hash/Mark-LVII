# JARVIS NEXUS — Standalone TV Station v0.1 (prototype)

**Laptop-independent** means the TV uses a *separately powered local AI
computer*, not that a plain USB flash drive can perform inference.

## What this version actually does
- Windows, Linux or macOS host with **Python 3.10+, Ollama and qwen3:8b**
- Ollama inference happens on **that host only**, including without internet
  once the model has been downloaded
- Display the host's screen on a TV/projector through **HDMI**
- Launch from USB with \`TV-BASLAT.cmd\` (Windows) or
  \`sh TV-BASLAT.sh\` (Linux/macOS)
- Open \`http://127.0.0.1:18767/\` on the same computer if needed
- TV-friendly browser chat, connection diagnostics, bounded conversation
  history, no stored conversations, local-only server
- No remote device control, wake word, television integration, internet AI,
  paid API, background autorun or privilege escalation

## Hardware and setup
An HDMI-equipped mini PC with **at least 16 GB RAM recommended** for Qwen3 8B.
A capable GPU is preferable; CPU-only operation may be slow. The USB carries
the launcher/app; the host must have Python, Ollama, and the model installed.
Install Ollama and \`ollama pull qwen3:8b\` **on the mini PC**, not the laptop.
Do not expose Ollama on a LAN or disable authentication/TLS to make it work.

TV and Android projectors are used as HDMI displays only, so Android APK/USB
app restrictions do not apply to the TV Station path. HDMI inputs vary by device.

## HY-320 Android 11 / 1 GB RAM
- Qwen3 8B **cannot realistically run on the projector itself**.
- A USB stick cannot auto-install/auto-run arbitrary Android code.
- Use the mini-PC HDMI path for offline, laptop-independent AI.
- Alternative future path: approved Android TV APK that uses internet AI with
  explicit opt-in, permissions and secure remote credentials. That is *not*
  offline or free by default and is not implemented here.

## Security limitations
Loopback-only HTTP; Host and Origin guards; per-run anti-CSRF token; one
inference at a time; limited request/body/response sizes; no shell commands,
no prompts written to disk. HTTPS is unnecessary across a single-device
loopback, but **this must never be bound to a LAN interface**.
Local browser/processes on the AI host are in the trust boundary.

This is prototype source, not a signed installer or preconfigured appliance.
End-to-end HDMI, GPU performance, remotes, USB removal/reinsertion and
real hardware have not yet been tested.
