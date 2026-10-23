"""Eclipse desktop app: starts the core on a free local port, then opens a NATIVE window
(Edge WebView2 on Windows, WebKit on macOS) — no browser, no address bar.

    pythonw desktop.py          (the shortcut runs this; no console window)
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def free_port(pref: int = 5173) -> int:
    for p in (pref, 0):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            return s.getsockname()[1]
        except OSError:
            continue
        finally:
            s.close()
    return pref


def wait_up(url: str, seconds: float = 20) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        try:
            urllib.request.urlopen(url + "/api/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


def single_instance():
    """Hold a fixed local port as a lock so two copies never fight over chats/settings."""
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 47615))
        return s
    except OSError:
        return None


def start_core(port: int) -> None:
    from nightcrew import server
    threading.Thread(target=server.main, args=(["--port", str(port)],), daemon=True).start()


def main() -> int:
    lock = single_instance()
    if lock is None:
        print("Eclipse is already running.")
        return 0
    try:
        import webview
    except ImportError:
        print("Missing pywebview: python -m pip install -r requirements.txt")
        return 1
    port = free_port()
    start_core(port)
    url = f"http://127.0.0.1:{port}"
    if not wait_up(url):
        print("The Eclipse core did not start; see the log above.")
        return 1
    icon = os.path.join(ROOT, "assets", "icon.ico" if sys.platform == "win32" else "icon.png")
    webview.create_window("Eclipse", url, width=1360, height=860, min_size=(900, 560),
                          background_color="#0A0A0A", text_select=True)
    webview.start(private_mode=False, icon=icon if os.path.isfile(icon) else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
