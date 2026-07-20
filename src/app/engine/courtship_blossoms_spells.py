"""Blossoms spell scroll effects (TCOTFD p.27)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..schemas import EnemyState, PartyMemberState, SessionState, TileState
from .courtship_ingredients import (
    RARE_INGREDIENT_NAMES,
    format_rare_ingredient,
    is_demesne_ingredient_item,
    remove_inventory_at,
)
from .dice import roll_d3, roll_d6, roll_exploding_for_level, roll_formula
from .scrolls import scroll_spell_name
from .spells import SpellOutcome, normalize_spell_name

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine

BLOSSOMS_SPELLS: tuple[str, ...] = (
    "Ætheric Conversion",
    "Bountiful Harvest",
    "Flower Portal",
    "Fools' Gold",
    "Libidinal Enhancement",
    "Song of Charm",
)

BLOSSOMS_SPELL_KEYS: frozenset[str] = frozenset(
    {
        "aetheric_conversion",
        "bountiful_harvest",
        "flower_portal",
        "fools_gold",
        "libidinal_enhancement",
        "song_of_charm",
    }
)

BOUNTIFUL_FAIL_SPAWNS: tuple[tuple[str, str, str], ...] = (
    ("Strangling Seaweed", "d3", "minions"),
    ("Venus Flytrap", "1", "minions"),
    ("Giant Purple Pitcherplant", "1", "weird"),
    ("Giant Sundew", "1", "minions"),
    ("Corrosive Shrub", "1", "minions"),
    ("Death Orchid", "1", "weird"),
)

SONG_OF_CHARM_REACTIONS: tuple[str, ...] = (
    "fight",
    "bribe",
    "trade_information",
    "quest",
    "offer_information",
    "sleep",
)

INSTRUMENT_KEYWORDS: tuple[str, ...] = (
    "instrument",
    "lute",
    "harp",
    "flute",
    "lyre",
    "drum",
    "mandolin",
    "pipe",
)


def blossoms_spell_key(spell_name: str) -> str:
    key = normalize_spell_name(spell_name)
    if "etheric_conversion" in key or key.endswith("theric_conversion"):
        return "aetheric_conversion"
    return key


def is_blossoms_spell(spell_name: str) -> bool:
    return blossoms_spell_key(spell_name) in BLOSSOMS_SPELL_KEYS


def is_blossoms_scroll_item(item: str) -> bool:
    spell = scroll_spell_name(item)
    return spell is not None and is_blossoms_spell(spell)


def blossoms_casting_modifier(member: PartyMemberState, *, from_scroll: bool) -> int:
    modifier = 0
    class_id = member.class_id.lower()
    if class_id in {"wizard", "conservationist"}:
        modifier += member.level
    if class_id == "satyr" and not from_scroll:
        modifier += member.level
    if from_scroll and class_id == "demonologist":
        modifier += member.level
    if from_scroll and class_id == "halfling":
        modifier += member.level
    return modifier


def _spellcasting_roll(
    member: PartyMemberState,
    level: int,
    *,
    from_scroll: bool,
    show_rolls: bool,
    log: list[str],
    label: str,
    auto_fail_rolls: frozenset[int] | None = None,
) -> tuple[bool, list[int]]:
    modifier = blossoms_casting_modifier(member, from_scroll=from_scroll)
    total, rolls = roll_exploding_for_level(member)
    if show_rolls:
        log.append(
            f"{label}: {member.name} rolls {' + '.join(str(v) for v in rolls)} + {modifier} vs L{level} (TCOTFD p.27)."
        )
    if auto_fail_rolls and rolls[0] in auto_fail_rolls:
        log.append(f"{label} fails on a natural {rolls[0]} (TCOTFD p.27).")
        return False, rolls
    ok = rolls[0] != 1 and total + modifier >= level
    if not ok:
        log.append(f"{label} fails (TCOTFD p.27).")
    return ok, rolls


def _living_on_tile(party: list[PartyMemberState]) -> list[PartyMemberState]:
    return [member for member in party if member.current_life > 0]


def _consume_soul_cube(member: PartyMemberState, log: list[str]) -> bool:
    index = next((i for i, item in enumerate(member.inventory) if "soul cube" in item.lower()), None)
    if index is None:
        log.append("Need a soul cube (TCOTFD p.27).")
        return False
    member.inventory.pop(index)
    log.append(f"{member.name} spends a soul cube (TCOTFD p.27).")
    return True


def _count_soul_cubes(member: PartyMemberState) -> int:
    return sum(1 for item in member.inventory if "soul cube" in item.lower())


def _consume_soul_cubes(member: PartyMemberState, count: int, log: list[str]) -> bool:
    if _count_soul_cubes(member) < count:
        log.append(f"Need {count} soul cube(s) (TCOTFD p.27).")
        return False
    for _ in range(count):
        if not _consume_soul_cube(member, log):
            return False
    return True


def _flower_portal_netherworld_modifier(member: PartyMemberState, *, from_scroll: bool) -> int:
    modifier = 0
    if member.class_id.lower() == "wizard":
        modifier += member.level
    if from_scroll and member.class_id.lower() == "demonologist":
        modifier += member.level
    return modifier


def flower_portal_destinations(
    session: SessionState,
    tile: TileState | None,
    engine: RandomDungeonEngine | None = None,
) -> list[str]:
    from .courtship_demesne import tile_at_water_landscape

    options: list[str] = []
    water = tile_at_water_landscape(session, tile, engine)
    if water and session.courtship_enabled and not session.courtship_demesne_active:
        options.append("enter_demesne")
    if session.courtship_demesne_active and session.courtship_demesne_region in {"seaside", "riverside"}:
        options.append("leave_demesne")
    if water:
        options.append("netherworld")
    return options


def _flower_portal_source_tile(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
) -> TileState:
    if session.courtship_demesne_active and session.courtship_return_tile_id:
        return_tile = engine._tile_by_id(session, session.courtship_return_tile_id)
        if return_tile is not None:
            return return_tile
    return tile


def _deactivate_demesne_for_portal(session: SessionState) -> None:
    session.courtship_demesne_active = False
    session.courtship_demesne_region = None
    session.courtship_pending_pathways = None
    session.courtship_encounter_reroll_spent = False


def open_flower_portal_netherworld(
    engine: RandomDungeonEngine,
    session: SessionState,
    caster: PartyMemberState,
    tile: TileState,
    *,
    show_rolls: bool,
    from_scroll: bool,
) -> bool:
    from .courtship_demesne import flower_portal_water_failure_message, tile_at_water_landscape

    if not tile_at_water_landscape(session, tile, engine):
        session.log.append(flower_portal_water_failure_message(session, tile, engine))
        return False
    if _count_soul_cubes(caster) < 3:
        session.log.append("Flower Portal to the Netherworld requires 3 soul cubes (TCOTFD p.27).")
        return False
    log: list[str] = []
    modifier = _flower_portal_netherworld_modifier(caster, from_scroll=from_scroll)
    total, rolls = roll_exploding_for_level(caster)
    if show_rolls:
        log.append(
            f"Flower Portal (Netherworld): {caster.name} rolls {' + '.join(str(v) for v in rolls)} + {modifier} vs L9 (TCOTFD p.27)."
        )
    ok = rolls[0] != 1 and total + modifier >= 9
    if not ok:
        _consume_soul_cubes(caster, 3, log)
        log.append("Flower Portal to the Netherworld fails — all three soul cubes are spent (TCOTFD p.27).")
        session.log.extend(log)
        return True
    roll_total = total + modifier
    cubes = 1 if roll_total >= 11 else 2 if roll_total >= 10 else 3
    if not _consume_soul_cubes(caster, cubes, log):
        session.log.extend(log)
        return False
    source = _flower_portal_source_tile(engine, session, tile)
    previous = session.environment
    if session.courtship_demesne_active:
        return_tile_id = session.courtship_return_tile_id
        _deactivate_demesne_for_portal(session)
        if return_tile_id:
            session.map_state.current_tile_id = return_tile_id
    opened = engine._open_secret_passage_destination(
        session,
        source,
        "caverns",
        previous_environment=previous,
        show_rolls=show_rolls,
    )
    if opened:
        log.append("Flower Portal opens a secret passage to the Netherworld (caverns, TCOTFD p.27).")
    else:
        log.append("Could not open the Netherworld passage from this tile (TCOTFD p.27).")
    session.log.extend(log)
    return opened


def resolve_flower_portal(
    engine: RandomDungeonEngine,
    session: SessionState,
    caster: PartyMemberState,
    tile: TileState,
    *,
    destination: str | None,
    show_rolls: bool,
    from_scroll: bool,
) -> bool:
    from .courtship_classes import (
        flower_portal_casts_remaining,
        flower_portal_innate_cast,
        is_satyr,
        note_flower_portal_cast,
        note_satyr_blossoms_cast,
    )
    from .courtship_demesne import enter_courtship_via_flower_portal, flower_portal_water_failure_message, leave_courtship_demesne

    if flower_portal_innate_cast(caster, from_scroll=from_scroll):
        remaining = flower_portal_casts_remaining(session, caster)
        if remaining is not None and remaining <= 0:
            session.log.append(
                f"{caster.name} has already cast Flower Portal innately this adventure "
                "(once per adventure; scrolls are unlimited, TCOTFD p.7-8 / p.27)."
            )
            return False

    if from_scroll:
        log: list[str] = [f"{caster.name} reads a scroll of Flower Portal (TCOTFD p.27)."]
    else:
        log = [f"{caster.name} casts Flower Portal (TCOTFD p.27)."]
    options = flower_portal_destinations(session, tile, engine)
    if not options:
        session.log.append(flower_portal_water_failure_message(session, tile, engine))
        return False
    if destination is None:
        if len(options) == 1:
            destination = options[0]
        else:
            session.log.append("Choose a Flower Portal destination (TCOTFD p.27).")
            session.courtship_pending_choice = "flower_portal_destination"
            session.courtship_pending_choice_label = caster.character_id
            return True

    if destination not in options:
        session.log.append("Choose a valid Flower Portal destination (TCOTFD p.27).")
        session.courtship_pending_choice = "flower_portal_destination"
        session.courtship_pending_choice_label = caster.character_id
        return False

    session.courtship_pending_choice = None
    session.courtship_pending_choice_label = None

    if destination == "enter_demesne":
        if not _consume_soul_cube(caster, log):
            session.log.extend(log)
            return False
        session.log.extend(log)
        opened = enter_courtship_via_flower_portal(engine, session, tile, show_rolls=show_rolls)
        if opened:
            note_flower_portal_cast(session, caster, from_scroll=from_scroll)
        if opened and is_satyr(caster) and not from_scroll:
            note_satyr_blossoms_cast(session, caster)
        return opened

    if destination == "leave_demesne":
        if not _consume_soul_cube(caster, log):
            session.log.extend(log)
            return False
        session.log.extend(log)
        left = leave_courtship_demesne(engine, session, show_rolls=show_rolls)
        if left:
            note_flower_portal_cast(session, caster, from_scroll=from_scroll)
        if left and is_satyr(caster) and not from_scroll:
            note_satyr_blossoms_cast(session, caster)
        return left

    if destination == "netherworld":
        session.log.extend(log)
        opened = open_flower_portal_netherworld(
            engine,
            session,
            caster,
            tile,
            show_rolls=show_rolls,
            from_scroll=from_scroll,
        )
        if opened:
            note_flower_portal_cast(session, caster, from_scroll=from_scroll)
        if opened and is_satyr(caster) and not from_scroll:
            note_satyr_blossoms_cast(session, caster)
        return opened

    session.log.append("Unknown Flower Portal destination (TCOTFD p.27).")
    return False


def resolve_flower_portal_destination_choice(
    engine: RandomDungeonEngine,
    session: SessionState,
    choice: str | None,
    *,
    show_rolls: bool,
) -> bool:
    caster = next(
        (member for member in session.party if member.character_id == session.courtship_pending_choice_label),
        None,
    )
    if caster is None:
        session.courtship_pending_choice = None
        session.courtship_pending_choice_label = None
        session.log.append("No caster is waiting on Flower Portal (TCOTFD).")
        return False
    tile = engine._current_tile(session)
    if tile is None:
        session.log.append("No map tile for Flower Portal (TCOTFD).")
        return False
    ok = resolve_flower_portal(
        engine,
        session,
        caster,
        tile,
        destination=choice,
        show_rolls=show_rolls,
        from_scroll=True,
    )
    if ok and session.courtship_pending_choice != "flower_portal_destination":
        finish_blossoms_scroll(session, caster, session.courtship_blossoms_scroll_pending)
    return ok


def _spawn_bountiful_fail_plant(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    show_rolls: bool,
) -> None:
    from .courtship_demesne import _spawn_courtship

    roll = roll_d6()
    template, count, category = BOUNTIFUL_FAIL_SPAWNS[roll - 1]
    hcl = engine._highest_character_level(session.party)
    _spawn_courtship(
        engine,
        session,
        tile,
        {"template": template, "count": count, "category": category, "level_delta": 0},
        hcl=hcl,
        show_rolls=show_rolls,
    )
    if session.mode == "exploration" and tile.enemies:
        engine._announce_encounter(session, tile, show_rolls=show_rolls)


def cast_bountiful_harvest(
    engine: RandomDungeonEngine,
    session: SessionState,
    member: PartyMemberState,
    tile: TileState | None,
    *,
    show_rolls: bool,
) -> bool:
    if tile is None:
        session.log.append("Bountiful Harvest needs a map location (TCOTFD p.27).")
        return False
    log: list[str] = []
    ok, _ = _spellcasting_roll(
        member,
        5,
        from_scroll=True,
        show_rolls=show_rolls,
        log=log,
        label="Bountiful Harvest",
    )
    session.log.extend(log)
    if not ok:
        session.log.append("Bountiful Harvest fails — a hostile plant grows instead (TCOTFD p.27).")
        _spawn_bountiful_fail_plant(engine, session, tile, show_rolls=show_rolls)
        return True
    session.log.append("Bountiful Harvest succeeds — choose common (d6) or uncommon (d3) ingredients (TCOTFD p.27).")
    session.courtship_pending_choice = "bountiful_harvest"
    session.courtship_pending_choice_label = member.character_id
    return True


def resolve_bountiful_harvest_choice(
    session: SessionState,
    member: PartyMemberState,
    choice: str | None,
    *,
    show_rolls: bool,
) -> bool:
    session.courtship_pending_choice = None
    session.courtship_pending_choice_label = None
    if choice == "uncommon":
        count = roll_d3()
        for _ in range(count):
            member.inventory.append("Uncommon ingredient")
        session.log.append(f"{member.name} grows {count} uncommon ingredient(s) (Bountiful Harvest, TCOTFD).")
        finish_blossoms_scroll(session, member)
        return True
    if choice == "common":
        count = roll_d6()
        for _ in range(count):
            member.inventory.append("Common ingredient")
        session.log.append(f"{member.name} grows {count} common ingredient(s) (Bountiful Harvest, TCOTFD).")
        finish_blossoms_scroll(session, member)
        return True
    session.log.append("Choose common or uncommon ingredients from Bountiful Harvest (TCOTFD).")
    session.courtship_pending_choice = "bountiful_harvest"
    session.courtship_pending_choice_label = member.character_id
    return False


def _count_ingredients(inventory: list[str], *, mineral: bool = False, common: bool = False) -> int:
    count = 0
    for item in inventory:
        lower = item.lower()
        if mineral:
            if "mineral ingredient" in lower or lower == "mineral ingredient":
                count += 1
            continue
        if common:
            if "common ingredient" in lower and "mineral" not in lower:
                count += 1
    return count


def _consume_brew_ingredients(member: PartyMemberState, *, mineral: int, common: int) -> bool:
    removed_mineral = 0
    removed_common = 0
    keep: list[str] = []
    for item in member.inventory:
        lower = item.lower()
        if removed_mineral < mineral and ("mineral ingredient" in lower or lower == "mineral ingredient"):
            removed_mineral += 1
            continue
        if (
            removed_common < common
            and "common ingredient" in lower
            and "mineral" not in lower
            and "uncommon" not in lower
        ):
            removed_common += 1
            continue
        keep.append(item)
    if removed_mineral < mineral or removed_common < common:
        return False
    member.inventory = keep
    return True


def _member_has_instrument(member: PartyMemberState) -> bool:
    if member.class_id.lower() == "satyr":
        return True
    return any(keyword in item.lower() for item in member.inventory for keyword in INSTRUMENT_KEYWORDS)


def _apply_exploding_damage(
    session: SessionState,
    party: list[PartyMemberState],
    *,
    show_rolls: bool,
    log: list[str],
) -> int:
    total = 0
    while True:
        roll = roll_d6()
        total += roll
        if show_rolls:
            log.append(f"Ætheric explosion d6 = {roll} (total {total}, TCOTFD p.27).")
        if roll != 6:
            break
    for member in _living_on_tile(party):
        member.current_life = max(0, member.current_life - total)
        log.append(f"{member.name} suffers {total} Life from the alchemical explosion (TCOTFD p.27).")
    return total


def _destroy_belongings_and_summon(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    member: PartyMemberState,
    *,
    show_rolls: bool,
    log: list[str],
) -> None:
    from .star_object_curse import removable_inventory_items
    from .item_containers import remove_inventory_item_with_contents

    destroyed = removable_inventory_items(member.inventory)
    for item in destroyed:
        remove_inventory_item_with_contents(member, item_name=item)
    member.gold = 0
    if destroyed:
        log.append(f"{member.name}'s belongings are destroyed in the blaze ({len(destroyed)} item(s), TCOTFD p.27).")
    if member.inventory:
        log.append("The bound star-shaped object survives the blaze (TAG p.30).")
    from .courtship_demesne import _spawn_courtship

    hcl = engine._highest_character_level(session.party)
    _spawn_courtship(
        engine,
        session,
        tile,
        {"template": "Flower demon", "count": "1", "category": "minions", "level_delta": 0},
        hcl=hcl,
        show_rolls=show_rolls,
    )
    if session.mode == "exploration" and tile.enemies:
        engine._announce_encounter(session, tile, show_rolls=show_rolls)
    log.append("The fire summons a wandering monster (TCOTFD p.27).")


def cast_blossoms_spell(
    engine: RandomDungeonEngine,
    session: SessionState,
    caster: PartyMemberState,
    spell_name: str,
    tile: TileState | None,
    *,
    target_character_id: str | None = None,
    courtship_choice: str | None = None,
    show_rolls: bool = True,
    from_scroll: bool = False,
) -> bool:
    """Resolve a Blossoms spell. Returns True when resolved or pending UI; False on hard failure."""
    from .courtship_classes import is_satyr, note_satyr_blossoms_cast, satyr_blossoms_casts_remaining

    key = blossoms_spell_key(spell_name)
    log: list[str] = [f"{caster.name} casts {spell_name} (Blossoms spell, TCOTFD p.27)."]
    if is_satyr(caster) and not from_scroll:
        remaining = satyr_blossoms_casts_remaining(session, caster)
        if remaining is not None and remaining <= 0:
            session.log.append(
                f"{caster.name} has already cast a Blossoms spell {caster.level} time(s) this adventure "
                "(once per level, TCOTFD p.11)."
            )
            return False
    if tile is None:
        session.log.append("No active map tile for the Blossoms spell.")
        return False

    if key == "bountiful_harvest":
        session.log.extend(log)
        return cast_bountiful_harvest(engine, session, caster, tile, show_rolls=show_rolls)

    if key == "flower_portal":
        return resolve_flower_portal(
            engine,
            session,
            caster,
            tile,
            destination=courtship_choice,
            show_rolls=show_rolls,
            from_scroll=from_scroll,
        )

    if key == "aetheric_conversion":
        if courtship_choice is None:
            session.log.append("Choose which rare ingredient to synthesize (Ætheric Conversion, TCOTFD p.27).")
            session.courtship_pending_choice = "aetheric_conversion"
            session.courtship_pending_choice_label = caster.character_id
            return True
        target = courtship_choice.strip()
        if target not in RARE_INGREDIENT_NAMES:
            session.log.append("Choose a valid rare ingredient (Ætheric Conversion, TCOTFD p.27).")
            session.courtship_pending_choice = "aetheric_conversion"
            session.courtship_pending_choice_label = caster.character_id
            return True
        if caster.gold < 150:
            session.log.append("Ætheric Conversion requires 150gp in materials (TCOTFD p.27).")
            return False
        ok, _ = _spellcasting_roll(
            caster,
            10,
            from_scroll=from_scroll,
            show_rolls=show_rolls,
            log=log,
            label="Ætheric Conversion",
            auto_fail_rolls=frozenset({1, 2}),
        )
        caster.gold -= 150
        session.log.extend(log)
        if ok:
            value = roll_formula("5d6") * 10
            caster.inventory.append(format_rare_ingredient(target, value_gp=value))
            session.log.append(f"{caster.name} creates {target} ({value}gp, Ætheric Conversion, TCOTFD).")
            return True
        damage = _apply_exploding_damage(session, session.party, show_rolls=show_rolls, log=session.log)
        if damage >= 10:
            _destroy_belongings_and_summon(engine, session, tile, caster, show_rolls=show_rolls, log=session.log)
        return True

    if key == "fools_gold":
        mineral = _count_ingredients(caster.inventory, mineral=True)
        common = _count_ingredients(caster.inventory, common=True)
        if mineral < 5 or common < 3:
            session.log.append("Fools' Gold requires 5 mineral and 3 common ingredients (TCOTFD p.27).")
            return False
        ok, _ = _spellcasting_roll(
            caster,
            6,
            from_scroll=from_scroll,
            show_rolls=show_rolls,
            log=log,
            label="Fools' Gold",
        )
        session.log.extend(log)
        if not _consume_brew_ingredients(caster, mineral=5, common=3):
            session.log.append("Could not consume the required ingredients (TCOTFD p.27).")
            return False
        if ok:
            caster.inventory.append("Fools' Gold")
            session.log.append(f"{caster.name} brews one use of Fools' Gold (TCOTFD p.27).")
        else:
            session.log.append("The ingredients are wasted (Fools' Gold, TCOTFD p.27).")
        return True

    if key == "libidinal_enhancement":
        if not session.courtship_woo_active:
            session.log.append("Libidinal Enhancement applies during a wooing encounter (TCOTFD p.27).")
            return False
        target = next(
            (member for member in session.party if member.character_id == target_character_id),
            caster,
        )
        if target.current_life <= 0:
            session.log.append("Choose a living wooing partner for Libidinal Enhancement (TCOTFD p.27).")
            return False
        session.courtship_libidinal_character_id = target.character_id
        session.courtship_libidinal_reroll_available = True
        session.log.extend(log)
        session.log.append(
            f"{target.name} may re-roll one Giving roll this wooing encounter at a cost of 1 Life (TCOTFD p.27)."
        )
        from .courtship_apothecary import apply_libidinal_virile_conjunction

        apply_libidinal_virile_conjunction(session, target, show_rolls=show_rolls)
        return True

    if key == "song_of_charm":
        if session.mode != "combat":
            session.log.append("Song of Charm must be cast during combat (TCOTFD p.27).")
            return False
        living_foes = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living_foes:
            session.log.append("Song of Charm requires living foes (TCOTFD p.27).")
            return False
        if not _member_has_instrument(caster):
            session.log.append(
                f"{caster.name} needs a musical instrument (or satyr performance) for Song of Charm (TCOTFD p.27)."
            )
            return False
        foe_level = max(enemy.level for enemy in living_foes)
        ok, _ = _spellcasting_roll(
            caster,
            foe_level,
            from_scroll=from_scroll,
            show_rolls=show_rolls,
            log=log,
            label="Song of Charm",
        )
        session.log.extend(log)
        if not ok:
            return True
        session.courtship_pending_choice = "song_of_charm"
        session.courtship_pending_choice_label = caster.character_id
        session.log.append("Song of Charm succeeds — choose the monsters' reaction (TCOTFD p.27).")
        return True

    session.log.append(f"{spell_name} is not implemented.")
    return False


def resolve_aetheric_conversion_choice(
    engine: RandomDungeonEngine,
    session: SessionState,
    choice: str | None,
    *,
    show_rolls: bool,
) -> bool:
    member = next(
        (item for item in session.party if item.character_id == session.courtship_pending_choice_label),
        None,
    )
    session.courtship_pending_choice = None
    session.courtship_pending_choice_label = None
    if member is None:
        session.log.append("No caster is waiting on Ætheric Conversion (TCOTFD).")
        return False
    tile = engine._current_tile(session)
    ok = cast_blossoms_spell(
        engine,
        session,
        member,
        "Ætheric Conversion",
        tile,
        courtship_choice=choice,
        show_rolls=show_rolls,
        from_scroll=True,
    )
    if ok:
        finish_blossoms_scroll(session, member, session.courtship_blossoms_scroll_pending)
    return ok


def resolve_song_of_charm_choice(session: SessionState, choice: str | None) -> bool:
    caster_id = session.courtship_pending_choice_label
    session.courtship_pending_choice = None
    session.courtship_pending_choice_label = None
    if choice not in SONG_OF_CHARM_REACTIONS:
        session.log.append("Choose a reaction outcome for Song of Charm (TCOTFD p.27).")
        session.courtship_pending_choice = "song_of_charm"
        session.courtship_pending_choice_label = caster_id
        return False
    session.reaction_key = choice
    session.reaction_checked = True
    session.reaction_pending = False
    session.log.append(f"Song of Charm sets the foes' reaction to {choice.replace('_', ' ')} (TCOTFD p.27).")
    caster = next((member for member in session.party if member.character_id == caster_id), None)
    if caster is not None:
        finish_blossoms_scroll(session, caster, session.courtship_blossoms_scroll_pending)
    return True


def finish_blossoms_scroll(
    session: SessionState,
    caster: PartyMemberState,
    scroll_item: str | None = None,
) -> None:
    pending = scroll_item or session.courtship_blossoms_scroll_pending
    if pending and pending in caster.inventory:
        caster.inventory = [item for item in caster.inventory if item != pending]
        session.log.append("The scroll is destroyed.")
    session.courtship_blossoms_scroll_pending = None


def try_cast_blossoms_scroll(
    engine: RandomDungeonEngine,
    session: SessionState,
    caster: PartyMemberState,
    spell_name: str,
    scroll_item: str,
    *,
    target_character_id: str | None = None,
    courtship_choice: str | None = None,
    show_rolls: bool = True,
) -> bool:
    """Handle Blossoms scroll casting. Returns True if handled (including pending choice)."""
    if not is_blossoms_spell(spell_name):
        return False
    if session.mode == "complete":
        session.log.append("This adventure is complete.")
        return True
    tile = engine._current_tile(session)
    if tile is None:
        session.log.append("No map tile for the Blossoms scroll.")
        return True
    from .courtship_lex import apply_lex_soul_tax_if_needed

    if not apply_lex_soul_tax_if_needed(session, caster, scroll_item, show_rolls=show_rolls):
        return True
    pending_before = session.courtship_pending_choice
    ok = cast_blossoms_spell(
        engine,
        session,
        caster,
        spell_name,
        tile,
        target_character_id=target_character_id,
        courtship_choice=courtship_choice,
        show_rolls=show_rolls,
        from_scroll=True,
    )
    if not ok:
        return True
    if session.courtship_pending_choice != pending_before:
        session.courtship_blossoms_scroll_pending = scroll_item
        return True
    finish_blossoms_scroll(session, caster, scroll_item)
    return True


def try_resolve_blossoms_spell_in_combat(
    spell_key: str,
    spell_name: str,
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    session: SessionState | None = None,
    show_rolls: bool = True,
) -> SpellOutcome | None:
    """Hook for resolve_spell_cast — Song of Charm is handled via scroll path; others return None."""
    return None
