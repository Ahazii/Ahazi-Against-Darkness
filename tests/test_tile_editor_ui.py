from __future__ import annotations

from pathlib import Path


TILE_EDITOR_HTML = Path("src/app/static/tile-editor.html").read_text(encoding="utf-8")
TILE_EDITOR_JS = Path("src/app/static/tile-editor.js").read_text(encoding="utf-8")
STYLES_CSS = Path("src/app/static/styles.css").read_text(encoding="utf-8")


def _function_body(name: str, src: str) -> str:
    marker = f"function {name}("
    start = src.find(marker)
    assert start != -1, f"function {name} not found"
    paren_start = src.index("(", start)
    depth = 0
    i = paren_start
    while i < len(src):
        if src[i] == "(":
            depth += 1
        elif src[i] == ")":
            depth -= 1
            if depth == 0:
                break
        i += 1
    brace = src.index("{", i)
    depth = 0
    for j, ch in enumerate(src[brace:], brace):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[brace + 1 : j]
    raise AssertionError(f"Could not find closing brace for function {name}")


def test_tile_editor_exits_have_delete_tool_and_help() -> None:
    assert 'data-mode="delete_exit"' in TILE_EDITOR_HTML
    assert 'data-mode="water_toggle"' in TILE_EDITOR_HTML
    assert 'id="tile-catalog"' in TILE_EDITOR_HTML
    assert 'id="room-code-fieldset"' in TILE_EDITOR_HTML
    assert "Click an existing door or passage marker to remove it." in TILE_EDITOR_HTML
    assert 'data-help-topic="exit-placement"' in TILE_EDITOR_HTML
    assert "Explain exit placement, inset padding, and deletion." in TILE_EDITOR_HTML
    assert "/static/tile-editor.js?v=0.37.6" in TILE_EDITOR_HTML
    assert '"z"' in TILE_EDITOR_JS and '"1"' in TILE_EDITOR_JS
    assert "semicircle" in TILE_EDITOR_JS
    assert 'data-mode="half_curve_cycle"' in TILE_EDITOR_HTML
    assert "HALF_CURVE_CYCLE" in TILE_EDITOR_JS
    assert "BIDIRECTIONAL_GRID_MODES" in TILE_EDITOR_JS
    assert "handleGridInteraction" in TILE_EDITOR_JS
    assert "cycleShapeList" in TILE_EDITOR_JS
    assert 'half_cycle: ["a", "b", "c", "d", "A", "B", "C", "D"]' in TILE_EDITOR_JS
    assert 'curve_cycle: ["e", "g", "h", "i", "J", "K", "L", "M"]' in TILE_EDITOR_JS
    assert "WALKABLE_SURFACE_CYCLE" in TILE_EDITOR_JS
    assert "cycleWalkableSurface" in TILE_EDITOR_JS
    assert "Left click forward / right click back" in TILE_EDITOR_HTML
    assert ".grid-square.shape-a::after" in STYLES_CSS
    assert ".grid-square.shape-l::after" in STYLES_CSS
    assert "100% 26%" in STYLES_CSS
    assert ".icon-half-curve" in STYLES_CSS


def test_tile_editor_delete_exit_tool_removes_markers() -> None:
    grid_click = _function_body("handleGridInteraction", TILE_EDITOR_JS)
    marker = _function_body("exitMarker", TILE_EDITOR_JS)

    assert 'if (editor.mode === "delete_exit")' in grid_click
    assert "removeExitAt(tile, x, y, direction);" in grid_click
    assert "function removeExit(tile, exitId)" in TILE_EDITOR_JS
    assert "function removeExitAt(tile, x, y, direction)" in TILE_EDITOR_JS
    assert 'if (editor.mode !== "delete_exit") return;' in marker
    assert "removeExit(tile, exit.id);" in marker
    assert "Drag to move; choose Delete Exit and click this marker to remove it." in marker


def test_tile_editor_documents_inset_exit_padding_rule() -> None:
    assert '"exit-placement": {' in TILE_EDITOR_JS
    assert '"room-codes": {' in TILE_EDITOR_JS
    assert 'editor.mode === "water_toggle"' in TILE_EDITOR_JS
    assert "surfaceClass" in TILE_EDITOR_JS
    assert "Door and passage markers store the exact square and side you place in the editor." in TILE_EDITOR_JS
    assert "gameplay keeps the marker in that authored position" in TILE_EDITOR_JS
    assert ".icon-delete-exit::before" in STYLES_CSS
    assert ".icon-delete-exit::after" in STYLES_CSS
