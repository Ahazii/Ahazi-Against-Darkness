"""Blossoms magic items (TCOTFD p.69) — use effects and passives."""

from __future__ import annotations

import random
import re
from typing import TYPE_CHECKING, Any

from ..schemas import PartyMemberState, SessionState, TileState
from .courtship_ingredients import is_demesne_ingredient_item
from .dice import roll_d3, roll_d6, roll_exploding_for_level, roll_formula

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine

MAGIC_SHOVEL = "Magic Shovel"
TALISMAN_OF_IMPOTENCE = "Talisman of Impotence"
KARMIC_CALCINATOR = "Karmic Calcinator"
ENCHANTED_ALEMBIC = "Enchanted Alembic"
MORTAR_OF_SOULS = "Mortar of Souls"
FOLDABLE_PAVILION = "Foldable Pavilion"

BLOSSOMS_MAGIC_ITEMS: frozenset[str] = frozenset(
    {
        MAGIC_SHOVEL,
        TALISMAN_OF_IMPOTENCE,
        KARMIC_CALCINATOR,
        ENCHANTED_ALEMBIC,
        MORTAR_OF_SOULS,
        FOLDABLE_PAVILION,
    }
)

from .courtship_blossoms_spells import BLOSSOMS_SPELLS, cast_bountiful_harvest as _cast_bountiful_harvest_spell

COMMON_INGREDIENT_OPTIONS: tuple[str, ...] = (
    "Common ingredient (Herbs)",
    "Common ingredient (Minerals)",
    "Common ingredient (Resins)",
    "Common ingredient (Bark)",
    "Common ingredient (Roots)",
    "Common ingredient (Fungi)",
)

UNCOMMON_INGREDIENT_OPTIONS: tuple[str, ...] = (
    "Uncommon ingredient (Nectar)",
    "Uncommon ingredient (Pollen)",
    "Uncommon ingredient (Sap)",
)

_ALEMBIC_CHARGE_RE = re.compile(r"^Enchanted Alembic \((\d+) charges?\)$", re.IGNORECASE)


def is_blossoms_magic_item(item: str) -> bool:
    base = item.split(" (")[0].strip()
    return base in BLOSSOMS_MAGIC_ITEMS


def prepare_blossoms_magic_item(item: str, *, alembic_charges: int | None = None) -> str:
    """Normalize inventory label when granting Blossoms magic items."""
    base = item.split(" (")[0].strip()
    if base == ENCHANTED_ALEMBIC and not _ALEMBIC_CHARGE_RE.match(item.strip()):
        charges = alembic_charges if alembic_charges is not None else roll_d6()
        return f"{ENCHANTED_ALEMBIC} ({charges} charges)"
    return item


def parse_alembic_charges(item: str) -> int | None:
    match = _ALEMBIC_CHARGE_RE.match(item.strip())
    if not match:
        return None
    return int(match.group(1))


def update_alembic_charges(item: str, charges: int) -> str | None:
    if charges <= 0:
        return None
    charge_word = "charge" if charges == 1 else "charges"
    return f"{ENCHANTED_ALEMBIC} ({charges} {charge_word})"


def member_carries_item(member: PartyMemberState, base_name: str) -> bool:
    target = base_name.lower()
    return any(item.split(" (")[0].strip().lower() == target for item in member.inventory)


def shovel_carrier(session: SessionState) -> PartyMemberState | None:
    for member in session.party:
        if member.current_life > 0 and member_carries_item(member, MAGIC_SHOVEL):
            return member
    return None


def member_wears_talisman(member: PartyMemberState) -> bool:
    return member_carries_item(member, TALISMAN_OF_IMPOTENCE)


def talisman_mesmerize_bonus(member: PartyMemberState) -> int:
    return 2 if member_wears_talisman(member) else 0


def talisman_blocks_giving(member: PartyMemberState) -> bool:
    return member_wears_talisman(member)


def karmic_calcinator_active(member: PartyMemberState) -> bool:
    return member_carries_item(member, KARMIC_CALCINATOR)


def party_has_karmic_calcinator(party: list[PartyMemberState]) -> PartyMemberState | None:
    for member in party:
        if karmic_calcinator_active(member):
            return member
    return None


def roll_karmic_calcinator_depletion(*, show_rolls: bool, log: list[str]) -> bool:
    """Roll d6 on Karmic Calcinator use; returns True if still usable."""
    roll = roll_d6()
    if show_rolls:
        log.append(f"Karmic Calcinator d6 = {roll} (1 depletes forever, TCOTFD p.69).")
    if roll == 1:
        log.append("The Karmic Calcinator's magic is spent forever (TCOTFD p.69).")
        return False
    return True


def _consume_soul_cube(member: PartyMemberState, log: list[str]) -> bool:
    index = next((i for i, item in enumerate(member.inventory) if "soul cube" in item.lower()), None)
    if index is None:
        log.append("Need a soul cube (TCOTFD).")
        return False
    member.inventory.pop(index)
    log.append(f"{member.name} spends a soul cube (TCOTFD).")
    return True


def cast_bountiful_harvest(
    engine: RandomDungeonEngine,
    session: SessionState,
    member: PartyMemberState,
    tile: TileState | None,
    *,
    show_rolls: bool,
    consume_alembic_charge: bool = False,
    alembic_item: str | None = None,
) -> bool:
    if consume_alembic_charge and alembic_item:
        charges = parse_alembic_charges(alembic_item)
        if charges is None or charges <= 0:
            session.log.append(f"{member.name} has no charges on the Enchanted Alembic.")
            return False
        updated = update_alembic_charges(alembic_item, charges - 1)
        member.inventory = [
            updated if item == alembic_item and updated else item
            for item in member.inventory
            if item != alembic_item or updated
        ]
        if updated is None:
            member.inventory = [item for item in member.inventory if item != alembic_item]
            session.log.append("The Enchanted Alembic is spent (TCOTFD p.69).")
            return False
        session.log.append(f"The Enchanted Alembic now has {parse_alembic_charges(updated)} charge(s).")
    if tile is None:
        session.log.append("Bountiful Harvest needs a map location (TCOTFD p.27).")
        return False
    return _cast_bountiful_harvest_spell(engine, session, member, tile, show_rolls=show_rolls)


def recharge_enchanted_alembic(
    session: SessionState,
    member: PartyMemberState,
    item: str,
    *,
    show_rolls: bool,
) -> bool:
    charges = parse_alembic_charges(item)
    if charges is not None and charges > 0:
        session.log.append("The Enchanted Alembic still has charges (TCOTFD p.69).")
        return False
    if not member_carries_item(member, ENCHANTED_ALEMBIC):
        session.log.append(f"{member.name} does not carry the Enchanted Alembic.")
        return False
    if not _consume_soul_cube(member, session.log):
        return False
    new_charges = roll_d6()
    updated = update_alembic_charges(ENCHANTED_ALEMBIC, new_charges)
    replaced = False
    new_inventory: list[str] = []
    for old in member.inventory:
        if not replaced and old.split(" (")[0].strip() == ENCHANTED_ALEMBIC:
            if updated:
                new_inventory.append(updated)
            replaced = True
        else:
            new_inventory.append(old)
    if not replaced and updated:
        new_inventory.append(updated)
    member.inventory = new_inventory
    session.log.append(f"The Enchanted Alembic is recharged with {new_charges} charge(s) (TCOTFD p.69).")
    return True


def cast_mortar_of_souls(
    engine: RandomDungeonEngine,
    session: SessionState,
    member: PartyMemberState,
    spell_name: str,
    tile: TileState | None,
    *,
    show_rolls: bool,
) -> bool:
    if not member_carries_item(member, MORTAR_OF_SOULS):
        session.log.append(f"{member.name} does not carry the Mortar of Souls.")
        return False
    if spell_name not in BLOSSOMS_SPELLS:
        session.log.append("The Mortar of Souls can only cast Blossoms spells (TCOTFD p.69).")
        return False
    if not _consume_soul_cube(member, session.log):
        return False
    roll = roll_d6()
    if show_rolls:
        session.log.append(f"Mortar of Souls d6 = {roll} (1 depletes forever, TCOTFD p.69).")
    if roll == 1:
        member.inventory = [
            item for item in member.inventory if item.split(" (")[0].strip() != MORTAR_OF_SOULS
        ]
        session.log.append(f"{member.name}'s Mortar of Souls is spent forever (TCOTFD p.69).")
        return False
    from .courtship_blossoms_spells import cast_blossoms_spell

    return cast_blossoms_spell(
        engine,
        session,
        member,
        spell_name,
        tile,
        show_rolls=show_rolls,
        from_scroll=True,
    )


def apply_pavilion_rest(
    session: SessionState,
    member: PartyMemberState,
    *,
    show_rolls: bool,
    outdoor: bool = True,
) -> bool:
    if not member_carries_item(member, FOLDABLE_PAVILION):
        session.log.append(f"{member.name} does not carry the Foldable Pavilion.")
        return False
    if session.courtship_pavilion_rest_used:
        session.log.append("The Foldable Pavilion has already been used for rest this adventure (TCOTFD p.69).")
        return False
    if session.mode != "exploration":
        session.log.append("Deploy the Foldable Pavilion during exploration (TCOTFD p.69).")
        return False
    if not outdoor:
        session.log.append("The Foldable Pavilion can only be used outdoors (TCOTFD p.69).")
        return False
    session.courtship_pavilion_rest_used = True
    if member.current_life > 0 and member.current_life < member.max_life:
        member.current_life += 1
        session.log.append(f"{member.name} heals 1 Life inside the pavilion ({member.current_life}/{member.max_life}, TCOTFD p.69).")
    from .rest import recover_ability

    restored = recover_ability(session, member)
    if restored:
        session.log.append(restored)
    else:
        session.log.append(f"{member.name} has no expended spell to rememorize (TCOTFD p.69).")
    session.log.append("The Foldable Pavilion grants shelter from the elements (TCOTFD p.69).")
    return True


def bury_shovel_stash(session: SessionState, member: PartyMemberState, *, show_rolls: bool) -> bool:
    if not member_carries_item(member, MAGIC_SHOVEL):
        session.log.append(f"{member.name} needs the Magic Shovel to bury a stash (TCOTFD p.69).")
        return False
    if session.courtship_buried_stash_items:
        session.log.append("There is already a buried stash in this Demesne visit (TCOTFD p.69).")
        return False
    to_bury = [item for item in member.inventory if is_demesne_ingredient_item(item) or "gp)" in item.lower()]
    if not to_bury:
        session.log.append("Nothing suitable to bury — carry ingredients or valued gems (TCOTFD p.69).")
        return False
    for item in to_bury:
        member.inventory.remove(item)
    session.courtship_buried_stash_region = session.courtship_demesne_region
    session.courtship_buried_stash_items = list(to_bury)
    session.log.append(
        f"{member.name} buries {len(to_bury)} item(s) with the Magic Shovel in "
        f"{session.courtship_demesne_region or 'the Demesne'} (TCOTFD p.69)."
    )
    return True


def retrieve_shovel_stash(session: SessionState, member: PartyMemberState, *, show_rolls: bool) -> bool:
    if not session.courtship_buried_stash_items:
        session.log.append("No buried stash is recorded here (TCOTFD p.69).")
        return False
    if session.courtship_buried_stash_region != session.courtship_demesne_region:
        session.log.append("Return to the region where the stash was buried (TCOTFD p.69).")
        return False
    roll = roll_d6()
    if show_rolls:
        session.log.append(f"Buried stash d6 = {roll} (1 = looted, TCOTFD p.69).")
    items = list(session.courtship_buried_stash_items)
    session.courtship_buried_stash_items = []
    session.courtship_buried_stash_region = None
    if roll == 1:
        session.log.append("The buried stash was found and looted (TCOTFD p.69).")
        return True
    spoiled = [item for item in items if is_demesne_ingredient_item(item) and roll_d6() <= 3]
    recovered = [item for item in items if item not in spoiled]
    for item in recovered:
        member.inventory.append(item)
    if spoiled:
        session.log.append(
            f"Perishables spoiled: {', '.join(spoiled)}. Recovered: {', '.join(recovered) or 'nothing'} (TCOTFD p.69)."
        )
    else:
        session.log.append(f"{member.name} recovers the buried stash ({len(recovered)} item(s), TCOTFD p.69).")
    return True


def offer_shovel_substitute(session: SessionState, harvested_item: str, *, tier: str) -> None:
    if shovel_carrier(session) is None:
        return
    session.courtship_pending_choice = "shovel_substitute"
    session.courtship_pending_choice_label = harvested_item
    session.courtship_shovel_substitute_tier = tier
    session.log.append(
        "Magic Shovel — choose a substitute ingredient from the same table (TCOTFD p.69)."
    )


def resolve_shovel_substitute(
    session: SessionState,
    member: PartyMemberState,
    choice: str | None,
) -> bool:
    old_item = session.courtship_pending_choice_label or ""
    tier = session.courtship_shovel_substitute_tier or "common"
    session.courtship_pending_choice = None
    session.courtship_pending_choice_label = None
    session.courtship_shovel_substitute_tier = None
    options = COMMON_INGREDIENT_OPTIONS if tier == "common" else UNCOMMON_INGREDIENT_OPTIONS
    if choice not in options:
        session.log.append("Choose a substitute ingredient (Magic Shovel, TCOTFD p.69).")
        session.courtship_pending_choice = "shovel_substitute"
        session.courtship_pending_choice_label = old_item
        session.courtship_shovel_substitute_tier = tier
        return False
    harvester = next((item for item in session.party if old_item in item.inventory), member)
    if old_item in harvester.inventory:
        harvester.inventory.remove(old_item)
    harvester.inventory.append(choice)
    session.log.append(
        f"{harvester.name} substitutes {choice} for the harvested ingredient (Magic Shovel, TCOTFD p.69)."
    )
    return True


def apply_satyr_talisman_wounds(
    session: SessionState,
    party: list[PartyMemberState],
    *,
    show_rolls: bool,
) -> list[str]:
    log: list[str] = []
    for member in party:
        if member.current_life <= 0:
            continue
        if member.class_id.lower() != "satyr":
            continue
        if not member_wears_talisman(member):
            continue
        damage = roll_d6()
        member.current_life = max(0, member.current_life - damage)
        if show_rolls:
            log.append(
                f"{member.name} suffers {damage} Life from the Talisman of Impotence (satyr, TCOTFD p.69)."
            )
    return log


def use_blossoms_item(
    engine: RandomDungeonEngine,
    session: SessionState,
    member: PartyMemberState,
    item_name: str,
    mode: str | None,
    *,
    show_rolls: bool,
) -> bool:
    """Dispatch Blossoms magic item use (TCOTFD p.69)."""
    from .courtship_lex import apply_lex_soul_tax_if_needed

    base = item_name.split(" (")[0].strip()
    if base not in BLOSSOMS_MAGIC_ITEMS:
        session.log.append(f"{item_name} is not a Blossoms magic item (TCOTFD p.69).")
        return False
    if not member_carries_item(member, base):
        session.log.append(f"{member.name} does not carry {base}.")
        return False
    if base in {ENCHANTED_ALEMBIC, MORTAR_OF_SOULS} and not apply_lex_soul_tax_if_needed(
        session, member, item_name, show_rolls=show_rolls
    ):
        return False
    tile = engine._current_tile(session)
    outdoor = tile is None or tile.terrain == "outdoor"
    if base == ENCHANTED_ALEMBIC:
        if mode == "recharge":
            return recharge_enchanted_alembic(session, member, item_name, show_rolls=show_rolls)
        return cast_bountiful_harvest(
            engine,
            session,
            member,
            tile,
            show_rolls=show_rolls,
            consume_alembic_charge=True,
            alembic_item=item_name,
        )
    if base == MORTAR_OF_SOULS:
        if not mode or mode not in BLOSSOMS_SPELLS:
            session.log.append("Choose a Blossoms spell for the Mortar of Souls (TCOTFD p.69).")
            return False
        return cast_mortar_of_souls(engine, session, member, mode, tile, show_rolls=show_rolls)
    if base == FOLDABLE_PAVILION:
        return apply_pavilion_rest(session, member, show_rolls=show_rolls, outdoor=outdoor)
    if base == MAGIC_SHOVEL:
        if mode == "retrieve":
            return retrieve_shovel_stash(session, member, show_rolls=show_rolls)
        if mode == "bury":
            return bury_shovel_stash(session, member, show_rolls=show_rolls)
        session.log.append("Choose bury or retrieve stash for the Magic Shovel (TCOTFD p.69).")
        return False
    if base == KARMIC_CALCINATOR:
        session.log.append(
            "The Karmic Calcinator doubles brewed potion duration when the Apothecary brews (TCOTFD p.69)."
        )
        return True
    if base == TALISMAN_OF_IMPOTENCE:
        session.log.append(
            "The Talisman of Impotence is passive: +2 mesmerizing saves, blocks Giving, satyr d6 Life per encounter (TCOTFD p.69)."
        )
        return True
    return False


def blossoms_item_tooltip(item: str) -> str | None:
    base = item.split(" (")[0].strip()
    tips: dict[str, str] = {
        MAGIC_SHOVEL: "Substitute harvest ingredients; bury/recover stashes; magic light bludgeoning +1 Attack (TCOTFD p.69).",
        TALISMAN_OF_IMPOTENCE: "+2 mesmerizing saves; blocks Giving rolls; satyrs suffer d6 Life per encounter (TCOTFD p.69).",
        KARMIC_CALCINATOR: "Doubles brewed potion duration; d6 depletion on each use (TCOTFD p.69).",
        ENCHANTED_ALEMBIC: "Cast Bountiful Harvest as L5 wizard; recharge empty with a soul cube (TCOTFD p.69).",
        MORTAR_OF_SOULS: "Spend 1 soul cube to cast a Blossoms spell as L5 wizard; d6 depletion on 1 (TCOTFD p.69).",
        FOLDABLE_PAVILION: "Outdoor rest: +1 Life and rememorize 1 spell once per adventure (TCOTFD p.69).",
    }
    return tips.get(base)
