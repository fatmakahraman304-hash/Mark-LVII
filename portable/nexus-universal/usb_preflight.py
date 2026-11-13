"""Offline USB readiness check; no network, installs or paid calls."""
from __future__ import annotations
import importlib.util
import json
import platform
import sys
from pathlib import Path


def check(root: Path | None = None) -> dict:
    root = root or Path(__file__).resolve().parent
    required = ("desktop_client.py", "command_protocol.py", "capabilities.json",
                "nexus_core.py", "client_contract.py")
    missing = [name for name in required if not (root / name).is_file()]
    issues = []
    if sys.version_info < (3, 10):
        issues.append("Python 3.10+ required")
    if missing:
        issues.append("Missing files: " + ", ".join(missing))
    try:
        catalog = json.loads((root / "capabilities.json").read_text(encoding="utf-8"))
        if type(catalog) is not dict or catalog.get("schema_version") != 1:
            issues.append("Unsupported device catalog")
    except (OSError, UnicodeError, ValueError) as exc:
        issues.append("Device catalog cannot be read")
    return {
        "ready_for_read_only_client": not issues,
        "usb_autorun_supported": False,
        "real_device_control_ready": False,
        "platform": platform.system(),
        "python": platform.python_version(),
        "issues": issues,
    }


def main() -> int:
    result = check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready_for_read_only_client"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
