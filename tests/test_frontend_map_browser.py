from __future__ import annotations

import json
import os
import re
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


def _json_get(base_url: str, path: str):
    with urlopen(f"{base_url}{path}", timeout=5) as response:
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


def _create_session(base_url: str, *, adventure_id: str = "random") -> str:
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
            "adventure_id": adventure_id,
            "xp_system": "classical",
            "map_bounds_mode": "unlimited",
        },
    )
    return session["id"]


def _patch_session_record(live_app: LiveApp, session_id: str, patch: dict) -> None:
    db_path = live_app.data_dir / "game.db"
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "select data from records where collection='sessions' and id=?",
            (session_id,),
        ).fetchone()
        assert row is not None
        session = json.loads(row[0])
        session.update(patch)
        connection.execute(
            "update records set data=?, updated_at=? where collection='sessions' and id=?",
            (json.dumps(session), session["updated_at"], session_id),
        )


def test_generated_rumor_4_entry_choices_are_visible_beneath_narrative(live_app) -> None:
    playwright_api = pytest.importorskip("playwright.sync_api")
    generated = _json_request(
        live_app.base_url,
        "/api/campaign/tag/create-adventure",
        {"lead_type": "rumor", "detail": "4"},
    )
    session_id = _create_session(
        live_app.base_url,
        adventure_id=generated["adventure_id"],
    )
    session = _json_get(live_app.base_url, f"/api/sessions/{session_id}")
    assert session["active_quest"]["key"] == "imported_room"

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
            banner = page.locator("#current-objective-banner")
            playwright_api.expect(banner).to_be_visible(timeout=10_000)
            playwright_api.expect(banner).to_have_class(re.compile(r"\bnarrative-choices\b"))
            playwright_api.expect(banner.locator("button")).to_have_count(2)
            playwright_api.expect(
                banner.get_by_role("button", name="Investigate", exact=True)
            ).to_be_visible()
            playwright_api.expect(
                banner.get_by_role("button", name="Not now — return to town", exact=True)
            ).to_be_visible()
            playwright_api.expect(banner).not_to_contain_text("Quest progress")
        finally:
            browser.close()


def test_legacy_imported_medusa_quest_uses_scene_1_guided_controls(live_app) -> None:
    playwright_api = pytest.importorskip("playwright.sync_api")
    generated = _json_request(
        live_app.base_url,
        "/api/campaign/tag/create-adventure",
        {"lead_type": "rumor", "detail": "2"},
    )
    session_id = _create_session(
        live_app.base_url,
        adventure_id=generated["adventure_id"],
    )
    session = _json_get(live_app.base_url, f"/api/sessions/{session_id}")
    entry_actions = session["imported_manifest"]["source"]["parameters"]["tag_reference"]["room_prompts"][
        "tag-lead-entry"
    ]["actions"]
    moved = _json_request(
        live_app.base_url,
        f"/api/sessions/{session_id}/tag-route-action",
        {
            "route_action": "unlock_scene",
            "reference": entry_actions[0]["reference"],
        },
    )["session"]
    legacy_quest = dict(moved["active_quest"])
    legacy_quest.update({"key": "imported_boss", "completed": False, "reward_claimed": False})
    _patch_session_record(live_app, session_id, {"active_quest": legacy_quest})
    resumed = _json_get(live_app.base_url, f"/api/sessions/{session_id}")
    assert resumed["active_quest"]["key"] == "imported_boss"

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
            banner = page.locator("#current-objective-banner")
            playwright_api.expect(banner.locator(".medusa-scene1-guided")).to_be_visible(timeout=10_000)
            playwright_api.expect(
                banner.get_by_role("button", name="Approach the cabin", exact=True)
            ).to_be_visible()
            playwright_api.expect(
                banner.get_by_role("button", name="Shout out to Xasartha", exact=True)
            ).to_be_visible()
        finally:
            browser.close()


def _replace_session_map(live_app: LiveApp, session_id: str, map_state: dict) -> None:
    _patch_session_record(live_app, session_id, {"map_state": map_state})


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


def test_diagonal_exit_marker_renders_on_game_map(live_app) -> None:
    playwright_api = pytest.importorskip("playwright.sync_api")
    session_id = _create_session(live_app)
    _replace_session_map(
        live_app,
        session_id,
        {
            "width": 31,
            "height": 31,
            "current_tile_id": "diagonal-room",
            "tiles": [
                {
                    "id": "diagonal-room",
                    "x": 0,
                    "y": 0,
                    "tile_key": "99",
                    "tile_type": "room",
                    "rotation": 0,
                    "footprint_width": 3,
                    "footprint_height": 3,
                    "editor_cell_size": 80,
                    "image_scale": 1.0,
                    "image_offset_x": 0,
                    "image_offset_y": 0,
                    "walkable": ["111", "111", "111"],
                    "cell_shapes": ["FFF", "FFF", "FFF"],
                    "visible": ["111", "111", "111"],
                    "image": None,
                    "title": "Diagonal Room",
                    "description": "Diagonal Room",
                    "content_key": "empty",
                    "objects": [],
                    "enemies": [],
                    "exits": [
                        {
                            "id": "northeast-wide",
                            "direction": "northeast",
                            "kind": "passage",
                            "x": 0,
                            "y": 0,
                            "span": 2,
                            "status": "unexplored",
                        }
                    ],
                }
            ],
        },
    )

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
            page.locator("#map .placed-tile.current").wait_for(timeout=10_000)
            marker = page.locator("#map .map-exit-marker.northeast")
            debug = page.evaluate(
                """
                () => ({
                  markers: Array.from(document.querySelectorAll("#map .map-exit-marker")).map((item) => item.className),
                  tile: document.querySelector("#map .placed-tile.current")?.outerHTML.slice(0, 1500),
                })
                """
            )
            assert marker.count() == 1, debug
            state = marker.evaluate(
                """
                (element) => ({
                  transform: element.style.transform,
                  width: element.style.width,
                  label: element.querySelector(".map-exit-marker-label")?.textContent || "",
                })
                """
            )
            assert "rotate(45deg)" in state["transform"], state
            assert float(state["width"].rstrip("%")) > 20, state
            assert "NE" in state["label"], state
        finally:
            browser.close()


def test_river_23_blocked_padding_exit_anchor_renders_at_inner_edge(live_app) -> None:
    playwright_api = pytest.importorskip("playwright.sync_api")
    tiles = _json_get(live_app.base_url, "/api/rules/tiles?catalog=forsaken_depths_rivers")
    tile = next(item for item in tiles if item["key"] == "23")
    tile.update(
        {
            "tile_type": "corridor",
            "footprint_width": 3,
            "footprint_height": 1,
            "walkable": ["120"],
            "cell_shapes": ["FFF"],
            "exits": [
                {
                    "id": "river-23-east-padding",
                    "label": "",
                    "direction": "east",
                    "kind": "passage",
                    "x": 2,
                    "y": 0,
                    "span": 1,
                    "offset": 0,
                    "position": 0.5,
                    "dungeon_exit": False,
                }
            ],
        }
    )
    _json_request(
        live_app.base_url,
        "/api/rules/tiles?catalog=forsaken_depths_rivers",
        tiles,
        method="PUT",
    )

    with playwright_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as error:  # pragma: no cover - depends on local browser install
            pytest.skip(f"Playwright Chromium is not installed: {error}")
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{live_app}/static/tile-editor.html?catalog=forsaken_depths_rivers")
            page.get_by_role("button", name=re.compile(r"^23 Forsaken Depths River 23")).click()
            page.get_by_text("All exits have traversable interior squares", exact=True).wait_for(timeout=10_000)
            marker = page.locator(".exit-marker.east")
            assert marker.count() == 1
            state = marker.evaluate(
                """
                (element) => ({
                  left: Number.parseFloat(element.style.left),
                  className: element.className,
                })
                """
            )
            assert 66 <= state["left"] <= 67, state
            assert "passage" in state["className"], state
        finally:
            browser.close()


def test_tile_editor_persists_tile_46_east_exit_span(live_app) -> None:
    playwright_api = pytest.importorskip("playwright.sync_api")

    try:
        with playwright_api.sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True)
            except Exception as error:  # pragma: no cover - depends on local browser install
                pytest.skip(f"Playwright Chromium is not installed: {error}")
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                page.goto(f"{live_app}/static/tile-editor.html")
                page.locator("#tile-catalog").select_option("forsaken_depths")
                page.get_by_role("button", name="46 Forsaken Depths Tile 46 1 error", exact=True).click()

                exit_row = page.locator(".visual-exit-row").filter(has_text="North 1 Passage")
                exit_row.get_by_role("button", name="E", exact=True).click()
                exit_row = page.locator(".visual-exit-row").filter(has_text="East 1 Passage")
                exit_row.get_by_label("Span", exact=True).fill("2")
                exit_row.get_by_label("Span", exact=True).press("Enter")

                expect = playwright_api.expect
                expect(exit_row).to_contain_text("canonical east, square 5,1, span 2")
                page.get_by_role("button", name="Save Metadata", exact=True).click()
                expect(page.locator("#editor-status")).to_have_text("Saved")

                page.reload()
                page.locator("#tile-catalog").select_option("forsaken_depths")
                page.get_by_role("button", name="46 Forsaken Depths Tile 46 1 error", exact=True).click()
                saved_row = page.locator(".visual-exit-row").filter(has_text="East 1 Passage")
                expect(saved_row).to_contain_text("canonical east, square 5,1, span 2")
                expect(saved_row.get_by_label("Span", exact=True)).to_have_value("2")
            finally:
                browser.close()
    except playwright_api.Error as error:
        pytest.skip(f"Playwright browser test could not run: {error}")


def test_tile_editor_water_mode_paints_partial_river_shapes(live_app) -> None:
    playwright_api = pytest.importorskip("playwright.sync_api")

    try:
        with playwright_api.sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True)
            except Exception as error:  # pragma: no cover - depends on local browser install
                pytest.skip(f"Playwright Chromium is not installed: {error}")
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                page.goto(f"{live_app}/static/tile-editor.html")
                page.locator("#tile-catalog").select_option("forsaken_depths_rivers")

                water = page.get_by_role("button", name="Water", exact=True)
                water.click()
                expect = playwright_api.expect
                expect(water).to_have_attribute("aria-pressed", "true")
                expect(page.locator("#editor-tools")).to_have_class(
                    re.compile(r"\bwater-paint-active\b")
                )

                page.get_by_role("button", name="Half", exact=True).click()
                page.get_by_role("button", name="Walkable square 1,1", exact=True).click()
                partial_water = page.get_by_role(
                    "button",
                    name="Water with Blocked NE quarter square 1,1",
                    exact=True,
                )
                expect(partial_water).to_have_class(re.compile(r"\bwater\b"))
                expect(partial_water).to_have_class(re.compile(r"\bshape-a\b"))

                page.get_by_role("button", name="Walk/Block", exact=True).click()
                page.get_by_role("button", name="Walkable square 2,1", exact=True).click()
                expect(page.get_by_role("button", name="Water square 2,1", exact=True)).to_be_visible()

                page.get_by_role("button", name="Save Metadata", exact=True).click()
                expect(page.locator("#editor-status")).to_have_text("Saved")
                page.reload()
                page.locator("#tile-catalog").select_option("forsaken_depths_rivers")
                expect(
                    page.get_by_role(
                        "button",
                        name="Water with Blocked NE quarter square 1,1",
                        exact=True,
                    )
                ).to_be_visible()
                expect(page.get_by_role("button", name="Water square 2,1", exact=True)).to_be_visible()
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
