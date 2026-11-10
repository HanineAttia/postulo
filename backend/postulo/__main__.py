"""`postulo` / `python -m postulo`: start the local server and open the browser.

Never asks anything in the terminal (SPEC section 3). Always binds to 127.0.0.1.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import socket
import sys
import threading
import time
import urllib.request
import webbrowser

import uvicorn

from postulo import APP_NAME, __version__, config

HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((HOST, port))
        except OSError:
            return False
        return True


def find_free_port(start: int = DEFAULT_PORT, attempts: int = 50) -> int:
    for port in range(start, start + attempts):
        if _port_is_free(port):
            return port
    raise RuntimeError(f"Aucun port libre entre {start} et {start + attempts - 1}.")


def running_instance(port: int) -> bool:
    """True if a Postulo server already answers on this port."""
    try:
        with urllib.request.urlopen(f"http://{HOST}:{port}/api/health", timeout=1) as resp:
            return bool(json.loads(resp.read()).get("app") == APP_NAME)
    except (OSError, ValueError):
        return False


def _open_browser_when_ready(server: uvicorn.Server, url: str) -> None:
    def wait_and_open() -> None:
        for _ in range(200):
            if server.started:
                webbrowser.open(url)
                return
            time.sleep(0.05)

    threading.Thread(target=wait_and_open, daemon=True).start()


def main(argv: list[str] | None = None) -> None:
    with contextlib.suppress(AttributeError, ValueError):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

    parser = argparse.ArgumentParser(prog="postulo", description=f"{APP_NAME} {__version__}")
    parser.add_argument("--port", type=int, default=None, help=f"port (default: {DEFAULT_PORT})")
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser")
    parser.add_argument("--reload", action="store_true", help="development: reload on changes")
    args = parser.parse_args(argv)

    if args.port is None and running_instance(DEFAULT_PORT):
        url = f"http://{HOST}:{DEFAULT_PORT}/"
        print(f"{APP_NAME} est déjà lancé : {url}", flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        return

    port = args.port or find_free_port()
    url = f"http://{HOST}:{port}/"
    print(f"{APP_NAME} {__version__} : {url}", flush=True)
    print(f"Données : {config.data_dir()}", flush=True)
    print("Ctrl+C pour arrêter.", flush=True)

    if args.reload:
        uvicorn.run(
            "postulo.app:create_app",
            factory=True,
            host=HOST,
            port=port,
            reload=True,
            reload_dirs=[str(config.PACKAGE_DIR)],
        )
        return

    from postulo.app import create_app

    server = uvicorn.Server(uvicorn.Config(create_app(), host=HOST, port=port, log_level="info"))
    if not args.no_browser:
        _open_browser_when_ready(server, url)
    server.run()


if __name__ == "__main__":
    main()
