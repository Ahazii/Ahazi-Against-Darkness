from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from .dice import roll_2d6, roll_d6
from .tables import DungeonTables
from ..models import Enemy, Tile, MapState


@dataclass(frozen=True)
class TileContentResult:
    content: str
    enemies: list[Enemy]
    objects: list[str]


class RandomAdventure:
    def __init__(self, width: int = 20, height: int = 28) -> None:
        self.width = width
        self.height = height
        self.tables = DungeonTables()

    def create_map(self) -> MapState:
        start_x = self.width // 2
        start_y = self.height - 1
        tile_id = uuid4().hex
        start_tile = Tile(
            id=tile_id,
            x=start_x,
            y=start_y,
            tile_type="room",
            content="Entrance",
            enemies=[],
            objects=["Entrance"],
            visited=True,
        )
        return MapState(
            width=self.width,
            height=self.height,
            tiles=[start_tile],
            current_tile_id=tile_id,
        )

    def generate_next_tile(
        self,
        map_state: MapState,
        hcl: int,
    ) -> tuple[MapState, Tile]:
        current_tile = next(tile for tile in map_state.tiles if tile.id == map_state.current_tile_id)
        candidates = [
            (current_tile.x + 1, current_tile.y),
            (current_tile.x - 1, current_tile.y),
            (current_tile.x, current_tile.y + 1),
            (current_tile.x, current_tile.y - 1),
        ]
        available = [
            (x, y)
            for (x, y) in candidates
            if 0 <= x < map_state.width
            and 0 <= y < map_state.height
            and not any(t.x == x and t.y == y for t in map_state.tiles)
        ]
        if not available:
            return map_state, current_tile

        next_x, next_y = available[roll_d6() % len(available)]
        tile_type: Literal["room", "corridor"] = "corridor" if roll_d6() <= 2 else "room"
        content_result = self.roll_tile_content(tile_type, hcl)

        new_tile = Tile(
            id=uuid4().hex,
            x=next_x,
            y=next_y,
            tile_type=tile_type,
            content=content_result.content,
            enemies=content_result.enemies,
            objects=content_result.objects,
            visited=True,
        )
        map_state.tiles.append(new_tile)
        map_state.current_tile_id = new_tile.id
        return map_state, new_tile

    def roll_tile_content(self, tile_type: Literal["room", "corridor"], hcl: int) -> TileContentResult:
        roll = roll_2d6()
        enemies: list[Enemy] = []
        objects: list[str] = []
        content = "Empty"

        if roll == 2:
            content = "Treasure"
            objects.append("Treasure")
        elif roll == 3:
            content = "Treasure + Trap"
            objects.extend(["Trap", "Treasure"])
        elif roll == 4:
            content = "Special Event"
            objects.append("Special Event")
        elif roll == 5:
            if tile_type == "corridor":
                content = "Empty"
            else:
                content = "Special Feature"
                objects.append("Special Feature")
        elif roll == 6:
            foe = self.tables.roll_foe("vermin", hcl)
            content = f"Vermin: {foe.name}"
            enemies.extend(self._expand_foes(foe))
        elif roll == 7:
            foe = self.tables.roll_foe("minions", hcl)
            content = f"Minions: {foe.name}"
            enemies.extend(self._expand_foes(foe))
        elif roll == 8:
            if tile_type == "corridor":
                content = "Empty"
            else:
                foe = self.tables.roll_foe("minions", hcl)
                content = f"Minions: {foe.name}"
                enemies.extend(self._expand_foes(foe))
        elif roll == 9:
            content = "Empty"
            objects.append("Searchable")
        elif roll == 10:
            if tile_type == "corridor":
                content = "Empty"
            else:
                foe = self.tables.roll_foe("weird", hcl)
                content = f"Weird Monster: {foe.name}"
                enemies.extend(self._expand_foes(foe))
        elif roll == 11:
            if tile_type == "corridor":
                content = "Empty"
            else:
                foe = self.tables.roll_foe("boss", hcl)
                content = f"Boss: {foe.name}"
                enemies.extend(self._expand_foes(foe))
        elif roll == 12:
            if tile_type == "corridor":
                content = "Empty"
            else:
                content = "Dragon's Lair"
                objects.append("Dragon's Lair")

        return TileContentResult(content=content, enemies=enemies, objects=objects)

    def _expand_foes(self, foe) -> list[Enemy]:
        enemies: list[Enemy] = []
        for _ in range(foe.count):
            enemies.append(
                Enemy(
                    id=uuid4().hex,
                    name=foe.name,
                    level=foe.level,
                    life=foe.life,
                    attacks=foe.attacks,
                )
            )
        return enemies
