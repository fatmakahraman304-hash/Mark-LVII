"""Apply the local map adapter only to the audited OSIRIS revision."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

REVISION = "fa394afbc49f6eaa43446f7cc321590556cd665b"
# Refuse upstream changes instead of guessing at React internals.
PAGE_SHA256 = "3dcd69b52958b483ca3917722f70555a908456c2816c62f435f0f3759047baac"
MIDDLEWARE_SHA256 = "acd19d981121ef248fc619a3ccf8abe8fc7df6ca161c0dabdb8697d7bf7cb0a0"
IMPORT = "import { installJarvisBridge } from '@/lib/jarvis-bridge.mjs';\n"
ANCHOR = "  const assist = useAssist({"
HOOK = "  useEffect(() => installJarvisBridge(assistSite), [assistSite]);\n"


def prepare(root: Path) -> None:
    root = root.resolve()
    revision = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if revision != REVISION:
        raise ValueError("OSIRIS revision mismatch; expected " + REVISION)
    page = root / "src/app/page.tsx"
    source = page.read_text(encoding="utf-8")
    clean = source.replace("\n" + IMPORT, "", 1).replace(HOOK, "", 1)
    if hashlib.sha256(clean.encode()).hexdigest() != PAGE_SHA256:
        raise ValueError("OSIRIS page differs from the audited source; no files changed")
    middleware = root / "src/middleware.ts"
    profile = Path(__file__).resolve().parents[1] / "integrations/osiris/local-middleware.ts"
    current = middleware.read_text(encoding="utf-8").encode()
    if hashlib.sha256(current).hexdigest() != MIDDLEWARE_SHA256 and current != profile.read_text(encoding="utf-8").encode():
        raise ValueError("OSIRIS middleware differs; no files changed")
    patched = clean.replace("'use client';\n", "'use client';\n\n" + IMPORT, 1)
    # Keep idempotence: the import's separating blank line is part of the patch.
    patched = patched.replace(ANCHOR, HOOK + ANCHOR, 1)
    adapter = Path(__file__).resolve().parents[1] / "integrations/osiris/jarvis-bridge.mjs"
    shutil.copyfile(adapter, root / "src/lib/jarvis-bridge.mjs")
    page.write_text(patched, encoding="utf-8", newline="\n")
    shutil.copyfile(profile, middleware)
    (root / "public/jarvis-bridge-health.json").write_text('{"jarvis_bridge":1}', encoding="utf-8")
    print("OSIRIS local bridge prepared at pinned revision", REVISION)


def fingerprint(root: Path) -> str:
    digest = hashlib.sha256(REVISION.encode())
    for name in ("src/app/page.tsx", "src/lib/jarvis-bridge.mjs", "src/middleware.ts"):
        digest.update((root / name).read_text(encoding="utf-8").encode())
    return digest.hexdigest()


def build(root: Path) -> None:
    node = shutil.which("node")
    if not node:
        raise ValueError("Node.js is required")
    marker = root / ".next/jarvis-build.json"
    marker.unlink(missing_ok=True)
    env = dict(os.environ, NEXT_TELEMETRY_DISABLED="1")
    subprocess.run([node, "tools/prepare-map-worker.mjs"], cwd=root, env=env, check=True)
    subprocess.run([node, "node_modules/next/dist/bin/next", "build"], cwd=root, env=env, check=True)
    marker.write_text(json.dumps({"fingerprint": fingerprint(root)}), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    prepare(args.root)
    if args.build:
        build(args.root.resolve())
