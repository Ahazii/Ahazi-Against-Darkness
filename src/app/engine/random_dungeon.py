from __future__ import annotations

from dataclasses import dataclass
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
from .dice import roll_2d6, roll_d6, roll_exploding_d6, roll_formula, roll_start_tile_key, roll_tile_key
from .dungeon_table_roller import DungeonTableRoller, attempt_open_door


DIRECTIONS: dict[str, tuple[int, int]] = {
    "north": (0, -1),
    "east": (1, 0),
    "south": (0, 1),
    "west": (-1, 0),
}
OPPOSITE = {"north": "south", "east": "west", "south": "north", "west": "east"}
DIRECTION_ORDER = ["north", "east", "south", "west"]
ROTATIONS = [0, 90, 180, 270]


@dataclass
class Placement:
    x: int
    y: int
    rotation: int
    exits: list[ExitState]
    walkable: list[str]
    cell_shapes: list[str]
    visible: list[str]
    truncated: bool = False


class RandomDungeonEngine:
    def __init__(self, rules: RulesRepository, asset_dir: Path) -> None:
        self.rules = rules
        self.asset_dir = asset_dir
        self.table_roller = DungeonTableRoller.from_rules(rules)

    def create_session(self, session_id: str, party_id: str, party: list[PartyMemberState]) -> SessionState:
        tile_key = roll_start_tile_key()
        tile_def = self.rules.tiles().get(tile_key)
        tile_type = self._tile_type(tile_def.tile_type if tile_def else "room")
        width = tile_def.footprint_width if tile_def else 1
        height = tile_def.footprint_height if tile_def else 1
        exits = self._starting_exits(tile_key, tile_def, width, height)
        entrance = TileState(
            id=uuid4().hex,
            x=0,
            y=0,
            tile_key=tile_key,
            tile_type=tile_type,
            rotation=0,
            footprint_width=width,
            footprint_height=height,
            editor_cell_size=tile_def.editor_cell_size if tile_def else 80,
            image_scale=tile_def.image_scale if tile_def else 1.0,
            image_offset_x=tile_def.image_offset_x if tile_def else 0,
            image_offset_y=tile_def.image_offset_y if tile_def else 0,
            walkable=self._normalized_walkable(tile_def, width, height),
            cell_shapes=self._normalized_cell_shapes(tile_def, width, height),
            visible=self._visible_rows(width, height),
            image=self._tile_image(tile_key, tile_def.image if tile_def else None),
            title=tile_def.name if tile_def else f"Entrance Map Element {tile_key}",
            description="The party enters the dungeon.",
            content_key="entrance",
            objects=["Entrance"],
            exits=exits,
        )
        for index, member in enumerate(party, start=1):
            member.marching_order = index
        timestamp = now_utc()
        return SessionState(
            id=session_id,
            party_id=party_id,
            adventure_id="random",
            adventure_type="random",
            mode="exploration",
            party=party,
            map_state=MapState(tiles=[entrance], current_tile_id=entrance.id),
            log=[
                f"Entrance map element roll: d6 = {tile_key[1]} -> {tile_key}.",
                "Adventure begins at the dungeon entrance.",
            ],
            created_at=timestamp,
            updated_at=timestamp,
        )

    def advance(
        self,
        session: SessionState,
        action: str,
        exit_id: str | None = None,
        direction: str | None = None,
        character_id: str | None = None,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> SessionState:
        if session.mode == "complete":
            session.log.append("This adventure is complete.")
            return self._touch(session)

        if action == "explore":
            self._explore(session, exit_id, direction, show_rolls=show_rolls, explain_math=explain_math)
        elif action == "search":
            self._search(session, show_rolls=show_rolls, explain_math=explain_math)
        elif action == "combat_round":
            self._combat_round(session, show_rolls=show_rolls, explain_math=explain_math)
        elif action == "rest":
            self._rest(session)
        elif action == "open_door":
            self._open_door(session, exit_id, character_id, show_rolls=show_rolls, explain_math=explain_math)
        elif action == "resolve_trap":
            self._resolve_trap(session, show_rolls=show_rolls, explain_math=explain_math)
        elif action == "claim_treasure":
            self._claim_treasure(session)
        else:
            session.log.append(f"Unknown action: {action}.")

        return self._touch(session)

    def _explore(
        self,
        session: SessionState,
        exit_id: str | None = None,
        direction: str | None = None,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Exploration is blocked until the current encounter is resolved.")
            return

        current = self._current_tile(session)
        if exit_id:
            exit_state = next((item for item in current.exits if item.id == exit_id), None)
            if exit_state is None:
                session.log.append("That exit is not available from this map element.")
                return
        elif direction:
            exit_state = next((item for item in current.exits if item.direction == direction), None)
            if exit_state is None:
                session.log.append(f"There is no exit to the {direction}.")
                return
        else:
            exit_state = next((item for item in current.exits if item.status == "unexplored"), None)

        if exit_state is None:
            exit_state = self._add_emergency_exit(session, current)
            if exit_state is None:
                session.log.append("There are no open ways forward from this location.")
                return

        if exit_state.status == "blocked":
            session.log.append(f"The {exit_state.direction} exit is blocked.")
            return

        if exit_state.dungeon_exit:
            exit_state.status = "open"
            self._complete_dungeon(session)
            return

        if exit_state.kind == "door" and not exit_state.door_open:
            self._inherit_open_door_from_reciprocal(session, current, exit_state)
        if exit_state.kind == "door" and not exit_state.door_open:
            opener = self._member_by_marching_order(session, 1)
            if opener is None:
                session.log.append("No hero is available to work the door.")
                return
            opened, door_log = attempt_open_door(
                exit_state,
                opener,
                hcl=self._highest_character_level(session.party),
                show_rolls=show_rolls,
                explain_math=explain_math,
                roller=self.table_roller,
                party=session.party,
                marching_order=self._marching_order_ids(session),
            )
            session.log.extend(door_log)
            if opened:
                self._sync_linked_door(session, current, exit_state)
            if not opened:
                return

        _, destination = self._exit_edge(current, exit_state)
        if destination in self._occupied_cells(current):
            session.log.append(
                "That exit points back into the same map element. Move the exit marker to an outside edge, "
                "or mark it as the dungeon exit if it leaves the dungeon."
            )
            return
        existing = (
            self._tile_by_id(session, exit_state.destination_tile_id)
            if exit_state.destination_tile_id
            else self._tile_occupying(session, *destination, exclude_tile_id=current.id)
        )
        if existing and existing.id == current.id:
            session.log.append(
                "That exit resolves to the current map element. Check the map element metadata before exploring it."
            )
            return
        exit_state.status = "open"
        if existing:
            exit_state.destination_tile_id = existing.id
            self._set_reciprocal_exit(existing, current, exit_state)
            session.map_state.current_tile_id = existing.id
            session.log.append(f"The party moves {exit_state.direction} to {existing.title}.")
            return

        new_tile = self._generate_tile(
            session=session,
            origin=current,
            origin_exit=exit_state,
            hcl=self._highest_character_level(session.party),
            show_rolls=show_rolls,
            explain_math=explain_math,
        )
        if new_tile is None:
            exit_state.status = "unexplored"
            exit_state.destination_tile_id = None
            session.log.append(
                "No legal placement is available for that map element without overlap. "
                "Even after truncation there is no usable entry square."
            )
            return
        exit_state.destination_tile_id = new_tile.id
        session.map_state.tiles.append(new_tile)
        self._clip_origin_visible_for_neighbor(current, new_tile)
        self._set_reciprocal_exit(new_tile, current, exit_state)
        session.map_state.current_tile_id = new_tile.id
        session.log.append(f"Entered {new_tile.title}: {new_tile.description}")
        self._prepare_tile_features(session, new_tile, show_rolls=show_rolls, explain_math=explain_math)
        if new_tile.enemies:
            session.mode = "combat"
            session.log.append("An encounter starts.")

    def _search(self, session: SessionState, *, show_rolls: bool = True, explain_math: bool = False) -> None:
        if session.mode != "exploration":
            session.log.append("Search after the encounter is resolved.")
            return
        tile = self._current_tile(session)
        if tile.searched:
            session.log.append("This location has already been searched.")
            return

        tile.searched = True
        roll = roll_d6()
        effective_roll = roll - 1 if tile.tile_type == "corridor" else roll
        if show_rolls:
            if tile.tile_type == "corridor":
                session.log.append(f"Search roll: d6 = {roll} (corridor -1 = {effective_roll}).")
            else:
                session.log.append(f"Search roll: d6 = {roll}.")
        if explain_math:
            session.log.append(f"Search table: {self.table_roller.search_table_summary()}.")
        outcome = self.table_roller.lookup_search(effective_roll)
        if outcome.effect == "wandering_monsters":
            foe = self._roll_enemy("wandering", self._highest_character_level(session.party))
            tile.enemies.extend(foe)
            session.mode = "combat"
            session.log.append("Wandering Monsters attack!")
        elif outcome.effect == "nothing":
            session.log.append("The search finds nothing useful.")
        elif outcome.effect == "found_something":
            session.log.append(
                "Search find: choose hidden treasure, secret door, secret passage, or 1 Clue "
                "(starter default: hidden treasure)."
            )
            self._grant_hidden_treasure(session, tile, show_rolls=show_rolls, explain_math=explain_math)
        elif outcome.effect == "clue":
            tile.objects.append("Clue")
            session.log.append("The party finds a clue.")
        else:
            self._grant_hidden_treasure(session, tile, show_rolls=show_rolls, explain_math=explain_math)

    def _grant_hidden_treasure(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        hcl = self._highest_character_level(session.party)
        treasure = self.table_roller.roll_hidden_treasure(hcl)
        tile.treasure_summary = treasure.summary
        tile.treasure_gold = treasure.gold
        tile.treasure_items = treasure.items
        session.log.extend(treasure.log)
        if treasure.complication_effect == "alarm":
            foe = self._roll_enemy("wandering", hcl)
            tile.enemies.extend(foe)
            session.mode = "combat"
            session.log.append("Wandering Monsters attack!")
        elif treasure.complication_effect:
            session.log.extend(
                self.table_roller.apply_hidden_complication(
                    treasure.complication_effect,
                    hcl=hcl,
                    party=session.party,
                    marching_order=self._marching_order_ids(session),
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                )
            )
        session.log.append("Hidden treasure is ready to claim once complications are handled.")

    def _combat_round(self, session: SessionState, *, show_rolls: bool = True, explain_math: bool = False) -> None:
        if session.mode != "combat":
            session.log.append("There are no active enemies here.")
            return
        tile = self._current_tile(session)
        standing_before = {pc.character_id for pc in session.party if pc.current_life > 0}
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        initial_minor_count = tile.initial_enemy_count or len(tile.enemies)
        result = resolve_combat_round(
            session.party,
            tile.enemies,
            show_rolls=show_rolls,
            explain_math=explain_math,
            initial_minor_count=initial_minor_count,
        )
        session.party = result.party
        tile.enemies = result.enemies
        session.log.extend(result.log)
        known_defeated_ids = {enemy.id for enemy in tile.defeated_enemies}
        for enemy in result.enemies:
            if enemy.id in active_enemy_ids and enemy.life <= 0 and enemy.id not in known_defeated_ids:
                tile.defeated_enemies.append(enemy.model_copy(deep=True))
                known_defeated_ids.add(enemy.id)
        fallen_now = [
            pc.character_id
            for pc in session.party
            if pc.character_id in standing_before and pc.current_life <= 0
        ]
        for character_id in fallen_now:
            if character_id not in tile.fallen_character_ids:
                tile.fallen_character_ids.append(character_id)
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
        if result.morale_failed:
            self._award_treasure(session, tile, show_rolls=show_rolls)
        elif not tile.enemies:
            self._award_treasure(session, tile, show_rolls=show_rolls)

    def _rest(self, session: SessionState) -> None:
        if session.mode != "exploration":
            session.log.append("The party cannot rest during combat.")
            return
        for pc in session.party:
            if pc.current_life > 0 and pc.current_life < pc.max_life:
                pc.current_life += 1
        session.log.append("The party catches its breath and recovers 1 life where possible.")

    def _generate_tile(
        self,
        session: SessionState,
        origin: TileState,
        origin_exit: ExitState,
        hcl: int,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> TileState | None:
        tile_key = self._roll_generated_tile_key()
        tile_def = self.rules.tiles().get(tile_key)
        tile_type = self._tile_type(tile_def.tile_type if tile_def else "unknown")
        content = self._roll_content(tile_type, hcl)
        placement = self._select_placement(session, origin, origin_exit, tile_type, tile_def)
        if placement is None:
            return None
        if show_rolls:
            session.log.append(f"Map element roll: d66 = {tile_key}.")
        if explain_math:
            session.log.append(f"Map element lookup for {tile_key}: {tile_def.name if tile_def else 'metadata missing'}.")
        if show_rolls:
            session.log.append(f"Room content roll: 2d6 = {content['roll']}.")
        if explain_math:
            session.log.append(f"{tile_type.title()} content lookup for {content['roll']}: {content['description']}")
        if placement.truncated:
            session.log.append("The map element was truncated to avoid overlapping explored space or open exits.")
        tile = TileState(
            id=uuid4().hex,
            x=placement.x,
            y=placement.y,
            tile_key=tile_key,
            tile_type=tile_type,
            rotation=placement.rotation,
            footprint_width=tile_def.footprint_width if tile_def else 1,
            footprint_height=tile_def.footprint_height if tile_def else 1,
            editor_cell_size=tile_def.editor_cell_size if tile_def else 80,
            image_scale=tile_def.image_scale if tile_def else 1.0,
            image_offset_x=tile_def.image_offset_x if tile_def else 0,
            image_offset_y=tile_def.image_offset_y if tile_def else 0,
            walkable=placement.walkable,
            cell_shapes=placement.cell_shapes,
            visible=placement.visible,
            image=self._tile_image(tile_key, tile_def.image if tile_def else None),
            title=tile_def.name if tile_def else f"{tile_type.title()} {tile_key}",
            description=self._tile_description(tile_def.description if tile_def else "", content["description"]),
            content_key=content["key"],
            objects=content["objects"],
            enemies=content["enemies"],
            exits=placement.exits,
            initial_enemy_count=len(content["enemies"]),
        )
        self._seed_tile_features(tile, hcl, show_rolls=show_rolls)
        return tile

    def _roll_content(self, tile_type: str, hcl: int) -> dict:
        roll = roll_2d6()
        outcome = self.table_roller.lookup_room_content(roll, tile_type)
        if outcome is None:
            return self._content("empty", "The area is quiet.", [], [], roll=roll)
        enemies: list[EnemyState] = []
        if outcome.enemy_category:
            enemies = self._roll_enemy(outcome.enemy_category, hcl)
        return self._content(outcome.key, outcome.description, list(outcome.objects), enemies, roll=roll)

    def _content(
        self,
        key: str,
        description: str,
        objects: list[str],
        enemies: list[EnemyState],
        roll: int | None = None,
    ) -> dict:
        content = {"key": key, "description": description, "objects": objects, "enemies": enemies}
        if roll is not None:
            content["roll"] = roll
        return content

    def _select_placement(
        self,
        session: SessionState,
        origin: TileState,
        origin_exit: ExitState,
        tile_type: str,
        tile_def: TileDefinition | None,
    ) -> Placement | None:
        entered_from = OPPOSITE[origin_exit.direction]
        footprint_width = tile_def.footprint_width if tile_def else 1
        footprint_height = tile_def.footprint_height if tile_def else 1
        truncation_candidate: Placement | None = None

        if tile_def and tile_def.exits:
            rotations = ROTATIONS[:]
            random.shuffle(rotations)
            for rotation in rotations:
                exits = self._rotated_exits(tile_def, rotation)
                matching_exits = [exit_state for exit_state in exits if exit_state.direction == entered_from]
                random.shuffle(matching_exits)
                width, height = self._rotated_size(footprint_width, footprint_height, rotation)
                for matching in matching_exits:
                    matching.status = "open"
                    x, y = self._aligned_origin(origin, origin_exit, matching, width, height)
                    if not self._placement_blocked(session, x, y, width, height, tile_def, rotation, origin, origin_exit):
                        return Placement(
                            x=x,
                            y=y,
                            rotation=rotation,
                            exits=exits,
                            walkable=self._rotated_walkable(tile_def, rotation),
                            cell_shapes=self._rotated_cell_shapes(tile_def, rotation),
                            visible=self._visible_rows(width, height),
                        )
                    if truncation_candidate is None:
                        truncation_candidate = self._truncated_placement(
                            session,
                            x,
                            y,
                            width,
                            height,
                            tile_def,
                            rotation,
                            origin,
                            origin_exit,
                            exits,
                            matching,
                        )
                    matching.status = "unexplored"
            return truncation_candidate

        rotation = 0
        width, height = self._rotated_size(footprint_width, footprint_height, rotation)
        exits = self._fallback_exits(tile_type, entered_from, width, height)
        matching = next(exit_state for exit_state in exits if exit_state.direction == entered_from)
        x, y = self._aligned_origin(origin, origin_exit, matching, width, height)
        if self._placement_blocked(session, x, y, width, height, tile_def, rotation, origin, origin_exit):
            return self._truncated_placement(
                session,
                x,
                y,
                width,
                height,
                tile_def,
                rotation,
                origin,
                origin_exit,
                exits,
                matching,
            )
        return Placement(
            x=x,
            y=y,
            rotation=rotation,
            exits=exits,
            walkable=self._rotated_walkable(tile_def, rotation),
            cell_shapes=self._rotated_cell_shapes(tile_def, rotation),
            visible=self._visible_rows(width, height),
        )

    def _roll_generated_tile_key(self) -> str:
        tiles = self.rules.tiles()
        for _ in range(20):
            tile_key = roll_tile_key()
            if tile_key in tiles and tile_key[0] in "123456" and tile_key[1] in "123456":
                return tile_key
        valid_generated = [key for key in tiles if key[0] in "123456" and key[1] in "123456"]
        return random.choice(valid_generated)

    def _complete_dungeon(self, session: SessionState) -> None:
        session.mode = "complete"
        explored = len(session.map_state.tiles)
        survivors = sum(1 for member in session.party if member.current_life > 0)
        for member in session.party:
            if member.current_life > 0:
                member.current_life = member.max_life
        session.summary = [
            f"Explored {explored} map element{'s' if explored != 1 else ''}.",
            f"{survivors} of {len(session.party)} party members left the dungeon.",
            "Between adventures, surviving heroes fully heal and keep treasure already recorded on their sheets.",
        ]
        session.log.append("The party leaves the dungeon. Surviving heroes fully heal between adventures.")

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

    def _rotated_exits(self, tile_def: TileDefinition, rotation: int) -> list[ExitState]:
        width, height = self._rotated_size(tile_def.footprint_width, tile_def.footprint_height, rotation)
        exits: list[ExitState] = []
        for exit_def in tile_def.exits:
            direction = self._rotate_direction(exit_def.direction, rotation)
            cells = [
                self._rotate_cell(x, y, tile_def.footprint_width, tile_def.footprint_height, rotation)
                for x, y in self._exit_cells(
                    exit_def.x,
                    exit_def.y,
                    exit_def.direction,
                    exit_def.span,
                    tile_def.footprint_width,
                    tile_def.footprint_height,
                )
            ]
            xs = [x for x, _ in cells]
            ys = [y for _, y in cells]
            if direction in {"north", "south"}:
                x, y = min(xs), ys[0]
                span = max(xs) - min(xs) + 1
            else:
                x, y = xs[0], min(ys)
                span = max(ys) - min(ys) + 1
            offset = self._exit_offset(direction, x, y)
            exits.append(
                ExitState(
                    id=exit_def.id,
                    label=exit_def.label,
                    direction=direction,
                    kind=exit_def.kind,
                    x=x,
                    y=y,
                    span=span,
                    offset=offset,
                    position=self._position_from_offset(offset, direction, width, height),
                    dungeon_exit=exit_def.dungeon_exit,
                    status="unexplored",
                )
            )
        return exits

    def _starting_exits(
        self,
        tile_key: str,
        tile_def: TileDefinition | None,
        width: int,
        height: int,
    ) -> list[ExitState]:
        if tile_def and tile_def.exits:
            return self._rotated_exits(tile_def, 0)

        return [
            self._new_exit(direction="north", kind="passage", width=width, height=height),
            self._new_exit(direction="east", kind="door", width=width, height=height),
            self._new_exit(direction="west", kind="door", width=width, height=height),
            self._new_exit(
                direction="south",
                kind="passage",
                width=width,
                height=height,
                dungeon_exit=True,
                exit_id=f"{tile_key}-dungeon-exit",
            ),
        ]

    def _fallback_exits(self, tile_type: str, entered_from: str, width: int, height: int) -> list[ExitState]:
        directions = list(DIRECTIONS)
        random.shuffle(directions)
        exits = [
            self._new_exit(
                direction=entered_from,
                kind="passage",
                width=width,
                height=height,
                status="open",
            )
        ]
        extra_count = roll_d6() // (2 if tile_type == "room" else 3)
        for direction in directions:
            if direction == entered_from:
                continue
            if len(exits) >= extra_count + 1:
                break
            kind = "door" if roll_d6() >= 4 else "passage"
            exits.append(self._new_exit(direction=direction, kind=kind, width=width, height=height))
        return exits

    def _new_exit(
        self,
        direction: str,
        kind: str,
        width: int,
        height: int,
        status: str = "unexplored",
        dungeon_exit: bool = False,
        exit_id: str | None = None,
        label: str = "",
        span: int = 1,
    ) -> ExitState:
        x, y = self._default_entry_cell(direction, width, height)
        offset = self._exit_offset(direction, x, y)
        return ExitState(
            id=exit_id or uuid4().hex,
            label=label,
            direction=direction,
            kind=kind,
            x=x,
            y=y,
            span=max(1, min(span, self._max_exit_span(direction, x, y, width, height))),
            offset=offset,
            position=self._position_from_offset(offset, direction, width, height),
            dungeon_exit=dungeon_exit,
            status=status,
        )

    def _default_entry_cell(self, direction: str, width: int, height: int) -> tuple[int, int]:
        offset = max(0, self._side_length(direction, width, height) // 2)
        if direction in {"north", "south"}:
            return min(offset, width - 1), 0 if direction == "north" else height - 1
        return 0 if direction == "west" else width - 1, min(offset, height - 1)

    def _rotate_cell(self, x: int, y: int, width: int, height: int, rotation: int) -> tuple[int, int]:
        turns = (rotation // 90) % 4
        if turns == 1:
            return height - 1 - y, x
        if turns == 2:
            return width - 1 - x, height - 1 - y
        if turns == 3:
            return y, width - 1 - x
        return x, y

    def _aligned_origin(
        self,
        origin: TileState,
        origin_exit: ExitState,
        entry_exit: ExitState,
        width: int,
        height: int,
    ) -> tuple[int, int]:
        _, outside = self._exit_edge(origin, origin_exit)
        x = max(0, min(entry_exit.x, width - 1))
        y = max(0, min(entry_exit.y, height - 1))
        return outside[0] - x, outside[1] - y

    def _exit_edge(self, tile: TileState, exit_state: ExitState) -> tuple[tuple[int, int], tuple[int, int]]:
        width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        local_x = max(0, min(exit_state.x, width - 1))
        local_y = max(0, min(exit_state.y, height - 1))
        inside = (tile.x + local_x, tile.y + local_y)
        dx, dy = DIRECTIONS[exit_state.direction]
        return inside, (inside[0] + dx, inside[1] + dy)

    def _position_from_offset(self, offset: int, direction: str, width: int, height: int) -> float:
        side_length = self._side_length(direction, width, height)
        if side_length <= 1:
            return 0.5
        return max(0.0, min(1.0, offset / (side_length - 1)))

    def _side_length(self, direction: str, width: int, height: int) -> int:
        return width if direction in {"north", "south"} else height

    def _exit_offset(self, direction: str, x: int, y: int) -> int:
        return x if direction in {"north", "south"} else y

    def _exit_cells(
        self,
        x: int,
        y: int,
        direction: str,
        span: int,
        width: int,
        height: int,
    ) -> list[tuple[int, int]]:
        max_span = self._max_exit_span(direction, x, y, width, height)
        clamped_span = max(1, min(span, max_span))
        if direction in {"north", "south"}:
            return [(x + index, y) for index in range(clamped_span)]
        return [(x, y + index) for index in range(clamped_span)]

    def _max_exit_span(self, direction: str, x: int, y: int, width: int, height: int) -> int:
        if direction in {"north", "south"}:
            return max(1, width - max(0, min(x, width - 1)))
        return max(1, height - max(0, min(y, height - 1)))

    def _add_emergency_exit(self, session: SessionState, current: TileState) -> ExitState | None:
        occupied = set().union(*(self._occupied_cells(tile) for tile in session.map_state.tiles))
        width, height = self._rotated_size(current.footprint_width, current.footprint_height, current.rotation)
        for direction in DIRECTIONS:
            probe = self._new_exit(direction=direction, kind="passage", width=width, height=height)
            _, outside = self._exit_edge(current, probe)
            if outside not in occupied:
                current.exits.append(probe)
                return probe
        return None

    def _set_reciprocal_exit(self, destination: TileState, origin: TileState, origin_exit: ExitState) -> None:
        reciprocal_direction = OPPOSITE[origin_exit.direction]
        origin_inside, _ = self._exit_edge(origin, origin_exit)
        reciprocal = next(
            (
                exit_state
                for exit_state in destination.exits
                if exit_state.direction == reciprocal_direction and exit_state.destination_tile_id in (None, origin.id)
                and self._exit_edge(destination, exit_state)[1] == origin_inside
            ),
            None,
        ) or next((exit_state for exit_state in destination.exits if exit_state.direction == reciprocal_direction), None)
        if reciprocal is None:
            width, height = self._rotated_size(destination.footprint_width, destination.footprint_height, destination.rotation)
            reciprocal = self._new_exit(
                direction=reciprocal_direction,
                kind=origin_exit.kind,
                width=width,
                height=height,
                status="open",
                span=origin_exit.span,
            )
            destination.exits.append(reciprocal)
        reciprocal.status = "open"
        reciprocal.destination_tile_id = origin.id
        self._copy_door_state(origin_exit, reciprocal)

    def _copy_door_state(self, source: ExitState, target: ExitState) -> None:
        if source.kind != "door":
            return
        target.door_type = source.door_type
        target.door_level = source.door_level
        target.door_result = source.door_result
        target.door_open = source.door_open
        target.door_treasure_bonus = source.door_treasure_bonus

    def _reciprocal_exit_on_tile(self, tile: TileState, other_tile_id: str) -> ExitState | None:
        return next((exit_state for exit_state in tile.exits if exit_state.destination_tile_id == other_tile_id), None)

    def _inherit_open_door_from_reciprocal(
        self,
        session: SessionState,
        current: TileState,
        exit_state: ExitState,
    ) -> None:
        if exit_state.kind != "door" or exit_state.door_open or not exit_state.destination_tile_id:
            return
        other_tile = self._tile_by_id(session, exit_state.destination_tile_id)
        if other_tile is None:
            return
        reciprocal = self._reciprocal_exit_on_tile(other_tile, current.id)
        if reciprocal and reciprocal.door_open:
            self._copy_door_state(reciprocal, exit_state)

    def _sync_linked_door(self, session: SessionState, current: TileState, exit_state: ExitState) -> None:
        if exit_state.kind != "door" or not exit_state.destination_tile_id:
            return
        other_tile = self._tile_by_id(session, exit_state.destination_tile_id)
        if other_tile is None:
            return
        reciprocal = self._reciprocal_exit_on_tile(other_tile, current.id)
        if reciprocal:
            self._copy_door_state(exit_state, reciprocal)

    def _overlaps_existing(self, session: SessionState, candidate: TileState) -> bool:
        candidate_cells = self._occupied_cells(candidate)
        for tile in session.map_state.tiles:
            if candidate_cells.intersection(self._occupied_cells(tile)):
                return True
        return False

    def _occupied_cells(self, tile: TileState) -> set[tuple[int, int]]:
        width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        if len(tile.walkable) == height and all(len(row) == width for row in tile.walkable):
            return {
                (tile.x + local_x, tile.y + local_y)
                for local_y, row in enumerate(tile.walkable)
                for local_x, value in enumerate(row)
                if value != "0"
            }
        return self._footprint_cells(tile.x, tile.y, width, height)

    def _visible_cells(self, tile: TileState) -> set[tuple[int, int]]:
        width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        if len(tile.visible) == height and all(len(row) == width for row in tile.visible):
            return {
                (tile.x + local_x, tile.y + local_y)
                for local_y, row in enumerate(tile.visible)
                for local_x, value in enumerate(row)
                if value != "0"
            }
        return self._footprint_cells(tile.x, tile.y, width, height)

    def _normalized_walkable(self, tile_def: TileDefinition | None, width: int, height: int) -> list[str]:
        if tile_def and len(tile_def.walkable) == height and all(len(row) == width for row in tile_def.walkable):
            return ["".join("1" if char in {"1", "w", "W", "."} else "0" for char in row) for row in tile_def.walkable]
        return ["1" * width for _ in range(height)]

    def _normalized_cell_shapes(self, tile_def: TileDefinition | None, width: int, height: int) -> list[str]:
        allowed = {
            "F",
            "A",
            "B",
            "C",
            "D",
            "E",
            "G",
            "H",
            "I",
            "J",
            "K",
            "L",
            "M",
            "N",
            "O",
            "P",
            "Q",
            "R",
            "S",
            "T",
            "U",
        }
        if tile_def and len(tile_def.cell_shapes) == height and all(len(row) == width for row in tile_def.cell_shapes):
            return ["".join(char if char in allowed else "F" for char in row) for row in tile_def.cell_shapes]
        return ["F" * width for _ in range(height)]

    def _visible_rows(self, width: int, height: int) -> list[str]:
        return ["1" * width for _ in range(height)]

    def _rotated_walkable(self, tile_def: TileDefinition | None, rotation: int) -> list[str]:
        width = tile_def.footprint_width if tile_def else 1
        height = tile_def.footprint_height if tile_def else 1
        source = self._normalized_walkable(tile_def, width, height)
        return self._rotate_rows(source, width, height, rotation)

    def _rotated_cell_shapes(self, tile_def: TileDefinition | None, rotation: int) -> list[str]:
        width = tile_def.footprint_width if tile_def else 1
        height = tile_def.footprint_height if tile_def else 1
        source = self._normalized_cell_shapes(tile_def, width, height)
        return self._rotate_rows(source, width, height, rotation, self._rotate_cell_shape)

    def _rotate_rows(
        self,
        source: list[str],
        width: int,
        height: int,
        rotation: int,
        transform_value=None,
    ) -> list[str]:
        rotated_width, rotated_height = self._rotated_size(width, height, rotation)
        rows = [["0" for _ in range(rotated_width)] for _ in range(rotated_height)]
        transform_value = transform_value or (lambda value, _rotation: value)
        for y, row in enumerate(source):
            for x, value in enumerate(row):
                rotated_x, rotated_y = self._rotate_cell(x, y, width, height, rotation)
                rows[rotated_y][rotated_x] = transform_value(value, rotation)
        return ["".join(row) for row in rows]

    def _rotate_cell_shape(self, value: str, rotation: int) -> str:
        turns = (rotation // 90) % 4
        maps = [
            {},
            {
                "A": "C",
                "C": "D",
                "D": "B",
                "B": "A",
                "E": "H",
                "H": "I",
                "I": "G",
                "G": "E",
                "J": "L",
                "L": "M",
                "M": "K",
                "K": "J",
                "N": "T",
                "O": "U",
                "P": "R",
                "Q": "S",
                "R": "N",
                "S": "O",
                "T": "P",
                "U": "Q",
            },
            {
                "A": "D",
                "D": "A",
                "B": "C",
                "C": "B",
                "E": "I",
                "I": "E",
                "G": "H",
                "H": "G",
                "J": "M",
                "M": "J",
                "K": "L",
                "L": "K",
                "N": "Q",
                "O": "P",
                "P": "O",
                "Q": "N",
                "R": "U",
                "S": "T",
                "T": "S",
                "U": "R",
            },
            {
                "A": "B",
                "B": "D",
                "D": "C",
                "C": "A",
                "E": "G",
                "G": "I",
                "I": "H",
                "H": "E",
                "J": "K",
                "K": "M",
                "M": "L",
                "L": "J",
                "N": "R",
                "O": "S",
                "P": "T",
                "Q": "U",
                "R": "P",
                "S": "Q",
                "T": "N",
                "U": "O",
            },
        ]
        return maps[turns].get(value, value)

    def _placement_blocked(
        self,
        session: SessionState,
        x: int,
        y: int,
        width: int,
        height: int,
        tile_def: TileDefinition | None,
        rotation: int,
        origin: TileState,
        origin_exit: ExitState,
    ) -> bool:
        candidate_cells = self._candidate_footprint_cells(x, y, width, height)
        if any(candidate_cells.intersection(self._visible_cells(tile)) for tile in session.map_state.tiles):
            return True
        reserved_exit_cells = self._reserved_exit_cells(session, origin, origin_exit)
        return bool(candidate_cells.intersection(reserved_exit_cells))

    def _truncated_placement(
        self,
        session: SessionState,
        x: int,
        y: int,
        width: int,
        height: int,
        tile_def: TileDefinition | None,
        rotation: int,
        origin: TileState,
        origin_exit: ExitState,
        exits: list[ExitState],
        matching: ExitState,
    ) -> Placement | None:
        candidate_exits = [exit_state.model_copy(deep=True) for exit_state in exits]
        candidate_matching = next((exit_state for exit_state in candidate_exits if exit_state.id == matching.id), None)
        if candidate_matching is None:
            return None
        base_walkable = self._rotated_walkable(tile_def, rotation)
        base_shapes = self._rotated_cell_shapes(tile_def, rotation)
        occupied_blockers = set().union(*(self._occupied_cells(tile) for tile in session.map_state.tiles))
        visible_blockers = set().union(*(self._visible_cells(tile) for tile in session.map_state.tiles))
        origin_visible_cells = self._visible_cells(origin)
        reserved_exit_cells = self._reserved_exit_cells(session, origin, origin_exit)
        hard_blockers = occupied_blockers | reserved_exit_cells
        visible_blockers = visible_blockers | reserved_exit_cells
        matching_cells = {
            (x + local_x, y + local_y)
            for local_x, local_y in self._exit_cells(
                candidate_matching.x,
                candidate_matching.y,
                candidate_matching.direction,
                candidate_matching.span,
                width,
                height,
            )
        }
        matching_local_cells = {
            (local_x, local_y)
            for local_x, local_y in self._exit_cells(
                candidate_matching.x,
                candidate_matching.y,
                candidate_matching.direction,
                candidate_matching.span,
                width,
                height,
            )
        }
        origin_overlap_allowance = self._footprint_cells(x, y, width, height).intersection(origin_visible_cells)
        entry_allowance = matching_cells.intersection(origin_visible_cells) | origin_overlap_allowance
        other_visible_blockers = visible_blockers - origin_visible_cells

        if matching_cells.intersection(hard_blockers | other_visible_blockers):
            return None

        blockers = visible_blockers - entry_allowance
        local_blockers = {
            (global_x - x, global_y - y)
            for global_x, global_y in blockers
            if x <= global_x < x + width and y <= global_y < y + height
        }
        removed_cells = self._directional_truncation_cells(
            local_blockers,
            width,
            height,
            OPPOSITE[origin_exit.direction],
        )
        if matching_local_cells.intersection(removed_cells):
            return None

        truncated = False
        walkable_rows: list[str] = []
        shape_rows: list[str] = []
        visible_rows: list[str] = []
        for local_y in range(height):
            walkable_row = []
            shape_row = []
            visible_row = []
            for local_x in range(width):
                if (local_x, local_y) in removed_cells:
                    walkable_row.append("0")
                    shape_row.append("F")
                    visible_row.append("0")
                    truncated = True
                else:
                    walkable_row.append(base_walkable[local_y][local_x])
                    shape_row.append(base_shapes[local_y][local_x])
                    visible_row.append("1")
            walkable_rows.append("".join(walkable_row))
            shape_rows.append("".join(shape_row))
            visible_rows.append("".join(visible_row))

        if not any(char != "0" for row in walkable_rows for char in row):
            return None
        if any(walkable_rows[local_y][local_x] == "0" for local_x, local_y in matching_local_cells):
            return None

        for exit_state in candidate_exits:
            exit_cells = self._exit_cells(exit_state.x, exit_state.y, exit_state.direction, exit_state.span, width, height)
            if exit_state.id == candidate_matching.id:
                exit_state.status = "open"
                continue
            if any((local_x, local_y) in removed_cells for local_x, local_y in exit_cells):
                exit_state.status = "blocked"
                truncated = True
                continue
            if any(walkable_rows[local_y][local_x] == "0" for local_x, local_y in exit_cells):
                exit_state.status = "blocked"
                truncated = True
                continue
            outside_cells = self._candidate_exit_outside_cells(x, y, exit_state, width, height)
            if outside_cells.intersection(blockers):
                exit_state.status = "blocked"
                truncated = True

        return Placement(
            x=x,
            y=y,
            rotation=rotation,
            exits=candidate_exits,
            walkable=walkable_rows,
            cell_shapes=shape_rows,
            visible=visible_rows,
            truncated=truncated,
        )

    def _candidate_footprint_cells(self, x: int, y: int, width: int, height: int) -> set[tuple[int, int]]:
        return self._footprint_cells(x, y, width, height)

    def _clip_origin_visible_for_neighbor(self, origin: TileState, neighbor: TileState) -> None:
        neighbor_visible = self._visible_cells(neighbor)
        if not neighbor_visible:
            return
        width, height = self._rotated_size(origin.footprint_width, origin.footprint_height, origin.rotation)
        if len(origin.visible) != height or not all(len(row) == width for row in origin.visible):
            origin.visible = self._visible_rows(width, height)
        updated: list[str] = []
        changed = False
        for local_y in range(height):
            row_chars: list[str] = []
            for local_x in range(width):
                global_pos = (origin.x + local_x, origin.y + local_y)
                if global_pos in neighbor_visible and origin.visible[local_y][local_x] != "0":
                    row_chars.append("0")
                    changed = True
                else:
                    row_chars.append(origin.visible[local_y][local_x])
            updated.append("".join(row_chars))
        if changed:
            origin.visible = updated

    def _directional_truncation_cells(
        self,
        blockers: set[tuple[int, int]],
        width: int,
        height: int,
        direction: str,
    ) -> set[tuple[int, int]]:
        removed: set[tuple[int, int]] = set()
        if direction == "north":
            for local_x in range(width):
                blocker_ys = [local_y for blocker_x, local_y in blockers if blocker_x == local_x]
                if blocker_ys:
                    removed.update((local_x, local_y) for local_y in range(max(blocker_ys) + 1))
        elif direction == "south":
            for local_x in range(width):
                blocker_ys = [local_y for blocker_x, local_y in blockers if blocker_x == local_x]
                if blocker_ys:
                    removed.update((local_x, local_y) for local_y in range(min(blocker_ys), height))
        elif direction == "west":
            for local_y in range(height):
                blocker_xs = [local_x for local_x, blocker_y in blockers if blocker_y == local_y]
                if blocker_xs:
                    removed.update((local_x, local_y) for local_x in range(max(blocker_xs) + 1))
        else:
            for local_y in range(height):
                blocker_xs = [local_x for local_x, blocker_y in blockers if blocker_y == local_y]
                if blocker_xs:
                    removed.update((local_x, local_y) for local_x in range(min(blocker_xs), width))
        return removed

    def _candidate_occupied_cells(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        tile_def: TileDefinition | None,
        rotation: int,
    ) -> set[tuple[int, int]]:
        if tile_def is None:
            return self._footprint_cells(x, y, width, height)
        rows = self._rotated_walkable(tile_def, rotation)
        cells = {
            (x + local_x, y + local_y)
            for local_y, row in enumerate(rows)
            for local_x, value in enumerate(row)
            if value != "0"
        }
        return cells or self._footprint_cells(x, y, width, height)

    def _reserved_exit_cells(
        self,
        session: SessionState,
        origin: TileState,
        origin_exit: ExitState,
    ) -> set[tuple[int, int]]:
        cells: set[tuple[int, int]] = set()
        for tile in session.map_state.tiles:
            for exit_state in tile.exits:
                if tile.id == origin.id and exit_state.id == origin_exit.id:
                    continue
                if exit_state.dungeon_exit or exit_state.status == "blocked" or exit_state.destination_tile_id:
                    continue
                cells.update(self._exit_outside_cells(tile, exit_state))
        return cells

    def _exit_outside_cells(self, tile: TileState, exit_state: ExitState) -> set[tuple[int, int]]:
        width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        dx, dy = DIRECTIONS[exit_state.direction]
        return {
            (tile.x + local_x + dx, tile.y + local_y + dy)
            for local_x, local_y in self._exit_cells(
                exit_state.x,
                exit_state.y,
                exit_state.direction,
                exit_state.span,
                width,
                height,
            )
        }

    def _candidate_exit_outside_cells(
        self,
        x: int,
        y: int,
        exit_state: ExitState,
        width: int,
        height: int,
    ) -> set[tuple[int, int]]:
        dx, dy = DIRECTIONS[exit_state.direction]
        return {
            (x + local_x + dx, y + local_y + dy)
            for local_x, local_y in self._exit_cells(
                exit_state.x,
                exit_state.y,
                exit_state.direction,
                exit_state.span,
                width,
                height,
            )
        }

    def _footprint_cells(self, x: int, y: int, width: int, height: int) -> set[tuple[int, int]]:
        return {(x + dx, y + dy) for dx in range(width) for dy in range(height)}

    def _rotated_size(self, width: int, height: int, rotation: int) -> tuple[int, int]:
        return (height, width) if rotation in (90, 270) else (width, height)

    def _current_tile(self, session: SessionState) -> TileState:
        return next(tile for tile in session.map_state.tiles if tile.id == session.map_state.current_tile_id)

    def _tile_by_id(self, session: SessionState, tile_id: str | None) -> TileState | None:
        if tile_id is None:
            return None
        return next((tile for tile in session.map_state.tiles if tile.id == tile_id), None)

    def _tile_occupying(
        self,
        session: SessionState,
        x: int,
        y: int,
        exclude_tile_id: str | None = None,
    ) -> TileState | None:
        return next(
            (
                tile
                for tile in session.map_state.tiles
                if tile.id != exclude_tile_id and (x, y) in self._occupied_cells(tile)
            ),
            None,
        )

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

    def _member_by_marching_order(self, session: SessionState, position: int) -> PartyMemberState | None:
        living = [member for member in session.party if member.current_life > 0]
        if not living:
            return None
        return next((member for member in living if member.marching_order == position), living[0])

    def _marching_order_ids(self, session: SessionState) -> list[str]:
        return [
            member.character_id
            for member in sorted(session.party, key=lambda item: item.marching_order)
            if member.current_life > 0
        ]

    def _seed_tile_features(self, tile: TileState, hcl: int, *, show_rolls: bool) -> None:
        if tile.content_key in {"treasure", "trap_treasure"} or any("treasure" in item.lower() for item in tile.objects):
            outcome = self.table_roller.roll_treasure()
            tile.treasure_summary = outcome.summary
            tile.treasure_gold = outcome.gold
            tile.treasure_items = outcome.items
        if tile.content_key == "trap_treasure" or any("trap" in item.lower() for item in tile.objects):
            trap = self.table_roller.roll_trap(hcl, show_rolls=show_rolls, explain_math=False)
            tile.trap_key = trap.trap_key
            tile.trap_level = trap.trap_level
            tile.objects = [item for item in tile.objects if item.lower() != "trap"] + [trap.summary]

    def _prepare_tile_features(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        if tile.trap_key and not tile.trap_resolved and not tile.enemies:
            session.log.append("A trap waits in this area. Resolve it before claiming treasure.")

    def _open_door(
        self,
        session: SessionState,
        exit_id: str | None,
        character_id: str | None,
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Doors can only be worked during exploration.")
            return
        current = self._current_tile(session)
        exit_state = next((item for item in current.exits if item.id == exit_id), None) if exit_id else None
        if exit_state is None or exit_state.kind != "door":
            session.log.append("Choose a door to open.")
            return
        member = (
            next((item for item in session.party if item.character_id == character_id), None)
            if character_id
            else self._member_by_marching_order(session, 1)
        )
        if member is None:
            session.log.append("That hero is not available.")
            return
        session.log.append(f"{member.name} works the {exit_state.direction} door.")
        opened, log = attempt_open_door(
            exit_state,
            member,
            hcl=self._highest_character_level(session.party),
            show_rolls=show_rolls,
            explain_math=explain_math,
            roller=self.table_roller,
            party=session.party,
            marching_order=self._marching_order_ids(session),
        )
        session.log.extend(log)
        if not log:
            session.log.append("Nothing happens at this door.")
        if opened:
            exit_state.status = "open"
            self._sync_linked_door(session, current, exit_state)
            session.log.append(f"The {exit_state.direction} door is now open.")
        elif exit_state.door_result:
            session.log.append(f"The {exit_state.direction} door remains closed ({exit_state.door_result}).")

    def _resolve_trap(self, session: SessionState, *, show_rolls: bool, explain_math: bool) -> None:
        tile = self._current_tile(session)
        if not tile.trap_key or tile.trap_resolved:
            session.log.append("There is no active trap here.")
            return
        if session.mode == "combat":
            session.log.append("Handle the fight before disarming traps.")
            return
        member = self._member_by_marching_order(session, 1)
        if member and member.class_id.lower() == "rogue":
            total, rolls = roll_exploding_d6()
            modifier = member.level
            trap_level = tile.trap_level or self._highest_character_level(session.party)
            if show_rolls:
                session.log.append(
                    f"Disarm attempt: {member.name} rolls {' + '.join(str(value) for value in rolls)} + {modifier}."
                )
            if rolls[0] != 1 and total + modifier >= trap_level:
                tile.trap_resolved = True
                session.log.append("The rogue disarms the trap.")
                return
            session.log.append("The rogue fails to disarm the trap.")
        session.log.extend(
            self.table_roller.resolve_trap(
                tile.trap_key,
                tile.trap_level or self._highest_character_level(session.party),
                session.party,
                self._marching_order_ids(session),
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        )
        tile.trap_resolved = True
        tile.objects = [item for item in tile.objects if "trap" not in item.lower()]

    def _award_treasure(self, session: SessionState, tile: TileState, *, show_rolls: bool) -> None:
        if tile.treasure_summary or tile.treasure_gold or tile.treasure_items:
            return
        if tile.content_key in {"treasure", "trap_treasure"} or tile.resolved:
            outcome = self.table_roller.roll_treasure()
            tile.treasure_summary = outcome.summary
            tile.treasure_gold = outcome.gold
            tile.treasure_items = outcome.items
            if show_rolls:
                session.log.extend(outcome.log)
            session.log.append("Treasure is available to claim.")

    def _claim_treasure(self, session: SessionState) -> None:
        tile = self._current_tile(session)
        if tile.trap_key and not tile.trap_resolved:
            session.log.append("Resolve the trap before claiming treasure.")
            return
        if tile.treasure_claimed or (not tile.treasure_gold and not tile.treasure_items):
            session.log.append("There is no unclaimed treasure here.")
            return
        survivors = [member for member in session.party if member.current_life > 0]
        if not survivors:
            session.log.append("There is no one left to carry treasure.")
            return
        share, remainder = divmod(tile.treasure_gold, len(survivors))
        payouts: list[str] = []
        for index, member in enumerate(survivors):
            gold_gain = share + (1 if index < remainder else 0)
            member.gold += gold_gain
            if gold_gain:
                payouts.append(f"{member.name} +{gold_gain}gp")
        for item_index, item in enumerate(tile.treasure_items):
            survivors[item_index % len(survivors)].inventory.append(item)
        tile.treasure_claimed = True
        summary = tile.treasure_summary or "Treasure"
        session.log.append(f"Treasure claimed: {summary}")
        if payouts:
            session.log.append(f"Gold split: {', '.join(payouts)}.")
        if tile.treasure_items:
            item_list = ", ".join(tile.treasure_items)
            session.log.append(f"Items added to party inventories: {item_list}.")
        tile.objects = [item for item in tile.objects if "treasure" not in item.lower()]

    def _touch(self, session: SessionState) -> SessionState:
        session.updated_at = now_utc()
        return session
