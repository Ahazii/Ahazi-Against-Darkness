from __future__ import annotations

from app.engine.dice import roll_tile_key


def test_roll_tile_key_uses_d66_faces() -> None:
    for _ in range(500):
        key = roll_tile_key()
        assert len(key) == 2
        assert key[0] in "123456"
        assert key[1] in "123456"
