from __future__ import annotations

from pathlib import Path


def test_frontend_keeps_dungeon_and_linked_inset_exits_visible() -> None:
   app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")

   assert "!exit.dungeon_exit && !exit.destination_tile_id && exitPointsInward(tile, exit)" in app_js


def test_frontend_map_navigation_uses_explicit_focus_controls() -> None:
    app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")

    assert "function renderMap(session, { skipFocus = false } = {})" in app_js
    assert "if (!skipFocus) scheduleMapFocus(session)" in app_js
    assert "function tileVisibleWorldBounds(tile)" in app_js
    assert "function visibleMapBounds(session)" in app_js
    assert "function zoomMapAtClientPoint(nextZoom, clientX, clientY)" in app_js
    assert "function handleMapWheel(event) {\n  event.preventDefault();" in app_js


def test_frontend_map_art_and_tactical_grid_do_not_stretch_current_room() -> None:
    app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")
    styles = Path("src/app/static/styles.css").read_text(encoding="utf-8")

    assert "!isCurrentTile && tileNeedsOwnershipClip" not in app_js
    assert "const ownershipClipped = tileNeedsOwnershipClip(tile, width, height, visible, cellOwnership);" in app_js
    assert "return Math.max(minCell, Math.min(cellFromWidth, cellFromHeight, maxCell));" in app_js
    assert ".tactical-room-stage {\n  position: relative;\n  flex: 0 0 auto;" in styles
