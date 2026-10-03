"""
Marks Analyser — Desktop Application Launcher
Launches Flask in the background and opens Marks Analyser in a dedicated
frameless/app-mode native desktop window without browser URL bars or tabs.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from app import app

PORT = 5000
URL = f"http://127.0.0.1:{PORT}"


def run_flask_backend():
    # Run the Flask analytical engine quietly
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)


def open_desktop_window():
    time.sleep(1.2)  # Wait for server to bind

    # 1. Option A: pywebview if available
    try:
        import webview
        window = webview.create_window(
            title="Marks Analyser",
            url=URL,
            width=1320,
            height=860,
            min_size=(960, 640),
            resizable=True
        )
        webview.start()
        os._exit(0)
    except ImportError:
        pass

    # 2. Option B: Native Windows Edge/Chrome App Mode (zero browser chrome/URL bar)
    browser_candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]

    for exe in browser_candidates:
        if os.path.isfile(exe):
            print(f"[Marks Analyser] Launching Desktop Window via: {exe}")
            proc = subprocess.Popen([
                exe,
                f"--app={URL}",
                "--window-size=1320,860",
                "--app-id=marks-analyser-desktop"
            ])
            proc.wait()
            os._exit(0)

    # 3. Fallback: Default Browser
    import webbrowser
    webbrowser.open(URL)


if __name__ == "__main__":
    print("==================================================")
    print("      MARKS ANALYSER — DESKTOP WORKSPACE          ")
    print("==================================================")
    print(f"Backend Server Starting on {URL} ...")
    
    server_thread = threading.Thread(target=run_flask_backend, daemon=True)
    server_thread.start()

    open_desktop_window()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Marks Analyser] Closing application...")
        sys.exit(0)
