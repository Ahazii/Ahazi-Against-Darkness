from __future__ import annotations

from pathlib import Path


def test_frontend_keeps_dungeon_and_linked_inset_exits_visible() -> None:
    app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")

    assert "!exit.dungeon_exit && !exit.destination_tile_id && exitPointsInward(tile, exit)" in app_js
