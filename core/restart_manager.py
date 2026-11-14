"""Start a reliable post-update JARVIS relaunch without Qt imports.

When JARVIS was started by the local OSIRIS supervisor, return control to
that supervisor (which restarts on main.py's exit code 75). Otherwise launch
a detached helper that waits for the running process to release audio/Qt
resources before opening the updated main.py.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def schedule_restart(project_root: Path, current_pid: int,
                     executable: str | None = None) -> str:
    """Schedule restart, or raise *before* the existing GUI is closed.

    This function never kills the old process. Calling Qt code can request
    application quit only after this function has returned successfully.
    """
    if not isinstance(current_pid, int) or current_pid <= 0:
        raise ValueError("JARVIS yeniden başlatma PID değeri geçersiz.")

    if os.environ.get("JARVIS_MANAGED_RESTART") == "1":
        # tools/start_with_osiris.py will restart exit code 75.
        return "managed"

    project = Path(project_root).resolve()
    helper = project / "tools" / "restart_app.py"
    if not helper.is_file():
        raise FileNotFoundError(
            f"Yeniden başlatma aracı bulunamadı: {helper}"
        )
    python = str(executable or sys.executable)
    if not Path(python).is_file():
        raise FileNotFoundError(
            f"JARVIS Python yürütülebilir dosyası bulunamadı: {python}"
        )

    log_root = Path(os.environ.get("LOCALAPPDATA")
                    or str(Path.home() / ".local" / "share"))
    log_dir = log_root / "Jarvis" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / "restart.log").open("a", encoding="utf-8") as log:
        helper_proc = subprocess.Popen(
            [python, str(helper), str(current_pid), str(project)],
            cwd=str(project),
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=(0x08000000 if os.name == "nt" else 0),
            start_new_session=(os.name != "nt"),
        )
    if helper_proc.poll() is not None and helper_proc.returncode != 0:
        raise RuntimeError(
            "Yeniden başlatma aracı hemen sonlandı. "
            "Jarvis/logs/restart.log dosyasını kontrol edin."
        )
    return "helper"
