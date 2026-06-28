"""
Regression guard for map interaction behaviours that were broken by CSS/JS refactors
and repaired in v0.68.7–v0.68.10.

Each test documents *why* the check is important, not just what string to find, so
future maintainers know the consequence of removing or changing the guarded code.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest


APP_JS = Path("src/app/static/app.js").read_text(encoding="utf-8")
STYLES_CSS = Path("src/app/static/styles.css").read_text(encoding="utf-8")
INDEX_HTML = Path("src/app/static/index.html").read_text(encoding="utf-8")
ICON_EDITOR_JS = Path("src/app/static/icon-editor.js").read_text(encoding="utf-8")


# ── Helper ─────────────────────────────────────────────────────────────────────

def _function_body(name: str, src: str) -> str:
    """
    Return everything between the opening and closing brace of the first
    top-level JS function with the given name.

    Correctly skips past destructured default parameters (e.g.
    `function foo({ bar = false } = {})`) by matching the full parameter-list
    parentheses before looking for the body's opening brace.
    """
    marker = f"function {name}("
    start = src.find(marker)
    assert start != -1, f"function {name} not found in app.js"

    # Skip past the complete parameter list to find the body's opening brace.
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


def _event_listener_body(target: str, event: str, src: str) -> str:
    """Return the body of a top-level `target.addEventListener("event", ... => { ... })` handler."""
    marker = f'{target}.addEventListener("{event}",'
    start = src.find(marker)
    assert start != -1, f"{target}.{event} listener not found in app.js"

    brace = src.find("{", start)
    assert brace != -1, f"{target}.{event} listener body not found in app.js"

    depth = 0
    for j, ch in enumerate(src[brace:], brace):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[brace + 1 : j]
    raise AssertionError(f"Could not find closing brace for {target}.{event} listener")


def _compact(src: str) -> str:
    return re.sub(r"\s+", "", src)


# ── CSS layout: map viewport must have a definite height ──────────────────────

def test_map_panel_layout_has_explicit_height_not_just_min_height() -> None:
    """
    .map-panel-layout needs `height:` (not just `min-height:`) so that flex
    children receive a concrete allocated height.  Without it,
    mapViewportEl.clientHeight returns the full map content height instead of
    the visible viewport height, breaking every scroll-range and zoom calculation.
    (Regressed in the combat-workspace restructure; fixed v0.68.7.)
    """
    assert "height: calc(100vh - 140px);" in STYLES_CSS
    assert "min-height: 420px;" in STYLES_CSS


# ── MAP_RENDER_PAD constant ────────────────────────────────────────────────────

def test_map_render_pad_constant_is_three() -> None:
    """
    MAP_RENDER_PAD = 3 adds three empty grid cells around every map tile.
    This makes the canvas wide enough that even a single-column dungeon
    overflows the viewport horizontally, so scroll-based left/right pan works.
    (Fixed in v0.68.8; reduced from 1.)
    """
    assert "const MAP_RENDER_PAD = 3;" in APP_JS


def test_render_map_bounds_use_map_render_pad() -> None:
    """
    renderMap must derive boundsWidth / boundsHeight from MAP_RENDER_PAD so
    the map canvas size and tile pixel positions stay in sync.
    If this hardcodes a different constant, tiles will be misaligned on the canvas.
    """
    body = _function_body("renderMap", APP_JS)
    assert "2 * MAP_RENDER_PAD + 1" in body
    assert "const pad = MAP_RENDER_PAD;" in body


def test_map_pixel_for_world_point_uses_map_render_pad() -> None:
    """
    mapPixelForWorldPoint translates world tile coordinates to canvas pixels.
    It must use the same MAP_RENDER_PAD offset as renderMap or tile centres
    will be computed at the wrong pixel positions, causing RM / centering to
    zoom to the wrong location.
    """
    body = _function_body("mapPixelForWorldPoint", APP_JS)
    assert "MAP_RENDER_PAD" in body


def test_zoom_to_full_map_bounds_use_map_render_pad() -> None:
    """
    zoomToFullMap computes a target zoom from the canvas bounds.  It must use
    2 * MAP_RENDER_PAD + 1 (matching renderMap) or the zoom will be wrong by
    a factor of (actual_width / assumed_width), making the All button either
    clip or leave huge margins.
    (Hardcoded +3 was left over in v0.68.8; fixed v0.68.9.)
    """
    body = _function_body("zoomToFullMap", APP_JS)
    assert "2 * MAP_RENDER_PAD + 1" in body
    assert "bounds.maxX - bounds.minX + 3" not in body, (
        "zoomToFullMap still uses hardcoded +3 instead of MAP_RENDER_PAD"
    )


# ── Wheel zoom factor ──────────────────────────────────────────────────────────

def test_wheel_zoom_factor_is_one_percent_not_twelve() -> None:
    """
    handleMapWheel zoom step must be 1 % per scroll tick (1.01).
    The previous value of 1.12 (12 % per tick) made fine-grained zoom
    impossible and jumped the map across the screen.
    (Fixed v0.68.8.)
    """
    body = _function_body("handleMapWheel", APP_JS)
    assert "1.01 : 1 / 1.01" in body
    assert "1.12" not in body


def test_trade_information_buttons_use_current_encounter_resources() -> None:
    """
    Trade Information is scoped to heroes physically in the current encounter.
    Split-party heroes elsewhere must not make Sell/Buy buttons look usable.
    """
    assert "function currentEncounterMembers(session)" in APP_JS
    assert "function currentEncounterClues(session)" in APP_JS
    assert "function currentEncounterGold(session)" in APP_JS
    assert "currentEncounterClues(session)" in APP_JS
    assert "currentEncounterGold(session)" in APP_JS
    assert "heroes in this encounter" in APP_JS
    assert "tradeInfoSellBtn.disabled = !tradeInfoOutstanding || tradeClues <= 0;" in APP_JS
    assert "tradeInfoBuyBtn.disabled = !tradeInfoOutstanding || tradeGold < 100;" in APP_JS
    assert "const clueCount = currentEncounterClues(session);" in APP_JS
    assert "buy.disabled = currentEncounterGold(session) < 100;" in APP_JS
    assert "const clues = currentEncounterClues(session);" in APP_JS
    assert "const gold = currentEncounterGold(session);" in APP_JS


def test_environment_special_events_are_clickable_from_map_marker() -> None:
    """Caverns/Fungal special events must be resolved from the main map marker UI."""
    assert "const ENVIRONMENT_EVENT_KEYS = new Set" in APP_JS
    assert "function pendingEnvironmentEventChoice(tile)" in APP_JS
    assert "function collectEnvironmentEventMenuItems(session, tile)" in APP_JS
    assert "function openMapEnvironmentEventMenu(session, tile, anchorEl)" in APP_JS
    assert "function fungalMerchantEquipmentItems()" in APP_JS
    body = _function_body("tileContentMarkers", APP_JS)
    assert "pendingEnvironmentEventChoice(tile)" in body
    assert "openMapEnvironmentEventMenu(session, tile, marker)" in body
    menu = _function_body("collectEnvironmentEventMenuItems", APP_JS)
    for key in (
        "cavemen_explorers",
        "morlock_spy",
        "cave_goblin_scout",
        "dwarf_miner",
        "dwarf_party_gem",
        "fungal_cavemen",
        "halfling_scout",
        "fungal_merchant",
        "mycelial_warning",
    ):
        assert key in menu
    action = _function_body("environmentEventAction", APP_JS)
    assert 'advance("resolve_environment_event"' in action
    assert '"buy_equipment"' in menu
    assert "target_weapon" in menu
    assert "Math.ceil(Number(item.price_gp) * 1.2)" in APP_JS
    assert "PDF p.155" in menu
    assert "PDF p.156" in menu


def test_combat_focus_reaction_outcome_block_summarizes_outstanding_choices() -> None:
    assert "function reactionOutcomeDetails(session)" in APP_JS
    assert "function appendReactionOutcomeBlock(container, session)" in APP_JS
    details = _function_body("reactionOutcomeDetails", APP_JS)
    assert "Bribe demanded" in details
    assert "Trade Information" in details
    assert "Fight to the death" in details
    assert "Foes attack first and will not make morale checks this encounter." in details
    assert "Available here: ${gold}gp and ${weapons} weapon(s)." in details
    assert "Buy: 1 Clue for 100gp (${gold}gp available here)." in details
    deck = _function_body("renderCombatDeckSlim", APP_JS)
    assert "appendReactionOutcomeBlock(status, session)" in deck
    panel = _function_body("renderCombatPanel", APP_JS)
    assert "appendReactionOutcomeBlock(combatPanelStatusEl, session)" in panel
    assert "appendReactionOutcomeBlock(combatPreviewEl, session)" in panel
    assert ".reaction-outcome-block" in STYLES_CSS


# ── syncMapViewportMode: per-axis mode sync ────────────────────────────────────

def test_sync_map_viewport_mode_per_axis() -> None:
    """
    syncMapViewportMode must handle each axis independently:
    - If X overflows (maxScrollLeft > 0): zero mapPanX (scroll owns X)
    - If X fits: zero scrollLeft (transform owns X)
    - Same independently for Y

    The old combined `maxScrollLeft > 0 || maxScrollTop > 0` branch zeroed
    mapPanX even when only Y scrolled, preventing horizontal centering on
    wide monitors where the map fits horizontally.
    (Refactored in v0.68.10.)
    """
    body = _function_body("syncMapViewportMode", APP_JS)
    assert "if (maxScrollLeft > 0)" in body, "X-axis overflow check missing"
    assert "if (maxScrollTop > 0)" in body, "Y-axis overflow check missing"
    assert "const scrollable" not in body, (
        "syncMapViewportMode must not use a combined scrollable flag; per-axis checks required"
    )
    assert "clampMapPan()" in body, "clampMapPan() call missing from syncMapViewportMode"


# ── clampMapPan: no forced centering ───────────────────────────────────────────

def test_clamp_map_pan_allows_panning_when_map_fits() -> None:
    """
    clampMapPan must NOT force mapPanX to the centre when the map fits inside
    the viewport.  The old `state.mapPanX = (viewportWidth - mapWidth) / 2`
    assignment overrode every programmatic pan attempt, making arrow-pad L/R
    and RM tile-centering completely ineffective on wide monitors.

    The correct behaviour is `clampFloat(state.mapPanX, 0, viewportWidth - mapWidth)`
    which keeps the current pan value within bounds without overriding it.
    (Fixed v0.68.10.)
    """
    body = _function_body("clampMapPan", APP_JS)
    # Must NOT use the forced-centre assignment
    assert "state.mapPanX = (viewportWidth - mapWidth) / 2" not in body, (
        "clampMapPan must not force-centre mapPanX; use clampFloat range instead"
    )
    assert "state.mapPanY = (viewportHeight - mapHeight) / 2" not in body, (
        "clampMapPan must not force-centre mapPanY; use clampFloat range instead"
    )
    # Must use clampFloat so pan is bounded but free within bounds
    assert "clampFloat(state.mapPanX" in body, "mapPanX must be clamped via clampFloat"
    assert "clampFloat(state.mapPanY" in body, "mapPanY must be clamped via clampFloat"


# ── positionMapContentAtPointer: per-axis zoom focal-point ─────────────────────

def test_position_map_content_at_pointer_per_axis() -> None:
    """
    positionMapContentAtPointer must use per-axis logic (separate maxScrollLeft
    and maxScrollTop checks) and must NOT call syncMapViewportMode() — by the
    time this runs (afterMapRender frame 2) syncMapViewportMode has already
    fired at frame 1 via renderMap's rAF.

    Calling syncMapViewportMode() here would reset mapPanX to 0 before we set
    it to the focal-point value, losing the centering.
    (Refactored in v0.68.10.)
    """
    body = _function_body("positionMapContentAtPointer", APP_JS)
    assert "syncMapViewportMode()" not in body, (
        "positionMapContentAtPointer must not call syncMapViewportMode(); "
        "it runs after syncMapViewportMode already fired in renderMap's rAF"
    )
    assert "if (maxScrollLeft > 0)" in body, "X-axis overflow check missing"
    assert "if (maxScrollTop > 0)" in body, "Y-axis overflow check missing"
    assert "const scrollable" not in body, "per-axis checks required; no combined scrollable flag"


# ── centerMapOnPoint: per-axis tile centering ──────────────────────────────────

def test_center_map_on_point_per_axis() -> None:
    """
    centerMapOnPoint (RM button → centerMapOnTile → centerMapOnWorldBounds) must
    use per-axis logic and must NOT call syncMapViewportMode() internally.

    On a wide monitor (map fits horizontally, maxScrollLeft = 0):
    - The old combined branch set scrollLeft = clamp(pixelX - vw/2, 0, 0) = 0
      and returned, leaving the tile left-aligned instead of centred.
    - Per-axis: when maxScrollLeft = 0, set mapPanX = vw/2 - pixelX to centre
      the tile via transform.

    syncMapViewportMode() must NOT be called here — it would zero mapPanX
    (combined or per-axis scroll branch) before we set the centering value.
    (Refactored in v0.68.10.)
    """
    body = _function_body("centerMapOnPoint", APP_JS)
    assert "syncMapViewportMode()" not in body, (
        "centerMapOnPoint must not call syncMapViewportMode(); "
        "it must use per-axis scroll/transform logic directly"
    )
    assert "if (maxScrollLeft > 0)" in body, "X-axis overflow check missing"
    assert "if (maxScrollTop > 0)" in body, "Y-axis overflow check missing"
    assert "const scrollable" not in body, "per-axis checks required; no combined scrollable flag"


# ── mapContentPointForClient: per-axis focal-point calculation ─────────────────

def test_map_content_point_for_client_uses_per_axis_mode() -> None:
    """
    mapContentPointForClient captures the map content coordinates under the
    cursor before a zoom.  It must use PER-AXIS mode detection:
    - X uses scrollLeft when maxScrollLeft > 0, else subtracts mapPanX
    - Y uses scrollTop  when maxScrollTop  > 0, else subtracts mapPanY

    The old combined `scrollable = maxScrollLeft > 0 || maxScrollTop > 0`
    flag was wrong when only one axis scrolled: in a tall-narrow dungeon Y
    scrolls but X doesn't, so the X content position was computed as
    `scrollLeft + pointerX = pointerX` (ignoring mapPanX centering offset).
    This made every wheel-zoom jump the focal point to the left edge.
    (Fixed v0.68.8, retained in v0.68.9.)
    """
    body = _function_body("mapContentPointForClient", APP_JS)
    assert (
        "maxScrollLeft > 0 ? mapViewportEl.scrollLeft + pointerX : pointerX - state.mapPanX"
        in body
    ), "X focal point must use per-axis mode (maxScrollLeft check)"
    assert (
        "maxScrollTop > 0 ? mapViewportEl.scrollTop + pointerY : pointerY - state.mapPanY"
        in body
    ), "Y focal point must use per-axis mode (maxScrollTop check)"
    assert "const scrollable" not in body, (
        "mapContentPointForClient must not use a combined `scrollable` flag; "
        "per-axis checks are required"
    )


# ── applyMapPanDelta: drag and arrow-pad panning ───────────────────────────────

def test_apply_map_pan_delta_resets_pan_when_scrollable() -> None:
    """
    applyMapPanDelta (used by drag and arrow-pad buttons) must:

    1. Clear mapPanX/Y = 0 for scroll-mode axes before applying scroll deltas,
       so the CSS transform and scrollLeft/scrollTop never double-count an offset.
    2. Call applyMapTransform() immediately after the resets (before scrollTo) so
       the DOM transform is flushed to (0,0) — without this flush the stale
       translate() interferes with subsequent scroll positioning.
    3. Use a SINGLE scrollTo call for both axes when smooth=true.
       Two sequential scrollTo({...smooth}) calls cancel each other in browsers:
       the second call aborts the first smooth animation before it starts.
       This was the direct cause of arrow-pad left/right doing nothing while
       up/down worked (Y scrollTo fired last and was not cancelled).
    """
    body = _function_body("applyMapPanDelta", APP_JS)
    assert "state.mapPanX = 0;" in body
    assert "state.mapPanY = 0;" in body
    assert "mapViewportEl.scrollLeft" in body
    assert "mapViewportEl.scrollTop" in body
    # applyMapTransform must appear before the scrollTo / direct scroll assignment that
    # moves the viewport.  The cleanup resets (scrollLeft = 0 or scrollTop = 0 at the top)
    # appear before applyMapTransform and that is correct — we test against scrollTo( only,
    # which is the movement call, not the cleanup call.
    transform_pos = body.find("applyMapTransform()")
    scroll_to_pos = body.find("scrollTo(")
    assert transform_pos != -1, "applyMapTransform() flush missing from applyMapPanDelta"
    assert scroll_to_pos  != -1, "scrollTo( missing from applyMapPanDelta"
    assert transform_pos < scroll_to_pos, (
        "applyMapTransform() must be called before scrollTo() in applyMapPanDelta "
        "so the DOM transform is flushed to zero before scroll offsets are applied"
    )
    # Must not have two separate scrollTo calls (that would cancel each other)
    second_scroll_to_pos = body.find("scrollTo(", scroll_to_pos + 1)
    assert second_scroll_to_pos == -1, (
        "applyMapPanDelta must use a single scrollTo call for both axes; "
        "two smooth scrollTo calls cancel each other — the second aborts the first"
    )


# ── RM / zoom-to-room wiring ───────────────────────────────────────────────────

def test_zoom_to_current_room_centers_on_tile_after_render() -> None:
    """
    zoomToCurrentRoom (RM button) must call centerMapOnTile inside afterMapRender
    so the centering runs after the new zoom level is fully laid out.
    Calling it synchronously would read stale clientWidth/scrollWidth values.
    """
    body = _function_body("zoomToCurrentRoom", APP_JS)
    assert "afterMapRender" in body
    assert "centerMapOnTile" in body


def test_map_view_revision_cancels_stale_position_callbacks() -> None:
    """
    RM / All / wheel zoom all schedule or trigger viewport positioning around a
    render.  A later map-view operation must invalidate older callbacks, or an
    old wheel focal-point correction can run after RM and move the viewport away
    from the current room.
    """
    assert "mapViewRevision: 0" in APP_JS
    assert "function nextMapViewRevision()" in APP_JS
    render_body = _function_body("renderMap", APP_JS)
    assert "const syncRevision = viewRevision ?? state.mapViewRevision;" in render_body
    assert "isCurrentMapViewRevision(syncRevision)" in render_body
    after_body = _function_body("afterMapRender", APP_JS)
    assert "isCurrentMapViewRevision(viewRevision)" in after_body


def test_wheel_zoom_repositions_synchronously_with_revision() -> None:
    """
    Rapid wheel input must not queue a stack of delayed focal-point corrections.
    zoomMapAtClientPoint should invalidate older map-view work, render once for
    the new zoom, then apply the focal-point position immediately so the next
    wheel event reads the current viewport state.
    """
    body = _function_body("zoomMapAtClientPoint", APP_JS)
    assert "const viewRevision = nextMapViewRevision();" in body
    assert "renderMap(state.session, { skipFocus: true, viewRevision });" in body
    assert "positionMapContentAtPointer(focus.ratioX, focus.ratioY, focus.pointerX, focus.pointerY, { instant: true });" in body
    assert "afterMapRender" not in body


def test_current_room_zoom_uses_instant_scroll_and_no_debug_logs() -> None:
    """
    RM must cancel any in-flight smooth scroll and land on the current room
    immediately.  Debug logs here were misleading because they printed before
    smooth scrolling had finished.
    """
    body = _function_body("zoomToCurrentRoom", APP_JS)
    assert "const viewRevision = nextMapViewRevision();" in body
    assert "centerMapOnTile(state.session, targetTile, { instant: true })" in body
    assert "[RM]" not in APP_JS
    assert "[centerMapOnPoint]" not in APP_JS


# ── Character sheet, abilities, and icon registry ─────────────────────────────

def test_home_rules_notes_click_does_not_toggle_roster_row() -> None:
    """
    The roster row itself is clickable to select/collapse a character.  Nested
    Rules & abilities details must stop bubbling, otherwise the details link
    opens and immediately loses its selected row on the home screen.
    """
    body = _function_body("appendSheetRulesNotes", APP_JS)
    assert 'details.className = "sheet-rules-notes";' in body
    assert "details.addEventListener(\"click\", (event) => event.stopPropagation());" in body
    assert 'summary.textContent = "Rules & abilities";' in body


def test_targeted_class_abilities_have_selectors_and_tooltips() -> None:
    """
    Targetable abilities should not silently pick the first legal ally/fallen
    hero.  The sheet should show explicit target rows and hover text.
    """
    paladin = _function_body("appendPaladinHealAction", APP_JS)
    assert '"Prayer heal target:"' in paladin
    assert 'classAbilityAllyTargetSelect(member, "paladin_heal", living, fallback)' in paladin
    assert 'classAbilityTooltip("paladin_heal")' in paladin

    combat_acrobatics = _function_body("appendCombatAcrobaticsAction", APP_JS)
    assert '"Combat Acrobatics:"' in combat_acrobatics
    assert 'classAbilityAllyTargetSelect(member, "combat_acrobatics", allies)' in combat_acrobatics
    assert 'classAbilityTooltip("combat_acrobatics")' in combat_acrobatics

    lesser_necromancy = _function_body("appendLesserNecromancyAction", APP_JS)
    assert '"Lesser Necromancy:"' in lesser_necromancy
    assert 'classAbilityAllyTargetSelect(member, "lesser_necromancy", fallen' in lesser_necromancy
    assert 'classAbilityTooltip("lesser_necromancy")' in lesser_necromancy

    assert "const CLASS_ABILITY_TOOLTIPS = {" in APP_JS
    assert "option.title = classAbilityTooltip(value);" in APP_JS


def test_pending_secret_choices_surface_on_sheets_and_foe_menus() -> None:
    """
    Revealed Secrets such as Weakness of a Foe are often held for a future
    timing window. The UI must show the pending timing on character sheets and
    expose foe-targeted Secret actions from the foe menu.
    """
    assert "function appendPendingSecretPrompts(" in APP_JS
    assert "function secretUsePrompt(secretId, session = null, tile = null, livingFoes = [])" in APP_JS
    assert "Waiting for combat with a Major Foe" in APP_JS
    assert "Ready now: choose a Major Foe" in APP_JS
    assert "function pendingSecretReminderLines(session, tile = null, livingFoes = [])" in APP_JS
    assert "Pending Secrets:" in APP_JS
    assert "appendPendingSecretPrompts(body, character" in APP_JS
    assert "appendPendingSecretPrompts(body, member, session, tile, livingFoes)" in APP_JS
    assert "appendPendingSecretPrompts(body, member, session, tile, currentLivingFoes)" in APP_JS
    foe_menu = _function_body("collectFoeMenuItems", APP_JS)
    assert "memberHasSecret(member, \"weakness_of_a_foe\")" in foe_menu
    assert "secret_id: \"weakness_of_a_foe\"" in foe_menu
    assert "foe_id: foe.id" in foe_menu
    assert "memberHasSecret(member, \"enemy_in_dungeon\")" in foe_menu
    assert "Demonic True Name" in foe_menu
    assert ".sheet-secret-prompts" in STYLES_CSS


def test_water_jet_exposes_explicit_effect_choice() -> None:
    payload = _function_body("spellCastPayload", APP_JS)
    targeting = _function_body("appendSpellTargetingRows", APP_JS)

    assert "waterJetEffectKey(casterId)" in payload
    assert "payload.spell_target_mode = waterJetMode" in payload
    assert '"Water Jet effect:"' in targeting
    assert '"2 damage to fire target"' in targeting
    assert '"Disperse 2 Vermin"' in targeting
    assert '"Knock out 1 Minion"' in targeting
    assert '"Distract Major Foe"' in targeting
    assert "successful spellcasting roll vs the target's Level" in targeting


def test_quest_panel_shows_disabled_turn_in_reason() -> None:
    assert "function questClaimStatus(session, quest)" in APP_JS
    assert "function questObjectiveRows(session, quest)" in APP_JS
    assert "function questJournalNode(session, quest)" in APP_JS
    status = _function_body("questClaimStatus", APP_JS)
    assert "Return to the Quest-giver's tile" in status
    assert "Quest target is not yet correctly subdued or slain." in status
    assert "Peaceful progress:" in status
    rows = _function_body("questObjectiveRows", APP_JS)
    assert "Objective" in rows
    assert "Progress" in rows
    assert "Turn-in" in rows
    assert "Epic Reward roll on claim" in rows
    render = _function_body("renderOngoingQuests", APP_JS)
    assert "questJournalNode(session, quest)" in render
    assert "Turn-in blocked: ${claimStatus.reason}" in render
    assert "claim.disabled = !claimStatus.ok;" in render
    assert "Cannot claim yet: ${claimStatus.reason}" in render
    assert "function openMapQuestMenu(session, tile, anchorEl)" in APP_JS
    assert "function collectQuestMenuItems(session, tile)" in APP_JS
    assert "Quest turn-in ready" in APP_JS
    assert "openMapQuestMenu(session, tile, marker)" in APP_JS
    assert ".quest-journal" in STYLES_CSS
    assert ".map-content-marker.quest-ready" in STYLES_CSS
    assert ".ongoing-quest-turnin" in STYLES_CSS


def test_epic_reward_statuses_have_ui_actions_and_hints() -> None:
    render = _function_body("renderClueChoices", APP_JS)
    assert "Kerrak Dar Hoard" in render
    assert "claim_kerrak_dar_hoard" in render
    assert "ACTION_TOOLTIPS.claimKerrakDarHoard" in render
    assert "const SKALITOS_SPELLS" in APP_JS
    assert "function heroSkalitosBook(member)" in APP_JS
    sheet = _function_body("appendMemberExplorationActions", APP_JS)
    assert "Book of Skalitos" in sheet
    assert "Book:" in sheet
    combat = _function_body("appendMemberCombatActions", APP_JS)
    assert "Arrow of Slaying" in combat
    assert "use_arrow_of_slaying" in combat
    assert "arrowOfSlayingTargetName(arrow)" in combat
    assert "createFoeTargetSelect(arrowFoes" in combat
    assert "Arrow of Slaying may be used only by a PC with a bow." in combat
    tooltip = _function_body("statusChipTooltip", APP_JS)
    assert "roll two attack dice" in tooltip
    assert "Kerrak Dar's 500gp hoard" in tooltip
    assert "church pays for one resurrection attempt" in tooltip
    assert "rolled target Foe" in tooltip
    assert "Bear Trap Wound" in tooltip
    assert "six basic wizard spell pages" in tooltip
    status = _function_body("heroStatusChips", APP_JS)
    assert "enchanted weapon" in status
    assert "kerrak dar hoard" in status
    assert "holy symbol of healing" in status
    assert "arrow of slaying" in status
    assert "heroSkalitosBook(member)" in status


def test_summary_log_preserves_state_effect_lines() -> None:
    """
    Summary mode hides rolls and lookup detail, but it must keep state changes
    such as curses, buffs, poison, and special-feature benefits.
    """
    summary_filter = _function_body("shouldShowLogEntry", APP_JS)
    assert "isStateEffectLogEntry(line)" in summary_filter
    state_filter = _function_body("isStateEffectLogEntry", APP_JS)
    assert "/^Effect:/i.test(line)" in state_filter
    assert "/^Event:/i.test(line)" in state_filter
    assert "/^Feature:/i.test(line)" in state_filter
    assert "is cursed" in state_filter
    assert "blessing removes" in state_filter
    assert "mirror image" in state_filter
    assert "takes" in state_filter


def test_special_feature_choice_controls_are_wired() -> None:
    assert 'const specialFeatureChoicesEl = document.getElementById("special-feature-choices")' in APP_JS
    assert "function pendingSpecialFeatureChoice(tile)" in APP_JS
    assert "function pendingSpecialFeatureTitle(feature)" in APP_JS
    assert "function focusSpecialFeatureChoices()" in APP_JS
    body = _function_body("renderSpecialFeatureChoices", APP_JS)
    assert 'advance("resolve_special_feature", { special_feature_choice: "touch_statue" })' in body
    assert 'advance("resolve_special_feature", { special_feature_choice: "leave_statue" })' in body
    assert 'advance("resolve_special_feature", { special_feature_choice: "attempt_puzzle_box" })' in body
    assert 'advance("resolve_special_feature", { special_feature_choice: "leave_puzzle_box" })' in body
    assert 'special_feature_choice: "bless_temple"' in body
    assert "target_character_id: select.value" in body
    assert "Roll d6: 1-3 animates a Living Statue; 4-6 breaks it open for gold." in body
    assert "failure costs 1 Life" in body
    assert 'safeSessionRender("specialFeatureChoices", () => renderSpecialFeatureChoices(session))' in APP_JS
    assert 'id="special-feature-choices"' in INDEX_HTML


def test_pending_special_feature_marker_is_distinct_and_clickable() -> None:
    markers = _function_body("tileContentMarkers", APP_JS)
    assert "const pendingFeature = pendingSpecialFeatureChoice(tile)" in markers
    assert "pendingSpecialFeatureTitle(pendingFeature)" in markers
    assert "focusSpecialFeatureChoices()" in markers
    assert '{ markerClass: "pending-special-feature" }' in markers
    assert '"pending-special-feature"' in APP_JS
    assert ".map-content-marker.pending-special-feature" in STYLES_CSS


def test_special_event_summary_is_visible_in_tile_detail() -> None:
    body = _function_body("renderTileDetail", APP_JS)
    assert "tile.special_event_summary" in body
    assert "Special event: ${tile.special_event_summary}" in body


def test_active_foe_specials_surface_in_combat_status() -> None:
    assert "function activeFoeSpecialLabels(foes)" in APP_JS
    assert "function activeFoeSpecialExplanations(foes)" in APP_JS
    assert "function appendFoeSpecialsReference(container, foes)" in APP_JS
    foe_labels = _function_body("foeStatusLabels", APP_JS)
    assert 'labels.push("Caster")' in foe_labels
    assert 'labels.push("Dragon")' in foe_labels
    assert 'labels.push("Construct")' in foe_labels
    specials = _function_body("activeFoeSpecialLabels", APP_JS)
    assert 'labels.add("poison saves on hits")' in specials
    assert "labels.add(`MR up to +${mrTier}`)" in specials
    assert 'labels.add("regeneration")' in specials
    assert 'labels.add("construct immunities")' in specials
    assert 'labels.add("multiple attacks")' in specials
    assert 'if (lower === "dragon") return "Dragon trait: contributes one MR tier and affects dragon-specific rules."' in APP_JS
    assert 'if (lower === "caster") return "Caster trait: contributes one MR tier for spell penetration."' in APP_JS
    assert 'if (lower === "construct") return "Construct/artificial foe: immune to some sleep and illusion effects."' in APP_JS
    status = _function_body("renderCombatStatus", APP_JS)
    assert "activeFoeSpecialLabels(livingFoesOnTile(session))" in status
    assert "Foe specials:" in status
    assert "Hover or click foe chips for details." in status
    explanations = _function_body("activeFoeSpecialExplanations", APP_JS)
    assert "Poison: a failed Save after a hit causes +1 damage and can leave lingering poison." in explanations
    assert "spells connect first, then penetrate at foe Level plus MR" in explanations
    assert "Regeneration: recovers 1 Life unless blocked by fire, acid, lightning, or oil." in explanations
    assert "Multiple attacks: this foe makes each listed attack every foe melee phase." in explanations
    assert "Construct: immune to some sleep and illusion effects." in explanations
    assert (
        "Undead: clerics use full Level Attack; holy water, Turn Undead, blessed bonuses, "
        "and common sleep/illusion immunities may apply."
    ) in explanations
    assert "Dragon: contributes an MR tier and may trigger dragon-specific bonuses." in explanations
    reference = _function_body("appendFoeSpecialsReference", APP_JS)
    assert 'node("div", "combat-section-label", "Foe specials")' in reference
    assert "activeFoeSpecialExplanations(foes)" in reference
    combat_render = _function_body("renderCombatPanel", APP_JS)
    assert "appendFoeSpecialsReference(combatPreviewEl, livingFoes)" in combat_render


def test_undead_holy_ui_hints_cover_actions_and_chips() -> None:
    assert "Turn Undead: once per encounter, affects all undead foes in this combat." in APP_JS
    assert "Roll d6 + half Level vs each undead foe's Level" in APP_JS
    holy_helper = _function_body("heroUsableHolyWater", APP_JS)
    assert 'member.class_id === "barbarian"' not in holy_helper
    assert "heroHolyWaterItems(member)" in APP_JS
    assert "Holy water affects undead only; no living undead foe is present." in APP_JS
    assert "Target: ${selectedHolyWaterTarget.name}." in APP_JS
    party_render = _function_body("appendPartyMemberSheet", APP_JS)
    assert "Turn Undead affects undead only; no living undead foe is present." in party_render
    assert "Turn Undead has already been used by this hero in this encounter." in party_render
    foe_summary = _function_body("foeRulesSummary", APP_JS)
    assert (
        "Undead: clerics use full Level Attack; holy water and Turn Undead apply; "
        "common sleep/illusion effects may fail."
    ) in foe_summary
    status_tooltip = _function_body("statusChipTooltip", APP_JS)
    assert "Blessed Temple/Shrine: +1 Attack vs undead and demon foes until one such foe is slain." in status_tooltip


def test_expected_foe_attacks_group_multiple_attacks() -> None:
    assert "function groupPreviewEnemyAttacks(previewPairs)" in APP_JS
    assert "function previewEnemyAttackText(group, foeLabels)" in APP_JS
    group_fn = _function_body("groupPreviewEnemyAttacks", APP_JS)
    assert "byEnemy.get(key).targets.push(pair.target)" in group_fn
    text_fn = _function_body("previewEnemyAttackText", APP_JS)
    assert "const suffix = attackCount > 1 ? ` (${attackCount} attacks)` : \"\";" in text_fn
    combat_render = _function_body("renderCombatPanel", APP_JS)
    assert "for (const group of groupPreviewEnemyAttacks(previewPairs))" in combat_render
    assert "previewEnemyAttackText(group, foeLabels)" in combat_render


def test_level_up_spell_picker_shows_existing_spell_slots() -> None:
    """
    When a level-up grants a spell slot, choosing a duplicate is legal but the
    player needs to see current prepared slots before deciding.
    """
    assert "function spellInventoryLine(member)" in APP_JS
    assert "Current spell slots:" in APP_JS
    assert "levelUpSpellChoicesEl.appendChild(subline(spellInventoryLine(member)))" in APP_JS
    assert "pick.appendChild(subline(spellInventoryLine(member)))" in APP_JS
    assert "${spell} (+1 slot; already ${prepared})" in APP_JS


def test_room_state_icons_and_editor_class_category_are_wired() -> None:
    """
    Map markers need to distinguish searched rooms, trap/treasure resolution,
    vendors/events, and monster-specific icon ids that can be overridden later.
    """
    markers = _function_body("tileContentMarkers", APP_JS)
    assert 'contentMarker("searched", "Room searched")' in markers
    assert 'interactiveContentMarker("treasure"' in markers
    assert 'contentMarker("treasure-claimed"' in markers
    assert 'contentMarker("treasure-empty"' in markers
    assert 'contentMarker("trap-resolved"' in markers
    assert 'contentMarker("vendor"' in markers
    assert 'contentMarker("wandering-monsters", tileSpecialEventTitle(tile), 0, { markerClass: "wandering-monsters" })' in markers
    assert 'contentMarker("event"' in markers
    assert "enemyMarkerIconId(liveEnemies)" in markers
    assert "tileHasWanderingMonsterEvent(tile, liveEnemies, defeatedEnemies)" in markers

    icon_key = _function_body("renderIconKey", APP_JS)
    assert "Icon key (${state.icons.length})" in icon_key
    assert "iconKeyGroups()" in icon_key
    assert "iconKeySection(group)" in icon_key
    assert 'const ICON_KEY_MAP_ORDER = [' in APP_JS
    for icon_id in ["searched", "treasure-claimed", "treasure-empty", "trap-resolved", "vendor", "wandering-monsters", "event"]:
        assert f'"{icon_id}"' in APP_JS
    assert 'const ICON_KEY_CATEGORY_ORDER = ["map", "class", "monster", "item", "condition", "ui", "character"];' in APP_JS
    assert 'monster: { label: "Monsters", open: false }' in APP_JS
    assert 'class: { label: "Classes", open: false }' in APP_JS
    assert 'map: { label: "Map states", open: false }' in APP_JS
    assert 'function iconKeyMarkerClass(definition)' in APP_JS
    assert 'function iconKeyList(definitions)' in APP_JS
    assert "details.open && !details.querySelector(\".icon-key-list\")" in APP_JS
    assert 'definition.category === "monster"' in APP_JS
    assert 'definition.category === "class"' in APP_JS

    assert '["map", "class", "character", "monster", "item", "condition", "ui"]' in ICON_EDITOR_JS
    assert '.map-content-icon.class-paladin::before' in STYLES_CSS
    assert ".map-content-icon.wandering-monsters::after" in STYLES_CSS
    assert ".icon-key-section" in STYLES_CSS
    assert ".map-content-marker.class-icon-key" in STYLES_CSS


def test_mycelium_snare_map_trap_menu_exposes_held_object_choices() -> None:
    trap_menu = _function_body("collectTrapMenuItems", APP_JS)
    assert "pending_mycelium_snare" in trap_menu
    assert "myceliumSnareHeldObjects" in trap_menu
    assert "trap_snare_item_name: item" in trap_menu
    assert "choose which held object" in trap_menu.lower() or "held object" in trap_menu


def test_rolling_boulder_map_trap_menu_exposes_pdf_choices() -> None:
    trap_menu = _function_body("collectTrapMenuItems", APP_JS)
    assert 'tile.trap_key === "rolling_boulder"' in trap_menu
    assert 'for (const origin of ["front", "back"])' in trap_menu
    assert "trap_boulder_origin: origin" in trap_menu
    assert "trap_boulder_block_exit_id: exit.id" in trap_menu
    assert "choose whether it comes from the front or back" in trap_menu
    assert "choose one opening on the tile for it to block" in trap_menu


def test_hidden_pit_clue_follow_up_is_visible_in_clue_panel() -> None:
    clue_panel = _function_body("renderClueChoices", APP_JS)
    assert "tile?.hidden_pit_secret_passage_available" in clue_panel
    assert "Find Secret Passage (1 Clue)" in clue_panel
    assert "advance(\"use_hidden_pit_clue\")" in clue_panel
    assert "Need 1 held Clue to find the Secret Passage at the bottom of the hidden pit." in clue_panel
    assert "Spend 1 held Clue at the bottom of the Hidden Pit" in clue_panel


def test_hidden_pit_secret_passage_limits_destination_environments() -> None:
    passage_ui = _function_body("renderSecretPassageChoices", APP_JS)
    assert "pending_secret_passage_hidden_pit" in passage_ui
    assert "Hidden pit passage" in passage_ui
    assert "Fungal Grottoes" in passage_ui
    assert '"caverns"' not in passage_ui.split("hiddenPitPassage")[1].split("]")[0]


def test_home_bank_button_and_roster_bank_labels_are_present() -> None:
    """
    The home screen should expose the active camp bank near transfer actions and
    roster sheets should distinguish banked gold from active carried gold.
    """
    assert 'id="bank-setup"' in INDEX_HTML
    assert 'const bankSetupBtn = document.getElementById("bank-setup");' in APP_JS
    assert "SETUP_TOOLTIPS.homeBank" in APP_JS
    assert "updateSetupBankButton();" in APP_JS
    assert "bankSetupBtn.disabled = false;" in APP_JS
    assert "Bank carried gold while camped outside." in APP_JS
    assert "function rosterGoldLine(character)" in APP_JS
    assert "In hand:" in APP_JS
    assert "Bank:" in APP_JS
    assert "Home bank gold" not in APP_JS
    assert "Banked XP rolls" in APP_JS
    assert "Stored gear:" in APP_JS
    assert "depositAllCarriedGoldForCharacter(character.id)" in APP_JS
    assert "Bank carried gold" in APP_JS
    assert "function transferMemberGoldLabel(member)" in APP_JS
    assert "home-bank gold between roster heroes" in APP_JS


# ── Disabled action consistency ───────────────────────────────────────────────

def test_disabled_buttons_are_dimmed_blocked_and_still_have_tooltips() -> None:
    """
    Disabled action buttons must be a consistent UI state: visibly dimmed,
    unavailable to click, and still able to explain why on hover.

    Native disabled buttons do not reliably expose hover text, so app.js wraps
    disabled buttons with a titled span and leaves the button itself disabled.
    """
    assert "button:disabled" in STYLES_CSS
    assert "cursor: not-allowed;" in STYLES_CSS
    assert ".action-tooltip-wrap" in STYLES_CSS

    body = _function_body("syncButtonTooltip", APP_JS)
    assert "if (button.disabled)" in body
    assert "ensureTooltipWrap(button)" in body
    assert "wrap.title = text" in body
    assert 'button.title = "";' in body
    assert "removeTooltipWrap(button)" in body


def test_surprise_reaction_lock_disables_combat_actions_in_every_ui_path() -> None:
    """
    When Check Reactions is mandatory (surprised round 0), party actions must
    be disabled everywhere they can appear. They must not remain active buttons
    with only the cursor implying "no".
    """
    sidebar = _compact(_function_body("renderCombatPanel", APP_JS))
    assert "constimmediateLocked=surpriseReactionLocked(session);" in sidebar
    assert "constcombatLocked=combatRoundLocked(session);" in sidebar
    assert "combatResolveBtn.disabled=!canResolve||combatLocked;" in sidebar
    assert "combatFleeBtn.disabled=!inCombat||combatLocked;" in sidebar
    assert "combatWithdrawBtn.disabled=!inCombat||!withdrawDoors.length||combatLocked;" in sidebar

    deck = _compact(_function_body("renderCombatDeckSlim", APP_JS))
    assert "constimmediateLocked=surpriseReactionLocked(session);" in deck
    assert "constcombatLocked=combatRoundLocked(session);" in deck
    assert "resolve.disabled=!livingFoes.length||combatLocked;" in deck
    assert "flee.disabled=combatLocked;" in deck
    assert "withdraw.disabled=!withdrawDoors.length||combatLocked;" in deck
    assert "spellBtn.disabled=immediateLocked;" in deck
    assert "refreshButtonTooltips(actionRow);" in deck

    sticky = _compact(_function_body("renderSession", APP_JS))
    assert "constimmediateLocked=surpriseReactionLocked(session);" in sticky
    assert "constcombatLocked=combatRoundLocked(session);" in sticky
    assert "combatBtn.disabled=!inCombat||!livingCombatFoes.length||combatLocked;" in sticky
    assert "fleeBtn.disabled=!inCombat||combatLocked;" in sticky
    assert "withdrawBtn.disabled=!inCombat||!combatWithdrawDoors.length||combatLocked;" in sticky

    hero_sheet = _compact(_function_body("appendMemberCombatActions", APP_JS))
    assert "constimmediateLocked=surpriseReactionLocked(session);" in hero_sheet
    assert "disabled:immediateLocked" in hero_sheet
    assert "holyBtn.disabled=immediateLocked;" in hero_sheet
    assert "oilBtn.disabled=immediateLocked;" in hero_sheet
    assert "acidBtn.disabled=immediateLocked;" in hero_sheet
    assert "magicBtn.disabled=immediateLocked;" in hero_sheet
    assert "spellBtn.disabled=immediateLocked;" in hero_sheet

    monster_menu = _compact(_function_body("collectMonsterMenuItems", APP_JS))
    assert "constcombatLocked=combatRoundLocked(session);" in monster_menu
    assert "constimmediateLocked=surpriseReactionLocked(session);" in monster_menu
    assert "actionLocked=combatLocked||immediateLocked" in monster_menu
    assert monster_menu.count("disabled:actionLocked") >= 2


def test_dead_shot_and_continual_light_combat_ability_ui_copy() -> None:
    choices = _function_body("buildCombatAbilityChoices", APP_JS)
    assert 'hasExpertSkill(member, "dead_shot")' in choices
    assert '"dead_shot", "Dead Shot (reroll missile miss)"' in choices
    assert "hasMissileWeapon(member)" in choices
    assert '["cleric", "wizard"].includes(member.class_id)' in choices
    assert "option.title = classAbilityTooltip(value);" in APP_JS

    assert "Declare Dead Shot" in APP_JS
    assert "Maintain a worn Continual Light" in APP_JS


def test_chaos_fanatics_secret_button_has_tooltip_text() -> None:
    actions = _function_body("appendMemberSecretActions", APP_JS)
    assert 'memberHasSecret(member, "chaos_fanatics")' in actions
    assert 'node("button", "secondary", "Secret: Chaos Fanatics")' in actions
    assert "ACTION_TOOLTIPS.useSecretChaosFanatics" in actions
    assert "setButtonTooltip(" in actions
    assert "Chaos Fanatics requires living chaos fanatics" in actions

    context_menu = _function_body("openMapContextMenu", APP_JS)
    assert "button.disabled = Boolean(item.disabled);" in context_menu
    assert 'if (!item.disabled && typeof item.onClick === "function")' in context_menu


def test_home_party_bank_and_hunger_controls_have_tooltips() -> None:
    camp_actions = _function_body("appendPartyCampActions", APP_JS)
    assert "Eat ration" in camp_actions
    assert "Bank all characters gold" in camp_actions
    assert "setTooltip(feedSelect" in camp_actions
    assert "setButtonTooltip(" in camp_actions
    assert "eat_food_ration" in camp_actions
    assert "depositPartyBankGoldFromDialog" in camp_actions

    summary = _function_body("appendHomePartyResourceSummary", APP_JS)
    assert "Banking -" in summary
    assert "Hunger timer -" in summary
    assert "Party Eat and carried-gold banking actions are available" in summary

    parties = _function_body("renderParties", APP_JS)
    assert "appendHomePartyResourceSummary(item, stats, campSession)" in parties
    assert 'node("button", "secondary", "Bank all characters gold")' in parties


def test_required_hireling_assignment_lists_eligible_assignees_before_slot() -> None:
    assign = _function_body("populateHirelingAssignSelect", APP_JS)
    assert "eligibleAssigneesForRetainer(session, retainerRow)" in assign
    assert "assignSelect.disabled = false" in assign
    assert "heroes.some((member) => member.character_id === preferredAssignedId)" in assign
    assert "if (needsAssign && heroes.length === 1)" in assign
    assert "assignSelect.value = heroes[0].character_id;" in assign

    hire_panel = _function_body("appendCampHirelingsPanel", APP_JS)
    assert "refreshHirelingSlotSelect(session, slotSelect, assignSelect, freeSlots)" in hire_panel
    assert "marchingSlotsForAssignee(session, assigneeId)" in APP_JS


def test_app_js_cache_buster_bumped_for_hireling_form_fix() -> None:
    assert '<script src="/static/app.js?v=0.69.8"></script>' in INDEX_HTML


def test_app_js_has_no_syntax_errors() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available for syntax check")
    result = subprocess.run(
        [node, "--check", "src/app/static/app.js"],
        capture_output=True,
        text=True,
        cwd=Path("."),
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_append_party_member_sheet_uses_return_for_detached_heroes() -> None:
    body = _function_body("appendPartyMemberSheet", APP_JS)
    assert "if (memberAway)" in body
    assert "return;" in body
    assert "continue;" not in body


def test_unified_marching_order_ui_helpers_exist() -> None:
    body = APP_JS
    assert "function hirelingNeedsReassignment(session, hireling)" in body
    assert "function hirelingIsNestedUnderAssignee(session, hireling)" in body
    assert "function buildHirelingPartySheet(session, hireling, mode = \"standalone\")" in body
    assert "function openEditPartyDialog(session)" in body
    assert "function renderActiveHirelingsPanel" not in body
    assert "Swap Party Members" not in body
    assert 'node("button", "secondary", "Edit Party")' in body
    assert "HIRELING_TOOLTIPS.groupMarchingOrder" in body
    assert "ACTION_TOOLTIPS.heroMarchUp" in body


def test_party_sheet_styles_cover_nested_hirelings() -> None:
    styles = Path("src/app/static/styles.css").read_text(encoding="utf-8")
    assert ".party-hireling-sheet.party-hireling-nested" in styles
    assert ".party-hireling-orphan-badge" in styles
    assert ".edit-party-dialog" in styles


def test_cast_spell_advance_does_not_show_confirmation_dialog() -> None:
    advance_body = _function_body("advance", APP_JS)
    assert "shouldConfirmAdventureSpell" not in APP_JS
    assert "ADVENTURE_SPELL_CONFIRM_KEYS" not in APP_JS
    assert "window.confirm" not in advance_body


def test_frontend_ration_counter_accepts_legacy_rations_label() -> None:
    count_body = _function_body("countFoodRations", APP_JS)
    ration_body = _function_body("isFoodRationItem", APP_JS)
    assert "isFoodRationItem(item)" in count_body
    assert "(?:food\\s+)?rations?" in ration_body


def test_start_setup_preferences_are_persisted() -> None:
    assert 'const START_SETUP_PREFS_KEY = "startSetupPrefs";' in APP_JS
    assert "function readStartSetupPrefs()" in APP_JS
    assert "function writeStartSetupPrefs()" in APP_JS
    assert "function loadStartSetupPrefsIntoControls()" in APP_JS
    assert "adventureId: adventureSelect?.value" in APP_JS
    assert "xpSystem: xpSystemSelect?.value" in APP_JS
    assert "mapBoundsMode: mapBoundsSelect?.value" in APP_JS
    assert "mapElementCapPreset: mapElementCapPreset?.value" in APP_JS
    assert "mapElementCapCustom: mapElementCapCustom?.value" in APP_JS
    assert "startCampedOutside: Boolean(startCampedOutside?.checked)" in APP_JS
    assert "loadStartSetupPrefsIntoControls();" in _function_body("renderSetup", APP_JS)
    assert "writeStartSetupPrefs();" in _event_listener_body("startSession", "click", APP_JS)


def test_api_validation_errors_are_formatted_for_status() -> None:
    api_body = _function_body("api", APP_JS)
    formatter = _function_body("formatApiErrorDetail", APP_JS)
    assert "formatApiErrorDetail(detail.detail)" in api_body
    assert "Array.isArray(detail)" in formatter
    assert 'part !== "body"' in formatter
    assert "Request failed:" in formatter


# ── Log mode controls ─────────────────────────────────────────────────────────

def test_log_controls_are_summary_verbose_not_rolls_math_or_expand() -> None:
    """
    Log detail is one explicit mode: Summary hides rolls/lookups/math, Verbose
    includes them.  The old Rolls/Math checkboxes and Expand Log controls should
    not return because they split one concern across three controls.
    """
    assert 'id="log-mode-summary"' in INDEX_HTML
    assert 'id="log-mode-verbose"' in INDEX_HTML
    assert 'title="Summary log: show outcomes without roll, lookup, or math detail."' in INDEX_HTML
    assert 'title="Verbose log: include rolls, table lookups, and modifier math."' in INDEX_HTML
    assert 'id="show-rolls"' not in INDEX_HTML
    assert 'id="show-math"' not in INDEX_HTML
    assert "Expand log" not in INDEX_HTML

    assert "logMode: \"summary\"" in APP_JS
    assert "function setLogMode(mode)" in APP_JS
    assert "state.showRolls = verbose;" in APP_JS
    assert "state.showMath = verbose;" in APP_JS
    log_filter = _function_body("shouldShowLogEntry", APP_JS)
    assert 'line.startsWith("Round summary:")' in log_filter
    assert "row|result|roll|uses" in log_filter
    assert "total\\s+\\d+\\s+vs\\s+(?:L)?\\d+" in log_filter
    log_mode_controls = _function_body("updateLogModeControls", APP_JS)
    assert "setButtonTooltip(logModeSummaryBtn, ACTION_TOOLTIPS.logSummary);" in log_mode_controls
    assert "setButtonTooltip(logModeVerboseBtn, ACTION_TOOLTIPS.logVerbose);" in log_mode_controls
    assert "showRollsInput" not in APP_JS
    assert "showMathInput" not in APP_JS
    assert "logExpanded" not in APP_JS
    assert "combatLogExpanded" not in APP_JS


def test_combat_log_tab_uses_log_mode_without_local_filters_or_expand() -> None:
    """
    Combat Focus should not hide reaction results behind a second collapsed
    combat log.  The Log tab follows the global Summary/Verbose mode and shows
    the latest filtered entries directly.
    """
    body = _function_body("renderCombatRailLog", APP_JS)
    assert "buildLogModeToggle()" in body
    assert "allFilteredLogEntries(session)" in body
    assert "COMBAT_RAIL_LOG_SOURCE_LIMIT" in body
    assert "COMBAT_RAIL_LOG_VISIBLE_LIMIT" in body
    assert "logLimitNotice(shown.length, filteredEntries.length" in body
    assert "checkbox" not in body
    assert "Show full log" not in body
    assert "Show recent" not in body

    toggle = _function_body("buildLogModeToggle", APP_JS)
    assert "setLogMode(\"summary\")" in toggle
    assert "setLogMode(\"verbose\")" in toggle


def test_log_windows_keep_more_history_available() -> None:
    """
    Long fights and verbose exploration can exceed the old 80-line adventure log
    and 24-line combat rail.  The visible windows should be larger and disclose
    when even the enlarged window is clipped.
    """
    assert "const MAIN_LOG_ENTRY_LIMIT = 300;" in APP_JS
    assert "const COMBAT_RAIL_LOG_SOURCE_LIMIT = 300;" in APP_JS
    assert "const COMBAT_RAIL_LOG_VISIBLE_LIMIT = 80;" in APP_JS

    main_log = _function_body("renderLog", APP_JS)
    assert "filteredEntries.slice(-MAIN_LOG_ENTRY_LIMIT)" in main_log
    assert "logLimitNotice(entries.length, filteredEntries.length)" in main_log
    assert "{ limit: 80 }" not in main_log

    notice = _function_body("logLimitNotice", APP_JS)
    assert "Showing latest" in notice
    assert "filtered ${context} entries" in notice


def test_split_party_controls_have_tooltips_and_away_heroes_have_no_actions() -> None:
    """Detached heroes away from the current map element should be visible but inert."""
    assert "leaveBehind:" in APP_JS
    assert "scoutAhead:" in APP_JS
    assert "scoutThrough:" in APP_JS
    assert "scoutClosedDoor:" in APP_JS
    assert "rejoinGroup:" in APP_JS
    assert "detachedCombatRound:" in APP_JS
    assert "callOfTheWild:" in APP_JS
    assert "advance(\"call_of_the_wild\", { character_id: member.character_id })" in APP_JS
    assert "function callOfTheWildTurns(session, member)" in APP_JS
    assert "function isCallOfTheWildDetached(session, member)" in APP_JS
    assert "function renderDetachedCombatPanel(session)" in APP_JS
    assert "function partyGroupInfo(session, member)" in APP_JS
    assert "function partyGroupHeading(info, session)" in APP_JS
    assert "function appendDetachedNavigationPrompt(body, session, group, member)" in APP_JS
    body = _function_body("renderPartyState", APP_JS)
    assert "if (!target) return;" in body
    assert "const detachedCombat = renderDetachedCombatPanel(session);" in body
    assert "const groupInfoByMember = new Map" in body
    assert "target.appendChild(partyGroupHeading(bucket.info, session));" in body
    member_body = _function_body("appendPartyMemberSheet", APP_JS)
    assert "if (memberAway)" in member_body or "isDetachedElsewhere(session, member)" in member_body
    assert "setButtonTooltip(leaveBtn, ACTION_TOOLTIPS.leaveBehind);" in member_body
    assert "setButtonTooltip(scoutBtn, ACTION_TOOLTIPS.scoutAhead);" in member_body
    assert "setButtonTooltip(rejoinBtn, ACTION_TOOLTIPS.rejoinGroup);" in member_body
    assert "setButtonTooltip(callBtn, ACTION_TOOLTIPS.callOfTheWild);" in member_body
    assert "Call of the Wild: returns in ${callTurns} turn(s)." in member_body
    assert "rejoinBtn.disabled = callTurns > 0;" in member_body
    assert "const memberAway = isDetachedElsewhere(session, member);" in member_body
    assert "if (memberAway)" in member_body
    assert "appendDetachedNavigationPrompt(body, session, elsewhere, member);" in member_body
    assert "return;" in member_body
    prompt = _function_body("appendDetachedNavigationPrompt", APP_JS)
    assert "Scout is ahead:" in prompt
    assert "Navigate back" in prompt
    assert "Wait here" in prompt
    assert "advance(\"set_active_group\", { detached_tile_id: group.tile_id })" in prompt
    assert "advance(\"set_active_group\", { detached_tile_id: null })" in prompt
    detached_panel = _function_body("renderDetachedCombatPanel", APP_JS)
    assert "advance(\"detached_combat_round\", { detached_tile_id: tile.id })" in detached_panel
    assert "setButtonTooltip(button, ACTION_TOOLTIPS.detachedCombatRound);" in detached_panel
    group_info = _function_body("partyGroupInfo", APP_JS)
    assert "Group 1 - Main Group" in group_info
    assert "Detached Group" in group_info
    assert ".party-group-heading" in STYLES_CSS
    assert "grid-column: 1 / -1;" in STYLES_CSS


def test_combat_ui_excludes_heroes_detached_elsewhere() -> None:
    """
    The backend's combat_party() already excludes heroes detached on another
    tile, but the combat UI used to render every party member anyway — a
    scouting/left-behind hero appeared as a hero chip, a tactical room token,
    and a legacy combat row even though they could not act. All combat hero
    surfaces must filter through combatPartyMembers() so the UI mirrors the
    engine's view of who is physically in the fight.
    """
    assert "function combatPartyMembers(session)" in APP_JS
    helper = _function_body("combatPartyMembers", APP_JS)
    assert "detachedElsewhereIds(session)" in helper
    assert "callOfTheWildTurns(session, member) <= 0" in helper
    assert "!isCallOfTheWildDetached(session, member)" in helper

    chips = _function_body("renderCombatHeroChips", APP_JS)
    assert "combatPartyMembers(session)" in chips
    assert "session.party || []" not in chips

    layout = _function_body("computeTacticalTokenLayout", APP_JS)
    assert "combatPartyMembers(session)" in layout
    assert "[...(session.party || [])]" not in layout

    rows = _function_body("renderCombatHeroRows", APP_JS)
    assert "combatPartyMembers(session)" in rows
    assert "(session.party || [])" not in rows


def test_session_actions_have_immediate_pending_feedback() -> None:
    """
    Session clicks should acknowledge input before the network round trip and
    prevent accidental double submits while the action is in flight.
    """
    assert "sessionActionPending: false" in APP_JS
    assert "function beginSessionAction(action, button = trackedSessionActionButton())" in APP_JS
    assert "function endSessionAction({ restoreDisabled = false } = {})" in APP_JS

    advance_body = _function_body("advance", APP_JS)
    assert "if (state.sessionActionPending) return false;" in advance_body
    assert "if (!beginSessionAction(action)) return false;" in advance_body
    assert "endSessionAction({ restoreDisabled: !succeeded });" in advance_body

    assert "button.action-pending" in STYLES_CSS
    assert "button.action-pending::after" in STYLES_CSS
    assert "@keyframes action-pending-spin" in STYLES_CSS
    assert "body.session-action-pending #session-panel button:not(.action-pending)" in STYLES_CSS


def test_advance_uses_returned_session_without_full_session_list_refresh() -> None:
    """
    The /advance response already contains the updated session.  Avoid fetching
    and rebuilding active/saved games, characters, and parties after every
    exploration/combat action.
    """
    assert "function syncSessionListFromSession(session, { render = setupViewVisible() } = {})" in APP_JS
    assert "function sessionListEntryFromSession(session)" in APP_JS
    assert 'api("/api/sessions/summaries")' in APP_JS
    assert "function exportInstalledAdventureJson(adventure)" in APP_JS
    assert "function renderSetupSessionListsFromCache()" in APP_JS
    assert "function markSetupRosterDirty()" in APP_JS
    assert "function reloadCharacters(options = {})" in APP_JS

    advance_body = _function_body("advance", APP_JS)
    assert "syncSessionListFromSession(state.session, { render: setupViewVisible() });" in advance_body
    assert "await refreshSessions();" not in advance_body
    assert "await reloadCharacters({ render: setupViewVisible() });" in advance_body

    save_handler = _event_listener_body("saveSessionBtn", "click", APP_JS)
    assert "beginSessionAction(\"save_session\", saveSessionBtn)" in save_handler
    assert "syncSessionListFromSession(state.session, { render: setupViewVisible() });" in save_handler
    assert "await refreshSessions();" not in save_handler


def test_session_mutations_defer_home_screen_refresh_work() -> None:
    """
    Main session mutations should update cached session state and defer Home
    Screen roster/list rebuilds while the player remains in the game view.
    """
    guarded_bodies = {
        "advance": _function_body("advance", APP_JS),
        "save": _event_listener_body("saveSessionBtn", "click", APP_JS),
        "start": _event_listener_body("startSession", "click", APP_JS),
    }
    for name, body in guarded_bodies.items():
        assert "await refreshSessions();" not in body, name

    advance_body = guarded_bodies["advance"]
    assert "syncSessionListFromSession(state.session, { render: setupViewVisible() });" in advance_body
    assert "await reloadCharacters({ render: setupViewVisible() });" in advance_body

    save_body = guarded_bodies["save"]
    assert "if (state.sessionActionPending) return;" in save_body
    assert "syncSessionListFromSession(state.session, { render: setupViewVisible() });" in save_body

    start_body = guarded_bodies["start"]
    assert "resetSessionRenderCache();" in start_body
    assert "syncSessionListFromSession(state.session, { render: setupViewVisible() });" in start_body
    assert "markSetupRosterDirty();" in start_body

    sync_body = _function_body("syncSessionListFromSession", APP_JS)
    assert "function syncSessionListFromSession(session, { render = setupViewVisible() } = {})" in APP_JS
    assert "else state.setupSessionListsDirty = true;" in sync_body

    reload_body = _function_body("reloadCharacters", APP_JS)
    assert "const { render = true } = options;" in reload_body
    assert "markSetupRosterDirty();" in reload_body

    setup_body = _function_body("showSetupView", APP_JS)
    assert "if (state.setupSessionListsDirty) renderSetupSessionListsFromCache();" in setup_body
    assert "if (state.setupRosterDirty) renderSetupRosterFromCache();" in setup_body


def test_session_render_caches_stable_heavy_surfaces() -> None:
    """
    Map, icon key, and adventure log are expensive to rebuild after every small
    interaction.  Cache only those stable surfaces, and key session-owned DOM to
    the session id so saved-game switches cannot reuse stale content.
    """
    render_body = _function_body("renderSession", APP_JS)
    assert 'cachedSessionRender("map", mapRenderSignature(session), () => renderMap(session));' in render_body
    assert 'cachedSessionRender("iconKey", iconKeyRenderSignature(), () => renderIconKey());' in render_body
    assert 'cachedSessionRender("log", logRenderSignature(session), () => renderLog(session));' in render_body

    cache_body = _function_body("cachedSessionRender", APP_JS)
    assert "state.sessionRenderCache?.[label] === signature" in cache_body
    assert "state.sessionRenderCache[label] = signature" in cache_body

    log_signature = _function_body("logRenderSignature", APP_JS)
    assert 'sessionId: session?.id || ""' in log_signature
    assert "entries[entries.length - 1]" in log_signature

    map_signature = _function_body("mapRenderSignature", APP_JS)
    assert 'sessionId: session.id || ""' in map_signature
    assert "map: session.map_state" in map_signature
    assert "party: (session.party || []).map" in map_signature

    load_session_body = _function_body("loadSession", APP_JS)
    assert "resetSessionRenderCache();" in load_session_body

    log_mode_body = _function_body("setLogMode", APP_JS)
    assert 'resetSessionRenderCache(["log"]);' in log_mode_body

    start_handler = _event_listener_body("startSession", "click", APP_JS)
    assert "resetSessionRenderCache();" in start_handler


def test_cached_session_render_stays_limited_to_stable_heavy_surfaces() -> None:
    """
    The speed cache is for stable, expensive DOM only.  Dynamic panels still
    redraw every session render so combat controls, party state, exits, and
    targeting UI cannot be left stale by an over-broad optimization.
    """
    render_body = _function_body("renderSession", APP_JS)
    cached_labels = re.findall(r'cachedSessionRender\("([^"]+)"', render_body)
    assert cached_labels == ["map", "iconKey", "log"]

    for label in [
        "tacticalRoom",
        "combatHeroChips",
        "combatHeroDrawer",
        "tileDetail",
        "mapExits",
        "campPanel",
        "exitActions",
        "combatPanel",
        "partyState",
    ]:
        assert f'safeSessionRender("{label}"' in render_body


def test_current_party_marker_anchors_to_bottom_of_room_contents() -> None:
    """
    Room content markers belong in the walkable-center position.  The current
    party tag should sit at the bottom of the visible walkable bounds so it
    does not obscure treasure, event, foe, or fallen-hero icons.
    """
    assert "positionPartyMarkerInVisibleBounds(marker, tile, width, height);" in APP_JS
    assert "function positionPartyMarkerInVisibleBounds(element, tile, width, height)" in APP_JS

    body = _function_body("positionPartyMarkerInVisibleBounds", APP_JS)
    assert "walkableCellBounds(tile, width, height)" in body
    assert "(bounds.maxY + 1) / height" in body
    assert 'element.style.transform = "translate(-50%, -100%)";' in body

    assert ".placed-tile.current .map-square.walkable:not(.hidden)" in STYLES_CSS
    assert "background: rgba(198, 143, 59, 0.14);" in STYLES_CSS
    assert "background: rgba(198, 143, 59, 0.68);" in STYLES_CSS


def test_clipped_walkable_room_edges_are_render_only_seams() -> None:
    """
    Adjacent displayed walkable cells from different rooms need a visual seam,
    but this must stay in map rendering and not alter placement, rotation, or
    truncation data.
    """
    assert "const walkableCellOwnership = buildMapWalkableCellOwnership(session);" in APP_JS
    assert "tileOverlay(tile, session, cellOwnership, { walkableCellOwnership })" in APP_JS
    assert "function buildMapWalkableCellOwnership(session)" in APP_JS
    assert "function clippedWalkableEdgeClasses(tile, x, y, walkableCellOwnership)" in APP_JS

    ownership_body = _function_body("buildMapWalkableCellOwnership", APP_JS)
    assert "normalizedVisible(tile, width, height)" in ownership_body
    assert "normalizedWalkable(tile, width, height)" in ownership_body
    assert 'if (walkable[y]?.[x] === "0") continue;' in ownership_body
    assert "ownership.set(key, { tileId: tile.id, tileIndex: tileIndexes.get(tile.id) ?? 0 });" in ownership_body

    seam_body = _function_body("clippedWalkableEdgeClasses", APP_JS)
    assert "neighbor.tileId === tile.id" in seam_body
    assert "owner.tileIndex <= neighbor.tileIndex" in seam_body
    assert "classes.push(`clipped-edge-${edge.direction}`);" in seam_body

    overlay_body = _function_body("tileOverlay", APP_JS)
    assert "clippedWalkableEdgeClasses(tile, x, y, walkableCellOwnership)" in overlay_body
    assert "${clippedEdgeClass}" in overlay_body

    assert '.map-square[class*="clipped-edge-"]::before' in STYLES_CSS
    for direction in ("north", "east", "south", "west"):
        assert f".map-square.clipped-edge-{direction}" in STYLES_CSS


def test_combat_deck_does_not_duplicate_foe_list_before_actions() -> None:
    """
    Foes are listed in the Encounter rail and tactical map.  The slim action
    deck should not repeat the same foe list above Start Combat / Check
    Reactions.
    """
    body = _function_body("renderCombatDeckSlim", APP_JS)
    assert "combat-deck-foe-peek" not in body
    assert "combat-deck-foe-list" not in body
    assert "Start Combat" in body


def test_scout_ahead_ui_uses_pending_scout_id_and_exit_button() -> None:
    """The scout-ahead feature must use a two-phase UI:
    1. Party-sheet 'Scout ahead…' button sets state.pendingScoutId (no immediate API call).
    2. Exit rows show a 'Scout [name] through' button when pendingScoutId is set.
    3. That button calls advance('scout_ahead', { character_id, exit_id }).
    4. A 'Cancel scout' button clears the pending state without an API call.
    """
    assert "pendingScoutId: null" in APP_JS

    party_body = _function_body("appendPartyMemberSheet", APP_JS)
    # Scout ahead button sets state.pendingScoutId instead of calling advance directly
    assert "state.pendingScoutId = member.character_id" in party_body
    assert "Cancel scout" in party_body
    assert "state.pendingScoutId = null" in party_body
    assert "state.mapExitsOpen = true;" in party_body
    assert "setStatus(`Choose an open exit for ${member.name}, or open a door first.`);" in party_body

    exits_fn = _function_body("appendExitRowActions", APP_JS)
    # Exit row shows scout button when pendingScoutId is set
    assert "state.pendingScoutId" in exits_fn
    assert "Scout ${scout.name} through" in exits_fn
    assert "setButtonTooltip(scoutBtn, ACTION_TOOLTIPS.scoutThrough);" in exits_fn
    assert "advance(\"scout_ahead\", { character_id: state.pendingScoutId, exit_id: exit.id })" in exits_fn

    # After any advance() call the pending scout is cleared server-side
    advance_fn = _function_body("advance", APP_JS)
    assert "state.pendingScoutId = null" in advance_fn


def test_append_member_exploration_actions_defines_in_exploration() -> None:
    """Exploration item buttons must not reference an undefined inExploration flag."""
    body = _function_body("appendMemberExplorationActions", APP_JS)
    assert "const inExploration = session.mode === \"exploration\" && member.current_life > 0;" in body
    assert "const immediateLocked = surpriseReactionLocked(session);" in body


def test_eligible_expert_skill_options_declares_class_codes() -> None:
    body = _function_body("eligibleExpertSkillOptions", APP_JS)
    assert "const codes = CLASS_SKILL_CODES[member.class_id] || [];" in body


def test_professional_coating_eligible_items_handles_null_member() -> None:
    body = _function_body("professionalCoatingEligibleItems", APP_JS)
    assert "if (!member) return [];" in body


def test_fiendish_foes_prefs_element_is_bound() -> None:
    """syncRulesetControls toggles the Fiendish Foes fieldset; missing const crashes startup."""
    assert 'const fiendishFoesPrefs = document.getElementById("fiendish-foes-prefs");' in APP_JS
    sync_body = _function_body("syncRulesetControls", APP_JS)
    assert "fiendishFoesPrefs?.classList.toggle" in sync_body


def test_dom_optional_chain_targets_are_declared() -> None:
    """Identifiers used with ?. must be declared somewhere in app.js (prevents ReferenceError crashes)."""
    declared = set(re.findall(r"\b(?:const|let|var|function)\s+(\w+)", APP_JS))
    declared.update(re.findall(r"\((\w+)\)\s*=>", APP_JS))
    dom_suffixes = ("El", "Btn", "Select", "Prefs", "Hint", "Panel", "Form", "Input", "Dialog")
    pattern = re.compile(rf"\b(\w+(?:{'|'.join(dom_suffixes)}))\?\.")

    missing: list[str] = []
    for match in pattern.finditer(APP_JS):
        ident = match.group(1)
        if ident not in declared:
            missing.append(ident)
    assert not missing, f"DOM-like handles used with ?. but never declared: {sorted(set(missing))}"


def test_scope_sensitive_action_helpers_declare_lock_flags() -> None:
    """Combat/exploration action helpers must declare lock flags locally, not leak from siblings."""
    for fn_name in ("appendMemberExplorationActions", "appendMemberCombatActions", "renderCombatDeckSlim"):
        body = _function_body(fn_name, APP_JS)
        if "immediateLocked" in body:
            assert re.search(r"\bconst immediateLocked\b", body), f"{fn_name} uses immediateLocked without declaring it"
        if "combatLocked" in body:
            assert re.search(r"\bconst combatLocked\b", body), f"{fn_name} uses combatLocked without declaring it"


def test_fiendish_foes_and_poison_expert_setup_tooltips() -> None:
    """Fiendish Foes checkboxes and Poison Expert camp controls should expose hover hints."""
    setup_body = _function_body("applySetupTooltips", APP_JS)
    assert "SETUP_TOOLTIPS.fiendishFoesRandom" in APP_JS
    assert "SETUP_TOOLTIPS.fiendishFoesImported" in APP_JS
    assert "SETUP_TOOLTIPS.fiendishFoesAi" in APP_JS
    assert "SETUP_TOOLTIPS.fiendishFoesHint" in setup_body
    hirelings_body = _function_body("appendCampHirelingsPanel", APP_JS)
    assert "ACTION_TOOLTIPS.poisonExpertUse" in hirelings_body
    assert "ACTION_TOOLTIPS.poisonExpertCoat" in hirelings_body
    assert "HIRELING_TOOLTIPS.poisonExpertProfessional" in hirelings_body
    assert "camp-hirelings-expert-gate" in hirelings_body
    assert "tierTrainingButtons(session, member, row)" in hirelings_body
    assert "camp-alchemist-potion-select" in hirelings_body
    assert "camp-alchemist-hero-select" in hirelings_body
    assert "camp-professional-controls" in hirelings_body
    assert "camp-professional-coating-controls" in APP_JS
    assert "professionalNeedsHeroTarget" in APP_JS
    assert "professionalNeedsItemChoice" in APP_JS
    assert "effectiveShopCharacter" in APP_JS
    assert "window.prompt(`Choose potion number" not in hirelings_body
    assert "window.prompt(`Choose hero number" not in hirelings_body


def test_ai_adventure_panel_has_hover_tooltips() -> None:
    """AI Adventure prompt/import controls should expose hover hints like the rest of setup."""
    assert "const AI_ADVENTURE_TOOLTIPS = {" in APP_JS
    assert "function applyAiAdventureTooltips()" in APP_JS
    assert "applyAiAdventureTooltips();" in _function_body("applySetupTooltips", APP_JS)
    assert "AI_ADVENTURE_TOOLTIPS.generatePrompt" in APP_JS
    assert "AI_ADVENTURE_TOOLTIPS.validateImport" in APP_JS
    assert "AI_ADVENTURE_TOOLTIPS.importAdventure" in APP_JS
    assert "SETUP_TOOLTIPS.adventureSelect" in APP_JS


def test_import_preview_shows_errors_below_validate_buttons() -> None:
  body = _function_body("renderImportPreview", APP_JS)
  assert "ai-import-preview-title" in body
  assert "ai-import-preview-errors" in body
  assert "import-invalid" in body
  assert "focusImportPreview" in body
  assert "showImportFailure" in _function_body("validateAdventureImport", APP_JS)
  assert "see errors below Validate" in APP_JS


def test_combat_minimap_respects_imported_fog_of_war() -> None:
    body = _function_body("renderCombatMinimap", APP_JS)
    assert "const importedMode = session.adventure_type === \"imported\"" in body
    assert "const visibleTiles = importedMode" in body
    assert "visibleMapBounds(session, visibleTiles)" in body


def test_map_exit_menu_includes_scout_navigation_actions() -> None:
    """Map door/exit clicks use collectExitMenuItems(), so scout navigation must
    be available there as well as in the Exits pane."""
    assert "function collectScoutExitMenuItems(session, exit)" in APP_JS

    scout_menu = _function_body("collectScoutExitMenuItems", APP_JS)
    assert "state.pendingScoutId" in scout_menu
    assert "exit.dungeon_exit" in scout_menu
    assert "ACTION_TOOLTIPS.scoutClosedDoor" in scout_menu
    assert "ACTION_TOOLTIPS.scoutThrough" in scout_menu
    assert "advance(\"scout_ahead\", { character_id: state.pendingScoutId, exit_id: exit.id })" in scout_menu

    travel_menu = _function_body("collectTravelExitMenuItems", APP_JS)
    assert "items.push(...collectScoutExitMenuItems(session, exit));" in travel_menu

    exit_menu = _function_body("collectExitMenuItems", APP_JS)
    assert "items.push(...collectScoutExitMenuItems(session, exit));" in exit_menu


def test_map_exits_overlay_uses_active_detached_tile() -> None:
    """
    When a detached/scout group is active for navigation, the Exits panel must
    render exits from activeTile(session), not the main party's currentTile().
    Otherwise a scout cannot navigate back to rejoin.
    """
    render_body = _function_body("renderMapExitsOverlay", APP_JS)
    assert "const tile = activeTile(session);" in render_body
    assert "buildExitListElement(session, tile)" in render_body
    assert "Choose an open exit below to send ${scout.name} scouting" in render_body
    assert "Open a closed door first; then send ${scout.name} scouting through that exit." in render_body

    build_body = _function_body("buildExitListElement", APP_JS)
    assert "const tile = currentTile(session)" not in build_body


def test_closed_doors_explain_scouting_requires_open_exit() -> None:
    """If the player has selected a scout but exits are closed doors, the row
    should explain why no Scout-through button is visible yet."""
    exits_fn = _function_body("appendExitRowActions", APP_JS)
    assert "Open this door before scouting through it." in exits_fn
    assert "note.title = ACTION_TOOLTIPS.scoutClosedDoor;" in exits_fn


def test_active_detached_group_has_distinct_map_marker() -> None:
    """The active detached navigation group should be visible on the map, not
    only in the party sheet heading."""
    render_map = _function_body("renderMap", APP_JS)
    assert 'el.classList.add("active-detached");' in render_map

    markers = _function_body("tileContentMarkers", APP_JS)
    assert "const activeDetached = session.active_group_tile_id === tile.id" in markers
    assert 'markerClass: activeDetached ? "active-detached" : "detached"' in markers
    assert "active detached group" in markers

    assert ".placed-tile.active-detached" in STYLES_CSS
    assert ".map-content-marker.active-detached" in STYLES_CSS


def test_combat_foe_chip_strip_renders_foes_and_final_boss_state() -> None:
    assert 'id="combat-foe-chips"' in INDEX_HTML
    assert 'const combatFoeChipsEl = document.getElementById("combat-foe-chips");' in APP_JS
    assert 'safeSessionRender("combatFoeChips", () => renderCombatFoeChips(session));' in APP_JS
    assert "function renderCombatFoeChips(session)" in APP_JS

    body = _function_body("renderCombatFoeChips", APP_JS)
    assert "foeChipGroups(livingFoes)" in body
    assert "foeIsFinalBoss" in body
    assert "Final Boss" in body
    assert "foeChipTitle(displayName, typeLabel, foe)" in body
    assert "function foeRulesSummary(foe)" in APP_JS
    assert "function foeMagicResistanceTier(foe)" in APP_JS
    assert "if (tags.has(\"magic_resist\")) tier += 1;" in APP_JS
    assert "if (tags.has(\"caster\")) tier += 1;" in APP_JS
    assert "if (tags.has(\"dragon\")) tier += 1;" in APP_JS
    assert "labels.push(`MR +${mrTier}`)" in APP_JS
    assert "Traits: ${labels.join" in APP_JS
    assert "Tags: ${tags.join" in APP_JS
    assert "openCombatFoeMenu(session, tile, foe, chip, foeLabels)" in body
    assert "for (const detail of foeRulesSummary(foe))" in APP_JS
    assert ".combat-foe-chips" in STYLES_CSS
    assert ".combat-foe-chip.final-boss" in STYLES_CSS


def test_home_roster_shop_tiers_and_party_sheet_bulk_controls() -> None:
    assert 'id="party-sheets-expand"' in INDEX_HTML
    assert 'id="party-sheets-collapse"' in INDEX_HTML
    assert 'aria-label="Expand all party sheets"' in INDEX_HTML
    assert 'aria-label="Collapse all party sheets"' in INDEX_HTML
    assert "Expand all</button>" not in INDEX_HTML
    assert "Collapse all</button>" not in INDEX_HTML
    assert 'const partySheetsExpandBtn = document.getElementById("party-sheets-expand");' in APP_JS
    assert 'const partySheetsCollapseBtn = document.getElementById("party-sheets-collapse");' in APP_JS
    assert "function setAllPartySheetsOpen(open)" in APP_JS
    assert 'partySheetsExpandBtn?.addEventListener("click", () => setAllPartySheetsOpen(true));' in APP_JS
    assert 'partySheetsCollapseBtn?.addEventListener("click", () => setAllPartySheetsOpen(false));' in APP_JS
    assert "function tierTrainingLabels(member)" in APP_JS
    assert "roster-status-badge roster-tier-badge" in APP_JS
    assert "tierTrainingLabels(member)" in _function_body("partySheetSummaryLine", APP_JS)
    assert 'id="roster-list-resizer"' in INDEX_HTML
    assert "rosterListHeight" in APP_JS
    assert "setupDragResizer(rosterListResizer" in APP_JS
    assert "--roster-list-height" in STYLES_CSS
    roster_list_block = STYLES_CSS.split(".roster-list {", 1)
    assert len(roster_list_block) > 1, ".roster-list CSS block missing"
    assert "resize: vertical;" not in roster_list_block[1].split("}", 1)[0]
    assert ".roster-tier-badge" in STYLES_CSS


def test_transfer_dialog_explains_item_capacity_blocks() -> None:
    assert "function memberReceiveItemBlockReason(member, itemName, session = null)" in APP_JS
    assert "has ${used}/${weaponCap} weapon slots used" in APP_JS
    assert "needs ${slots}" in APP_JS
    assert "label.title = blocked ? blockReason" in APP_JS
    assert "recipient full" not in APP_JS


def test_equipment_shop_uses_active_session_spendable_bank_gold() -> None:
    assert "function shopSpendableGold(character)" in APP_JS
    assert 'id="equipment-shop-quantity"' in INDEX_HTML
    assert "const equipmentShopQuantityInput" in APP_JS
    assert "function selectedShopQuantity()" in APP_JS
    assert "function updateEquipmentShopQuantityLimit()" in APP_JS
    assert "member.gold || 0) + (member.bank_gold || 0)" in APP_JS
    body = _function_body("refreshEquipmentShopDialog", APP_JS)
    assert "const spendableGold = shopSpendableGold(character);" in body
    assert "spendableGold < item.price_gp" in body
    assert "Not enough spendable gold" in body
    confirm = _function_body("confirmEquipmentShopDialog", APP_JS)
    assert "const quantity = selectedShopQuantity();" in confirm
    assert "const payload = { item_key: itemKey, quantity };" in confirm
    assert "payload.target_weapon" in confirm


def test_final_boss_completion_banner_and_completed_sessions_return_home() -> None:
    assert "function finalBossCompletionBanner(session)" in APP_JS
    assert "Final Boss slain" in APP_JS
    assert "The dungeon objective is complete." in APP_JS
    assert ".final-boss-complete-banner" in STYLES_CSS

    advance_body = _function_body("advance", APP_JS)
    assert 'if (state.session.mode === "complete")' in advance_body
    assert "state.session = null;" in advance_body
    assert 'writeActiveView("setup");' in advance_body
    assert "showSetupView();" in advance_body


def test_status_effect_chips_have_hover_text() -> None:
    assert "function statusChipTooltip(label)" in APP_JS
    body = _function_body("appendStatusChips", APP_JS)
    assert "el.title = title;" in body
    assert "el.dataset.tooltip = title;" in body
    assert "Shield bonus applies" in APP_JS
    assert "Blessed Temple/Shrine: +1 Attack vs undead and demon foes until one such foe is slain." in APP_JS
    assert "Magic Resistance" in APP_JS


def test_failed_scout_panel_exposes_reaction_rush_and_flee_controls() -> None:
    body = _function_body("renderDetachedCombatPanel", APP_JS)
    assert "session.scout_encounter_origin_tile_ids" in body
    assert "Check scout reaction" in body
    assert "Fight scout round" in body
    assert "Rush to Scout" in body
    assert "Scout flees back" in body
    assert 'advance("scout_reaction", { detached_tile_id: tile.id })' in body
    assert 'advance("rush_to_scout", { detached_tile_id: tile.id })' in body
    assert 'advance("scout_flee_back", { detached_tile_id: tile.id })' in body


def test_exploration_command_bar_stays_visible_and_typable() -> None:
    """
    Command input must sit below the scrollable log (not clipped by overflow:hidden)
    and stay enabled while session actions run so players can queue the next command.
    """
    assert 'id="exploration-command-input"' in INDEX_HTML
    assert 'id="exploration-command-bar"' in INDEX_HTML
    assert "function renderExplorationCommandBar(session)" in APP_JS
    assert "function executeExplorationCommand(rawInput)" in APP_JS
    assert "explorationCommandForm?.addEventListener(\"submit\"" in APP_JS
    render_body = _function_body("renderExplorationCommandBar", APP_JS)
    assert "explorationCommandInput.disabled" not in render_body
    assert "flex: 1 1 0%" in STYLES_CSS.split(".map-log {", 1)[1].split("}", 1)[0]
    assert "flex-shrink: 0" in STYLES_CSS.split(".exploration-command-bar {", 1)[1].split("}", 1)[0]
