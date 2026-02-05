"""\
Stops services started by installer/launch_services.py.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Dict

ROOT_DIR = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT_DIR / "run"


def _kill_pid(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return


def main() -> int:
    state_file = RUN_DIR / "services.json"
    if not state_file.exists():
        print("No running services found.")
        return 0

    state = json.loads(state_file.read_text(encoding="utf-8"))
    pids: Dict[str, int] = state.get("pids", {})

    for name, pid in pids.items():
        _kill_pid(pid)
        print(f"Stopped {name} (PID {pid})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
