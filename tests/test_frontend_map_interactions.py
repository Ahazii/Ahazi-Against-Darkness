"""
Regression guard for map interaction behaviours that were broken by CSS/JS refactors
and repaired in v0.68.7–v0.68.10.

Each test documents *why* the check is important, not just what string to find, so
future maintainers know the consequence of removing or changing the guarded code.
"""
from __future__ import annotations

from pathlib import Path


APP_JS = Path("src/app/static/app.js").read_text(encoding="utf-8")
STYLES_CSS = Path("src/app/static/styles.css").read_text(encoding="utf-8")


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
