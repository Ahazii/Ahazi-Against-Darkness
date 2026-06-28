"""Reproduce party sheet render against Tower camped session."""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TOWER_DB = ROOT / ".data" / "game-tower-copy.db"
SESSION_ID = "75732205fb2d44d3aa5dd988fe00d587"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed")
        return 1

    tmp = ROOT / ".data" / "party-sheet-repro"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    shutil.copy2(TOWER_DB, tmp / "game.db")

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["DATA_DIR"] = str(tmp)
    env["PYTHONPATH"] = f"{SRC}{os.pathsep}{env.get('PYTHONPATH', '')}"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    errors: list[str] = []
    try:
        deadline = time.time() + 20
        while time.time() < deadline:
            if proc.poll() is not None:
                print("server died")
                return 1
            try:
                with urlopen(f"{base}/healthz", timeout=1) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                time.sleep(0.1)
        else:
            print("healthz timeout")
            return 1

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.on("console", lambda msg: errors.append(f"console.{msg.type}: {msg.text}") if msg.type == "error" else None)
            page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))

            page.goto(f"{base}/static/index.html")
            page.wait_for_function("typeof loadAll === 'function'", timeout=15000)
            page.evaluate(
                """async (sessionId) => {
                  await loadAll();
                  const session = await api(`/api/sessions/${sessionId}`);
                  state.session = session;
                  writeActiveSessionId(sessionId);
                  showGameView({ rememberView: false });
                  renderSession();
                }""",
                SESSION_ID,
            )
            page.wait_for_timeout(800)
            text = page.locator("#party-state").inner_text()
            browser.close()

        print("party-state text:")
        print(text[:4000])
        if errors:
            print("\nerrors:")
            for line in errors:
                print(line)
        if "Could not render party sheets" in text:
            return 2
        return 0
    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
