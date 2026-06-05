"""
Regression guard for map interaction behaviours that were broken by CSS/JS refactors
and repaired in v0.68.7–v0.68.9.

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


# ── syncMapViewportMode: early-return before clampMapPan ──────────────────────

def test_sync_map_viewport_mode_returns_early_before_clamp_map_pan() -> None:
    """
    When the map overflows the viewport (scroll mode), syncMapViewportMode must
    return early BEFORE calling clampMapPan().

    clampMapPan reads mapEl.offsetWidth; if layout is transiently incomplete
    that value can be 0, which makes clampMapPan set
    mapPanX = viewportWidth / 2 (~500 px), shifting the entire map to the right
    on every zoom and breaking RM centering.

    Safe pattern: set panX/panY = 0, call applyMapTransform(), return.
    Only call clampMapPan in the transform (non-scroll) branch.
    (Regressed in v0.68.8 per-axis refactor; fixed v0.68.9.)
    """
    body = _function_body("syncMapViewportMode", APP_JS)
    clamp_pos = body.find("clampMapPan()")
    early_return_pos = body.find("return;")
    assert clamp_pos != -1, "clampMapPan() not found in syncMapViewportMode"
    assert early_return_pos != -1, "early return not found in syncMapViewportMode"
    assert early_return_pos < clamp_pos, (
        "syncMapViewportMode must return early (before clampMapPan) in scroll mode"
    )


# ── positionMapContentAtPointer ────────────────────────────────────────────────

def test_position_map_content_at_pointer_calls_sync_before_scroll_range() -> None:
    """
    positionMapContentAtPointer must call syncMapViewportMode() before it reads
    mapScrollRange().  Without the guard, a stale mapPanX from a previous
    transform-mode state can fight with the new scroll positioning and shift the
    focal point sideways.
    (Originally present; accidentally removed in v0.68.8; restored v0.68.9.)
    """
    body = _function_body("positionMapContentAtPointer", APP_JS)
    sync_pos = body.find("syncMapViewportMode()")
    range_pos = body.find("mapScrollRange()")
    assert sync_pos != -1, "syncMapViewportMode() missing from positionMapContentAtPointer"
    assert range_pos != -1, "mapScrollRange() missing from positionMapContentAtPointer"
    assert sync_pos < range_pos, (
        "syncMapViewportMode() must appear before mapScrollRange() in positionMapContentAtPointer"
    )


# ── centerMapOnPoint ────────────────────────────────────────────────────────────

def test_center_map_on_point_calls_sync_before_scroll_range() -> None:
    """
    centerMapOnPoint (used by RM button → centerMapOnTile → centerMapOnWorldBounds)
    must call syncMapViewportMode() before reading mapScrollRange(), for the same
    reason as positionMapContentAtPointer.
    (Originally present; accidentally removed in v0.68.8; restored v0.68.9.)
    """
    body = _function_body("centerMapOnPoint", APP_JS)
    sync_pos = body.find("syncMapViewportMode()")
    range_pos = body.find("mapScrollRange()")
    assert sync_pos != -1, "syncMapViewportMode() missing from centerMapOnPoint"
    assert range_pos != -1, "mapScrollRange() missing from centerMapOnPoint"
    assert sync_pos < range_pos, (
        "syncMapViewportMode() must appear before mapScrollRange() in centerMapOnPoint"
    )


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
    applyMapPanDelta (used by drag and arrow-pad buttons) must clear mapPanX/Y
    to zero when the map is in scroll mode before applying the scroll delta.
    Without this, a stale transform offset doubles with the scroll offset and
    appears to move the map to the wrong position.
    """
    body = _function_body("applyMapPanDelta", APP_JS)
    assert "state.mapPanX = 0;" in body
    assert "state.mapPanY = 0;" in body
    assert "mapViewportEl.scrollLeft" in body
    assert "mapViewportEl.scrollTop" in body


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
