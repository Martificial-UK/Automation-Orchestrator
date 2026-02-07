"""\
Service launcher for Automation Orchestrator.
Starts Redis (if available), API server, and task worker.
"""

from __future__ import annotations

import atexit
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
import shutil

ROOT_DIR = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT_DIR / "run"
LOG_DIR = ROOT_DIR / "logs"
DEFAULT_CONFIG = ROOT_DIR / "config" / "sample_config.json"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _find_redis_server() -> Optional[Path]:
    env_path = os.getenv("REDIS_SERVER_PATH")
    if env_path:
        candidate = Path(env_path)
        if candidate.exists():
            return candidate

    vendor_dir = ROOT_DIR / "vendor" / "redis"
    if os.name == "nt":
        candidate = vendor_dir / "redis-server.exe"
    else:
        candidate = vendor_dir / "redis-server"
    if candidate.exists():
        return candidate

    which_path = shutil.which("redis-server")
    if which_path:
        return Path(which_path)

    return None


def _start_process(cmd: List[str], log_name: str, env: Dict[str, str]) -> subprocess.Popen:
    log_file = LOG_DIR / log_name
    log_handle = log_file.open("a", encoding="utf-8")
    log_handle.write(f"[{_now_iso()}] Starting: {' '.join(cmd)}\n")
    log_handle.flush()
    
    return subprocess.Popen(
        cmd,
        cwd=str(ROOT_DIR),
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    )


def main() -> int:
    config_path = os.getenv("AO_CONFIG", str(DEFAULT_CONFIG))
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["AO_CONFIG"] = config_path

    processes: Dict[str, subprocess.Popen] = {}

    redis_server = _find_redis_server()
    if redis_server:
        processes["redis"] = _start_process([str(redis_server)], "redis.log", env)
    else:
        (LOG_DIR / "redis.log").write_text(
            f"[{_now_iso()}] Redis server not found. Using fakeredis fallback.\n",
            encoding="utf-8"
        )

    workers_env = os.getenv("AO_UVICORN_WORKERS")
    if workers_env:
        workers = max(1, int(workers_env))
    else:
        workers = 1 if os.getenv("CI") else 4

    processes["api"] = _start_process(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.automation_orchestrator.wsgi:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--workers",
            str(workers)
        ],
        "api.log",
        env
    )

    processes["worker"] = _start_process(
        [sys.executable, "task_worker.py"],
        "worker.log",
        env
    )

    state = {
        "started_at": _now_iso(),
        "config": config_path,
        "pids": {name: proc.pid for name, proc in processes.items()}
    }
    (RUN_DIR / "services.json").write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _shutdown() -> None:
        for proc in processes.values():
            if proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass

    atexit.register(_shutdown)

    try:
        while True:
            time.sleep(1)
            for name, proc in list(processes.items()):
                if proc.poll() is not None:
                    (LOG_DIR / "launcher.log").open("a", encoding="utf-8").write(
                        f"[{_now_iso()}] {name} exited with code {proc.returncode}.\n"
                    )
    except KeyboardInterrupt:
        pass
    finally:
        _shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
