from __future__ import annotations

from pathlib import Path


def test_frontend_keeps_dungeon_and_linked_inset_exits_visible() -> None:
   app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")

   assert "!exit.dungeon_exit && !exit.destination_tile_id && exitPointsInward(tile, exit)" in app_js


def test_frontend_map_navigation_uses_explicit_focus_controls() -> None:
    app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")

    assert "function renderMap(session, { skipFocus = false } = {})" in app_js
    assert 'mapEl.style.width = `${boundsWidth * cell}px`;' in app_js
    assert 'mapEl.style.height = `${boundsHeight * cell}px`;' in app_js
    assert "if (!skipFocus) scheduleMapFocus(session)" in app_js
    assert "function tileVisibleWorldBounds(tile)" in app_js
    assert "function visibleMapBounds(session)" in app_js
    assert "function zoomMapAtClientPoint(nextZoom, clientX, clientY)" in app_js
    assert "function handleMapWheel(event) {\n  event.preventDefault();" in app_js
    assert "state.mapPanX -= deltaX;" in app_js
    assert "state.mapPanY -= deltaY;" in app_js
    assert '".map-controls-overlay, .map-exit-menu, .map-context-menu' in app_js
    assert ".map-exit-marker.clickable, .map-content-marker.clickable, button" in app_js
    assert "const bounds = mapBounds(state.session);" in app_js
    assert "state.mapZoom = clampFloat(target * 0.92, MAP_MIN_ZOOM, MAP_MAX_ZOOM);" in app_js


def test_frontend_map_art_and_tactical_grid_do_not_stretch_current_room() -> None:
    app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")
    styles = Path("src/app/static/styles.css").read_text(encoding="utf-8")

    assert "!isCurrentTile && tileNeedsOwnershipClip" not in app_js
    assert "const ownershipClipped = tileNeedsOwnershipClip(tile, width, height, visible, cellOwnership);" in app_js
    assert "return Math.max(minCell, Math.min(cellFromWidth, cellFromHeight, maxCell));" in app_js
    assert ".tactical-room-stage {\n  position: relative;\n  flex: 0 0 auto;" in styles


def test_frontend_log_exits_row_is_resizable_without_exits_forcing_map_smaller() -> None:
    app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")
    styles = Path("src/app/static/styles.css").read_text(encoding="utf-8")
    index_html = Path("src/app/static/index.html").read_text(encoding="utf-8")

    assert 'id="log-map-resizer"\n              class="layout-resizer layout-resizer-horizontal"' in index_html
    assert "logMapResizer.classList.remove(\"hidden\")" in app_js
    assert "state.logPanelHeight = clampFloat(state.logPanelHeight + dy, 120, window.innerHeight * 0.68);" in app_js
    assert "mapLogRow.style.height = \"\";" in app_js
    assert ".map-log-row {\n  display: flex;" in styles
    assert "height: min(var(--log-panel-height, 240px), 58vh);" in styles
    assert ".map-exits-dock .map-exits-details[open] .map-exits-scroll {\n  flex: 1 1 auto;\n  min-height: 0;\n  max-height: none;" in styles
    assert ".map-exits-body {\n  display: grid;\n  grid-template-rows: minmax(0, 1fr) auto;\n  flex: 1 1 auto;" in styles
    assert ".map-exits-scroll {\n  flex: 1 1 auto;\n  min-height: 0;\n  max-height: 100%;" in styles
    assert "overflow-y: scroll;" in styles
    assert "calc(var(--exit-row-weight, var(--exit-row-count, 1)) * 100px)" not in styles


def test_frontend_exposes_deliberate_clue_spends() -> None:
    app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")
    index_html = Path("src/app/static/index.html").read_text(encoding="utf-8")

    assert 'id="clue-choices"' in index_html
    assert "function renderClueChoices(session)" in app_js
    assert 'safeSessionRender("clueChoices", () => renderClueChoices(session));' in app_js
    assert 'advance("reveal_secret_with_clues")' in app_js
    assert 'advance("learn_spell_with_clues"' in app_js
    assert '"clue_spends_table"' in app_js
    assert "held Clues are spent deliberately" in app_js


def test_frontend_marks_bloodied_foe_levels_as_effective() -> None:
    app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")

    assert "function foeLevelLabel(foe)" in app_js
    assert 'foe?.level_drop_applied ? `Eff L${level}` : `L${level}`' in app_js
    assert 'labels.push("Bloodied L drop");' in app_js
    assert "Life ${foe.life}/${foe.max_life} · ${foeLevelLabel(foe)}" in app_js
