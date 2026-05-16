from __future__ import annotations

import random
from pathlib import Path
from uuid import uuid4

from ..db import now_utc
from ..rules.repository import RulesRepository
from ..schemas import (
    EnemyState,
    ExitState,
    MapState,
    PartyMemberState,
    SessionState,
    TileDefinition,
    TileState,
)
from .combat import resolve_combat_round
from .dice import roll_2d6, roll_d6, roll_formula, roll_tile_key


DIRECTIONS: dict[str, tuple[int, int]] = {
    "north": (0, -1),
    "east": (1, 0),
    "south": (0, 1),
    "west": (-1, 0),
}
OPPOSITE = {"north": "south", "east": "west", "south": "north", "west": "east"}
DIRECTION_ORDER = ["north", "east", "south", "west"]
ROTATIONS = [0, 90, 180, 270]


class RandomDungeonEngine:
    def __init__(self, rules: RulesRepository, asset_dir: Path) -> None:
        self.rules = rules
        self.asset_dir = asset_dir

    def create_session(self, session_id: str, party_id: str, party: list[PartyMemberState]) -> SessionState:
        entrance = TileState(
            id=uuid4().hex,
            x=0,
            y=0,
            tile_key="01",
            tile_type="room",
            rotation=0,
            footprint_width=1,
            footprint_height=1,
            image=self._tile_image("01"),
            title="Entrance",
            description="The party enters the dungeon.",
            content_key="entrance",
            objects=["Entrance"],
            exits=[
                ExitState(direction="north", kind="passage", position=0.5),
                ExitState(direction="east", kind="door", position=0.5),
                ExitState(direction="west", kind="door", position=0.5),
            ],
        )
        timestamp = now_utc()
        return SessionState(
            id=session_id,
            party_id=party_id,
            adventure_id="random",
            adventure_type="random",
            mode="exploration",
            party=party,
            map_state=MapState(tiles=[entrance], current_tile_id=entrance.id),
            log=["Adventure begins at the dungeon entrance."],
            created_at=timestamp,
            updated_at=timestamp,
        )

    def advance(
        self,
        session: SessionState,
        action: str,
        exit_id: str | None = None,
        direction: str | None = None,
    ) -> SessionState:
        if session.mode == "complete":
            session.log.append("This adventure is complete.")
            return self._touch(session)

        if action == "explore":
            self._explore(session, exit_id, direction)
        elif action == "search":
            self._search(session)
        elif action == "combat_round":
            self._combat_round(session)
        elif action == "rest":
            self._rest(session)
        else:
            session.log.append(f"Unknown action: {action}.")

        return self._touch(session)

    def _explore(self, session: SessionState, exit_id: str | None = None, direction: str | None = None) -> None:
        if session.mode != "exploration":
            session.log.append("Exploration is blocked until the current encounter is resolved.")
            return

        current = self._current_tile(session)
        if exit_id:
            exit_state = next((item for item in current.exits if item.id == exit_id), None)
            if exit_state is None:
                session.log.append("That exit is not available from this tile.")
                return
        elif direction:
            exit_state = next((item for item in current.exits if item.direction == direction), None)
            if exit_state is None:
                session.log.append(f"There is no exit to the {direction}.")
                return
            if exit_state.status == "blocked":
                session.log.append(f"The {direction} exit is blocked.")
                return
        else:
            exit_state = next((item for item in current.exits if item.status == "unexplored"), None)

        if exit_state is None:
            exit_state = self._add_emergency_exit(session, current)
            if exit_state is None:
                session.log.append("There are no open ways forward from this location.")
                return

        if exit_state.kind == "door" and exit_state.door_result is None:
            exit_state.door_result = self._roll_door_result()
            session.log.append(f"Door: {exit_state.door_result}")

        dx, dy = DIRECTIONS[exit_state.direction]
        destination = (current.x + dx, current.y + dy)
        existing = (
            self._tile_by_id(session, exit_state.destination_tile_id)
            if exit_state.destination_tile_id
            else self._tile_at(session, *destination)
        )
        exit_state.status = "open"
        if existing:
            exit_state.destination_tile_id = existing.id
            self._set_reciprocal_exit(existing, current, exit_state)
            session.map_state.current_tile_id = existing.id
            session.log.append(f"The party moves {exit_state.direction} to {existing.title}.")
            return

        new_tile = self._generate_tile(
            x=destination[0],
            y=destination[1],
            entered_from=OPPOSITE[exit_state.direction],
            hcl=self._highest_character_level(session.party),
        )
        if self._overlaps_existing(session, new_tile):
            session.log.append("No legal placement is available for that tile without overlap. Draw another tile.")
            return
        exit_state.destination_tile_id = new_tile.id
        session.map_state.tiles.append(new_tile)
        self._set_reciprocal_exit(new_tile, current, exit_state)
        session.map_state.current_tile_id = new_tile.id
        session.log.append(f"Entered {new_tile.title}: {new_tile.description}")
        if new_tile.enemies:
            session.mode = "combat"
            session.log.append("An encounter starts.")

    def _search(self, session: SessionState) -> None:
        if session.mode != "exploration":
            session.log.append("Search after the encounter is resolved.")
            return
        tile = self._current_tile(session)
        if tile.searched:
            session.log.append("This location has already been searched.")
            return

        tile.searched = True
        roll = roll_d6()
        if roll == 1:
            foe = self._roll_enemy("wandering", self._highest_character_level(session.party))
            tile.enemies.extend(foe)
            session.mode = "combat"
            session.log.append("The search attracts wandering monsters.")
        elif roll <= 4:
            session.log.append("The search finds nothing useful.")
        elif roll == 5:
            tile.objects.append("Clue")
            session.log.append("The party finds a clue.")
        else:
            tile.objects.append("Hidden Treasure")
            session.log.append("The party finds hidden treasure.")

    def _combat_round(self, session: SessionState) -> None:
        if session.mode != "combat":
            session.log.append("There are no active enemies here.")
            return
        tile = self._current_tile(session)
        result = resolve_combat_round(session.party, tile.enemies)
        session.party = result.party
        tile.enemies = result.enemies
        session.log.extend(result.log)
        if not result.combat_over:
            return

        if not any(pc.current_life > 0 for pc in session.party):
            session.mode = "complete"
            session.log.append("The party has fallen.")
            return

        tile.enemies = [enemy for enemy in tile.enemies if enemy.life > 0]
        tile.resolved = True
        session.mode = "exploration"
        session.log.append("Combat ends.")

    def _rest(self, session: SessionState) -> None:
        if session.mode != "exploration":
            session.log.append("The party cannot rest during combat.")
            return
        for pc in session.party:
            if pc.current_life > 0 and pc.current_life < pc.max_life:
                pc.current_life += 1
        session.log.append("The party catches its breath and recovers 1 life where possible.")

    def _generate_tile(self, x: int, y: int, entered_from: str, hcl: int) -> TileState:
        tile_key = roll_tile_key()
        tile_def = self.rules.tiles().get(tile_key)
        tile_type = self._tile_type(tile_def.tile_type if tile_def else "unknown")
        content = self._roll_content(tile_type, hcl)
        rotation, exits = self._generate_exits(tile_type, entered_from, tile_def)
        return TileState(
            id=uuid4().hex,
            x=x,
            y=y,
            tile_key=tile_key,
            tile_type=tile_type,
            rotation=rotation,
            footprint_width=tile_def.footprint_width if tile_def else 1,
            footprint_height=tile_def.footprint_height if tile_def else 1,
            image=self._tile_image(tile_key, tile_def.image if tile_def else None),
            title=tile_def.name if tile_def else f"{tile_type.title()} {tile_key}",
            description=self._tile_description(tile_def.description if tile_def else "", content["description"]),
            content_key=content["key"],
            objects=content["objects"],
            enemies=content["enemies"],
            exits=exits,
        )

    def _roll_content(self, tile_type: str, hcl: int) -> dict:
        roll = roll_2d6()
        if roll == 2:
            return self._content("treasure", "There is treasure here.", ["Treasure"], [])
        if roll == 3:
            return self._content("trap_treasure", "A trap protects treasure.", ["Trap", "Treasure"], [])
        if roll == 4:
            return self._content("special_event", "A special event is triggered.", ["Special Event"], [])
        if roll == 5 and tile_type == "room":
            return self._content("special_feature", "The room contains a special feature.", ["Special Feature"], [])
        if roll == 6:
            return self._content("vermin", "Vermin are present.", [], self._roll_enemy("vermin", hcl))
        if roll in (7, 8) and tile_type == "room":
            return self._content("minions", "Minions occupy this room.", [], self._roll_enemy("minions", hcl))
        if roll == 10 and tile_type == "room":
            return self._content("weird", "A strange monster blocks the way.", [], self._roll_enemy("weird", hcl))
        if roll == 11 and tile_type == "room":
            return self._content("boss", "A boss monster waits here.", [], self._roll_enemy("boss", hcl))
        if roll == 12 and tile_type == "room":
            return self._content("lair", "This chamber feels like a lair.", ["Lair"], self._roll_enemy("boss", hcl))
        if roll == 9:
            return self._content("searchable", "The area looks worth searching.", ["Searchable"], [])
        return self._content("empty", "The area is quiet.", [], [])

    def _content(self, key: str, description: str, objects: list[str], enemies: list[EnemyState]) -> dict:
        return {"key": key, "description": description, "objects": objects, "enemies": enemies}

    def _generate_exits(
        self,
        tile_type: str,
        entered_from: str,
        tile_def: TileDefinition | None,
    ) -> tuple[int, list[ExitState]]:
        if tile_def and tile_def.exits:
            rotations = ROTATIONS[:]
            random.shuffle(rotations)
            for rotation in rotations:
                exits = [
                    ExitState(
                        id=exit_def.id,
                        direction=self._rotate_direction(exit_def.direction, rotation),
                        kind=exit_def.kind,
                        position=exit_def.position,
                        status="unexplored",
                    )
                    for exit_def in tile_def.exits
                ]
                matching = next((exit_state for exit_state in exits if exit_state.direction == entered_from), None)
                if matching:
                    matching.status = "open"
                    return rotation, exits

            exits = [
                ExitState(
                    id=exit_def.id,
                    direction=exit_def.direction,
                    kind=exit_def.kind,
                    position=exit_def.position,
                )
                for exit_def in tile_def.exits
            ]
            exits.append(ExitState(direction=entered_from, kind="passage", status="open"))
            return 0, exits

        directions = list(DIRECTIONS)
        random.shuffle(directions)
        exits = [ExitState(direction=entered_from, kind="passage", status="open")]
        extra_count = roll_d6() // (2 if tile_type == "room" else 3)
        for direction in directions:
            if direction == entered_from:
                continue
            if len(exits) >= extra_count + 1:
                break
            kind = "door" if roll_d6() >= 4 else "passage"
            exits.append(ExitState(direction=direction, kind=kind))
        return 0, exits

    def _roll_enemy(self, category: str, hcl: int) -> list[EnemyState]:
        monsters = self.rules.monsters()
        table = monsters.get(category) or monsters["vermin"]
        template = random.choice(table)
        count = max(1, roll_formula(str(template.get("count", "1"))))
        level = max(1, hcl + int(template.get("level_delta", 0)))
        enemies: list[EnemyState] = []
        for _ in range(count):
            life = int(template.get("life", 1))
            enemies.append(
                EnemyState(
                    id=uuid4().hex,
                    name=template["name"],
                    category=category,
                    level=level,
                    life=life,
                    max_life=life,
                    attacks=int(template.get("attacks", 1)),
                    tags=list(template.get("tags", [])),
                )
            )
        return enemies

    def _roll_door_result(self) -> str:
        table = self.rules.dungeon_tables().get("door_table", [])
        roll = roll_2d6()
        for entry in table:
            low, high = self._parse_roll_range(entry["roll"])
            if low <= roll <= high:
                return entry["result"]
        return "Unlocked door."

    def _parse_roll_range(self, value: str) -> tuple[int, int]:
        if "-" in value:
            low, high = value.split("-", 1)
            return int(low), int(high)
        number = int(value)
        return number, number

    def _add_emergency_exit(self, session: SessionState, current: TileState) -> ExitState | None:
        occupied = {(tile.x, tile.y) for tile in session.map_state.tiles}
        for direction, (dx, dy) in DIRECTIONS.items():
            if (current.x + dx, current.y + dy) not in occupied:
                exit_state = ExitState(direction=direction, kind="passage")
                current.exits.append(exit_state)
                return exit_state
        return None

    def _set_reciprocal_exit(self, destination: TileState, origin: TileState, origin_exit: ExitState) -> None:
        reciprocal_direction = OPPOSITE[origin_exit.direction]
        reciprocal = next(
            (
                exit_state
                for exit_state in destination.exits
                if exit_state.direction == reciprocal_direction and exit_state.destination_tile_id in (None, origin.id)
            ),
            None,
        ) or next((exit_state for exit_state in destination.exits if exit_state.direction == reciprocal_direction), None)
        if reciprocal is None:
            reciprocal = ExitState(
                direction=reciprocal_direction,
                kind=origin_exit.kind,
                status="open",
            )
            destination.exits.append(reciprocal)
        reciprocal.status = "open"
        reciprocal.destination_tile_id = origin.id
        if origin_exit.kind == "door" and reciprocal.door_result is None:
            reciprocal.door_result = origin_exit.door_result

    def _overlaps_existing(self, session: SessionState, candidate: TileState) -> bool:
        candidate_cells = self._occupied_cells(candidate)
        for tile in session.map_state.tiles:
            if candidate_cells.intersection(self._occupied_cells(tile)):
                return True
        return False

    def _occupied_cells(self, tile: TileState) -> set[tuple[int, int]]:
        width = tile.footprint_width
        height = tile.footprint_height
        if tile.rotation in (90, 270):
            width, height = height, width
        return {
            (tile.x + dx, tile.y + dy)
            for dx in range(width)
            for dy in range(height)
        }

    def _current_tile(self, session: SessionState) -> TileState:
        return next(tile for tile in session.map_state.tiles if tile.id == session.map_state.current_tile_id)

    def _tile_by_id(self, session: SessionState, tile_id: str | None) -> TileState | None:
        if tile_id is None:
            return None
        return next((tile for tile in session.map_state.tiles if tile.id == tile_id), None)

    def _tile_at(self, session: SessionState, x: int, y: int) -> TileState | None:
        return next((tile for tile in session.map_state.tiles if tile.x == x and tile.y == y), None)

    def _highest_character_level(self, party: list[PartyMemberState]) -> int:
        return max((pc.level for pc in party), default=1)

    def _tile_type(self, tile_type: str) -> str:
        if tile_type in {"room", "corridor"}:
            return tile_type
        return "corridor" if roll_d6() <= 2 else "room"

    def _rotate_direction(self, direction: str, rotation: int) -> str:
        turns = (rotation // 90) % 4
        index = DIRECTION_ORDER.index(direction)
        return DIRECTION_ORDER[(index + turns) % 4]

    def _tile_description(self, tile_description: str, content_description: str) -> str:
        if tile_description:
            return f"{tile_description} {content_description}"
        return content_description

    def _tile_image(self, tile_key: str, image: str | None = None) -> str | None:
        filename = image or f"{tile_key}.gif"
        if (self.asset_dir / "tiles" / filename).exists():
            return f"/assets/tiles/{filename}"
        return None

    def _touch(self, session: SessionState) -> SessionState:
        session.updated_at = now_utc()
        return session
