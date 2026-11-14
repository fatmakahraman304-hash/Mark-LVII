"""Wait for the old process to release audio/Qt resources before relaunching."""
import os
from pathlib import Path
import subprocess
import sys
import psutil


def restart(pid, project):
    try:
        psutil.Process(pid).wait(timeout=120)
    except psutil.NoSuchProcess:
        pass
    except psutil.TimeoutExpired:
        print('Restart cancelled: original JARVIS did not exit.', flush=True)
        return 1
    subprocess.Popen([sys.executable, str(Path(project) / 'main.py')], cwd=project,
                     stdout=sys.stdout, stderr=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(restart(int(sys.argv[1]), sys.argv[2]))
