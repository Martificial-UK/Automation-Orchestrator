"""\
Stops services started by installer/launch_services.py.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict

ROOT_DIR = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT_DIR / "run"


def _kill_pid(pid: int) -> bool:
    """Kill a process by PID. Returns True if successful."""
    if os.name == "nt":
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    else:
        try:
            os.kill(pid, signal.SIGTERM)
            return True
        except ProcessLookupError:
            return False


def _kill_port(port: int) -> None:
    """Kill all processes listening on a port."""
    if os.name == "nt":
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                if parts:
                    pid = parts[-1]
                    try:
                        subprocess.run(
                            ["taskkill", "/PID", pid, "/T", "/F"],
                            capture_output=True
                        )
                        print(f"Killed process {pid} listening on port {port}")
                    except Exception:
                        pass
    else:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True
        )
        for pid in result.stdout.strip().split():
            try:
                os.kill(int(pid), signal.SIGTERM)
                print(f"Killed process {pid} listening on port {port}")
            except Exception:
                pass


def main() -> int:
    state_file = RUN_DIR / "services.json"
    stopped_any = False

    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            pids: Dict[str, int] = state.get("pids", {})

            for name, pid in pids.items():
                if _kill_pid(pid):
                    print(f"Stopped {name} (PID {pid})")
                    stopped_any = True
        except Exception as e:
            print(f"Warning: Could not read services.json: {e}")

    # Also kill any lingering processes on port 8000
    _kill_port(8000)
    
    # Clean up state file
    if state_file.exists():
        try:
            state_file.unlink()
        except Exception:
            pass

    if not stopped_any:
        print("No running services found.")
    
    # Give processes time to shut down
    time.sleep(1)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
