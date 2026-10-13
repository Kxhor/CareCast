"""Capture real screenshots of all CareCast screens across breakpoints in prod mode.
Phase 6: AT-41, AT-42, and VC-01..VC-16 verification.
"""

from __future__ import annotations

import hashlib
import os
import socket
import struct
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path("reports/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

WIDTHS = [320, 375, 768, 1280, 1440]

SCREENS = [
    ("s1-overview", "/overview"),
    ("s2-forecast", "/forecast"),
    ("s3-performance", "/performance"),
    ("s4-explain", "/explain"),
    ("s5-scenario", "/scenario"),
    ("s6-data", "/data"),
]


def find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def get_png_dimensions(path: Path) -> tuple[int, int]:
    with open(path, "rb") as f:
        f.seek(16)
        width, height = struct.unpack(">II", f.read(8))
        return width, height


def get_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main():
    port = find_free_port()
    db_path = "data/carecast.db"
    
    # Run the server in real prod mode with real DB
    runner_code = f"""
import carecast.db
orig = carecast.db.connect_ro
def patched(path='{db_path}'):
    import sqlite3
    from pathlib import Path
    p = Path(path).resolve()
    uri = f"file:{{p.as_posix()}}?mode=ro"
    c = sqlite3.connect(uri, uri=True, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA query_only = ON;")
    c.execute("PRAGMA foreign_keys = ON;")
    return c
carecast.db.connect_ro = patched

import uvicorn
from carecast.api.main import create_app
from carecast.settings import Settings

app = create_app(Settings(
    env="prod",
    db_path='{db_path}',
    enable_docs=False,
    rate_get_per_min=1000,
    rate_post_per_min=500
))
uvicorn.run(app, host="127.0.0.1", port={port}, log_level="warning")
"""
    proc = subprocess.Popen([sys.executable, "-c", runner_code])

    # Wait for server readiness
    ready = False
    for _ in range(50):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/health", timeout=1.0) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.1)

    assert ready, "Server failed to start in prod mode!"
    print(f"Server started in PROD mode on port {port}")

    captured_files = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)

            for width in WIDTHS:
                context = browser.new_context(viewport={"width": width, "height": 900})
                page = context.new_page()

                for screen_name, route_path in SCREENS:
                    url = f"http://127.0.0.1:{port}/#{route_path}"
                    filename = f"p6-{screen_name}-{width}.png"
                    out_path = SCREENSHOTS_DIR / filename

                    page.goto(url, wait_until="networkidle")
                    # Allow animations / charts to settle
                    time.sleep(0.6)

                    page.screenshot(path=str(out_path), full_page=True)
                    captured_files.append(out_path)
                    print(f"Captured {filename} ({width}px, {route_path})")

                context.close()

            browser.close()
    finally:
        proc.terminate()
        proc.wait(timeout=5)

    print("\n--- SCREENSHOT AUDIT VERIFICATION TABLE ---")
    print("| Filename | Dimensions (W x H) | Size (bytes) | SHA-256 |")
    print("|---|---|---|---|")
    for filepath in captured_files:
        w, h = get_png_dimensions(filepath)
        size = filepath.stat().st_size
        sha = get_file_sha256(filepath)
        print(f"| `{filepath.name}` | {w} × {h} | {size:,} | `{sha}` |")


if __name__ == "__main__":
    main()
