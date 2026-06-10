from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


@dataclass(frozen=True)
class LiveApp:
    base_url: str
    data_dir: Path

    def __str__(self) -> str:
        return self.base_url


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _json_request(base_url: str, path: str, payload: dict | None = None, *, method: str = "POST") -> dict:
    data = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    request = Request(
        f"{base_url}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


@pytest.fixture()
def live_app(tmp_path):
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    data_dir = tmp_path / "data"
    env = os.environ.copy()
    env["DATA_DIR"] = str(data_dir)
    env["PYTHONPATH"] = f"{SRC}{os.pathsep}{env.get('PYTHONPATH', '')}"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 15
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Test app exited before /healthz became available.")
        try:
            with urlopen(f"{base_url}/healthz", timeout=1) as response:
                if response.status == 200:
                    break
        except URLError:
            time.sleep(0.1)
    else:
        process.terminate()
        raise RuntimeError("Timed out waiting for test app /healthz.")

    try:
        yield LiveApp(base_url=base_url, data_dir=data_dir)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _create_session(base_url: str) -> str:
    class_ids = ["warrior", "cleric", "rogue", "wizard"]
    character_ids = []
    for index, class_id in enumerate(class_ids, start=1):
        character = _json_request(
            base_url,
            "/api/characters",
            {"name": f"Browser Map Check {index}", "class_id": class_id},
        )
        character_ids.append(character["id"])
    party = _json_request(
        base_url,
        "/api/parties",
        {"name": "Browser Map Check", "character_ids": character_ids},
    )
    session = _json_request(
        base_url,
        "/api/sessions",
        {
            "party_id": party["id"],
            "adventure_id": "random",
            "xp_system": "classical",
            "map_bounds_mode": "unlimited",
        },
    )
    return session["id"]


def _replace_session_map(live_app: LiveApp, session_id: str, map_state: dict) -> None:
    db_path = live_app.data_dir / "game.db"
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "select data from records where collection='sessions' and id=?",
            (session_id,),
        ).fetchone()
        assert row is not None
        session = json.loads(row[0])
        session["map_state"] = map_state
        connection.execute(
            "update records set data=?, updated_at=? where collection='sessions' and id=?",
            (json.dumps(session), session["updated_at"], session_id),
        )


def test_clipped_map_art_uses_valid_svg_clip_path(live_app) -> None:
    playwright_api = pytest.importorskip("playwright.sync_api")

    session_id = _create_session(live_app)
    _replace_session_map(
        live_app,
        session_id,
        {
            "width": 31,
            "height": 31,
            "current_tile_id": "clipped-corridor",
            "tiles": [
                {
                    "id": "existing-corridor",
                    "x": 0,
                    "y": 1,
                    "tile_key": "99",
                    "tile_type": "corridor",
                    "rotation": 0,
                    "footprint_width": 1,
                    "footprint_height": 1,
                    "editor_cell_size": 80,
                    "image_scale": 1.0,
                    "image_offset_x": 0,
                    "image_offset_y": 0,
                    "walkable": ["1"],
                    "cell_shapes": ["F"],
                    "visible": ["1"],
                    "image": None,
                    "title": "Existing Corridor",
                    "description": "Existing Corridor",
                    "content_key": "empty",
                    "objects": [],
                    "enemies": [],
                    "exits": [],
                },
                {
                    "id": "clipped-corridor",
                    "x": 0,
                    "y": 0,
                    "tile_key": "63",
                    "tile_type": "corridor",
                    "rotation": 180,
                    "footprint_width": 5,
                    "footprint_height": 3,
                    "editor_cell_size": 80,
                    "image_scale": 1.0,
                    "image_offset_x": 0,
                    "image_offset_y": 0,
                    "walkable": ["00100", "11111", "00100"],
                    "cell_shapes": ["FFFFF", "FFFFF", "FFFFF"],
                    "visible": ["00100", "11111", "00100"],
                    "image": "/assets/tiles/63.gif",
                    "title": "Clipped Corridor",
                    "description": "Clipped Corridor",
                    "content_key": "empty",
                    "objects": [],
                    "enemies": [],
                    "exits": [
                        {"id": "north", "direction": "north", "kind": "passage", "x": 2, "y": 1, "status": "unexplored"},
                        {"id": "south", "direction": "south", "kind": "door", "x": 2, "y": 1, "status": "unexplored"},
                        {"id": "east", "direction": "east", "kind": "passage", "x": 4, "y": 1, "status": "unexplored"},
                        {"id": "west", "direction": "west", "kind": "passage", "x": 0, "y": 1, "status": "blocked"},
                    ],
                },
            ],
        },
    )

    try:
        with playwright_api.sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True)
            except Exception as error:  # pragma: no cover - depends on local browser install
                pytest.skip(f"Playwright Chromium is not installed: {error}")
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 720})
                page.add_init_script(
                    f"""
                    localStorage.setItem("ahazi-against-darkness.active-session-id", {json.dumps(session_id)});
                    localStorage.setItem("ahazi-against-darkness.active-view", "game");
                    """
                )
                page.goto(f"{live_app}/?view=game")
                page.wait_for_selector('#map .placed-tile.current[title="Clipped Corridor"]', timeout=10_000)
                clip_state = page.evaluate(
                    """
                    () => {
                      const tile = document.querySelector('#map .placed-tile.current[title="Clipped Corridor"]');
                      const stage = tile?.querySelector(".map-image-stage");
                      const clipPath = tile?.querySelector(".map-clip-def clipPath");
                      const squares = Array.from(tile?.querySelectorAll(".map-square") || []);
                      return {
                        inlineClip: stage?.style.clipPath || "",
                        computedClip: stage ? getComputedStyle(stage).clipPath : "",
                        hiddenSquares: tile?.querySelectorAll(".map-square.hidden").length || 0,
                        westSeamIndexes: squares
                          .map((square, index) => square.classList.contains("clipped-edge-west") ? index : -1)
                          .filter((index) => index >= 0),
                        allSeamIndexes: squares
                          .map((square, index) => Array.from(square.classList)
                            .some((className) => className.startsWith("clipped-edge-")) ? index : -1)
                          .filter((index) => index >= 0),
                        rects: Array.from(clipPath?.querySelectorAll("rect") || []).map((rect) => ({
                          x: rect.getAttribute("x"),
                          y: rect.getAttribute("y"),
                          width: rect.getAttribute("width"),
                          height: rect.getAttribute("height"),
                        })),
                      };
                    }
                    """
                )
                assert clip_state["hiddenSquares"] == 9, clip_state
                assert clip_state["westSeamIndexes"] == [6], clip_state
                assert clip_state["allSeamIndexes"] == [6], clip_state
                assert clip_state["inlineClip"].startswith("url("), clip_state
                assert clip_state["computedClip"] != "none", clip_state
                assert clip_state["rects"] == [
                    {"x": "0.400000", "y": "0.000000", "width": "0.200000", "height": "0.333333"},
                    {"x": "0.200000", "y": "0.333333", "width": "0.200000", "height": "0.333333"},
                    {"x": "0.400000", "y": "0.333333", "width": "0.200000", "height": "0.333333"},
                    {"x": "0.600000", "y": "0.333333", "width": "0.200000", "height": "0.333333"},
                    {"x": "0.800000", "y": "0.333333", "width": "0.200000", "height": "0.333333"},
                    {"x": "0.400000", "y": "0.666667", "width": "0.200000", "height": "0.333333"},
                ]
            finally:
                browser.close()
    except playwright_api.Error as error:
        pytest.skip(f"Playwright browser test could not run: {error}")


def test_rm_recenters_current_room_after_rapid_wheel_zoom(live_app) -> None:
    playwright_api = pytest.importorskip("playwright.sync_api")

    session_id = _create_session(live_app)
    try:
        with playwright_api.sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True)
            except Exception as error:  # pragma: no cover - depends on local browser install
                pytest.skip(f"Playwright Chromium is not installed: {error}")
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 720})
                page.add_init_script(
                    f"""
                    localStorage.setItem("ahazi-against-darkness.active-session-id", {json.dumps(session_id)});
                    localStorage.setItem("ahazi-against-darkness.active-view", "game");
                    """
                )
                page.goto(f"{live_app}/?view=game")
                page.wait_for_selector("#map-viewport .placed-tile.current", state="visible", timeout=10_000)
                page.wait_for_timeout(250)

                pointer = page.evaluate(
                    """
                    () => {
                      const rect = document.getElementById("map-viewport").getBoundingClientRect();
                      return { x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2) };
                    }
                    """
                )
                page.mouse.move(pointer["x"], pointer["y"])
                for _ in range(20):
                    page.mouse.wheel(0, -120)
                page.locator("#map-zoom-room").click()

                page.wait_for_function(
                    """
                    () => {
                      const viewport = document.getElementById("map-viewport");
                      const current = document.querySelector("#map .placed-tile.current");
                      if (!viewport || !current) return false;
                      const viewportRect = viewport.getBoundingClientRect();
                      const currentRect = current.getBoundingClientRect();
                      const centerOffsetX =
                        (currentRect.left + currentRect.right) / 2 - (viewportRect.left + viewportRect.right) / 2;
                      const centerOffsetY =
                        (currentRect.top + currentRect.bottom) / 2 - (viewportRect.top + viewportRect.bottom) / 2;
                      const currentCenterVisible =
                        (currentRect.left + currentRect.right) / 2 >= viewportRect.left &&
                        (currentRect.left + currentRect.right) / 2 <= viewportRect.right &&
                        (currentRect.top + currentRect.bottom) / 2 >= viewportRect.top &&
                        (currentRect.top + currentRect.bottom) / 2 <= viewportRect.bottom;
                      return currentCenterVisible && Math.abs(centerOffsetX) <= 20 && Math.abs(centerOffsetY) <= 20;
                    }
                    """,
                    timeout=5_000,
                )
                geometry = page.evaluate(
                    """
                    () => {
                      const viewport = document.getElementById("map-viewport");
                      const current = document.querySelector("#map .placed-tile.current");
                      const viewportRect = viewport.getBoundingClientRect();
                      const currentRect = current.getBoundingClientRect();
                      return {
                        zoom: document.getElementById("map-zoom-label").textContent,
                        viewport: {
                          left: viewportRect.left,
                          right: viewportRect.right,
                          top: viewportRect.top,
                          bottom: viewportRect.bottom,
                          scrollLeft: viewport.scrollLeft,
                          scrollTop: viewport.scrollTop,
                        },
                        current: {
                          left: currentRect.left,
                          right: currentRect.right,
                          top: currentRect.top,
                          bottom: currentRect.bottom,
                        },
                      };
                    }
                    """
                )
                viewport = geometry["viewport"]
                current = geometry["current"]
                current_center_x = (current["left"] + current["right"]) / 2
                current_center_y = (current["top"] + current["bottom"]) / 2
                viewport_center_x = (viewport["left"] + viewport["right"]) / 2
                viewport_center_y = (viewport["top"] + viewport["bottom"]) / 2
                assert abs(current_center_x - viewport_center_x) <= 20, geometry
                assert abs(current_center_y - viewport_center_y) <= 20, geometry
            finally:
                browser.close()
    except playwright_api.Error as error:
        pytest.skip(f"Playwright browser test could not run: {error}")
