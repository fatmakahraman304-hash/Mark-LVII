# Standalone USB/TV feasibility matrix

| Goal | Realistic? | Implementation |
|---|---|---|
| Plain USB plugged into an arbitrary TV runs Qwen3 8B | **No** | USB flash storage has no AI compute; TVs cannot run arbitrary EXEs from USB |
| HY-320 Android 11 (often 1 GB RAM / 8 GB ROM) runs Qwen3 8B on-device | **No** | Not enough RAM/storage for the model; verify actual variant |
| Laptop off + compatible HDMI TV + dedicated mini PC | **Yes, prototype** | TV Station on mini PC; HDMI carries video; Python/Ollama/model installed on mini PC |
| No internet after model download | **Yes, on capable host** | Local Ollama loopback inference only; test actual setup |
| USB only + TV Internet + third-party AI service | **Possible with provider** | Needs supported Android/browser client, explicit opt-in, internet, secure credentials and provider availability; **not implemented** |
| TV USB auto-run or automatic installation | **No general guarantee** | Explicit manual app launch/installation subject to OS rules |

## Hardware gate
- Recommend **at least 16 GB RAM** and compatible CPU; a sufficiently capable GPU improves speed.
- 8 GB VRAM helps Qwen3 8B, but actual throughput depends on CPU/GPU, quantization and context.
- Projector's HDMI input must be accessible. USB power output may not suffice to power a mini PC: use its own adapter. Use a keyboard/air mouse connected to the mini PC; TV remote control is not assumed.
- The target mini PC must have its **own copy** of Ollama and model downloaded; laptop's installation does not transfer.
- TV Station listens on \`127.0.0.1:18767\` on that host only. It is not remotely reachable from a TV's Android browser; HDMI mirrors the host UI.

## Remaining product work
Signed Windows/Linux builds without Python preinstallation; guided offline model
installation; app lifecycle/updates; projector remote support; power-loss recovery;
real-device testing; additional Android APK client with a secure independent
server option. Do not claim plug-and-play or universal platform compatibility.
