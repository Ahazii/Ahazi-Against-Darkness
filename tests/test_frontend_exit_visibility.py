from __future__ import annotations

from pathlib import Path


def test_frontend_traces_inset_exits_instead_of_hiding_them() -> None:
    app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")

    assert "function exitPortalEdgeLocal(tile, exit, width, height)" in app_js
    assert "function exitPortalDisplayLocal(tile, exit, width, height)" in app_js
    assert "if (isEntranceMapElement(tile)) return authoredExitPortalLocal(exit, width, height);" in app_js
    assert "const portal = exitPortalDisplayLocal(tile, exit, width, height);" in app_js
    assert "exitPortalEdgeLocal(tile, exit, width, height).outside" in app_js
    assert "exitPointsInward" not in app_js
    assert "!exit.dungeon_exit && !exit.destination_tile_id && exitPointsInward(tile, exit)" not in app_js


def test_frontend_map_ownership_lets_new_tiles_replace_soft_padding() -> None:
    app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")

    assert "function isEntranceMapElement(tile)" in app_js
    assert "const hardTiles = [\n    ...tiles.filter((tile) => isEntranceMapElement(tile))" in app_js
    assert "const walkable = normalizedWalkable(tile, width, height);" in app_js
    assert 'if (walkable[y]?.[x] === "0") continue;' in app_js
    assert "const softTiles = [...tiles].reverse();" in app_js
    assert 'if (walkable[y]?.[x] !== "0") continue;' in app_js
    assert "if (isEntranceMapElement(tile)) return false;" not in app_js


def test_frontend_map_navigation_uses_explicit_focus_controls() -> None:
    app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")

    assert "function renderMap(session, { skipFocus = false, viewRevision = null } = {})" in app_js
    assert 'mapEl.style.width = `${boundsWidth * cell}px`;' in app_js
    assert 'mapEl.style.height = `${boundsHeight * cell}px`;' in app_js
    assert "if (!skipFocus) scheduleMapFocus(session)" in app_js
    assert "function tileVisibleWorldBounds(tile)" in app_js
    assert "function visibleMapBounds(session)" in app_js
    assert "function zoomMapAtClientPoint(nextZoom, clientX, clientY)" in app_js
    assert "function mapContentPointForClient(clientX, clientY)" in app_js
    assert "function positionMapContentAtPointer(ratioX, ratioY, pointerX, pointerY, { instant = false } = {})" in app_js
    assert "function handleMapWheel(event) {\n  event.preventDefault();" in app_js
    assert "const totalMove = Math.hypot(moveEvent.clientX - startX, moveEvent.clientY - startY);" in app_js
    assert "state.mapSuppressClick = true;" in app_js
    assert '".map-controls-overlay, .map-exit-menu, .map-context-menu' in app_js
    assert ".map-exit-marker.clickable, .map-content-marker.clickable, button" not in app_js
    assert "const bounds = visibleMapBounds(state.session);" in app_js
    assert "state.mapZoom = clampFloat(target * 0.92, MAP_MIN_ZOOM, MAP_MAX_ZOOM);" in app_js
    assert 'mapCenterCurrent.addEventListener("click", centerCurrentTile);' in app_js


def test_frontend_map_art_and_tactical_grid_do_not_stretch_current_room() -> None:
    app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")
    styles = Path("src/app/static/styles.css").read_text(encoding="utf-8")

    assert "!isCurrentTile && tileNeedsOwnershipClip" not in app_js
    assert "const ownershipClipped = tileNeedsOwnershipClip(tile, width, height, visible, cellOwnership);" in app_js
    assert "return Math.max(minCell, Math.min(cellFromWidth, cellFromHeight, maxCell));" in app_js
    assert ".tactical-room-stage {\n  position: relative;\n  flex: 0 0 auto;" in styles


def test_frontend_expert_skill_buttons_have_hover_text() -> None:
    app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")

    assert "function skillOptionTooltip(option, fork)" in app_js
    assert "setButtonTooltip(skillBtn, skillOptionTooltip(option, fork));" in app_js
    assert "Eligible classes:" in app_js
    assert "Requires a monster type target when chosen." in app_js
    assert "Minimum level:" in app_js


def test_combat_minimap_uses_displayed_cells_not_full_tile_rectangles() -> None:
    app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")
    styles = Path("src/app/static/styles.css").read_text(encoding="utf-8")

    assert "const bounds = visibleMapBounds(session);" in app_js
    assert "const cellOwnership = buildMapCellOwnership(session);" in app_js
    assert "function displayedMinimapCells(tile, cellOwnership)" in app_js
    assert "const walkable = normalizedWalkable(tile, width, height);" in app_js
    assert 'if (walkable[y]?.[x] === "0") continue;' in app_js
    assert "isMapCellDisplayed(tile, x, y, visible, cellOwnership)" in app_js
    assert 'node("span", "combat-minimap-cell")' in app_js
    assert ".combat-minimap-tile {\n  position: absolute;\n  box-sizing: border-box;\n  background: transparent;" in styles
    assert ".combat-minimap-cell {\n  position: absolute;" in styles


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
    assert 'id="search-clue-holder"' in index_html
    assert "function renderClueChoices(session)" in app_js
    assert 'safeSessionRender("clueChoices", () => renderClueChoices(session));' in app_js
    assert "const SECRET_OPTIONS = [" in app_js
    assert '"secrets_table"' in app_js
    assert "secret_id: secretChoiceSelect.value || undefined" in app_js
    assert "memberSecretsLine(member)" in app_js
    assert "Recipe for a Potion reduces Potion of Healing to 50gp" in app_js
    assert "Big Money Buyer triples one gem/jewel/jewelry sale" in app_js
    assert "row.title = rowTips.join" in app_js
    assert 'advance("learn_spell_with_clues"' in app_js
    assert 'advance("use_secret"' in app_js
    assert "Secret: Weakness" in app_js
    assert "Secret: Deal" in app_js
    assert "Secret: Terrifying" in app_js
    assert "Secret: Diet" in app_js
    assert "Secret: Magic item" in app_js
    assert "Secret: Scroll" in app_js
    assert "ACTION_TOOLTIPS.useSecretWeakness" in app_js
    assert "ACTION_TOOLTIPS.useSecretMagicItem" in app_js
    assert "ACTION_TOOLTIPS.useSecretScroll" in app_js
    assert "state.rulesTables?.druid_spells_table" in app_js
    assert "searchClueHolderSelect?.value || undefined" in app_js
    assert '"clue_spends_table"' in app_js
    assert "held Clues are spent deliberately" in app_js


def test_frontend_marks_bloodied_foe_levels_as_effective() -> None:
    app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")

    assert "function foeLevelLabel(foe)" in app_js
    assert 'foe?.level_drop_applied ? `Eff L${level}` : `L${level}`' in app_js
    assert 'labels.push("Bloodied L drop");' in app_js
    assert "Life ${foe.life}/${foe.max_life} · ${foeLevelLabel(foe)}" in app_js
