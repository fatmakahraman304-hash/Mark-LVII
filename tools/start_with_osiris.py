"""Start the pinned local OSIRIS and JARVIS as one supervised session."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener
from prepare_osiris import prepare, fingerprint


def wait_ready(process, url, timeout=60):
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("OSIRIS stopped during startup; inspect the OSIRIS log.")
        try:
            with opener.open(url, timeout=2) as response:
                # The adapter file proves this is the prepared local instance.
                data = json.loads(response.read(1024))
                if data == {"jarvis_bridge": 1}:
                    return
        except (OSError, URLError, ValueError):
            pass
        time.sleep(.25)
    raise RuntimeError("OSIRIS startup timed out; inspect the OSIRIS log.")


def stop_owned(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("osiris_root", type=Path)
    parser.add_argument("--port", type=int, default=3010)
    parser.add_argument("--check-only", action="store_true", help="Start, health-check, then stop without opening JARVIS")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be in 1024..65535")
    root = args.osiris_root.resolve()
    node = shutil.which("node")
    if not node:
        parser.error("Node.js 20.9+ is required")
    version = subprocess.check_output([node, "--version"], text=True).strip().lstrip("v")
    if tuple(int(x) for x in version.split(".")[:2]) < (20, 9):
        parser.error("Node.js 20.9+ is required")
    prepare(root)
    next_bin = root / "node_modules/next/dist/bin/next"
    if not next_bin.is_file():
        parser.error("OSIRIS dependencies missing; run npm ci in the OSIRIS folder")
    marker = root / ".next/jarvis-build.json"
    try:
        stamped = json.loads(marker.read_text(encoding="utf-8"))["fingerprint"]
    except (OSError, ValueError, KeyError):
        stamped = None
    if not (root / ".next/BUILD_ID").is_file() or stamped != fingerprint(root):
        parser.error("Verified build missing or stale; run prepare_osiris.py ROOT --build")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", args.port))  # Fail on a busy port, never reuse/kill an unknown service.
    project = Path(__file__).resolve().parents[1]
    log_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local/share"))) / "Jarvis" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    url = f"http://127.0.0.1:{args.port}/"
    env = dict(os.environ, JARVIS_OSIRIS_URL=url, NEXT_TELEMETRY_DISABLED="1", JARVIS_MANAGED_RESTART="1")
    server = jarvis = None
    log_path = log_dir / "osiris.log"
    print("OSIRIS log:", log_path, flush=True)
    with log_path.open("a", encoding="utf-8") as log:
        try:
            server = subprocess.Popen([node, str(next_bin), "start",
                                       "--hostname", "127.0.0.1", "--port", str(args.port)],
                                      cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
            wait_ready(server, url + "jarvis-bridge-health.json")
            print("Local OSIRIS ready:", url, flush=True)
            if args.check_only:
                return
            jarvis = subprocess.Popen([sys.executable, "main.py"], cwd=project, env=env)
            warned = False
            while True:
                code = jarvis.poll()
                if code == 75:
                    jarvis = subprocess.Popen([sys.executable, "main.py"], cwd=project, env=env)
                elif code is not None:
                    break
                if server.poll() is not None and not warned:
                    print("OSIRIS stopped. JARVIS remains running; map requests may fail.", flush=True)
                    warned = True
                time.sleep(.5)
        finally:
            stop_owned(jarvis)
            stop_owned(server)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print("JARVIS/OSIRIS startup failed:", exc, file=sys.stderr)
        sys.exit(1)
