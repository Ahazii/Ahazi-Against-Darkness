"""Forsaken Depths underground river travel, room codes, and NC corridor rules."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from ..schemas import PartyMemberState, SessionState, TileState, ExitState
from .dice import roll_d6, roll_exploding_for_level
from .forsaken_depths_map import fd_river_type_label, is_fd_ruleset, session_tile_catalog, tile_has_room_code
from .weapons import WeaponProfile

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine

BOATMAN_TYPES = (
    "human boatman",
    "undead skeletal ferryman",
    "metallic clockwork boatman",
    "dark elf boatman",
    "deep hobgoblin boatman",
)

_DIRECTION_DELTA: dict[str, tuple[int, int]] = {
    "north": (0, -1),
    "northeast": (1, -1),
    "east": (1, 0),
    "southeast": (1, 1),
    "south": (0, 1),
    "southwest": (-1, 1),
    "west": (-1, 0),
    "northwest": (-1, -1),
}


def fd_exit_travel_kind(
    engine: RandomDungeonEngine,
    tile: TileState,
    exit_state: ExitState,
) -> str:
    """Classify a river exit as water channel, bank, or unknown from walkable grid."""
    width, height = engine._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
    walkable = engine._state_rows(tile.walkable, width, height, "1")
    dx, dy = _DIRECTION_DELTA.get(exit_state.direction, (0, 0))
    water = False
    bank = False
    for local_x, local_y in engine._exit_cells(
        exit_state.x,
        exit_state.y,
        exit_state.direction,
        exit_state.span,
        width,
        height,
    ):
        if not (0 <= local_x < width and 0 <= local_y < height):
            continue
        code = walkable[local_y][local_x]
        if code == "2":
            water = True
        elif code == "1":
            bank = True
        elif code == "0" and (dx, dy) != (0, 0):
            inside_x = local_x - dx
            inside_y = local_y - dy
            if 0 <= inside_x < width and 0 <= inside_y < height:
                inner = walkable[inside_y][inside_x]
                if inner == "2":
                    water = True
                elif inner != "0":
                    bank = True
    if water and not bank:
        return "water"
    if bank and not water:
        return "bank"
    if water:
        return "water"
    if bank:
        return "bank"
    return "unknown"


def fd_validate_river_exit_travel(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    exit_state: ExitState,
    *,
    show_rolls: bool = True,
) -> bool:
    """Return False when boat/foot travel mode blocks this exit (FD p.28)."""
    if not is_fd_ruleset(session) or session_tile_catalog(session) != "forsaken_depths_rivers":
        return True
    kind = fd_exit_travel_kind(engine, tile, exit_state)
    on_boat = session.fd_travel_mode == "boat" and session.fd_boat_status != "destroyed"
    if on_boat:
        if kind == "bank":
            session.fd_travel_mode = "foot"
            if show_rolls:
                session.log.append("The party disembarks and continues on foot via the bank (FD p.28).")
            return True
        if kind != "water":
            session.log.append(
                "While boating, follow water-channel exits. Disembark via a bank exit to travel on foot (FD p.28)."
            )
            return False
        return True
    if kind == "water":
        session.log.append(
            "The party is on foot — use bank exits on this stretch, or travel by boat on the water channel (FD p.28)."
        )
        return False
    return True


def tile_is_narrow_corridor(tile: TileState | None) -> bool:
    return tile is not None and tile_has_room_code(tile, "NC")


def fd_on_death_river(session: SessionState) -> bool:
    return (
        is_fd_ruleset(session)
        and session_tile_catalog(session) == "forsaken_depths_rivers"
        and session.fd_river_type == "death"
    )


def fd_death_river_combat_adjustments(session: SessionState) -> tuple[int, int]:
    """Attack bonus, defense bonus on the River of Death (FD p.32)."""
    if fd_on_death_river(session):
        return 1, -1
    return 0, 0


def fd_death_river_healing_multiplier(session: SessionState) -> float:
    return 0.5 if fd_on_death_river(session) else 1.0


def fd_tears_river_blocks_rest(session: SessionState) -> bool:
    return (
        is_fd_ruleset(session)
        and session_tile_catalog(session) == "forsaken_depths_rivers"
        and session.fd_river_type == "tears"
    )


def fd_narrow_corridor_ranged_allowed(member: PartyMemberState, *, rear_ambush: bool = False) -> bool:
    order = member.marching_order or 1
    if rear_ambush:
        return order == 4
    return order == 1


def fd_narrow_corridor_weapon_adjustment(
    weapon: WeaponProfile | None,
    *,
    missile: bool,
    item_name: str = "",
) -> tuple[int, str | None]:
    """Extra attack modifier and optional block reason for NC tiles (FD p.27)."""
    if weapon is None and not missile:
        return 0, None
    lower = (weapon.item if weapon else item_name).lower()
    if missile:
        return 0, None
    if weapon and weapon.two_handed:
        return -1, None
    if any(token in lower for token in ("spear", "pike", "halberd", "lance")):
        return 0, "Long weapons may not be used in narrow corridors (FD p.27)."
    if weapon and weapon.light and weapon.slashing:
        return 2, None
    return 0, None


def fd_serpent_boating_modifier(session: SessionState) -> int:
    if is_fd_ruleset(session) and session.fd_river_type == "serpent":
        return -2
    return 0


def _charge_fd_boatman_fee(
    session: SessionState,
    boatman_kind: str,
    *,
    show_rolls: bool = True,
) -> bool:
    """Deduct boatman fare from living heroes; return False when anyone cannot pay."""
    per_character = 30 if "deep hobgoblin" in boatman_kind else 20
    living = [member for member in session.party if member.current_life > 0]
    if not living:
        return False
    total_cost = per_character * len(living)
    if sum(member.gold for member in living) < total_cost:
        if show_rolls:
            session.log.append(
                f"The {boatman_kind} demands {per_character} gp per character "
                f"({total_cost} gp total) — the party cannot pay (FD p.28)."
            )
        return False
    remaining = total_cost
    for member in living:
        share = min(member.gold, per_character)
        member.gold -= share
        remaining -= share
    if remaining > 0:
        for member in living:
            if remaining <= 0:
                break
            extra = min(member.gold, remaining)
            member.gold -= extra
            remaining -= extra
    if show_rolls:
        session.log.append(
            f"The party pays the {boatman_kind} {total_cost} gp "
            f"({per_character} gp per character, FD p.28)."
        )
    return True


def fd_acquire_boat_at_etr(
    session: SessionState,
    etr_tile: TileState,
    *,
    show_rolls: bool = True,
) -> None:
    """ETR room boat / boatman setup when entering the underground river (FD p.27–28)."""
    violent = bool(etr_tile.enemies) or bool(etr_tile.defeated_enemies)
    session.fd_boatman_kind = None
    if violent:
        found = roll_d6() <= 4
        if show_rolls:
            session.log.append(
                f"ETR boat search: d6 = {'found' if found else 'none'} — "
                f"{'a boat is here after the encounter' if found else 'no boat in this ETR room (4-in-6).'} "
                "(FD p.27)."
            )
        if not found:
            session.fd_travel_mode = "foot"
            session.fd_boatman_present = False
            return
    else:
        boatman_roll = roll_d6()
        if boatman_roll <= 2:
            kind = BOATMAN_TYPES[0]
        elif boatman_roll == 3:
            kind = BOATMAN_TYPES[1]
        elif boatman_roll == 4:
            kind = BOATMAN_TYPES[2]
        elif boatman_roll == 5:
            kind = BOATMAN_TYPES[3]
        else:
            kind = BOATMAN_TYPES[4]
        session.fd_boatman_kind = kind
        if show_rolls:
            session.log.append(
                f"ETR boatman roll: d6 = {boatman_roll} → {kind} offers river passage "
                f"(20 gp per character; 30 gp for deep hobgoblin) (FD p.28)."
            )
        session.fd_boatman_present = True
        if not _charge_fd_boatman_fee(session, kind, show_rolls=show_rolls):
            session.fd_travel_mode = "foot"
            session.fd_boatman_present = False
            session.log.append("The party travels on foot along the river banks (FD p.28).")
            return
    session.fd_travel_mode = "boat"
    session.fd_boat_status = "ok"
    session.log.append("The party boards a river boat.")


def apply_river_type_on_stretch_entry(
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> None:
    river_type = session.fd_river_type
    if not river_type:
        return
    label = fd_river_type_label(river_type)
    if river_type == "oblivion":
        if not session.fd_oblivion_madness_redemption_used and not session.fd_oblivion_madness_redemption_pending:
            session.fd_oblivion_madness_redemption_pending = True
            session.log.append(
                f"{label}: the party may remove 1 Madness from one hero once (FD p.32). "
                "Use the party sheet when ready. Spellcasting or puzzle Save rolls of 1 may forget a spell."
            )
        elif show_rolls and not session.fd_oblivion_madness_redemption_pending:
            session.log.append(f"{label}: beware forgotten spells on natural 1 spellcasting or puzzle Saves (FD p.32).")
    elif river_type == "tears":
        session.log.append(f"{label}: Rest is unavailable on this river; death here spreads Madness (FD p.32).")
    elif river_type == "death":
        session.log.append(
            f"{label}: Attack rolls +1, Defense rolls −1; healing is half strength (FD p.32)."
        )
    elif river_type == "flame":
        session.log.append(f"{label}: fire Save on each stretch; non-fireproof boats risk destruction (FD p.32).")
    elif river_type == "conjuration":
        session.log.append(
            f"{label}: spirits of the dead may be consulted for Clues at the cost of Madness (FD p.34)."
        )
    elif river_type == "serpent":
        session.log.append(f"{label}: boating rolls at −2; Major Foe level +1 on this river (FD p.34).")
    elif show_rolls:
        session.log.append(f"Traveling the {label}.")


def apply_flame_river_entry(
    session: SessionState,
    *,
    hcl: int,
    show_rolls: bool = True,
) -> None:
    if session.fd_river_type != "flame":
        return
    for member in session.party:
        if member.current_life <= 0:
            continue
        class_id = member.class_id.lower()
        if class_id in {"pyromancer"} or "fire elf" in member.class_name.lower():
            if show_rolls:
                session.log.append(f"{member.name} is immune to Flame river entry damage (FD p.32).")
            continue
        total, _ = roll_exploding_for_level(hcl + 2)
        if show_rolls:
            session.log.append(
                f"Flame river entry: {member.name} Save vs. HCL+2 fire → {total} "
                f"({'pass' if total >= hcl + 2 else 'fail'})."
            )
        if total < hcl + 2:
            member.current_life = max(0, member.current_life - 1)
            session.log.append(f"{member.name} loses 1 Life to boiling steam (FD p.32).")
    if session.fd_travel_mode != "boat" or session.fd_boat_status == "destroyed":
        return
    session.fd_flame_stretch_count += 1
    boat_roll = roll_d6() + session.fd_flame_stretch_count - 1
    if show_rolls:
        session.log.append(
            f"Flame river boat check: d6 + {session.fd_flame_stretch_count - 1} consecutive = {boat_roll} "
            "(6+ destroys a non-fireproof boat) (FD p.32)."
        )
    if boat_roll >= 6:
        session.fd_boat_status = "destroyed"
        session.fd_travel_mode = "foot"
        session.log.append("The boat is destroyed in the boiling waters — the party swims for the banks (FD p.32).")


def apply_room_codes_on_stretch_entry(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    show_rolls: bool = True,
) -> None:
    codes = list(tile.room_codes or [])
    if "END" in codes:
        session.log.append(
            "END — this river stretch goes underground and can no longer be navigated by boat (FD p.32). "
            "A new river later requires a fresh river-type roll."
        )
        session.fd_travel_mode = "foot"
        session.fd_boatman_present = False
        session.fd_boatman_kind = None
        session.fd_river_type = None
        session.fd_flame_stretch_count = 0
        if show_rolls:
            session.log.append("Disembark and continue on foot; the next ETR rolls a new river type (FD p.32).")
    if "Ru" in codes:
        session.log.append(
            "Ru — Forsaken Ruins side sheet (d6+2 rooms). Use Enter side dungeon on this stretch (FD p.39)."
        )
    if "Ca" in codes:
        session.log.append(
            "Cairn (Ca) — spellcasters may tap cairn energy: HCL+5 spellcasting roll to cast without "
            "expending a spell at the cost of 1 Life (FD p.40)."
        )
    if "B" in codes:
        if roll_d6() <= 2:
            row = engine.table_roller.lookup_fd_subtable_row("fd_river_encounter_table", roll_d6())
            if row:
                if show_rolls:
                    session.log.append(
                        f"Bridge (B): guarded — river encounter d6 → {row.get('name', 'foes')} (FD p.40)."
                    )
                hcl = engine._highest_character_level(session.party)
                spawned = engine._fd_spawn_from_table_row(session, row, hcl)
                if spawned:
                    tile.enemies.extend(spawned)
                    if session.mode == "exploration":
                        engine._announce_encounter(session, tile, show_rolls=show_rolls)
        elif show_rolls:
            session.log.append("Bridge (B): no guard present (2-in-6) (FD p.40).")
    if "ETC" in codes:
        from .forsaken_depths_content import roll_fd_citadel

        roll_fd_citadel(engine, session, tile, show_rolls=show_rolls)
        session.log.append(
            "ETC — map this Citadel on a separate sheet (FD p.27)."
        )


def resolve_ghosts_of_the_river(
    session: SessionState,
    *,
    hcl: int,
    show_rolls: bool = True,
) -> None:
    from .heroic_skill_effects import resolve_fear_save
    from .madness import apply_madness_gain, madness_points

    for member in session.party:
        if member.current_life <= 0:
            continue
        class_id = member.class_id.lower()
        if class_id in {"necromancer", "paladin"} or "questing knight" in member.class_name.lower():
            if show_rolls:
                session.log.append(f"{member.name} is immune to Ghosts of the River (FD p.30).")
            continue
        before_madness = madness_points(member)
        saved, fear_log = resolve_fear_save(
            session,
            member,
            hcl,
            party=session.party,
            show_rolls=show_rolls,
            label="fear",
            madness_source="Ghosts of the River",
        )
        session.log.extend(fear_log)
        if saved:
            continue
        if madness_points(member) == before_madness:
            session.log.extend(
                apply_madness_gain(
                    session,
                    member,
                    source="Ghosts of the River",
                    show_rolls=show_rolls,
                )
            )
        else:
            member.current_life = max(0, member.current_life - 2)
            session.log.append(f"{member.name} loses 2 Life to the river ghosts (FD p.30).")


def resolve_river_teleport(
    engine: RandomDungeonEngine,
    session: SessionState,
    current_tile: TileState,
    *,
    show_rolls: bool = True,
) -> None:
    candidates = [
        tile
        for tile in session.map_state.tiles
        if tile.id != current_tile.id and tile.tile_catalog == "forsaken_depths_rivers"
    ]
    if not candidates:
        session.log.append("Teleport hazard — no other river stretch exists on the map yet (FD p.30).")
        return
    destination = random.choice(candidates)
    session.map_state.current_tile_id = destination.id
    session.log.append(f"Teleport hazard — the boat jumps to {destination.title} (FD p.30).")
    if session.fd_travel_mode == "foot" or session.fd_boat_status == "destroyed":
        if show_rolls:
            session.log.append("Teleport hazard — the party is on foot; no boating Save is required (FD p.30).")
        return
    boating_total, _ = roll_exploding_for_level(8, purpose="save")
    boatman_level = 9 if session.fd_boatman_present else 0
    serpent_mod = fd_serpent_boating_modifier(session)
    boating_target = 8
    total = boating_total + boatman_level + serpent_mod
    if show_rolls:
        label = "Boatman L8 boating Save" if session.fd_boatman_present else "Party boating Save"
        serpent_note = f" {serpent_mod:+d} Serpent River" if serpent_mod else ""
        session.log.append(
            f"{label}: d8+explode + L{boatman_level}{serpent_note} = {total} vs. {boating_target}."
        )
    if total < boating_target:
        engine._fd_apply_damaged_boat(session)


def apply_fd_dungeon_room_codes_on_enter(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    show_rolls: bool = True,
) -> None:
    """Dungeon-tile room codes (parallel to river stretch entry)."""
    if not is_fd_ruleset(session) or session_tile_catalog(session) != "forsaken_depths":
        return
    if tile_has_room_code(tile, "ETC") and not session.fd_citadel_type:
        from .forsaken_depths_content import roll_fd_citadel

        roll_fd_citadel(engine, session, tile, show_rolls=show_rolls)
        session.fd_citadel_entry_tile_id = tile.id
        session.log.append("ETC — map this Citadel on a separate sheet (FD p.27).")


def apply_special_feature_hazard(
    session: SessionState,
    tile: TileState,
    *,
    show_rolls: bool = True,
) -> None:
    feature_roll = roll_d6()
    if feature_roll <= 2:
        code = "B"
        label = "Bridge"
    elif feature_roll <= 4:
        code = "Ca"
        label = "Cairn"
    else:
        code = "ETC"
        label = "Entrance to Citadel"
    if code not in tile.room_codes:
        tile.room_codes = list(tile.room_codes or []) + [code]  # type: ignore[assignment]
    if show_rolls:
        session.log.append(
            f"Special Feature hazard: d6 = {feature_roll} → {label} ({code}) added to this stretch (FD p.30)."
        )


def fd_travel_mode_label(session: SessionState) -> str:
    if not is_fd_ruleset(session) or session_tile_catalog(session) != "forsaken_depths_rivers":
        return ""
    if session.fd_travel_mode == "foot" or session.fd_boat_status == "destroyed":
        return "On foot"
    if session.fd_boat_status == "damaged":
        return "Boat (damaged)"
    return "Boat"


def apply_fd_oblivion_forget_spell(
    session: SessionState,
    member: PartyMemberState,
    spell_name: str,
    *,
    show_rolls: bool = True,
    source: str = "spellcasting",
) -> None:
    if not is_fd_ruleset(session) or session.fd_river_type != "oblivion":
        return
    from .spells import normalize_spell_name

    clean_name = spell_name.strip()
    if not clean_name:
        return
    forgotten = session.fd_forgotten_spells.setdefault(member.character_id, [])
    if clean_name not in forgotten:
        forgotten.append(clean_name)
    key = normalize_spell_name(clean_name)
    member.spells = [entry for entry in member.spells if normalize_spell_name(entry) != key]
    if show_rolls:
        session.log.append(
            f"River of Oblivion: {member.name} forgets {clean_name} until end of adventure "
            f"(natural 1 on {source}, FD p.32)."
        )


def apply_fd_oblivion_forget_on_natural_one(
    session: SessionState,
    member: PartyMemberState,
    *,
    natural: int,
    spell_name: str | None = None,
    show_rolls: bool = True,
    source: str = "spellcasting",
) -> None:
    if natural != 1:
        return
    if not is_fd_ruleset(session) or session.fd_river_type != "oblivion":
        return
    chosen = spell_name.strip() if spell_name else ""
    if not chosen and member.spells:
        chosen = random.choice(list(member.spells))
    if not chosen:
        if show_rolls:
            session.log.append(
                f"River of Oblivion: {member.name} rolled a natural 1 but has no spells to forget (FD p.32)."
            )
        return
    apply_fd_oblivion_forget_spell(session, member, chosen, show_rolls=show_rolls, source=source)


def apply_fd_oblivion_spell_forget_from_cast(
    session: SessionState,
    caster: PartyMemberState,
    spell_name: str,
    outcome_log: list[str],
    *,
    show_rolls: bool = True,
) -> None:
    if not is_fd_ruleset(session) or session.fd_river_type != "oblivion":
        return
    import re

    natural: int | None = None
    for line in outcome_log:
        if caster.name not in line or " rolls " not in line:
            continue
        match = re.search(r"rolls (\d+)", line)
        if match:
            natural = int(match.group(1))
            break
    if natural != 1:
        return
    apply_fd_oblivion_forget_spell(
        session,
        caster,
        spell_name,
        show_rolls=show_rolls,
        source="spellcasting",
    )


def redeem_fd_oblivion_madness(
    session: SessionState,
    member: PartyMemberState,
    *,
    show_rolls: bool = True,
) -> bool:
    """One-time remove 1 Madness on the River of Oblivion (FD p.32)."""
    from .madness import heal_madness, madness_points

    if not is_fd_ruleset(session) or session.fd_river_type != "oblivion":
        return False
    if not session.fd_oblivion_madness_redemption_pending or session.fd_oblivion_madness_redemption_used:
        return False
    if member.current_life <= 0:
        return False
    if madness_points(member) <= 0:
        return False
    healed = heal_madness(member, 1)
    if healed <= 0:
        return False
    session.fd_oblivion_madness_redemption_used = True
    session.fd_oblivion_madness_redemption_pending = False
    if show_rolls:
        session.log.append(
            f"River of Oblivion: {member.name} sheds 1 Madness ({madness_points(member)} remain, FD p.32)."
        )
    return True

