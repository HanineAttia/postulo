"""Development launcher: backend with auto-reload + Vite dev server.

    uv run python scripts/dev.py

Open http://localhost:5173 (Vite proxies /api to the backend on port 8765).
A Python script instead of dev.ps1: PowerShell execution policies often block .ps1 files.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_PORT = "8765"


def main() -> int:
    pnpm = shutil.which("pnpm")
    if pnpm is None:
        print("pnpm est introuvable. Installe Node.js LTS puis pnpm (voir docs/dev-windows.md).")
        return 1
    if not (ROOT / "frontend" / "node_modules").is_dir():
        subprocess.run([pnpm, "install"], cwd=ROOT / "frontend", check=True)  # noqa: S603

    env = {**os.environ, "POSTULO_DEV": "1", "PYTHONUTF8": "1"}
    backend_cmd = [
        sys.executable,
        "-m",
        "postulo",
        "--reload",
        "--no-browser",
        "--port",
        BACKEND_PORT,
    ]
    processes = [
        subprocess.Popen(backend_cmd, cwd=ROOT, env=env),  # noqa: S603
        subprocess.Popen([pnpm, "dev"], cwd=ROOT / "frontend", env=env),  # noqa: S603
    ]
    print("Interface : http://localhost:5173  |  API : http://127.0.0.1:8765/api/docs")
    try:
        while all(p.poll() is None for p in processes):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                if sys.platform == "win32":
                    process.terminate()
                else:
                    process.send_signal(signal.SIGINT)
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
