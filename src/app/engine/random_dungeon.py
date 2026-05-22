from __future__ import annotations

from dataclasses import dataclass
import random
from pathlib import Path
from uuid import uuid4

from ..db import now_utc
from ..rules.repository import RulesRepository
from ..schemas import (
    ActiveQuestState,
    EnemyState,
    ExitState,
    MapState,
    PartyMemberState,
    SessionState,
    TileDefinition,
    TileState,
)
from .combat import CombatContext, CombatRound, attack_hits, foe_display_labels, resolve_combat_round, resolve_flee, resolve_flee_strike, resolve_withdraw
from .death_recovery import (
    attempt_resurrection,
    deliver_carried_body_outside,
    drop_carried_body,
    start_carrying_body,
)
from .class_combat import save_modifier
from .consumables import is_holy_water, is_undead_foe, throw_holy_water
from .roster_sync import initial_xp_tally
from .weapons import _parse_weapon_item, infer_default_weapons, prune_weapon_defaults, select_melee_weapon, set_weapon_default
from .experience import (
    CLUES_FOR_SECRET_XP,
    MINOR_ENCOUNTERS_FOR_XP,
    advancement_succeeds,
    apply_final_boss_treasure_bonus,
    apply_level_up,
    assign_level_up_spell,
    advancement_roll_explain,
    campaign_mode_label,
    dungeon_has_final_boss,
    is_minor_encounter,
    level_up_gate_reason,
    major_foes_defeated,
    mark_final_boss_candidate,
    old_school_level_cost,
    old_school_xp_for_defeated,
    perform_advancement_roll,
    potion_in_inventory,
    potion_kind,
    tier_entry_blocked_reason,
    tier_entry_requirements,
    tier_for_level,
    usable_potions_in_inventory,
)
from .expert_skills import apply_expert_skill_learn, validate_expert_skill_choice
from .expert_skill_effects import (
    adjust_reaction_roll,
    adjust_search_roll,
    rearguard_has_danger_sense,
    reset_expert_encounter,
)
from .inventory import (
    can_add_item,
    bandages_in_inventory,
    can_use_bandage,
    distribute_gold_among,
    distribute_items_among,
    encumbrance_penalty,
    has_illusionary_servant,
    transfer_gold,
    transfer_inventory_item,
)
from .magic_weapons import resolve_treasure_item_list
from .rest import (
    apply_rest_recovery,
    consume_nail_bags,
    member_has_recoverable_ability,
    nailable_doors,
    pick_wandering_door,
    rest_eligibility,
    validate_rest_request,
    wandering_roll_triggers,
)
from .reactions import (
    build_reaction_outcome,
    bribe_requirements_met,
    flee_if_outnumbered,
    lookup_reaction_row,
    pay_bribe_cost,
    resolve_reaction_source,
)
from .quests import quest_from_row
from .class_abilities import (
    acrobat_distract,
    acrobat_evade,
    acrobat_leap_out_of_harm,
    acrobat_shift_position,
    acrobat_serpent_twist,
    apply_nourishing_meal,
    assassin_hide,
    attempt_gnome_gadget_door,
    attempt_gnome_trap_disarm,
    clear_assassin_mark,
    gnome_smokescreen,
    illusionist_distract,
    make_kill_callback,
    mushroom_spore_cloud,
    open_lever_door_with_gnome_gadget,
    paladin_heal,
    recover_acrobat_tricks_on_rest,
    reroll_failed_save_with_luck,
    spend_acrobat_trick,
    spend_gnome_gadgets,
    spend_luck_point,
    spend_panache_point,
    spend_paladin_prayer,
    spend_rage_use,
)
from .class_profiles import EXPLORATION_SPELLS, spell_commits_to_attack
from .scrolls import (
    barbarian_cannot_use_magic,
    barbarian_cannot_use_scrolls,
    find_scroll_item,
    is_scroll_item,
    scroll_casting_modifier,
    scroll_spell_name,
)
from .combat_modifiers import is_spellcaster, spellcasting_modifier
from .spells import (
    can_cast_spell,
    cast_sleep_effect,
    knows_spell,
    mark_spell_expended,
    normalize_spell_name,
    resolve_spell_cast,
    spellcasting_roll_vs_level,
)
from .dice import roll_2d6, roll_d6, roll_die, roll_exploding_d6, roll_exploding_for_level, roll_formula, roll_start_tile_key, roll_tile_key, tier_die_sides
from .dungeon_table_roller import DungeonTableRoller, attempt_open_door, door_opening_hint, resolve_gold_formula


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

    def create_session(
        self,
        session_id: str,
        party_id: str,
        party: list[PartyMemberState],
        *,
        xp_system: str = "classical",
        map_bounds_mode: str = "unlimited",
    ) -> SessionState:
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
            environment="dungeon",
            terrain=tile_def.terrain if tile_def else "indoor",
        )
        for index, member in enumerate(party, start=1):
            member.marching_order = index
            prune_weapon_defaults(member)
        timestamp = now_utc()
        valid_xp = {"classical", "slow_and_sure", "old_school", "slower_advancement"}
        chosen_xp = xp_system if xp_system in valid_xp else "classical"
        valid_bounds = {"unlimited", "paper"}
        chosen_bounds = map_bounds_mode if map_bounds_mode in valid_bounds else "unlimited"
        map_width = 20 if chosen_bounds == "paper" else 31
        map_height = 28 if chosen_bounds == "paper" else 31
        party_xp = [member.xp for member in party]
        log = [
            f"Entrance map element roll: d6 = {tile_key[1]} -> {tile_key}.",
            "Adventure begins at the dungeon entrance.",
            f"Campaign mode: {campaign_mode_label(chosen_xp)}.",
        ]
        if chosen_bounds == "paper":
            log.append(f"Paper map mode: placement limited to a {map_width}×{map_height} grid (p.149).")
        self._initialize_outside_entrance(entrance, log=log)
        return SessionState(
            id=session_id,
            party_id=party_id,
            adventure_id="random",
            adventure_type="random",
            mode="exploration",
            party=party,
            map_state=MapState(
                width=map_width,
                height=map_height,
                tiles=[entrance],
                current_tile_id=entrance.id,
            ),
            log=log,
            xp_system=chosen_xp,
            map_bounds_mode=chosen_bounds,
            environment="dungeon",
            old_school_xp_tally=initial_xp_tally(party_xp) if chosen_xp == "old_school" else 0,
            slower_xp_bank=initial_xp_tally(party_xp) if chosen_xp == "slower_advancement" else 0,
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
        search_choice: str | None = None,
        spell_name: str | None = None,
        pay_bribe: bool = False,
        subdual: bool = False,
        marching_order: int | None = None,
        alchemist_item: str | None = None,
        xp_spent: int | None = None,
        target_character_id: str | None = None,
        item_name: str | None = None,
        gold_amount: int | None = None,
        weapon_kind: str | None = None,
        attack_targets: dict[str, str] | None = None,
        nail_doors: bool = False,
        rest_choices: dict[str, str] | None = None,
        combat_abilities: dict[str, str] | None = None,
        guard_targets: dict[str, str] | None = None,
        gadget_points: int | None = None,
        use_luck_flee: bool = False,
        class_ability: str | None = None,
        nourishing_meal: bool = False,
        nourishing_meal_eaters: list[str] | None = None,
        foe_id: str | None = None,
        spell_target_mode: str | None = None,
        tier_training: str | None = None,
        use_xp_for_tier: bool = False,
        advancement_fork: str | None = None,
        expert_skill_id: str | None = None,
        expert_skill_target: str | None = None,
        reaction_adjust: int | None = None,
    ) -> SessionState:
        if session.mode == "complete":
            session.log.append("This adventure is complete.")
            return self._touch(session)

        self._resolve_stale_combat(session)

        if action == "explore":
            self._explore(session, exit_id, direction, show_rolls=show_rolls, explain_math=explain_math)
        elif action == "search":
            self._search(
                session,
                search_choice=search_choice,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif action == "start_combat":
            self._start_combat(session, show_rolls=show_rolls)
        elif action == "combat_round":
            self._combat_round(
                session,
                show_rolls=show_rolls,
                explain_math=explain_math,
                subdual=subdual,
                attack_targets=attack_targets,
                combat_abilities=combat_abilities,
                guard_targets=guard_targets,
            )
        elif action == "check_reaction":
            self._check_reaction(
                session,
                show_rolls=show_rolls,
                explain_math=explain_math,
                reaction_adjust=reaction_adjust,
            )
        elif action == "pay_bribe":
            self._pay_bribe(session, accept=pay_bribe, show_rolls=show_rolls)
        elif action == "cast_spell":
            self._cast_spell(
                session,
                character_id,
                spell_name,
                exit_id=exit_id,
                target_character_id=target_character_id,
                target_foe_id=foe_id,
                spell_target_mode=spell_target_mode,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif action == "burn_scroll":
            self._burn_scroll(
                session,
                character_id,
                spell_name,
                exit_id=exit_id,
                target_character_id=target_character_id,
                target_foe_id=foe_id,
                spell_target_mode=spell_target_mode,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif action == "copy_scroll":
            self._copy_scroll(session, character_id, spell_name)
        elif action == "spellcast_door":
            self._spellcast_door(session, exit_id, character_id, show_rolls=show_rolls, explain_math=explain_math)
        elif action == "spend_clues_on_door":
            self._spend_clues_on_door(session, exit_id, show_rolls=show_rolls)
        elif action == "flee":
            self._flee(
                session,
                show_rolls=show_rolls,
                explain_math=explain_math,
                use_luck_flee=use_luck_flee,
                character_id=character_id,
            )
        elif action == "withdraw":
            self._withdraw(session, exit_id, show_rolls=show_rolls, explain_math=explain_math)
        elif action == "rest":
            self._rest(
                session,
                nail_doors=nail_doors,
                rest_choices=rest_choices,
                show_rolls=show_rolls,
                nourishing_meal=nourishing_meal,
                nourishing_meal_eaters=nourishing_meal_eaters,
            )
        elif action == "open_door":
            self._open_door(session, exit_id, character_id, show_rolls=show_rolls, explain_math=explain_math)
        elif action == "resolve_trap":
            self._resolve_trap(session, show_rolls=show_rolls, explain_math=explain_math)
        elif action == "claim_treasure":
            self._claim_treasure(session)
        elif action == "set_marching_order":
            self._set_marching_order(session, character_id, marching_order)
        elif action == "xp_roll":
            self._xp_roll(
                session,
                character_id,
                show_rolls=show_rolls,
                explain_math=explain_math,
                new_spell=spell_name,
                advancement_fork=advancement_fork,
                expert_skill_id=expert_skill_id,
                expert_skill_target=expert_skill_target,
            )
        elif action == "buy_healing":
            self._buy_healing(session, character_id, show_rolls=show_rolls)
        elif action == "buy_alchemist":
            self._buy_alchemist(session, character_id, alchemist_item, show_rolls=show_rolls)
        elif action == "use_potion":
            self._use_potion(session, character_id, item_name, show_rolls=show_rolls)
        elif action == "use_holy_water":
            self._use_holy_water(
                session,
                character_id,
                item_name,
                target_enemy_id=(attack_targets or {}).get(character_id or "") if attack_targets else None,
                show_rolls=show_rolls,
            )
        elif action == "use_bandage":
            self._use_bandage(session, character_id, show_rolls=show_rolls)
        elif action == "accept_quest":
            self._accept_quest(session, show_rolls=show_rolls)
        elif action == "refuse_quest":
            self._refuse_quest(session)
        elif action == "claim_quest_reward":
            self._claim_quest_reward(session, show_rolls=show_rolls)
        elif action == "old_school_level_up":
            self._old_school_level_up(session, character_id, show_rolls=show_rolls, new_spell=spell_name)
        elif action == "pick_level_up_spell":
            self._pick_level_up_spell(session, character_id, spell_name)
        elif action == "slower_xp_spend":
            self._slower_xp_spend(
                session,
                character_id,
                xp_spent=xp_spent,
                show_rolls=show_rolls,
                explain_math=explain_math,
                new_spell=spell_name,
                advancement_fork=advancement_fork,
                expert_skill_id=expert_skill_id,
                expert_skill_target=expert_skill_target,
            )
        elif action == "enter_tier_training":
            self._enter_tier_training(
                session,
                character_id,
                tier=tier_training,
                use_xp=use_xp_for_tier,
                show_rolls=show_rolls,
            )
        elif action == "transfer_item":
            self._transfer_item(session, character_id, target_character_id, item_name)
        elif action == "transfer_gold":
            self._transfer_gold(session, character_id, target_character_id, gold_amount)
        elif action == "set_default_weapon":
            self._set_default_weapon(session, character_id, item_name, weapon_kind=weapon_kind)
        elif action == "swap_weapon":
            self._swap_weapon(session, character_id, item_name, show_rolls=show_rolls)
        elif action == "carry_body":
            self._carry_body(session, character_id, target_character_id)
        elif action == "drop_body":
            self._drop_body(session)
        elif action == "attempt_resurrection":
            self._attempt_resurrection(session, target_character_id or character_id, show_rolls=show_rolls)
        elif action == "use_class_ability":
            self._use_class_ability(
                session,
                character_id,
                class_ability,
                target_character_id=target_character_id,
                foe_id=foe_id,
                show_rolls=show_rolls,
                explain_math=explain_math,
                exit_id=exit_id,
                gadget_points=gadget_points,
            )
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

        if session.mode != "exploration":
            if not exit_state.dungeon_exit:
                session.log.append("Exploration is blocked until the current encounter is resolved.")
                return
            if any(enemy.life > 0 for enemy in current.enemies):
                self._flee(session, show_rolls=show_rolls, explain_math=explain_math)
                if session.mode == "combat":
                    session.log.append("You must break contact before leaving the dungeon.")
                    return

        if exit_state.status == "blocked":
            session.log.append(f"The {exit_state.direction} exit is blocked.")
            return

        if exit_state.dungeon_exit:
            exit_state.status = "open"
            if exit_state.kind == "door":
                exit_state.door_open = True
            delivered_body = bool(session.carried_body_id)
            if delivered_body:
                session.log.extend(
                    deliver_carried_body_outside(
                        session,
                        servant_owner_ids=self._servant_owner_ids(session),
                    )
                )
            fallen = self._fallen_in_dungeon(session)
            if fallen:
                self._retreat_from_dungeon(session, fallen, show_rolls=show_rolls)
            elif delivered_body:
                session.log.append("The party regroups at the entrance and may continue the adventure.")
            else:
                self._complete_dungeon(session)
            return

        if exit_state.kind == "door" and not exit_state.door_open:
            self._inherit_connection_from_reciprocal(session, current, exit_state)
        if (
            current.content_key == "entrance"
            and not exit_state.dungeon_exit
            and exit_state.kind == "door"
            and not exit_state.door_open
            and exit_state.destination_tile_id is None
        ):
            self._open_entrance_threshold(session, exit_state, show_rolls=show_rolls)
        if exit_state.kind == "door" and not exit_state.door_open:
            session.log.append("The door is closed. Open it before moving through.")
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
            self._persist_open_connection(session, current, exit_state)
            session.map_state.current_tile_id = existing.id
            self._refresh_tile_connections(session, existing)
            if existing.content_key == "entrance":
                self._initialize_outside_entrance(existing)
            if session.camped_outside and current.content_key == "entrance":
                session.camped_outside = False
                session.log.append("The party re-enters the dungeon.")
            session.log.append(f"The party moves {exit_state.direction} to {existing.title}.")
            self._maybe_wandering_on_backtrack(session, existing, show_rolls=show_rolls)
            if session.mode == "exploration" and any(enemy.life > 0 for enemy in existing.enemies):
                self._announce_encounter(session, existing)
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
        self._persist_open_connection(session, current, exit_state)
        session.map_state.current_tile_id = new_tile.id
        if session.camped_outside and current.content_key == "entrance":
            session.camped_outside = False
            session.log.append("The party re-enters the dungeon.")
        session.log.append(f"Entered {new_tile.title}: {new_tile.description}")
        self._prepare_tile_features(session, new_tile, show_rolls=show_rolls, explain_math=explain_math)
        if new_tile.enemies:
            self._announce_encounter(session, new_tile)

    def _search(
        self,
        session: SessionState,
        *,
        search_choice: str | None = None,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
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
        search_choice_key = None
        if search_choice == "clue":
            search_choice_key = "clue"
        elif search_choice in {"secret_door", "secret_passage"}:
            search_choice_key = "secret_door"
        effective_roll, search_notes = adjust_search_roll(
            session.party,
            effective_roll,
            choice=search_choice_key,
        )
        session.log.extend(search_notes)
        if show_rolls and search_notes:
            session.log.append(f"Adjusted search roll: {effective_roll}.")
        if explain_math:
            session.log.append(f"Search table: {self.table_roller.search_table_summary()}.")
        outcome = self.table_roller.lookup_search(effective_roll)
        if outcome.effect == "wandering_monsters":
            self._spawn_wandering_monsters(session, tile, show_rolls=show_rolls)
        elif outcome.effect == "nothing":
            session.log.append("The search finds nothing useful.")
        elif outcome.effect == "found_something":
            choice = search_choice or "hidden_treasure"
            self._apply_search_choice(
                session,
                tile,
                choice,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif outcome.effect == "clue":
            self._grant_clue(session, tile)
        else:
            self._grant_hidden_treasure(session, tile, show_rolls=show_rolls, explain_math=explain_math)

    def _apply_search_choice(
        self,
        session: SessionState,
        tile: TileState,
        choice: str,
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        labels = {
            "hidden_treasure": "hidden treasure",
            "secret_door": "a secret door",
            "secret_passage": "a secret passage",
            "clue": "1 Clue",
        }
        session.log.append(f"Search find: the party chooses {labels.get(choice, choice)}.")
        if choice == "hidden_treasure":
            self._grant_hidden_treasure(session, tile, show_rolls=show_rolls, explain_math=explain_math)
        elif choice == "secret_door":
            self._reveal_secret_door(session, tile, show_rolls=show_rolls, explain_math=explain_math)
        elif choice == "secret_passage":
            self._reveal_secret_passage(session, tile)
        elif choice == "clue":
            self._grant_clue(session, tile)
        else:
            self._grant_hidden_treasure(session, tile, show_rolls=show_rolls, explain_math=explain_math)

    def _spawn_wandering_monsters(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
        special_event: bool = False,
        combat_message: str | None = None,
        party_strikes_first: bool = False,
        foes_strike_first: bool = False,
    ) -> None:
        hcl = self._highest_character_level(session.party)
        wandering = self.table_roller.roll_wandering_monsters(special_event=special_event)
        if show_rolls:
            label = "Special event wandering" if special_event else "Wandering Monsters"
            session.log.append(f"{label} table: d6 = {wandering.roll} -> {wandering.enemy_category}.")
        foe = self._roll_wandering_enemies(session, wandering.enemy_category, hcl)
        if not foe:
            session.log.append("Wandering Monsters were heard but none appeared.")
            return
        tile.enemies.extend(foe)
        tile.initial_enemy_count = len(tile.enemies)
        foe_summary = self._format_living_foes(foe)
        if foe_summary:
            session.log.append(f"Wandering foes: {foe_summary}.")
        if tile.tile_type == "corridor":
            tile.wandering_ambush = True
        self._begin_combat(
            session,
            combat_message or "Wandering Monsters attack!",
            show_rolls=show_rolls,
            allow_final_boss_check=False,
            party_strikes_first=party_strikes_first,
            foes_strike_first=foes_strike_first,
            tile=tile,
        )

    def _roll_wandering_enemies(self, session: SessionState, category: str, hcl: int) -> list[EnemyState]:
        for _ in range(3):
            enemies = self._roll_enemy(session, category, hcl)
            if not enemies:
                return enemies
            if category == "boss" and any("dragon" in enemy.tags for enemy in enemies):
                continue
            return enemies
        return self._roll_enemy(session, "minions", hcl)

    def _maybe_wandering_on_backtrack(self, session: SessionState, tile: TileState, *, show_rolls: bool) -> None:
        if session.mode != "exploration":
            return
        roll = roll_d6()
        if show_rolls:
            session.log.append(f"Backtrack roll: d6 = {roll}.")
        if roll != 1:
            return
        self._spawn_wandering_monsters(session, tile, show_rolls=show_rolls)

    def _reveal_secret_door(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        used_directions = {exit_state.direction for exit_state in tile.exits}
        direction = next((item for item in DIRECTION_ORDER if item not in used_directions), None)
        if direction is None:
            direction = next((item for item in DIRECTION_ORDER if item != "south"), "north")
        secret_exit = self._new_exit(
            direction=direction,
            kind="door",
            width=width,
            height=height,
            status="open",
            label="Secret door",
        )
        secret_exit.door_open = True
        tile.exits.append(secret_exit)
        session.log.append(f"A secret door appears on the {direction} wall.")
        hcl = self._highest_character_level(session.party)
        peek_tile = self._generate_tile(
            session=session,
            origin=tile,
            origin_exit=secret_exit,
            hcl=hcl,
            show_rolls=show_rolls,
            explain_math=explain_math,
        )
        if peek_tile is None:
            tile.exits = [exit_state for exit_state in tile.exits if exit_state.id != secret_exit.id]
            session.log.append("There is no space to place the chamber behind the secret door.")
            return
        peek_tile.treasure_doubled = True
        secret_exit.destination_tile_id = peek_tile.id
        session.map_state.tiles.append(peek_tile)
        self._clip_origin_visible_for_neighbor(tile, peek_tile)
        self._set_reciprocal_exit(peek_tile, tile, secret_exit)
        session.log.append(
            f"Peeking through the secret door: {peek_tile.title} — {peek_tile.description}"
        )
        if peek_tile.enemies:
            peek_tile.surprise_party = True
            session.log.append("Foes wait inside; entering will surprise them.")
        safe_roll = roll_d6()
        if show_rolls:
            session.log.append(f"Secret door shortcut roll: d6 = {safe_roll}.")
        if safe_roll == 6:
            secret_exit.dungeon_exit = True
            session.log.append("This secret door is a safe shortcut out of the dungeon.")

    def _reveal_secret_passage(self, session: SessionState, tile: TileState, *, show_rolls: bool = True) -> None:
        if "Secret Passage" not in tile.objects:
            tile.objects.append("Secret Passage")
        if session.environment != "dungeon":
            session.log.append(
                f"The party is already exploring the {session.environment.replace('_', ' ')} "
                "beyond the secret passage."
            )
            return
        roll = roll_d6()
        new_environment = "caverns" if roll <= 3 else "fungal_grottoes"
        session.environment = new_environment
        tile.environment = new_environment
        label = "caverns" if new_environment == "caverns" else "fungal grottoes"
        if show_rolls:
            session.log.append(f"Secret passage roll: d6 = {roll}.")
        session.log.append(
            f"The party follows the secret passage into the {label}. "
            "Draw new map elements in a different color; trap, event, and treasure rolls "
            f"now use {label} tables (EE p.112–113)."
        )

    def _finalize_treasure_items(
        self,
        session: SessionState,
        items: list[str],
        *,
        show_rolls: bool,
    ) -> list[str]:
        resolved, log = resolve_treasure_item_list(items)
        if show_rolls and log:
            session.log.extend(log)
        return resolved

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
        tile.treasure_items = self._finalize_treasure_items(session, treasure.items, show_rolls=show_rolls)
        session.log.extend(treasure.log)
        if treasure.complication_effect == "alarm":
            tile.hidden_treasure_alarm_pending = True
            self._spawn_wandering_monsters(session, tile, show_rolls=show_rolls)
            session.log.append(
                "The alarm must be answered before the hidden treasure can be claimed."
            )
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
            self._announce_hidden_treasure_claimable(session, tile)
        else:
            self._announce_hidden_treasure_claimable(session, tile)

    def _announce_hidden_treasure_claimable(self, session: SessionState, tile: TileState) -> None:
        if tile.treasure_claimed or (not tile.treasure_gold and not tile.treasure_items):
            return
        if tile.trap_key and not tile.trap_resolved:
            session.log.append(
                f"Hidden treasure ({self._treasure_value_label(tile)}) is here; resolve the trap before claiming."
            )
            return
        if any(enemy.life > 0 for enemy in tile.enemies):
            return
        tile.hidden_treasure_alarm_pending = False
        session.log.append(
            f"The hidden treasure ({self._treasure_value_label(tile)}) can be claimed here. Use Claim Treasure."
        )

    def _treasure_value_label(self, tile: TileState) -> str:
        parts: list[str] = []
        if tile.treasure_gold:
            parts.append(f"{tile.treasure_gold}gp")
        parts.extend(tile.treasure_items)
        if parts:
            return ", ".join(parts)
        return tile.treasure_summary or "loot"

    def _format_living_foes(self, enemies: list[EnemyState]) -> str:
        living = [enemy for enemy in enemies if enemy.life > 0]
        if not living:
            return ""
        labels = foe_display_labels(living)
        return ", ".join(
            f"{labels[enemy.id]} (L{enemy.level}, {enemy.life}/{enemy.max_life} Life)" for enemy in living
        )

    def _begin_combat(
        self,
        session: SessionState,
        message: str,
        *,
        show_rolls: bool = True,
        allow_final_boss_check: bool = True,
        party_strikes_first: bool = False,
        foes_strike_first: bool = False,
        tile: TileState | None = None,
    ) -> None:
        tile = tile or self._current_tile(session)
        if not any(enemy.life > 0 for enemy in tile.enemies):
            session.log.append("No foes remain to fight.")
            return
        session.combat_round = 0
        reset_expert_encounter(session)
        session.missile_used_character_ids = []
        session.spell_used_character_ids = []
        session.wielded_melee_weapons = {}
        session.gladiator_counter_pending = {}
        session.gladiator_counter_used = []
        session.evasion_character_ids = []
        for member in session.party:
            if member.current_life <= 0:
                continue
            prune_weapon_defaults(member)
            weapon = select_melee_weapon(member)
            if weapon is not None:
                session.wielded_melee_weapons[member.character_id] = weapon.item
        session.mode = "combat"
        session.reaction_pending = True
        session.reaction_checked = False
        session.reaction_key = None
        session.party_attacked_immediately = False
        session.party_surprised = bool(tile.wandering_ambush or tile.surprise_party)
        if rearguard_has_danger_sense(session.party) and tile.wandering_ambush:
            session.party_surprised = False
            session.log.append("Danger Sense: the rearguard was not surprised.")
        if party_strikes_first:
            session.party_surprised = False
            session.party_attacked_immediately = True
        elif foes_strike_first:
            session.party_surprised = True
            session.foes_strike_first = True
        if session.party_surprised:
            session.log.append("The party is surprised!")
        tile.surprise_party = False
        session.reaction_bribe_gold = 0
        session.reaction_bribe_weapons = 0
        session.reaction_bribe_gold_per_foe = 0
        session.reaction_bribe_weapons_per_foe = 0
        session.reaction_bribe_foe_count = 0
        session.foe_flee_strike_pending = False
        session.log.append(message)
        foe_summary = self._format_living_foes(tile.enemies)
        if foe_summary:
            session.log.append(f"You face: {foe_summary}.")
        living_majors = [enemy for enemy in tile.enemies if enemy.life > 0 and enemy.category in {"weird", "boss"}]
        if living_majors:
            session.major_foes_encountered += 1
            if allow_final_boss_check and not dungeon_has_final_boss(session):
                boss_log, boss = mark_final_boss_candidate(
                    tile.enemies,
                    major_foes_encountered=session.major_foes_encountered,
                    show_rolls=show_rolls,
                )
                session.log.extend(boss_log)
                if boss is not None:
                    tile.final_boss_treasure = True
                    session.final_boss_designated = True
        session.log.append(
            "Choose: Check Reactions, or attack immediately (End Combat Round or cast an offensive spell)."
        )

    def _reactions_unresolved(self, session: SessionState) -> bool:
        return (
            session.mode == "combat"
            and session.combat_round == 0
            and session.reaction_pending
            and not session.reaction_checked
        )

    def _commit_immediate_attack(self, session: SessionState) -> None:
        if not self._reactions_unresolved(session):
            return
        session.reaction_checked = True
        session.reaction_pending = False
        session.reaction_key = "fight"
        session.foes_strike_first = False
        session.party_attacked_immediately = True
        session.log.append("The party attacks without waiting for a Reaction roll.")

    def _resolve_stale_combat(self, session: SessionState, *, log: bool = True) -> bool:
        if session.mode != "combat":
            return False
        tile = self._current_tile(session)
        if any(enemy.life > 0 for enemy in tile.enemies):
            return False
        self._clear_combat_statuses(session)
        session.combat_round = 0
        session.mode = "exploration"
        if log:
            session.log.append("No active foes remain; the encounter is over.")
        return True

    def _announce_encounter(self, session: SessionState, tile: TileState) -> None:
        if session.mode != "exploration":
            return
        if not any(enemy.life > 0 for enemy in tile.enemies):
            return
        foe_summary = self._format_living_foes(tile.enemies)
        if foe_summary:
            session.log.append(f"Foes are here: {foe_summary}. Start combat when ready.")
        else:
            session.log.append("Foes are here. Start combat when ready.")

    def _start_combat(
        self,
        session: SessionState,
        *,
        show_rolls: bool = True,
    ) -> None:
        if session.mode == "combat":
            session.log.append("Combat is already underway.")
            return
        tile = self._current_tile(session)
        if not any(enemy.life > 0 for enemy in tile.enemies):
            session.log.append("There are no foes to fight.")
            return
        self._begin_combat(session, "Combat begins.", tile=tile, show_rolls=show_rolls)

    def normalize_session(self, session: SessionState) -> tuple[SessionState, bool]:
        """Clear stale combat state before returning a session to the client."""
        changed = self._resolve_stale_combat(session, log=False)
        if self._initialize_outside_entrance(self._entrance_tile(session)):
            changed = True
        if self._resume_orphaned_encounter(session):
            changed = True
        if self._resync_session_tile_layouts(session):
            changed = True
        if changed:
            self._touch(session)
        return session, changed

    def _resync_session_tile_layouts(self, session: SessionState) -> bool:
        """Refresh map element walkable/shape/image metadata from current tile definitions."""
        if self.rules is None:
            return False
        changed = False
        for tile in session.map_state.tiles:
            if self._resync_tile_from_definition(tile):
                changed = True
        return changed

    def _resync_tile_from_definition(self, tile: TileState) -> bool:
        if tile.content_key == "entrance":
            return False
        tile_def = self.rules.tiles().get(tile.tile_key)
        if tile_def is None:
            return False
        rotation = tile.rotation or 0
        width = tile.footprint_width
        height = tile.footprint_height
        rotated_width, rotated_height = self._rotated_size(width, height, rotation)
        changed = False
        for attr, value in (
            ("editor_cell_size", tile_def.editor_cell_size),
            ("image_scale", tile_def.image_scale),
            ("image_offset_x", tile_def.image_offset_x),
            ("image_offset_y", tile_def.image_offset_y),
            ("footprint_width", tile_def.footprint_width),
            ("footprint_height", tile_def.footprint_height),
        ):
            if getattr(tile, attr) != value:
                setattr(tile, attr, value)
                changed = True
        if self._is_truncated_tile(tile):
            return changed
        expected_walkable = self._rotated_walkable(tile_def, rotation)
        expected_shapes = self._rotated_cell_shapes(tile_def, rotation)
        if tile.walkable != expected_walkable:
            tile.walkable = expected_walkable
            changed = True
        if tile.cell_shapes != expected_shapes:
            tile.cell_shapes = expected_shapes
            changed = True
        expected_visible = self._visible_rows(rotated_width, rotated_height)
        if tile.visible != expected_visible and len(tile.visible or []) == rotated_height:
            if all(len(row) == rotated_width for row in tile.visible or []):
                if all(char == "1" for row in tile.visible or [] for char in row):
                    tile.visible = expected_visible
                    changed = True
        return changed

    def _is_truncated_tile(self, tile: TileState) -> bool:
        return any("0" in row for row in tile.visible or [])

    def _resume_orphaned_encounter(self, session: SessionState) -> bool:
        if session.mode != "exploration":
            return False
        tile = self._current_tile(session)
        if not any(enemy.life > 0 for enemy in tile.enemies):
            return False
        return False

    def _end_peaceful_encounter(self, session: SessionState, tile: TileState) -> None:
        tile.enemies = []
        session.reaction_pending = False
        session.reaction_checked = False
        session.reaction_key = None
        session.reaction_bribe_gold = 0
        session.reaction_bribe_weapons = 0
        session.reaction_bribe_gold_per_foe = 0
        session.reaction_bribe_weapons_per_foe = 0
        session.reaction_bribe_foe_count = 0
        session.foes_strike_first = False
        session.foe_flee_strike_pending = False
        session.combat_round = 0
        session.mode = "exploration"
        session.log.append("The encounter ends peacefully.")
        self._record_peaceful_quest_progress(session)

    def _clear_combat_statuses(self, session: SessionState) -> None:
        session.reaction_pending = False
        session.reaction_checked = False
        session.reaction_key = None
        session.reaction_bribe_gold = 0
        session.reaction_bribe_weapons = 0
        session.reaction_bribe_gold_per_foe = 0
        session.reaction_bribe_weapons_per_foe = 0
        session.reaction_bribe_foe_count = 0
        session.foes_strike_first = False
        session.party_surprised = False
        session.party_attacked_immediately = False
        session.foe_flee_strike_pending = False
        session.missile_used_character_ids = []
        session.spell_used_character_ids = []
        session.summoned_beast_life = 0
        session.summoned_beast_owner_id = None
        self._end_bear_form(session)
        session.bear_form_owner_id = None
        session.bear_form_start_life = 0
        session.bear_form_pre_life = 0
        session.subdual_penalty_ignored = False
        session.illusionary_fog_active = False
        session.illusionary_servant_active = False
        session.illusionary_servant_owner_id = None
        session.wielded_melee_weapons = {}
        session.gladiator_counter_pending = {}
        session.gladiator_counter_used = []
        session.evasion_character_ids = []
        combat_statuses = {
            "protection",
            "barkskin",
            "illusionary armor",
            "bear form",
            "illusionary sword",
            "specter swarm",
            "mirror image",
        }
        for member in session.party:
            member.statuses = [
                status
                for status in member.statuses
                if status.split("(")[0].strip().lower() not in combat_statuses
                and not status.lower().startswith("mirror image")
                and not status.lower().startswith("poisoned")
            ]

    def _check_reaction(
        self,
        session: SessionState,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
        reaction_adjust: int | None = None,
    ) -> None:
        if session.mode != "combat":
            session.log.append("There are no foes to check.")
            return
        tile = self._current_tile(session)
        living_enemies = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living_enemies:
            session.log.append("There are no active foes.")
            return
        if session.reaction_checked:
            session.log.append("Reactions were already checked this encounter.")
            return
        if any("final_boss" in enemy.tags for enemy in living_enemies):
            session.reaction_checked = True
            session.reaction_key = "fight_to_death"
            session.reaction_pending = False
            session.log.append("The Final Boss fights to the death!")
            return

        reaction_tables = self.rules.monsters().get("reaction_tables", {})
        if not isinstance(reaction_tables, dict):
            reaction_tables = {}
        source = resolve_reaction_source(living_enemies, reaction_tables)
        roll = roll_d6()
        adjust = max(-1, min(1, int(reaction_adjust or 0)))
        roll, negotiator_log = adjust_reaction_roll(session.party, roll, adjust)
        session.log.extend(negotiator_log)
        if source.inline_rows:
            row = lookup_reaction_row(source.inline_rows, roll)
            table_label = f"{source.label} reaction table"
        else:
            row = self.table_roller.roll_reaction(source.table_name or table_name, roll)
            table_label = source.table_name or table_name
        if row is None:
            row = self.table_roller.roll_reaction("default_reaction_table", roll)
            table_label = "default_reaction_table"
        if row is None:
            row = {"key": "fight", "result": "The foes attack!", "foes_first": True}

        if show_rolls:
            session.log.append(f"Reaction roll: d6 = {roll} on {table_label}.")
        if explain_math:
            session.log.append("Reaction lookup uses monster bestiary tables when available, otherwise dungeon_tables.json.")

        hcl = self._highest_character_level(session.party)
        foe_count = len(living_enemies)
        outcome = build_reaction_outcome(row, hcl=hcl, foe_count=foe_count)
        session.reaction_checked = True
        session.reaction_key = outcome.key
        session.reaction_bribe_gold = outcome.bribe_gold
        session.reaction_bribe_weapons = outcome.bribe_weapons
        session.reaction_bribe_gold_per_foe = outcome.bribe_gold_per_foe
        session.reaction_bribe_weapons_per_foe = outcome.bribe_weapons_per_foe
        session.reaction_bribe_foe_count = foe_count
        session.log.append(outcome.result)

        if outcome.key == "flee_if_outnumbered":
            if flee_if_outnumbered(living_enemies, session.party):
                session.log.append("The foes are outnumbered and flee.")
                session.reaction_pending = False
                self._resolve_foe_flee_strike(
                    session,
                    tile,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                )
            else:
                session.log.append("The foes fight!")
                session.foes_strike_first = True
                session.reaction_pending = False
            return

        if outcome.key == "flee":
            session.reaction_pending = False
            self._resolve_foe_flee_strike(
                session,
                tile,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
            return

        if outcome.key in {"peaceful", "ignore", "offer_food"}:
            if outcome.key == "offer_food":
                for member in session.party:
                    if 0 < member.current_life < member.max_life:
                        member.current_life += 1
                        session.log.append(f"{member.name} eats and heals 1 Life.")
            self._end_peaceful_encounter(session, tile)
            return

        if outcome.key == "bribe":
            if outcome.bribe_weapons:
                session.log.append(
                    f"Bribe required: {outcome.bribe_gold}gp or {outcome.bribe_weapons} weapons "
                    f"({outcome.bribe_gold_per_foe}gp or {outcome.bribe_weapons_per_foe} weapon(s) per foe; mix allowed). "
                    "Pay bribe or fight."
                )
            else:
                session.log.append(f"Bribe required: {outcome.bribe_gold}gp total. Pay bribe or fight.")
            return

        if outcome.key == "puzzle":
            solver = next(
                (member for member in sorted(session.party, key=lambda item: item.marching_order) if member.current_life > 0),
                None,
            )
            puzzle_level = max(enemy.level for enemy in living_enemies)
            if solver is None:
                session.log.append("No hero can attempt the puzzle; the foes attack first!")
                session.foes_strike_first = True
                session.reaction_pending = False
                return
            total, rolls = roll_exploding_for_level(solver.level)
            modifier = save_modifier(solver)
            if solver.class_id.lower() in {"wizard", "elf", "illusionist", "druid"}:
                modifier += solver.level
            final_total = total + modifier
            if show_rolls:
                session.log.append(
                    f"Puzzle Save: {solver.name} rolls {' + '.join(str(value) for value in rolls)} "
                    f"+ {modifier} = {final_total} vs L{puzzle_level}."
                )
            if final_total >= puzzle_level:
                session.log.append("The puzzle is solved; the foes let you pass.")
                session.pending_save_reroll = None
                self._end_peaceful_encounter(session, tile)
                return
            session.pending_save_reroll = {
                "character_id": solver.character_id,
                "context": "puzzle",
                "level": puzzle_level,
            }
            session.log.append("The puzzle fails; the foes attack first!")
            session.foes_strike_first = True
            session.reaction_pending = False
            return

        session.foes_strike_first = outcome.foes_first or outcome.key in {"fight", "fight_to_death"}
        session.reaction_pending = False

    def _pay_bribe(self, session: SessionState, *, accept: bool, show_rolls: bool = True) -> None:
        if session.reaction_key != "bribe":
            session.log.append("No bribe is outstanding.")
            return
        tile = self._current_tile(session)
        if not accept:
            session.log.append("You refuse to pay; the foes attack!")
            session.foes_strike_first = True
            session.reaction_pending = False
            return

        foe_count = session.reaction_bribe_foe_count or len([enemy for enemy in tile.enemies if enemy.life > 0])
        gold_per_foe = session.reaction_bribe_gold_per_foe
        weapons_per_foe = session.reaction_bribe_weapons_per_foe
        if gold_per_foe <= 0 and session.reaction_bribe_gold > 0 and foe_count > 0:
            gold_per_foe = session.reaction_bribe_gold // foe_count
        if weapons_per_foe <= 0 and session.reaction_bribe_weapons > 0 and foe_count > 0:
            weapons_per_foe = session.reaction_bribe_weapons // foe_count

        if not bribe_requirements_met(
            session.party,
            foe_count=foe_count,
            gold_per_foe=gold_per_foe,
            weapons_per_foe=weapons_per_foe,
        ):
            if weapons_per_foe > 0:
                session.log.append(
                    f"You cannot afford the bribe ({session.reaction_bribe_gold}gp or "
                    f"{session.reaction_bribe_weapons} weapons, mix allowed). The foes attack!"
                )
            else:
                session.log.append(
                    f"You need {session.reaction_bribe_gold}gp but only have "
                    f"{sum(member.gold for member in session.party)}gp. The foes attack!"
                )
            session.foes_strike_first = True
            session.reaction_pending = False
            return

        gold_paid, weapons_paid, payment_log = pay_bribe_cost(
            session.party,
            foe_count=foe_count,
            gold_per_foe=gold_per_foe,
            weapons_per_foe=weapons_per_foe,
        )
        session.log.extend(payment_log)
        if show_rolls:
            parts = []
            if gold_paid:
                parts.append(f"{gold_paid}gp")
            if weapons_paid:
                parts.append(f"{weapons_paid} weapon(s)")
            summary = " and ".join(parts) if parts else "nothing"
            session.log.append(f"The party pays {summary}.")
        self._end_peaceful_encounter(session, tile)

    def _cast_spell(
        self,
        session: SessionState,
        character_id: str | None,
        spell_name: str | None,
        *,
        exit_id: str | None = None,
        target_character_id: str | None = None,
        target_foe_id: str | None = None,
        spell_target_mode: str | None = None,
        from_scroll: bool = False,
        scroll_item: str | None = None,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if not spell_name:
            session.log.append("Choose a spell to cast.")
            return
        tile = self._current_tile(session)
        caster = next((member for member in session.party if member.character_id == character_id), None)
        if caster is None:
            caster = next(
                (member for member in sorted(session.party, key=lambda item: item.marching_order) if member.current_life > 0),
                None,
            )
        if caster is None or caster.current_life <= 0:
            session.log.append("That hero cannot cast.")
            return
        if barbarian_cannot_use_scrolls(caster.class_id) and from_scroll:
            session.log.append("Barbarians cannot use scrolls.")
            return

        spell_key = normalize_spell_name(spell_name)
        if not from_scroll:
            if not knows_spell(caster, spell_name):
                session.log.append(f"{caster.name} does not know {spell_name}.")
                return
            if not can_cast_spell(
                caster,
                spell_name,
                expended_spells=session.expended_spells.get(caster.character_id, []),
                healing_prayer_uses=session.healing_prayer_uses.get(caster.character_id, 0),
            ):
                session.log.append(f"{caster.name} cannot cast {spell_name} again this adventure.")
                return
        elif scroll_item and scroll_item not in caster.inventory:
            session.log.append(f"{caster.name} does not have that scroll.")
            return

        in_combat = session.mode == "combat"
        no_foe_ok = spell_key in EXPLORATION_SPELLS or from_scroll
        if in_combat and not from_scroll:
            if caster.character_id in session.spell_used_character_ids:
                session.log.append(f"{caster.name} has already cast a spell this combat round.")
                return
        if in_combat and not no_foe_ok and not any(enemy.life > 0 for enemy in tile.enemies):
            session.log.append("There are no foes to target.")
            return
        if in_combat and spell_commits_to_attack(spell_key):
            self._commit_immediate_attack(session)
        if not in_combat:
            exit_state = next((item for item in tile.exits if item.id == exit_id), None) if exit_id else None
            door_type = exit_state.door_type if exit_state and exit_state.kind == "door" else None
            allowed = spell_key in EXPLORATION_SPELLS
            allowed = allowed or (spell_key in {"fireball", "lightning"} and door_type == "iron")
            allowed = allowed or (spell_key == "warp_wood" and door_type in {"locked", "lever", "unlocked", "trap_door"})
            if not allowed:
                session.log.append("Cast that spell during combat, or use exploration spells (Escape, Blessing, Healing prayer, Protection).")
                return

        exit_state = next((item for item in tile.exits if item.id == exit_id), None) if exit_id else None
        door_type = exit_state.door_type if exit_state and exit_state.kind == "door" else None
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {member.character_id for member in session.party if member.current_life > 0}
        outcome = resolve_spell_cast(
            spell_name,
            caster,
            session.party,
            tile.enemies,
            target_character_id=target_character_id,
            target_foe_id=target_foe_id,
            spell_target_mode=spell_target_mode,
            show_rolls=show_rolls,
            terrain=tile.terrain,
            door_type=door_type,
            from_scroll=from_scroll,
        )
        session.log.extend(outcome.log)
        if in_combat and not from_scroll:
            if caster.character_id not in session.spell_used_character_ids:
                session.spell_used_character_ids.append(caster.character_id)
        if explain_math:
            session.log.append("Spellcasting: exploding d6 + caster level vs. target level when required.")

        if from_scroll and scroll_item:
            caster.inventory = [item for item in caster.inventory if item != scroll_item]
            session.log.append(f"The scroll is destroyed.")
        elif outcome.spell_consumed and not from_scroll:
            expended = list(session.expended_spells.get(caster.character_id, []))
            prayer_uses = session.healing_prayer_uses.get(caster.character_id, 0)
            expended, prayer_uses, expend_log = mark_spell_expended(
                spell_name,
                expended_spells=expended,
                healing_prayer_uses=prayer_uses,
            )
            session.expended_spells[caster.character_id] = expended
            session.healing_prayer_uses[caster.character_id] = prayer_uses
            session.log.extend(expend_log)

        if outcome.teleport_to_entrance:
            entrance = self._entrance_tile(session)
            session.map_state.current_tile_id = entrance.id
            session.log.append("The party regroups at the adventure entrance.")
            if session.mode == "combat":
                session.mode = "exploration"
                session.combat_round = 0
                tile.enemies = []
        if outcome.summon_beast:
            session.summoned_beast_life = 5
            session.summoned_beast_owner_id = caster.character_id
            session.log.append("A summoned beast joins the fight (5 Life, 1 damage per round, L3).")
        if outcome.bear_form:
            session.bear_form_owner_id = caster.character_id
            session.bear_form_start_life = 8
            session.bear_form_pre_life = outcome.bear_form_pre_life
        if outcome.subdual_penalty_ignored:
            session.subdual_penalty_ignored = True
        if outcome.illusionary_fog:
            session.illusionary_fog_active = True
        if outcome.illusionary_servant:
            session.illusionary_servant_active = True
            session.illusionary_servant_owner_id = caster.character_id
            session.log.append(
                f"{caster.name}'s illusionary servant can carry an extra 200gp and weapon slots until slain or trapped."
            )
        if (
            outcome.curse_break_target_id
            and session.cursed_character_id == outcome.curse_break_target_id
        ):
            session.cursed_character_id = None
        if outcome.destroy_door and exit_state and exit_state.kind == "door":
            exit_state.door_open = True
            exit_state.status = "open"
            exit_state.door_destroyed = True
            self._sync_linked_door(session, tile, exit_state)
            session.log.append(f"The {exit_state.direction} door is destroyed and open.")
        if outcome.peaceful_bribe:
            self._record_peaceful_quest_progress(session)
            session.mode = "exploration"
            session.combat_round = 0
            tile.enemies = []

        if outcome.combat_over and session.mode == "combat":
            if spell_key == "sleep":
                self._record_peaceful_quest_progress(session)
            result = CombatRound(
                party=outcome.party,
                enemies=outcome.enemies,
                log=[],
                combat_over=True,
            )
            self._apply_combat_result(
                session,
                tile,
                result,
                show_rolls=show_rolls,
                active_enemy_ids=active_enemy_ids,
                standing_before=standing_before,
            )
            session.party = outcome.party
            tile.enemies = outcome.enemies
        else:
            session.party = outcome.party
            tile.enemies = outcome.enemies
            if session.mode == "combat":
                remaining = sum(1 for enemy in tile.enemies if enemy.life > 0)
                if remaining:
                    session.log.append(
                        f"{remaining} foe(s) remain after the spell — use Combat Round to continue "
                        "(opening missile volley still applies on the first round)."
                    )

    def _burn_scroll(
        self,
        session: SessionState,
        character_id: str | None,
        spell_name: str | None,
        *,
        exit_id: str | None = None,
        target_character_id: str | None = None,
        target_foe_id: str | None = None,
        spell_target_mode: str | None = None,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if session.mode == "complete":
            session.log.append("This adventure is complete.")
            return
        caster = next((member for member in session.party if member.character_id == character_id), None)
        if caster is None or caster.current_life <= 0:
            session.log.append("That hero cannot use a scroll.")
            return
        if barbarian_cannot_use_scrolls(caster.class_id):
            session.log.append("Barbarians cannot use scrolls.")
            return
        if not spell_name:
            session.log.append("Choose a scroll spell to cast.")
            return
        scroll_item = find_scroll_item(caster.inventory, spell_name)
        if scroll_item is None:
            session.log.append(f"{caster.name} has no scroll of {spell_name}.")
            return
        self._cast_spell(
            session,
            caster.character_id,
            spell_name,
            exit_id=exit_id,
            target_character_id=target_character_id,
            target_foe_id=target_foe_id,
            spell_target_mode=spell_target_mode,
            from_scroll=True,
            scroll_item=scroll_item,
            show_rolls=show_rolls,
            explain_math=explain_math,
        )

    def _copy_scroll(self, session: SessionState, character_id: str | None, spell_name: str | None) -> None:
        if session.mode != "exploration":
            session.log.append("Copy scrolls to a spellbook during exploration.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.class_id.lower() != "wizard":
            session.log.append("Only wizards can copy spells from scrolls.")
            return
        if not spell_name:
            session.log.append("Choose a scroll to copy.")
            return
        scroll_item = find_scroll_item(member.inventory, spell_name)
        if scroll_item is None:
            session.log.append(f"{member.name} does not have that scroll.")
            return
        if any(normalize_spell_name(item) == normalize_spell_name(spell_name) for item in member.spells):
            session.log.append(f"{spell_name} is already in {member.name}'s spellbook.")
            return
        member.spells.append(spell_name.strip())
        member.inventory = [item for item in member.inventory if item != scroll_item]
        session.log.append(f"{member.name} copies {spell_name} into the spellbook (scroll destroyed).")

    def _spellcast_door(
        self,
        session: SessionState,
        exit_id: str | None,
        character_id: str | None,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Work doors during exploration.")
            return
        tile = self._current_tile(session)
        exit_state = next((item for item in tile.exits if item.id == exit_id), None) if exit_id else None
        if exit_state is None or exit_state.kind != "door" or exit_state.door_open:
            session.log.append("Choose a closed door.")
            return
        if exit_state.door_type is None:
            outcome = self.table_roller.roll_door(self._highest_character_level(session.party))
            exit_state.door_type = outcome.door_type
            exit_state.door_level = outcome.door_level
            exit_state.door_result = outcome.summary
            exit_state.door_treasure_bonus = outcome.treasure_bonus
            session.log.append(f"Door: {outcome.summary}")
            hcl = self._highest_character_level(session.party)
            session.log.append(door_opening_hint(outcome.door_type, door_level=outcome.door_level, hcl=hcl))

        member = next((item for item in session.party if item.character_id == character_id), None) if character_id else None
        if member is None:
            member = self._member_by_marching_order(session, 1)
        if member is None:
            session.log.append("No hero available.")
            return

        hcl = self._highest_character_level(session.party)
        door_type = exit_state.door_type or "unlocked"
        if door_type == "sealed":
            if not is_spellcaster(member):
                session.log.append("Only a spellcaster can open a magically sealed door.")
                return
            if exit_state.door_sealed_attempted:
                session.log.append("The sealed door already resisted a spellcasting attempt.")
                return
            exit_state.door_sealed_attempted = True
            level = exit_state.door_level or hcl
            total, rolls = roll_exploding_for_level(member.level)
            modifier = spellcasting_modifier(member)
            final_total = total + modifier
            if show_rolls:
                session.log.append(
                    f"Sealed door: {member.name} rolls {' + '.join(str(value) for value in rolls)} + {modifier} = {final_total} vs L{level}."
                )
            if rolls[0] == 1:
                member.current_life = max(0, member.current_life - 2)
                session.log.append("Magic feedback! The caster takes 2 damage.")
            success = final_total >= level
            if success:
                exit_state.door_open = True
                exit_state.status = "open"
                self._sync_linked_door(session, tile, exit_state)
                session.log.append(f"The {exit_state.direction} sealed door opens.")
            else:
                session.log.append("The sealed door holds.")
            return

        if door_type == "illusion":
            if member.class_id.lower() != "illusionist":
                session.log.append("An illusionist must dispel this door's magic.")
                return
            if member.character_id in exit_state.door_illusion_attempted_ids:
                session.log.append(f"{member.name} already tried to open this illusionary door.")
                return
            exit_state.door_illusion_attempted_ids.append(member.character_id)
            success, roll_log = spellcasting_roll_vs_level(
                member,
                hcl,
                show_rolls=show_rolls,
                label="Illusionary door",
            )
            session.log.extend(roll_log)
            if success:
                exit_state.door_open = True
                exit_state.status = "open"
                self._sync_linked_door(session, tile, exit_state)
                session.log.append(f"The illusion fades; the {exit_state.direction} door opens.")
            else:
                session.log.append("The illusion persists.")
            return

        session.log.append("This door does not respond to spellcasting.")

    def _spend_clues_on_door(self, session: SessionState, exit_id: str | None, *, show_rolls: bool = True) -> None:
        if session.mode != "exploration":
            session.log.append("Work doors during exploration.")
            return
        tile = self._current_tile(session)
        exit_state = next((item for item in tile.exits if item.id == exit_id), None) if exit_id else None
        if exit_state is None or exit_state.kind != "door" or exit_state.door_open:
            session.log.append("Choose a closed door.")
            return
        if exit_state.door_type is None:
            outcome = self.table_roller.roll_door(self._highest_character_level(session.party))
            exit_state.door_type = outcome.door_type
            exit_state.door_level = outcome.door_level
            exit_state.door_result = outcome.summary
            exit_state.door_treasure_bonus = outcome.treasure_bonus
            session.log.append(f"Door: {outcome.summary}")
            hcl = self._highest_character_level(session.party)
            session.log.append(door_opening_hint(outcome.door_type, door_level=outcome.door_level, hcl=hcl))
        if exit_state.door_type != "illusion" and exit_state.door_type != "lever":
            session.log.append("Spending Clues works on illusionary or lever doors only.")
            return
        required = 3 if exit_state.door_type == "illusion" else 1
        if session.clues_found < required:
            session.log.append(f"Need {required} Clue(s) to open this door (party has {session.clues_found}).")
            return
        session.clues_found -= required
        exit_state.door_open = True
        exit_state.status = "open"
        self._sync_linked_door(session, tile, exit_state)
        session.log.append(
            f"The party spends {required} Clue(s); the {exit_state.direction} {exit_state.door_type} door opens."
        )

    def _combat_context(
        self,
        session: SessionState,
        tile: TileState,
        combat_abilities: dict[str, str] | None = None,
        combat_log: list[str] | None = None,
        guard_targets: dict[str, str] | None = None,
    ) -> CombatContext:
        abilities = combat_abilities or {}
        rage_attackers = {cid for cid, choice in abilities.items() if choice == "rage"}
        luck_reroll_attackers = {cid for cid, choice in abilities.items() if choice == "luck_attack"}
        luck_reroll_defenders = {cid for cid, choice in abilities.items() if choice == "luck_defense"}
        panache_attack_bonus = {cid for cid, choice in abilities.items() if choice == "panache_attack"}
        panache_defense_bonus = {cid for cid, choice in abilities.items() if choice == "panache_defense"}
        gnome_gadget_attackers = {cid for cid, choice in abilities.items() if choice == "gnome_gadget"}
        flip_kick_attackers = {cid for cid, choice in abilities.items() if choice == "flip_kick"}
        parrying_character_ids = {cid for cid, choice in abilities.items() if choice == "gladiator_parry"}
        double_kick_attackers = {cid for cid, choice in abilities.items() if choice == "double_kick"}
        deadly_strike_attackers = {cid for cid, choice in abilities.items() if choice == "deadly_strike"}
        double_attack_attackers = {cid for cid, choice in abilities.items() if choice == "double_attack"}
        protective_incense_users = {cid for cid, choice in abilities.items() if choice == "protective_incense"}
        for cid in protective_incense_users:
            session.expert_protective_incense_target = cid
        sacrifice_guards: dict[str, str] = {}
        for cid, choice in abilities.items():
            if choice != "bulwark_sacrifice":
                continue
            ally_id = (guard_targets or {}).get(cid)
            if ally_id:
                sacrifice_guards[cid] = ally_id

        def spend_rage(member: PartyMemberState) -> bool:
            return spend_rage_use(session, member)

        def spend_luck(member: PartyMemberState) -> bool:
            return spend_luck_point(session, member)

        def spend_panache(member: PartyMemberState) -> bool:
            return spend_panache_point(session, member)

        def spend_gnome_gadget(member: PartyMemberState) -> bool:
            return spend_gnome_gadgets(session, member, 1)

        def spend_acrobat_trick_point(member: PartyMemberState) -> bool:
            return spend_acrobat_trick(session, member)

        def on_assassin_strike_used() -> None:
            clear_assassin_mark(session)

        from .terrain import tile_is_outdoors

        return CombatContext(
            tile_type=tile.tile_type,
            wandering_ambush=tile.wandering_ambush and session.combat_round == 0,
            combat_round=session.combat_round + 1,
            outdoors=tile_is_outdoors(tile.terrain),
            cursed_character_id=session.cursed_character_id,
            wielded_melee=session.wielded_melee_weapons,
            illusionary_fog_active=session.illusionary_fog_active,
            subdual_penalty_ignored=session.subdual_penalty_ignored,
            body_carrier_id=session.body_carrier_id,
            rage_attackers=rage_attackers,
            luck_reroll_attackers=luck_reroll_attackers,
            luck_reroll_defenders=luck_reroll_defenders,
            panache_attack_bonus=panache_attack_bonus,
            panache_defense_bonus=panache_defense_bonus,
            gnome_gadget_attackers=gnome_gadget_attackers,
            flip_kick_attackers=flip_kick_attackers,
            parrying_character_ids=parrying_character_ids,
            double_kick_attackers=double_kick_attackers,
            sacrifice_guards=sacrifice_guards,
            sacrifice_used=set(),
            evading_character_ids=set(session.evasion_character_ids),
            gladiator_counter_pending=session.gladiator_counter_pending,
            gladiator_counter_used=set(session.gladiator_counter_used),
            foe_level_penalties=session.foe_level_penalties,
            assassin_striker_id=session.assassin_hidden_id,
            assassin_mark_enemy_id=session.assassin_mark_enemy_id,
            acrobat_skip_attack=session.acrobat_skip_attack,
            on_foe_kill=make_kill_callback(session, combat_log),
            on_assassin_strike_used=on_assassin_strike_used,
            spend_rage=spend_rage,
            spend_luck=spend_luck,
            spend_panache=spend_panache,
            spend_gnome_gadget=spend_gnome_gadget,
            session=session,
            deadly_strike_attackers=deadly_strike_attackers,
            double_attack_attackers=double_attack_attackers,
            spend_acrobat_trick=spend_acrobat_trick_point,
        )

    def _apply_combat_result(
        self,
        session: SessionState,
        tile: TileState,
        result,
        *,
        show_rolls: bool,
        fled: bool = False,
        active_enemy_ids: set[str] | None = None,
        standing_before: set[str] | None = None,
    ) -> None:
        if standing_before is None:
            standing_before = {pc.character_id for pc in session.party if pc.current_life > 0}
        if active_enemy_ids is None:
            active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
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
        if session.summoned_beast_owner_id and session.summoned_beast_owner_id in fallen_now:
            session.summoned_beast_life = 0
            session.summoned_beast_owner_id = None
            session.log.append("The summoned beast fades as its master falls.")
        if session.body_carrier_id and session.body_carrier_id in fallen_now:
            if session.carried_body_id and session.carried_body_id not in tile.fallen_character_ids:
                tile.fallen_character_ids.append(session.carried_body_id)
            session.log.append("The carrier falls; the fallen comrade's body is dropped here.")
            session.body_carrier_id = None
            session.carried_body_id = None

        session.combat_round += 1
        session.spell_used_character_ids = []
        if session.combat_round == 1:
            session.party_surprised = False
            session.reaction_pending = False
        if session.combat_round > 1:
            tile.wandering_ambush = False
            session.reaction_pending = False

        if not result.combat_over:
            return

        self._clear_combat_statuses(session)
        session.combat_round = 0
        tile.wandering_ambush = False

        if not any(pc.current_life > 0 for pc in session.party):
            session.mode = "complete"
            session.log.append("The party has fallen.")
            return

        if fled:
            session.mode = "exploration"
            session.log.append("Combat ends in retreat.")
            self._clear_combat_statuses(session)
            if tile.hidden_treasure_alarm_pending and any(enemy.life > 0 for enemy in tile.enemies):
                session.log.append(
                    f"The hidden treasure ({self._treasure_value_label(tile)}) is still here, "
                    "but wandering monsters must be defeated before you can claim it."
                )
            return

        tile.enemies = [enemy for enemy in tile.enemies if enemy.life > 0]
        tile.resolved = True
        session.mode = "exploration"
        session.log.append("Combat ends.")
        if result.morale_failed:
            self._award_treasure(session, tile, show_rolls=show_rolls)
        elif not tile.enemies:
            self._award_treasure(session, tile, show_rolls=show_rolls)
        defeated_this_fight = [
            enemy.model_copy(deep=True)
            for enemy in result.enemies
            if enemy.id in active_enemy_ids and enemy.life <= 0
        ]
        if not fled and defeated_this_fight:
            self._award_encounter_xp(session, defeated_this_fight, show_rolls=show_rolls)
            self._update_quest_on_combat_end(session, defeated_this_fight, show_rolls=show_rolls)
        self._announce_hidden_treasure_claimable(session, tile)

    def _resolve_foe_flee_strike(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if not any(enemy.life > 0 for enemy in tile.enemies):
            return
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {pc.character_id for pc in session.party if pc.current_life > 0}
        session.foe_flee_strike_pending = False
        result = resolve_flee_strike(
            session.party,
            tile.enemies,
            show_rolls=show_rolls,
            explain_math=explain_math,
            context=self._combat_context(session, tile),
        )
        self._apply_combat_result(
            session,
            tile,
            result,
            show_rolls=show_rolls,
            active_enemy_ids=active_enemy_ids,
            standing_before=standing_before,
        )

    def _combat_round(
        self,
        session: SessionState,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
        subdual: bool = False,
        attack_targets: dict[str, str] | None = None,
        combat_abilities: dict[str, str] | None = None,
        guard_targets: dict[str, str] | None = None,
    ) -> None:
        if session.mode != "combat":
            session.log.append("There are no active enemies here.")
            return
        self._commit_immediate_attack(session)
        tile = self._current_tile(session)
        if not any(enemy.life > 0 for enemy in tile.enemies):
            session.log.append("There are no active enemies here.")
            return
        initial_minor_count = tile.initial_enemy_count or len(tile.enemies)
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {pc.character_id for pc in session.party if pc.current_life > 0}

        if session.summoned_beast_life > 0:
            owner = next((m for m in session.party if m.character_id == session.summoned_beast_owner_id), None)
            if owner and owner.current_life > 0:
                target = next((enemy for enemy in tile.enemies if enemy.life > 0), None)
                if target:
                    target.life = max(0, target.life - 1)
                    session.log.append(
                        f"The summoned beast claws {target.name} for 1 damage "
                        f"({session.summoned_beast_life} Life remaining)."
                    )
                    if target.life <= 0:
                        session.log.append(f"{target.name} is defeated.")
            else:
                session.summoned_beast_life = 0
                session.summoned_beast_owner_id = None
                session.log.append("The summoned beast fades as its master falls.")

        if not any(enemy.life > 0 for enemy in tile.enemies):
            session.log.append("Combat ends.")
            self._apply_combat_result(
                session,
                tile,
                CombatRound(party=session.party, enemies=tile.enemies, log=[], combat_over=True),
                show_rolls=show_rolls,
                active_enemy_ids=active_enemy_ids,
                standing_before=standing_before,
            )
            return

        if session.foe_flee_strike_pending:
            self._resolve_foe_flee_strike(
                session,
                tile,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
            return

        foes_strike_first = session.foes_strike_first and session.combat_round == 0
        if foes_strike_first:
            session.foes_strike_first = False
        missile_used = set(session.missile_used_character_ids)
        ability_log: list[str] = []
        combat_context = self._combat_context(
            session, tile, combat_abilities, ability_log, guard_targets=guard_targets
        )
        result = resolve_combat_round(
            session.party,
            tile.enemies,
            show_rolls=show_rolls,
            explain_math=explain_math,
            initial_minor_count=initial_minor_count,
            context=combat_context,
            party_surprised=session.party_surprised and session.combat_round == 0,
            party_attacked_immediately=session.party_attacked_immediately and session.combat_round == 0,
            foes_strike_first=foes_strike_first,
            subdual=subdual,
            encounter_round=session.combat_round,
            missile_used=missile_used,
            attack_targets=attack_targets,
        )
        session.gladiator_counter_used = sorted(combat_context.gladiator_counter_used)
        session.evasion_character_ids = []
        if ability_log:
            result.log.extend(ability_log)
        if result.missile_used is not None:
            session.missile_used_character_ids = sorted(result.missile_used)
        self._foes_strike_summoned_beast(session, tile, show_rolls=show_rolls)
        self._apply_combat_result(
            session,
            tile,
            result,
            show_rolls=show_rolls,
            active_enemy_ids=active_enemy_ids,
            standing_before=standing_before,
        )

    def _flee(
        self,
        session: SessionState,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
        use_luck_flee: bool = False,
        character_id: str | None = None,
    ) -> None:
        if session.mode != "combat":
            session.log.append("There is no fight to flee.")
            return
        tile = self._current_tile(session)
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {pc.character_id for pc in session.party if pc.current_life > 0}
        skip_parting_attacks = session.skip_parting_flee or session.gnome_smokescreen_ready
        if use_luck_flee:
            halfling = next((member for member in session.party if member.character_id == character_id), None)
            if halfling is None or halfling.class_id.lower() != "halfling":
                session.log.append("Choose a halfling to spend Luck for a clean escape.")
            elif halfling.current_life <= 0:
                session.log.append(f"{halfling.name} cannot spend Luck while fallen.")
            elif spend_luck_point(session, halfling):
                skip_parting_attacks = True
                session.log.append(
                    f"{halfling.name} spends 1 Luck; the party flees without parting blows."
                )
            else:
                session.log.append(f"{halfling.name} has no Luck points remaining.")
        elif skip_parting_attacks:
            session.log.append("The party escapes without parting blows (smokescreen or Serpent Twist).")
        result = resolve_flee(
            session.party,
            tile.enemies,
            show_rolls=show_rolls,
            explain_math=explain_math,
            context=self._combat_context(session, tile),
            skip_parting_attacks=skip_parting_attacks,
        )
        self._apply_combat_result(
            session,
            tile,
            result,
            show_rolls=show_rolls,
            fled=result.fled,
            active_enemy_ids=active_enemy_ids,
            standing_before=standing_before,
        )
        if result.fled:
            session.skip_parting_flee = False
            session.gnome_smokescreen_ready = False
            if show_rolls:
                roll = roll_d6()
                session.log.append(f"Flee wandering check: d6 = {roll}.")
                if roll == 1:
                    session.log.append("Something pursues the fleeing party (Wandering Monsters on 1).")

    def _withdraw(
        self,
        session: SessionState,
        exit_id: str | None,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if session.mode != "combat":
            session.log.append("There is no fight to withdraw from.")
            return
        tile = self._current_tile(session)
        exit_state = next((item for item in tile.exits if item.id == exit_id), None) if exit_id else None
        if exit_state is None or exit_state.kind != "door" or not exit_state.destination_tile_id:
            session.log.append("Withdraw requires an open door back to a visited tile.")
            return
        destination = self._tile_by_id(session, exit_state.destination_tile_id)
        if destination is None:
            session.log.append("That door does not lead anywhere known.")
            return
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {pc.character_id for pc in session.party if pc.current_life > 0}
        result = resolve_withdraw(
            session.party,
            tile.enemies,
            show_rolls=show_rolls,
            explain_math=explain_math,
            context=self._combat_context(session, tile),
        )
        self._apply_combat_result(
            session,
            tile,
            result,
            show_rolls=show_rolls,
            fled=result.fled,
            active_enemy_ids=active_enemy_ids,
            standing_before=standing_before,
        )
        if not result.fled:
            return
        exit_state.door_open = False
        reciprocal = next(
            (item for item in destination.exits if item.destination_tile_id == tile.id),
            None,
        )
        if reciprocal is not None:
            reciprocal.door_open = False
            reciprocal.status = "open"
        session.map_state.current_tile_id = destination.id
        session.log.append(f"The party withdraws to {destination.title}. The foes remain behind.")
        if show_rolls:
            roll = roll_d6()
            session.log.append(f"Withdraw wandering check: d6 = {roll}.")
            if roll == 1:
                self._spawn_wandering_monsters(session, destination, show_rolls=show_rolls)

    def _set_marching_order(
        self,
        session: SessionState,
        character_id: str | None,
        position: int | None,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Change marching order during combat.")
            return
        if not character_id or position is None or position not in {1, 2, 3, 4}:
            session.log.append("Choose a hero and position 1-4.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None:
            session.log.append("That hero is not in the party.")
            return
        if member.current_life <= 0:
            session.log.append(f"{member.name} cannot move in marching order while fallen.")
            return
        old_position = member.marching_order
        if old_position == position:
            session.log.append(f"{member.name} is already in position {position}.")
            return
        occupant = next(
            (
                item
                for item in session.party
                if item.marching_order == position and item.character_id != character_id
            ),
            None,
        )
        if occupant:
            occupant.marching_order = old_position
        member.marching_order = position
        session.log.append(f"Marching order: {member.name} moves from #{old_position} to #{position}.")

    def _set_default_weapon(
        self,
        session: SessionState,
        character_id: str | None,
        item_name: str | None,
        *,
        weapon_kind: str | None,
    ) -> None:
        if session.mode == "combat":
            session.log.append(
                "Use Swap Weapon during combat (costs 1 turn). To change sheet defaults, wait until exploration."
            )
            return
        if session.mode != "exploration":
            session.log.append("Set default weapons during exploration.")
            return
        if not character_id or not item_name:
            session.log.append("Choose a hero and weapon to set as default.")
            return
        if weapon_kind not in {"melee", "missile"}:
            session.log.append("Choose whether this is a melee or missile default weapon.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero.")
            return
        if item_name not in member.inventory:
            session.log.append(f"{member.name} does not carry {item_name}.")
            return
        ok, note = set_weapon_default(member, item_name=item_name, weapon_kind=weapon_kind)
        if not ok:
            session.log.append(note)
            return
        tile = self._current_tile(session)
        if tile.content_key == "armory" or any("armory" in obj.lower() for obj in tile.objects):
            note += " (Armory: changed within carried gear.)"
        session.log.append(note)

    def _swap_weapon(
        self,
        session: SessionState,
        character_id: str | None,
        item_name: str | None,
        *,
        show_rolls: bool,
    ) -> None:
        if session.mode != "combat":
            session.log.append("Swap weapons during combat only.")
            return
        if not character_id or not item_name:
            session.log.append("Choose a hero and melee weapon to draw.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to swap weapons.")
            return
        if item_name not in member.inventory:
            session.log.append(f"{member.name} does not carry {item_name}.")
            return
        profile = _parse_weapon_item(item_name)
        if profile is None or profile.kind != "melee":
            session.log.append(f"{item_name} is not a melee weapon.")
            return
        current = session.wielded_melee_weapons.get(member.character_id) or member.default_melee_weapon
        if current == item_name:
            session.log.append(f"{member.name} already wields {item_name}.")
            return
        session.wielded_melee_weapons[member.character_id] = item_name
        session.log.append(f"{member.name} spends the turn drawing {item_name}.")
        tile = self._current_tile(session)
        if not any(enemy.life > 0 for enemy in tile.enemies):
            session.log.append("There are no active enemies here.")
            return
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {pc.character_id for pc in session.party if pc.current_life > 0}
        result = resolve_combat_round(
            session.party,
            tile.enemies,
            show_rolls=show_rolls,
            context=self._combat_context(session, tile),
            encounter_round=session.combat_round,
            missile_used=set(session.missile_used_character_ids),
            foe_phase_only=True,
        )
        self._apply_combat_result(
            session,
            tile,
            result,
            show_rolls=show_rolls,
            active_enemy_ids=active_enemy_ids,
            standing_before=standing_before,
        )

    def _transfer_item(
        self,
        session: SessionState,
        from_character_id: str | None,
        to_character_id: str | None,
        item_name: str | None,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Exchange gear during exploration, not in combat.")
            return
        if not from_character_id or not to_character_id:
            session.log.append("Choose who gives and who receives the item.")
            return
        _ok, message = transfer_inventory_item(
            session.party,
            from_character_id=from_character_id,
            to_character_id=to_character_id,
            item_name=item_name or "",
        )
        session.log.append(message)

    def _transfer_gold(
        self,
        session: SessionState,
        from_character_id: str | None,
        to_character_id: str | None,
        amount: int | None,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Exchange gold during exploration, not in combat.")
            return
        if not from_character_id or not to_character_id:
            session.log.append("Choose who gives and who receives the gold.")
            return
        _ok, message = transfer_gold(
            session.party,
            from_character_id=from_character_id,
            to_character_id=to_character_id,
            amount=amount or 0,
        )
        session.log.append(message)

    def _grant_clue(self, session: SessionState, tile: TileState) -> None:
        tile.objects.append("Clue")
        session.clues_found += 1
        session.log.append(f"The party finds a clue ({session.clues_found} total this adventure).")
        if session.clues_found < CLUES_FOR_SECRET_XP:
            return
        session.clues_found -= CLUES_FOR_SECRET_XP
        self._grant_xp_credit(
            session,
            1,
            f"A Secret is revealed ({CLUES_FOR_SECRET_XP} Clues). Assign from party sheets.",
        )

    def _grant_xp_credit(self, session: SessionState, amount: int, reason: str) -> None:
        if amount <= 0 or session.xp_system == "slow_and_sure":
            return
        if session.xp_system == "old_school":
            tier = tier_for_level(self._highest_character_level(session.party))
            points = tier * 100 * amount
            session.old_school_xp_tally += points
            session.log.append(f"{reason} Old School XP +{points} (tally {session.old_school_xp_tally}).")
            return
        if session.xp_system == "slower_advancement":
            session.slower_xp_bank += amount
            session.log.append(f"{reason} Banked {amount} XP ({session.slower_xp_bank} total).")
            return
        session.xp_rolls_pending += amount
        session.log.append(f"{reason} Earned {amount} XP roll(s). Assign from party sheets.")

    def _can_assign_level_up(self, session: SessionState, character_id: str) -> bool:
        survivors = [member for member in session.party if member.current_life > 0]
        if len(survivors) <= 1:
            return True
        return session.last_leveled_character_id != character_id

    def _award_encounter_xp(
        self,
        session: SessionState,
        defeated: list[EnemyState],
        *,
        show_rolls: bool,
    ) -> None:
        if not defeated or session.xp_system == "slow_and_sure":
            return
        if session.xp_system == "old_school":
            points = old_school_xp_for_defeated(defeated)
            if points:
                session.old_school_xp_tally += points
                session.log.append(f"Old School XP +{points} (tally {session.old_school_xp_tally}).")
            return

        majors = major_foes_defeated(defeated)
        for enemy in majors:
            self._grant_xp_credit(session, 1, f"Defeated {enemy.name} (Major Foe):")
            if "final_boss" in enemy.tags:
                session.final_boss_defeated = True
                self._grant_xp_credit(session, 1, "Final Boss slain:")
        if majors:
            return
        if not is_minor_encounter(defeated):
            return
        session.minor_encounters_defeated += 1
        if show_rolls:
            session.log.append(
                f"Minor encounter cleared ({session.minor_encounters_defeated}/"
                f"{MINOR_ENCOUNTERS_FOR_XP} toward next XP credit)."
            )
        if session.minor_encounters_defeated >= MINOR_ENCOUNTERS_FOR_XP:
            session.minor_encounters_defeated -= MINOR_ENCOUNTERS_FOR_XP
            self._grant_xp_credit(session, 1, f"{MINOR_ENCOUNTERS_FOR_XP} minor encounters:")

    def _complete_level_up(
        self,
        session: SessionState,
        member: PartyMemberState,
        *,
        new_spell: str | None = None,
    ) -> None:
        result = apply_level_up(member, new_spell=new_spell)
        session.log.extend(result.log)
        session.last_leveled_character_id = member.character_id
        if result.spell_pick_pending:
            session.level_up_spell_pending_character_id = member.character_id
        else:
            session.level_up_spell_pending_character_id = None

    def _pick_level_up_spell(
        self,
        session: SessionState,
        character_id: str | None,
        spell_name: str | None,
    ) -> None:
        if not session.level_up_spell_pending_character_id:
            session.log.append("No spell choice is pending.")
            return
        if character_id != session.level_up_spell_pending_character_id:
            session.log.append("Choose a spell for the hero who just leveled up.")
            return
        if not spell_name:
            session.log.append("Select a spell to prepare.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None:
            session.log.append("Hero not found.")
            return
        session.log.extend(assign_level_up_spell(member, spell_name))
        session.level_up_spell_pending_character_id = None

    def _xp_roll(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        show_rolls: bool,
        explain_math: bool,
        new_spell: str | None = None,
        advancement_fork: str | None = None,
        expert_skill_id: str | None = None,
        expert_skill_target: str | None = None,
    ) -> None:
        if session.level_up_spell_pending_character_id:
            pending = next(
                (item for item in session.party if item.character_id == session.level_up_spell_pending_character_id),
                None,
            )
            name = pending.name if pending else "the hero"
            session.log.append(f"Choose a spell for {name} before spending another XP roll.")
            return
        if session.mode == "combat":
            session.log.append("XP rolls wait until combat ends.")
            return
        if session.xp_system != "classical":
            session.log.append(f"Use the {campaign_mode_label(session.xp_system)} advancement action instead.")
            return
        if session.xp_rolls_pending <= 0:
            session.log.append("No XP rolls are available.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero for the XP roll.")
            return
        if not self._can_assign_level_up(session, character_id or ""):
            session.log.append("Another hero must take the next level (same PC cannot level twice in a row).")
            return

        fork = advancement_fork or ("level_up" if member.level < 5 else None)
        if fork not in {"level_up", "learn_expert_skill"}:
            session.log.append("Choose Level up or Learn expert skill (Level 5+).")
            return
        if fork == "level_up":
            gate = level_up_gate_reason(member, member.level + 1)
            if gate:
                session.log.append(gate)
                return
        else:
            if member.level < 5:
                session.log.append("Expert skills require Level 5+.")
                return
            if not expert_skill_id:
                session.log.append("Choose an expert skill or spell to learn.")
                return
            catalog = self.rules.expert_skills()
            blocked = validate_expert_skill_choice(member, expert_skill_id, catalog)
            if blocked:
                session.log.append(blocked)
                return

        purpose = "level_up" if fork == "level_up" else "learn_expert_skill"
        session.xp_rolls_pending -= 1
        result = perform_advancement_roll(member, purpose=purpose)
        if show_rolls:
            label = "Level-up" if fork == "level_up" else "Expert skill"
            session.log.append(
                f"{label} roll for {member.name}: {result.die_label} = {result.natural}"
                + (f" + {result.modifier} = {result.total}" if result.modifier else "")
                + f" vs Level {member.level}."
            )
        if explain_math:
            session.log.append(advancement_roll_explain(member))
        if advancement_succeeds(result, member.level):
            if fork == "level_up":
                self._complete_level_up(session, member, new_spell=new_spell)
            else:
                session.log.extend(
                    apply_expert_skill_learn(
                        member,
                        expert_skill_id or "",
                        self.rules.expert_skills(),
                        target=expert_skill_target,
                    )
                )
        elif fork == "level_up":
            session.log.append(f"{member.name} fails to advance (needs > {member.level}).")
        else:
            session.log.append(f"{member.name} fails to learn the expert skill (needs > {member.level}).")

    def _buy_healing(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        show_rolls: bool,
    ) -> None:
        if session.mode == "combat":
            session.log.append("Buy healing between encounters.")
            return
        tile = self._current_tile(session)
        if not tile.healer_available:
            session.log.append("No wandering healer is here.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to heal.")
            return
        if member.current_life >= member.max_life:
            session.log.append(f"{member.name} is already at full Life.")
            return
        payer = next((item for item in session.party if item.gold >= 10), None)
        if payer is None:
            session.log.append("The party needs 10gp for the healer.")
            return
        payer.gold -= 10
        member.current_life += 1
        if show_rolls:
            session.log.append(
                f"{payer.name} pays 10gp; the healer restores 1 Life to {member.name} "
                f"({member.current_life}/{member.max_life})."
            )

    def _buy_alchemist(
        self,
        session: SessionState,
        character_id: str | None,
        item_key: str | None,
        *,
        show_rolls: bool,
    ) -> None:
        if session.mode == "combat":
            session.log.append("Buy from the alchemist between encounters.")
            return
        tile = self._current_tile(session)
        if not tile.alchemist_available:
            session.log.append("No wandering alchemist is here.")
            return
        if item_key not in {"potion", "poison"}:
            session.log.append("Choose Potion of Healing (50gp) or blade poison (30gp).")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero for the purchase.")
            return
        if item_key == "potion":
            if member.character_id in session.alchemist_potion_bought:
                session.log.append(f"{member.name} already bought a potion this adventure.")
                return
            cost = 50
            item_name = "Potion of Healing"
        else:
            if member.character_id in session.alchemist_poison_bought:
                session.log.append(f"{member.name} already bought poison this adventure.")
                return
            cost = 30
            item_name = "Blade poison"
        payer = next((item for item in session.party if item.gold >= cost), None)
        if payer is None:
            session.log.append(f"The party needs {cost}gp for {item_name}.")
            return
        payer.gold -= cost
        ok, message = can_add_item(member, item_name)
        if not ok:
            payer.gold += cost
            session.log.append(message)
            return
        member.inventory.append(item_name)
        if item_key == "potion":
            session.alchemist_potion_bought.append(member.character_id)
        else:
            session.alchemist_poison_bought.append(member.character_id)
        if show_rolls:
            session.log.append(f"{payer.name} pays {cost}gp; {member.name} receives {item_name}.")

    def _use_class_ability(
        self,
        session: SessionState,
        character_id: str | None,
        class_ability: str | None,
        *,
        target_character_id: str | None = None,
        foe_id: str | None = None,
        show_rolls: bool = True,
        explain_math: bool = False,
        exit_id: str | None = None,
        gadget_points: int | None = None,
    ) -> None:
        if not class_ability:
            session.log.append("No class ability specified.")
            return
        actor = next((member for member in session.party if member.character_id == character_id), None)
        if actor is None:
            session.log.append("Choose a hero for this ability.")
            return
        tile = self._current_tile(session)
        living_foes = [enemy for enemy in tile.enemies if enemy.life > 0]

        if class_ability == "turn_undead":
            from .expert_skill_effects import _is_undead, encounter_spent, has_skill, mark_encounter_spent

            if session.mode != "combat":
                session.log.append("Turn Undead is used during combat.")
                return
            if not has_skill(actor, "turn_undead"):
                session.log.append(f"{actor.name} has not learned Turn Undead.")
                return
            if encounter_spent(session, actor.character_id, "turn_undead"):
                session.log.append("Turn Undead was already used this encounter.")
                return
            undead = [enemy for enemy in living_foes if _is_undead(enemy)]
            if not undead:
                session.log.append("No undead foes to turn.")
                return
            mark_encounter_spent(session, actor.character_id, "turn_undead")
            for enemy in undead:
                total = roll_d6() + actor.level // 2
                if show_rolls:
                    session.log.append(
                        f"Turn Undead: {actor.name} rolls d6+½L = {total} vs L{enemy.level} ({enemy.name})."
                    )
                if total >= enemy.level:
                    flee = roll_d6()
                    enemy.life = max(0, enemy.life - flee)
                    session.log.append(f"{enemy.name} loses {flee} Life to Turn Undead.")
            return

        if class_ability == "paladin_heal":
            target_id = target_character_id or character_id
            target = next((member for member in session.party if member.character_id == target_id), None)
            if target is None:
                session.log.append("Choose a target to heal.")
                return
            session.log.extend(paladin_heal(session, actor, target))
            return

        if class_ability in {"paladin_reroll_save", "halfling_reroll_save"}:
            pending = session.pending_save_reroll
            if class_ability == "halfling_reroll_save" and actor.class_id.lower() != "halfling":
                session.log.append("Only a halfling may reroll with Luck.")
                return
            log, succeeded = reroll_failed_save_with_luck(session, actor, show_rolls=show_rolls)
            session.log.extend(log)
            if pending and pending.get("context") == "puzzle":
                if succeeded:
                    session.log.append("The puzzle is solved; the foes let you pass.")
                    self._end_peaceful_encounter(session, tile)
                else:
                    session.foes_strike_first = True
                    session.reaction_pending = False
            return

        if class_ability == "paladin_summon_steed":
            if session.mode == "combat":
                session.log.append("Cannot summon a steed during combat.")
                return
            if not spend_paladin_prayer(session, actor, 1):
                session.log.append(f"{actor.name} has no prayer points remaining.")
                return
            session.log.append(
                f"{actor.name} spends 1 prayer point to summon a steed for one day "
                "(outdoors only — not while dungeon delving)."
            )
            return

        if class_ability == "acrobat_shift_position":
            if session.mode != "exploration":
                session.log.append("Shift Position is used in exploration.")
                return
            ally = next(
                (member for member in session.party if member.character_id == target_character_id),
                None,
            )
            if ally is None or ally.character_id == actor.character_id:
                session.log.append("Choose another hero to swap marching order with.")
                return
            session.log.extend(acrobat_shift_position(session, actor, ally))
            return

        if class_ability == "acrobat_distract":
            enemy = next((item for item in living_foes if item.id == foe_id), None)
            if enemy is None:
                session.log.append("Choose a foe to distract.")
                return
            session.log.extend(acrobat_distract(session, actor, enemy))
            return

        if class_ability == "illusionist_distract":
            enemy = next((item for item in living_foes if item.id == foe_id), None)
            if enemy is None:
                session.log.append("Choose a foe to distract with lights.")
                return
            session.log.extend(illusionist_distract(session, actor, enemy))
            return

        if class_ability == "acrobat_leap_harm":
            session.log.extend(acrobat_leap_out_of_harm(session, actor))
            return

        if class_ability == "acrobat_serpent_twist":
            session.log.extend(acrobat_serpent_twist(session, actor))
            return

        if class_ability == "acrobat_evade":
            if session.mode != "combat":
                session.log.append("Evade is used during combat.")
                return
            session.log.extend(acrobat_evade(session, actor))
            return

        if class_ability == "gnome_smokescreen":
            session.log.extend(gnome_smokescreen(session, actor))
            return

        if class_ability == "mushroom_spore_cloud":
            if session.mode == "combat" and session.combat_round > 0:
                session.log.append("Spore cloud must be used before or at the start of a fight.")
                return
            session.log.extend(mushroom_spore_cloud(session, actor, tile.enemies))
            return

        if class_ability == "assassin_hide":
            if session.mode != "combat":
                session.log.append("Hide in Shadows is used when foes are present.")
                return
            session.log.extend(assassin_hide(session, actor, tile.enemies, show_rolls=show_rolls))
            return

        if class_ability == "gnome_gadget_trap":
            if session.mode == "combat":
                session.log.append("Disarm traps during exploration.")
                return
            if not tile.trap_key or tile.trap_resolved:
                session.log.append("There is no active trap here.")
                return
            points = gadget_points or 1
            trap_level = tile.trap_level or self._highest_character_level(session.party)
            ok, log = attempt_gnome_trap_disarm(
                session, actor, trap_level, gadget_points=points, show_rolls=show_rolls
            )
            session.log.extend(log)
            if ok:
                tile.trap_resolved = True
                tile.objects = [item for item in tile.objects if "trap" not in item.lower()]
                self._announce_hidden_treasure_claimable(session, tile)
            else:
                session.log.extend(
                    self.table_roller.resolve_trap(
                        tile.trap_key,
                        trap_level,
                        session.party,
                        self._marching_order_ids(session),
                        show_rolls=show_rolls,
                        explain_math=explain_math,
                    )
                )
                tile.trap_resolved = True
                tile.objects = [item for item in tile.objects if "trap" not in item.lower()]
            return

        if class_ability == "gnome_gadget_door":
            if session.mode != "exploration":
                session.log.append("Gadget doors are worked during exploration.")
                return
            exit_state = next((item for item in tile.exits if item.id == exit_id), None) if exit_id else None
            if exit_state is None or exit_state.kind != "door" or exit_state.door_open:
                session.log.append("Choose a closed door.")
                return
            if exit_state.door_type is None:
                outcome = self.table_roller.roll_door(self._highest_character_level(session.party))
                exit_state.door_type = outcome.door_type
                exit_state.door_level = outcome.door_level
                exit_state.door_result = outcome.summary
                exit_state.door_treasure_bonus = outcome.treasure_bonus
                session.log.append(f"Door: {outcome.summary}")
            door_type = exit_state.door_type or "unlocked"
            if door_type == "lever":
                session.log.extend(open_lever_door_with_gnome_gadget(session, actor))
                exit_state.door_open = True
                exit_state.status = "open"
                self._sync_linked_door(session, tile, exit_state)
                session.log.append(f"The {exit_state.direction} lever door opens.")
                return
            points = gadget_points or 1
            ok, log = attempt_gnome_gadget_door(
                session,
                actor,
                exit_state.door_level or 6,
                gadget_points=points,
                show_rolls=show_rolls,
            )
            session.log.extend(log)
            if ok:
                exit_state.door_open = True
                exit_state.status = "open"
                self._sync_linked_door(session, tile, exit_state)
                session.log.append(f"The {exit_state.direction} door is now open.")
            return

        if class_ability == "halfling_luck_treasure":
            if actor.class_id.lower() != "halfling":
                session.log.append("Only a halfling may reroll treasure with Luck.")
                return
            if session.pending_treasure_reroll_tile_id != tile.id:
                session.log.append("No fresh treasure roll is available to reroll on this tile.")
                return
            if not spend_luck_point(session, actor):
                session.log.append(f"{actor.name} has no Luck points remaining.")
                return
            tile.treasure_summary = ""
            tile.treasure_gold = 0
            tile.treasure_items = []
            outcome = self.table_roller.roll_treasure(environment=session.environment)
            if show_rolls:
                session.log.extend(outcome.log)
            session.log.append(f"{actor.name} spends 1 Luck point to reroll the treasure table.")
            if outcome.gold or outcome.items:
                tile.treasure_summary = outcome.summary
                tile.treasure_gold = outcome.gold
                tile.treasure_items = self._finalize_treasure_items(
                    session, list(outcome.items), show_rolls=show_rolls
                )
                self._apply_treasure_doubling(tile)
                session.log.append("Treasure is available to claim.")
            else:
                tile.treasure_summary = outcome.summary
                session.log.append(outcome.summary or "No treasure found.")
            session.pending_treasure_reroll_tile_id = None
            return

        session.log.append(f"Unknown class ability: {class_ability}.")

    def _rest(
        self,
        session: SessionState,
        *,
        nail_doors: bool = False,
        rest_choices: dict[str, str] | None = None,
        show_rolls: bool = True,
        nourishing_meal: bool = False,
        nourishing_meal_eaters: list[str] | None = None,
    ) -> None:
        tile = self._current_tile(session)
        living = [member for member in session.party if member.current_life > 0]
        choices = dict(rest_choices or {})
        for member in living:
            if member.character_id in choices:
                continue
            if member.current_life < member.max_life:
                choices[member.character_id] = "life"
            elif member_has_recoverable_ability(session, member):
                choices[member.character_id] = "ability"
            else:
                choices[member.character_id] = "life"

        ok, reason = validate_rest_request(session, tile, nail_doors=nail_doors, choices=choices)
        if not ok:
            session.log.append(reason)
            return

        doors = nailable_doors(tile)
        session.log.append("The party rests (once per adventure, rulebook p.114).")
        if nail_doors:
            if not consume_nail_bags(session.party, len(doors)):
                session.log.append("Not enough bags of nails to seal the doors.")
                return
            for exit_state in doors:
                exit_state.nailed_shut = True
                exit_state.door_open = False
                exit_state.status = "blocked"
                self._sync_linked_door(session, tile, exit_state)
            session.log.append(
                f"The party nails {len(doors)} door(s) shut ({len(doors)} bag(s) of nails used)."
            )
        else:
            session.log.append("The party does not nail the doors shut.")

        session.rest_used = True
        session.log.extend(apply_rest_recovery(session, session.party, choices))
        for member in living:
            trick_note = recover_acrobat_tricks_on_rest(session, member)
            if trick_note:
                session.log.append(trick_note)
        if nourishing_meal:
            eaters = nourishing_meal_eaters or [
                member.character_id for member in living if member.current_life > 0
            ]
            session.log.extend(apply_nourishing_meal(session, session.party, eaters))

        triggered, roll = wandering_roll_triggers()
        if show_rolls:
            session.log.append(f"Rest wandering-monster roll: d6 = {roll}.")
        if not triggered:
            session.log.append("The rest is undisturbed.")
            return

        door = pick_wandering_door(doors)
        if door is not None:
            if nail_doors:
                session.log.append(
                    f"Wandering Monsters force open the nailed {door.direction} door!"
                )
            else:
                session.log.append(
                    f"Wandering Monsters burst through the unnailed {door.direction} door!"
                )
        else:
            session.log.append("Wandering Monsters arrive!")
        tile.wandering_ambush = False
        self._spawn_wandering_monsters(
            session,
            tile,
            show_rolls=show_rolls,
            combat_message="Wandering Monsters disturb the rest!",
            party_strikes_first=nail_doors,
            foes_strike_first=not nail_doors,
        )
        if nail_doors:
            session.log.append(
                "The nailed doors gave warning — the party may attack first even if the foes would normally surprise you."
            )
        else:
            session.log.append("The unnailed doors gave no warning — Wandering Monsters attack first.")

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
        content = self._roll_content(session, tile_type, hcl)
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
            environment=session.environment,
            terrain=tile_def.terrain if tile_def else "indoor",
        )
        self._seed_tile_features(tile, hcl, show_rolls=show_rolls, session=session)
        return tile

    def _roll_content(self, session: SessionState, tile_type: str, hcl: int) -> dict:
        roll = roll_2d6()
        outcome = self.table_roller.lookup_room_content(roll, tile_type)
        if outcome is None:
            return self._content("empty", "The area is quiet.", [], [], roll=roll)
        enemies: list[EnemyState] = []
        if outcome.enemy_category:
            enemies = self._roll_enemy(session, outcome.enemy_category, hcl, required_tags=outcome.enemy_tags or None)
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

    def _fallen_in_dungeon(self, session: SessionState) -> list[str]:
        fallen: list[str] = []
        for tile in session.map_state.tiles:
            for character_id in tile.fallen_character_ids:
                if character_id not in fallen:
                    fallen.append(character_id)
        return fallen

    def _entrance_tile(self, session: SessionState) -> TileState:
        for tile in session.map_state.tiles:
            if tile.content_key == "entrance":
                return tile
        return min(session.map_state.tiles, key=lambda item: (item.y, item.x))

    def _retreat_from_dungeon(
        self,
        session: SessionState,
        fallen_ids: list[str],
        *,
        show_rolls: bool,
    ) -> None:
        entrance = self._entrance_tile(session)
        session.map_state.current_tile_id = entrance.id
        self._refresh_tile_connections(session, entrance)
        self._initialize_outside_entrance(entrance)
        session.camped_outside = True
        session.summary = []
        names = [
            member.name
            for member in session.party
            if member.character_id in fallen_ids
        ]
        label = ", ".join(names) if names else f"{len(fallen_ids)} hero(es)"
        session.log.append(
            f"The party retreats to camp outside the dungeon. Fallen comrades remain inside: {label}."
        )
        session.log.append(
            "The explored dungeon persists. Regroup and re-enter to recover them. "
            "Items left on unattended bodies may be stolen (5-in-6)."
        )
        self._steal_from_unattended_bodies(session, show_rolls=show_rolls)

    def _steal_from_unattended_bodies(self, session: SessionState, *, show_rolls: bool) -> None:
        for character_id in self._fallen_in_dungeon(session):
            member = next((item for item in session.party if item.character_id == character_id), None)
            if member is None or not member.inventory:
                continue
            roll = roll_d6()
            if roll >= 6:
                if show_rolls:
                    session.log.append(f"No theft from {member.name}'s body (d6 = {roll}).")
                continue
            stolen = member.inventory.pop(0)
            if show_rolls:
                session.log.append(
                    f"Loot stolen from {member.name}'s unattended body: {stolen} (d6 = {roll}, need 6 to avoid)."
                )
            else:
                session.log.append(f"Loot stolen from {member.name}'s unattended body: {stolen}.")

    def _complete_dungeon(self, session: SessionState) -> None:
        session.mode = "complete"
        session.camped_outside = False
        explored = len(session.map_state.tiles)
        survivors = [member for member in session.party if member.current_life > 0]
        if session.xp_system == "slow_and_sure" and survivors:
            target = survivors[0]
            self._complete_level_up(session, target)
            session.log.append(f"Slow and Sure: {target.name} gains 1 Level for completing the adventure.")
        for member in session.party:
            if member.current_life > 0:
                member.current_life = member.max_life
        boss_note = " Final Boss slain." if session.final_boss_defeated else ""
        session.summary = [
            f"Explored {explored} map element{'s' if explored != 1 else ''}.{boss_note}",
            f"{len(survivors)} of {len(session.party)} party members left the dungeon.",
            "Between adventures, surviving heroes fully heal and keep treasure already recorded on their sheets.",
        ]
        session.log.append("The party leaves the dungeon. Surviving heroes fully heal between adventures.")
        session.expended_spells = {}
        session.healing_prayer_uses = {}

    def _roll_enemy(
        self,
        session: SessionState,
        category: str,
        hcl: int,
        *,
        required_tags: list[str] | None = None,
    ) -> list[EnemyState]:
        monsters = self.rules.monsters()
        table_key = category
        if session.environment != "dungeon":
            env_key = f"{session.environment}_{category}"
            if env_key in monsters:
                table_key = env_key
        table = monsters.get(table_key) or monsters.get(category) or monsters["vermin"]
        if required_tags:
            filtered = [
                template
                for template in table
                if all(tag in template.get("tags", []) for tag in required_tags)
            ]
            if filtered:
                table = filtered
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
        self._sync_connection_state(origin_exit, reciprocal, passed_through=True)

    def _clear_door_state(self, exit_state: ExitState) -> None:
        exit_state.door_type = None
        exit_state.door_level = None
        exit_state.door_result = None
        exit_state.door_open = False
        exit_state.door_treasure_bonus = 0

    def _sync_connection_state(
        self,
        source: ExitState,
        target: ExitState,
        *,
        passed_through: bool = False,
    ) -> None:
        target.kind = source.kind
        target.span = max(source.span, target.span)
        target.door_destroyed = source.door_destroyed
        target.nailed_shut = source.nailed_shut
        if source.kind == "door":
            target.door_type = source.door_type
            target.door_level = source.door_level
            target.door_result = source.door_result
            target.door_treasure_bonus = source.door_treasure_bonus
            if source.nailed_shut:
                target.status = "blocked"
                target.door_open = False
            else:
                target.status = "open"
                target.door_open = True if passed_through else source.door_open
            return
        target.status = "open"
        self._clear_door_state(target)

    def _copy_door_state(self, source: ExitState, target: ExitState) -> None:
        if source.kind != "door":
            return
        self._sync_connection_state(source, target, passed_through=source.door_open)

    def _reciprocal_exit_on_tile(
        self,
        tile: TileState,
        other_tile_id: str,
        *,
        direction: str | None = None,
    ) -> ExitState | None:
        matches = [exit_state for exit_state in tile.exits if exit_state.destination_tile_id == other_tile_id]
        if not matches:
            return None
        if direction:
            directional = [exit_state for exit_state in matches if exit_state.direction == direction]
            if directional:
                return directional[0]
        return matches[0]

    def _persist_open_connection(self, session: SessionState, origin: TileState, origin_exit: ExitState) -> None:
        origin_exit.status = "open"
        if origin_exit.kind == "door":
            origin_exit.door_open = True
        if not origin_exit.destination_tile_id:
            return
        destination = self._tile_by_id(session, origin_exit.destination_tile_id)
        if destination is None:
            return
        reciprocal = self._reciprocal_exit_on_tile(
            destination,
            origin.id,
            direction=OPPOSITE[origin_exit.direction],
        )
        if reciprocal is None:
            return
        self._sync_connection_state(origin_exit, reciprocal, passed_through=True)

    def _inherit_connection_from_reciprocal(
        self,
        session: SessionState,
        current: TileState,
        exit_state: ExitState,
    ) -> None:
        if exit_state.door_open or not exit_state.destination_tile_id:
            return
        other_tile = self._tile_by_id(session, exit_state.destination_tile_id)
        if other_tile is None:
            return
        reciprocal = self._reciprocal_exit_on_tile(
            other_tile,
            current.id,
            direction=OPPOSITE[exit_state.direction],
        )
        if reciprocal is None:
            return
        if reciprocal.kind == "passage" and reciprocal.status == "open":
            self._sync_connection_state(reciprocal, exit_state, passed_through=True)
            return
        if reciprocal.kind == "door" and reciprocal.door_open:
            self._sync_connection_state(reciprocal, exit_state, passed_through=True)
            return

    def _refresh_tile_connections(self, session: SessionState, tile: TileState) -> None:
        for exit_state in tile.exits:
            if not exit_state.destination_tile_id:
                continue
            self._inherit_connection_from_reciprocal(session, tile, exit_state)
            if exit_state.kind == "door" and exit_state.door_open:
                self._sync_linked_door(session, tile, exit_state)

    def _initialize_outside_entrance(
        self,
        entrance: TileState,
        *,
        log: list[str] | None = None,
    ) -> bool:
        """Rulebook p.25: the party enters through the outside door; it stands open behind them."""
        changed = False
        for exit_state in entrance.exits:
            if not exit_state.dungeon_exit or exit_state.nailed_shut or exit_state.door_destroyed:
                continue
            if exit_state.status == "open" and (
                exit_state.kind != "door" or exit_state.door_open
            ):
                continue
            exit_state.status = "open"
            if exit_state.kind == "door":
                exit_state.door_open = True
                exit_state.door_type = exit_state.door_type or "unlocked"
            changed = True
            if log is not None:
                log.append(
                    f"The party entered through the {exit_state.direction} door; it remains open behind them."
                )
        return changed

    def _open_entrance_threshold(
        self,
        session: SessionState,
        exit_state: ExitState,
        *,
        show_rolls: bool,
    ) -> None:
        """Rulebook p.25: the party chooses an entrance door into the dungeon (no separate open step)."""
        exit_state.door_open = True
        exit_state.status = "open"
        if show_rolls:
            session.log.append(
                f"The party passes through the {exit_state.direction} entrance into the dungeon."
            )

    def _sync_linked_door(self, session: SessionState, current: TileState, exit_state: ExitState) -> None:
        if exit_state.kind != "door" or not exit_state.destination_tile_id:
            return
        other_tile = self._tile_by_id(session, exit_state.destination_tile_id)
        if other_tile is None:
            return
        reciprocal = self._reciprocal_exit_on_tile(
            other_tile,
            current.id,
            direction=OPPOSITE[exit_state.direction],
        )
        if reciprocal:
            self._sync_connection_state(exit_state, reciprocal, passed_through=exit_state.door_open)
            if not exit_state.nailed_shut:
                reciprocal.status = "open"

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
        if self._outside_paper_bounds(session, candidate_cells):
            return True
        if any(candidate_cells.intersection(self._visible_cells(tile)) for tile in session.map_state.tiles):
            return True
        reserved_exit_cells = self._reserved_exit_cells(session, origin, origin_exit)
        return bool(candidate_cells.intersection(reserved_exit_cells))

    def _outside_paper_bounds(self, session: SessionState, cells: set[tuple[int, int]]) -> bool:
        if session.map_bounds_mode != "paper":
            return False
        width = session.map_state.width
        height = session.map_state.height
        return any(cell_x < 0 or cell_y < 0 or cell_x >= width or cell_y >= height for cell_x, cell_y in cells)

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

    def _seed_tile_features(
        self,
        tile: TileState,
        hcl: int,
        *,
        show_rolls: bool,
        session: SessionState | None = None,
    ) -> None:
        if tile.content_key in {"treasure", "trap_treasure"} or any("treasure" in item.lower() for item in tile.objects):
            outcome = self.table_roller.roll_treasure(environment=session.environment if session else "dungeon")
            if show_rolls and session is not None:
                session.log.extend(outcome.log)
            if outcome.gold or outcome.items:
                tile.treasure_summary = outcome.summary
                tile.treasure_gold = outcome.gold
                tile.treasure_items = (
                    self._finalize_treasure_items(session, list(outcome.items), show_rolls=show_rolls)
                    if session is not None
                    else list(outcome.items)
                )
                if show_rolls and session is not None:
                    session.log.append("Treasure is available to claim.")
            else:
                tile.treasure_summary = outcome.summary
                tile.objects = [item for item in tile.objects if "treasure" not in item.lower()]
                empty_msg = outcome.summary or "No treasure found."
                self._apply_empty_treasure_description(tile, empty_msg)
                if show_rolls and session is not None:
                    session.log.append(empty_msg)
        if tile.content_key == "trap_treasure" or any("trap" in item.lower() for item in tile.objects):
            trap = self.table_roller.roll_trap(
                hcl,
                show_rolls=show_rolls,
                explain_math=False,
                environment=session.environment if session else "dungeon",
            )
            tile.trap_key = trap.trap_key
            tile.trap_level = trap.trap_level
            tile.objects = [item for item in tile.objects if item.lower() != "trap"] + [trap.summary]
        self._apply_treasure_doubling(tile)

    def _apply_empty_treasure_description(self, tile: TileState, empty_msg: str) -> None:
        if tile.content_key == "trap_treasure":
            tile.description = tile.description.replace(
                "Treasure is protected by a trap.",
                f"{empty_msg} A trap remains.",
            )
        elif tile.content_key == "treasure":
            tile.description = tile.description.replace("There is treasure here.", empty_msg)
            tile.content_key = "empty"
        elif "There is treasure here." in tile.description:
            tile.description = tile.description.replace("There is treasure here.", empty_msg)

    def _apply_treasure_doubling(self, tile: TileState) -> None:
        if not tile.treasure_doubled or not tile.treasure_gold:
            return
        tile.treasure_gold *= 2
        if tile.treasure_summary:
            tile.treasure_summary = f"{tile.treasure_summary} (doubled behind secret door: {tile.treasure_gold}gp)."

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
        if tile.content_key == "special_event":
            self._apply_special_event(session, tile, show_rolls=show_rolls, explain_math=explain_math)
        elif tile.content_key == "special_feature":
            self._apply_special_feature(session, tile, show_rolls=show_rolls, explain_math=explain_math)

    def _apply_special_event(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        hcl = self._highest_character_level(session.party)
        outcome = self.table_roller.roll_special_event(
            healer_met=session.wandering_healer_met,
            alchemist_met=session.wandering_alchemist_met,
            lady_in_white_refused=session.lady_in_white_refused,
            environment=session.environment,
        )
        if show_rolls:
            session.log.append(f"Special event: {outcome.result}")
        if outcome.key == "ghost" or outcome.key == "spore_vision":
            self._resolve_ghost_event(session, show_rolls=show_rolls)
        elif outcome.key == "rockfall":
            self._resolve_rockfall_event(session, show_rolls=show_rolls)
        elif outcome.key == "lost":
            session.log.append(
                "The party is disoriented. On the next move, the lantern-bearer must Save vs "
                "L1+exits/doors into this area or the party moves randomly."
            )
        elif outcome.key == "wandering_monsters":
            self._spawn_wandering_monsters(session, tile, show_rolls=show_rolls, special_event=True)
        elif outcome.key == "lady_in_white":
            if session.active_quest is not None:
                session.log.append("The Lady in White waits while your current Quest is unfinished.")
            elif session.lady_in_white_refused:
                session.log.append("The Lady in White will not appear again this adventure.")
            else:
                tile.lady_in_white_available = True
                session.log.append(
                    "The Lady in White offers a Quest. Accept to roll on the Quest Table; "
                    "refuse and she will not appear again this adventure."
                )
        elif outcome.key == "trap":
            trap = self.table_roller.roll_trap(
                hcl,
                show_rolls=show_rolls,
                explain_math=explain_math,
                environment=session.environment,
            )
            tile.trap_key = trap.trap_key
            tile.trap_level = trap.trap_level
            tile.objects.append(trap.summary)
            session.log.append(trap.summary)
        elif outcome.key == "healer":
            session.wandering_healer_met = True
            tile.healer_available = True
            session.log.append(
                "A wandering healer is here: 10gp restores 1 Life (use Buy Healing on party sheets)."
            )
        elif outcome.key == "alchemist":
            session.wandering_alchemist_met = True
            tile.alchemist_available = True
            session.log.append(
                "A wandering alchemist is here: Potion of Healing 50gp or blade poison 30gp, once per hero."
            )
        tile.objects = [item for item in tile.objects if item != "Special Event"]

    def _resolve_ghost_event(self, session: SessionState, *, show_rolls: bool) -> None:
        fear_level = 4
        for member in session.party:
            if member.current_life <= 0:
                continue
            if member.class_id.lower() == "paladin":
                session.log.append(f"{member.name} is immune to the ghost's fear.")
                continue
            modifier = member.level if member.class_id.lower() == "cleric" else 0
            total, rolls = roll_exploding_for_level(member.level)
            if show_rolls:
                detail = f" {' + '.join(str(value) for value in rolls)}"
                if modifier:
                    detail += f" + {modifier}"
                session.log.append(f"{member.name} fear Save vs L{fear_level}:{detail}.")
            if rolls[0] == 1 or total + modifier < fear_level:
                member.current_life = max(0, member.current_life - 1)
                session.log.append(f"{member.name} loses 1 Life to fear.")
            else:
                session.log.append(f"{member.name} shrugs off the ghost.")

    def _resolve_rockfall_event(self, session: SessionState, *, show_rolls: bool) -> None:
        dodge_level = 4
        for member in session.party:
            if member.current_life <= 0:
                continue
            modifier = save_modifier(member) + encumbrance_penalty(member)
            if member.class_id.lower() == "rogue":
                modifier += member.level
            if member.class_id.lower() in {"halfling", "elf"}:
                modifier += 1
            total, rolls = roll_exploding_for_level(member.level)
            if show_rolls:
                detail = f" {' + '.join(str(value) for value in rolls)}"
                if modifier:
                    detail += f" + {modifier}"
                session.log.append(f"{member.name} dodge Save vs L{dodge_level}:{detail}.")
            if rolls[0] == 1 or total + modifier < dodge_level:
                member.current_life = max(0, member.current_life - 1)
                session.log.append(f"{member.name} loses 1 Life to the rockfall.")
            else:
                session.log.append(f"{member.name} dodges the falling rocks.")

    def _apply_special_feature(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        hcl = self._highest_character_level(session.party)
        outcome = self.table_roller.roll_special_feature()
        if show_rolls:
            session.log.append(f"Special feature: {outcome.result}")
        if outcome.key == "fountain":
            if session.fountain_used:
                session.log.append("The fountain has no further effect this adventure.")
            else:
                healed: list[str] = []
                for member in session.party:
                    if member.current_life > 0 and member.current_life < member.max_life:
                        member.current_life += 1
                        healed.append(member.name)
                session.fountain_used = True
                if healed:
                    session.log.append(f"The fountain restores 1 Life: {', '.join(healed)}.")
                else:
                    session.log.append("The fountain refreshes the party but no one needed healing.")
        elif outcome.key == "blessed_temple":
            living = [member for member in session.party if member.current_life > 0]
            if living:
                chosen = living[0]
                session.blessed_undead_bonus_character_id = chosen.character_id
                session.log.append(
                    f"{chosen.name} gains +1 Attack vs undead or demons until one is slain."
                )
        elif outcome.key == "armory":
            session.log.append("The armory allows weapon changes within class limits.")
        elif outcome.key == "cursed_altar":
            living = [member for member in session.party if member.current_life > 0]
            if living:
                cursed = random.choice(living)
                session.cursed_character_id = cursed.character_id
                session.log.append(f"{cursed.name} is cursed (-1 Defense until broken).")
        elif outcome.key == "statue":
            self._resolve_statue_feature(session, tile, hcl, show_rolls=show_rolls)
        elif outcome.key == "puzzle_box":
            self._resolve_puzzle_box(session, tile, hcl, show_rolls=show_rolls, explain_math=explain_math)
        tile.objects = [item for item in tile.objects if item != "Special Feature"]

    def _resolve_statue_feature(self, session: SessionState, tile: TileState, hcl: int, *, show_rolls: bool) -> None:
        roll = roll_d6()
        if show_rolls:
            session.log.append(f"Statue touch roll: d6 = {roll}.")
        if roll <= 3:
            level = max(1, hcl + 3)
            life = max(5, hcl + 5)
            tile.enemies.append(
                EnemyState(
                    id=uuid4().hex,
                    name="Living Statue",
                    category="boss",
                    level=level,
                    life=life,
                    max_life=life,
                    attacks=max(1, (hcl + 2) // 2),
                    tags=["boss", "artificial"],
                )
            )
            tile.initial_enemy_count = len(tile.enemies)
            self._begin_combat(session, "The statue animates and attacks!")
        else:
            gold = resolve_gold_formula("3d6*10", hcl=0)
            tile.treasure_summary = f"Broken statue yields {gold}gp."
            tile.treasure_gold = gold
            session.log.append(f"The statue breaks open, revealing {gold}gp (no XP).")

    def _resolve_puzzle_box(
        self,
        session: SessionState,
        tile: TileState,
        hcl: int,
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        box_level = roll_d6()
        member = self._member_by_marching_order(session, 1)
        if member is None:
            session.log.append("No one is available to solve the puzzle box.")
            return
        modifier = member.level if member.class_id.lower() in {"wizard", "rogue"} else 0
        total, rolls = roll_exploding_for_level(member.level)
        if show_rolls:
            detail = f" {' + '.join(str(value) for value in rolls)}"
            if modifier:
                detail += f" + {modifier}"
            session.log.append(
                f"Puzzle box (L{box_level}): {member.name} Save{detail}."
            )
        if rolls[0] != 1 and total + modifier >= box_level:
            outcome = self.table_roller.roll_treasure(environment=session.environment if session else "dungeon")
            if show_rolls:
                session.log.extend(outcome.log)
            tile.treasure_summary = outcome.summary
            tile.treasure_gold = outcome.gold
            tile.treasure_items = self._finalize_treasure_items(session, list(outcome.items), show_rolls=show_rolls)
            session.log.append("The puzzle box opens!")
            self._apply_treasure_doubling(tile)
        else:
            member.current_life = max(0, member.current_life - 1)
            session.log.append(f"{member.name} takes 1 damage from the puzzle box.")

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
            servant_active=has_illusionary_servant(session, member.character_id),
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
        member = next(
            (
                item
                for item in sorted(session.party, key=lambda row: row.marching_order)
                if item.current_life > 0 and item.class_id.lower() == "rogue"
            ),
            None,
        )
        trap_level = tile.trap_level or self._highest_character_level(session.party)
        if member is not None:
            total, rolls = roll_exploding_for_level(member.level)
            modifier = member.level
            if show_rolls:
                session.log.append(
                    f"Disarm attempt: {member.name} rolls {' + '.join(str(value) for value in rolls)} + {modifier}."
                )
            if rolls[0] != 1 and total + modifier >= trap_level:
                tile.trap_resolved = True
                session.log.append("The rogue disarms the trap.")
                return
            session.log.append("The rogue fails to disarm the trap.")
        gnome = next(
            (
                item
                for item in sorted(session.party, key=lambda row: row.marching_order)
                if item.current_life > 0 and item.class_id.lower() == "gnome"
            ),
            None,
        )
        if gnome is not None:
            ok, log = attempt_gnome_trap_disarm(session, gnome, trap_level, show_rolls=show_rolls)
            session.log.extend(log)
            if ok:
                tile.trap_resolved = True
                tile.objects = [item for item in tile.objects if "trap" not in item.lower()]
                self._announce_hidden_treasure_claimable(session, tile)
                return
            session.log.append("The gnome fails to disarm the trap.")
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
        if session.illusionary_servant_active:
            self._dismiss_illusionary_servant(session, "trapped by the mechanism")
        self._announce_hidden_treasure_claimable(session, tile)

    def _servant_owner_ids(self, session: SessionState) -> set[str]:
        if session.illusionary_servant_active and session.illusionary_servant_owner_id:
            return {session.illusionary_servant_owner_id}
        return set()

    def _dismiss_illusionary_servant(self, session: SessionState, reason: str) -> None:
        if not session.illusionary_servant_active:
            return
        session.illusionary_servant_active = False
        session.illusionary_servant_owner_id = None
        session.log.append(f"The illusionary servant is lost ({reason}).")

    def _award_treasure(self, session: SessionState, tile: TileState, *, show_rolls: bool) -> None:
        if tile.treasure_claimed or tile.treasure_summary or tile.treasure_gold or tile.treasure_items:
            return
        if tile.content_key in {"treasure", "trap_treasure"} or tile.resolved:
            outcome = self.table_roller.roll_treasure(environment=session.environment if session else "dungeon")
            if show_rolls:
                session.log.extend(outcome.log)
            if outcome.gold or outcome.items:
                tile.treasure_summary = outcome.summary
                tile.treasure_gold = outcome.gold
                tile.treasure_items = self._finalize_treasure_items(session, list(outcome.items), show_rolls=show_rolls)
                if tile.final_boss_treasure:
                    tile.treasure_gold = apply_final_boss_treasure_bonus(tile.treasure_gold)
                    if len(tile.treasure_items) == 1:
                        tile.treasure_items.append(tile.treasure_items[0])
                    tile.treasure_summary = (
                        f"Final Boss treasure: {tile.treasure_gold}gp"
                        + (f", {', '.join(tile.treasure_items)}" if tile.treasure_items else "")
                    )
                self._apply_treasure_doubling(tile)
                session.pending_treasure_reroll_tile_id = tile.id
                session.log.append("Treasure is available to claim.")
            else:
                tile.treasure_summary = outcome.summary
                session.log.append(outcome.summary or "No treasure found.")

    def _claim_treasure(self, session: SessionState) -> None:
        tile = self._current_tile(session)
        if tile.trap_key and not tile.trap_resolved:
            session.log.append("Resolve the trap before claiming treasure.")
            return
        if tile.treasure_claimed:
            session.log.append("Treasure has already been claimed here.")
            return
        if not tile.treasure_gold and not tile.treasure_items:
            if tile.treasure_summary:
                session.log.append(tile.treasure_summary)
            else:
                session.log.append("There is no treasure here.")
            return
        survivors = sorted(
            [member for member in session.party if member.current_life > 0],
            key=lambda member: member.marching_order,
        )
        if not survivors:
            session.log.append("There is no one left to carry treasure.")
            return
        gold_total = tile.treasure_gold
        if tile.final_boss_treasure and gold_total:
            gold_total = apply_final_boss_treasure_bonus(gold_total)
        remaining_gold, payouts = distribute_gold_among(
            survivors,
            gold_total,
            servant_owner_ids=self._servant_owner_ids(session),
        )
        items = list(tile.treasure_items)
        if tile.final_boss_treasure and len(items) == 1:
            items.append(items[0])
        uncarried_items, placed_items = distribute_items_among(survivors, items)
        if session.xp_system == "old_school" and gold_total:
            session.old_school_xp_tally += gold_total
            session.log.append(f"Old School XP +{gold_total} from treasure (tally {session.old_school_xp_tally}).")
        tile.treasure_gold = remaining_gold
        tile.treasure_items = uncarried_items
        tile.treasure_claimed = remaining_gold <= 0 and not uncarried_items
        summary = tile.treasure_summary or "Treasure"
        if tile.treasure_claimed:
            session.log.append(f"Treasure claimed: {summary}")
        else:
            session.log.append(f"Treasure partially claimed: {summary}")
        if payouts:
            session.log.append(f"Gold split: {', '.join(payouts)}.")
        if remaining_gold:
            session.log.append(
                f"{remaining_gold}gp left behind (each hero carries at most 200gp)."
            )
        if placed_items:
            item_list = ", ".join(placed_items)
            session.log.append(f"Items added to party inventories: {item_list}.")
        if uncarried_items:
            item_list = ", ".join(uncarried_items)
            session.log.append(
                f"Could not carry: {item_list} (weapon/shield limits or no free carrier)."
            )
        if tile.treasure_claimed:
            tile.objects = [item for item in tile.objects if "treasure" not in item.lower()]

    def _carry_body(
        self,
        session: SessionState,
        carrier_id: str | None,
        fallen_id: str | None,
    ) -> None:
        tile = self._current_tile(session)
        if not carrier_id or not fallen_id:
            session.log.append("Choose who carries which fallen hero.")
            return
        session.log.extend(start_carrying_body(session, tile, carrier_id, fallen_id))

    def _drop_body(self, session: SessionState) -> None:
        tile = self._current_tile(session)
        session.log.extend(drop_carried_body(session, tile))

    def _attempt_resurrection(
        self,
        session: SessionState,
        fallen_id: str | None,
        *,
        show_rolls: bool,
    ) -> None:
        session.log.extend(attempt_resurrection(session, fallen_id, show_rolls=show_rolls))

    def _use_bandage(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        show_rolls: bool,
    ) -> None:
        if session.mode == "combat":
            session.log.append("Bandages cannot be applied during combat.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None:
            session.log.append("Choose a hero to apply the bandage.")
            return
        ok, message = can_use_bandage(
            member,
            bandage_used_character_ids=set(session.bandage_used_character_ids),
        )
        if not ok:
            session.log.append(message)
            return
        bandage_name = bandages_in_inventory(member)[0]
        member.inventory = [item for item in member.inventory if item != bandage_name]
        member.current_life = min(member.max_life, member.current_life + 1)
        session.bandage_used_character_ids.append(member.character_id)
        if show_rolls:
            session.log.append(
                f"{member.name} applies {bandage_name} and recovers 1 Life "
                f"({member.current_life}/{member.max_life})."
            )

    def _end_bear_form(self, session: SessionState) -> None:
        owner_id = session.bear_form_owner_id
        if not owner_id:
            return
        member = next((item for item in session.party if item.character_id == owner_id), None)
        if member is None:
            session.bear_form_owner_id = None
            session.bear_form_start_life = 0
            session.bear_form_pre_life = 0
            return
        damage_as_bear = max(0, session.bear_form_start_life - member.current_life)
        carry_over = damage_as_bear // 2
        member.current_life = max(0, session.bear_form_pre_life - carry_over)
        if damage_as_bear:
            session.log.append(
                f"{member.name} reverts from bear form; half the wounds carry over ({carry_over} damage)."
            )
        elif any(status.strip().lower() == "bear form" for status in member.statuses):
            session.log.append(f"{member.name} reverts from bear form unscathed.")
        session.bear_form_owner_id = None
        session.bear_form_start_life = 0
        session.bear_form_pre_life = 0

    def _foes_strike_summoned_beast(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
    ) -> None:
        if session.summoned_beast_life <= 0:
            return
        living_foes = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living_foes:
            return
        owner = next((m for m in session.party if m.character_id == session.summoned_beast_owner_id), None)
        if owner is None or owner.current_life <= 0:
            session.summoned_beast_life = 0
            session.summoned_beast_owner_id = None
            return
        attacker = living_foes[0]
        beast_level = 3
        total, rolls = roll_exploding_for_level(attacker.level)
        if show_rolls:
            session.log.append(
                f"{attacker.name} strikes the summoned beast: "
                f"{' + '.join(str(value) for value in rolls)} = {total} vs L{beast_level}."
            )
        if not attack_hits(total, beast_level):
            session.log.append("The summoned beast shrugs off the blow.")
            return
        session.summoned_beast_life = max(0, session.summoned_beast_life - 1)
        session.log.append(
            f"The summoned beast takes 1 damage ({session.summoned_beast_life} Life remaining)."
        )
        if session.summoned_beast_life <= 0:
            session.summoned_beast_owner_id = None
            session.log.append("The summoned beast is slain.")

    def _use_holy_water(
        self,
        session: SessionState,
        character_id: str | None,
        item_name: str | None = None,
        *,
        target_enemy_id: str | None = None,
        show_rolls: bool = True,
    ) -> None:
        if session.mode != "combat":
            session.log.append("Holy water can only be thrown during combat.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to throw holy water.")
            return
        if barbarian_cannot_use_magic(member.class_id):
            session.log.append(
                f"{member.name} cannot use holy water (barbarians may not use magic items). "
                "Transfer the vial to an ally."
            )
            return
        available = [item for item in member.inventory if is_holy_water(item)]
        if not available:
            session.log.append(f"{member.name} has no holy water.")
            return
        vial_name = item_name if item_name and item_name in member.inventory and is_holy_water(item_name) else None
        if vial_name is None:
            vial_name = available[0] if len(available) == 1 else None
        if vial_name is None:
            session.log.append("Choose which holy water vial to throw.")
            return

        tile = self._current_tile(session)
        living_enemies = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living_enemies:
            session.log.append("There are no foes to target.")
            return
        undead_foes = [enemy for enemy in living_enemies if is_undead_foe(enemy)]
        if not undead_foes:
            session.log.append("There are no undead foes to target with holy water.")
            return
        target = next((enemy for enemy in undead_foes if enemy.id == target_enemy_id), None)
        if target is None:
            target = undead_foes[0]

        self._commit_immediate_attack(session)
        member.inventory = [item for item in member.inventory if item != vial_name]
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {pc.character_id for pc in session.party if pc.current_life > 0}
        log_lines, _hit = throw_holy_water(member, target, show_rolls=show_rolls)
        session.log.extend(log_lines)
        if not any(enemy.life > 0 for enemy in tile.enemies):
            self._apply_combat_result(
                session,
                tile,
                CombatRound(
                    party=session.party,
                    enemies=tile.enemies,
                    log=[],
                    combat_over=True,
                ),
                show_rolls=show_rolls,
                active_enemy_ids=active_enemy_ids,
                standing_before=standing_before,
            )

    def _use_potion(
        self,
        session: SessionState,
        character_id: str | None,
        item_name: str | None = None,
        *,
        show_rolls: bool,
    ) -> None:
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to use the potion.")
            return
        if barbarian_cannot_use_magic(member.class_id):
            session.log.append(
                f"{member.name} cannot use potions (barbarians may not use magic items, scrolls, or potions). "
                "Transfer the potion to an ally."
            )
            return

        available = usable_potions_in_inventory(member)
        if not available:
            session.log.append(f"{member.name} has no potions.")
            return
        potion_name = item_name if item_name and item_name in member.inventory else None
        if potion_name is None:
            if len(available) == 1:
                potion_name = available[0]
            else:
                session.log.append("Choose which potion to use.")
                return

        kind = potion_kind(potion_name)
        if kind == "sleep":
            if session.mode != "combat":
                session.log.append("Potion of Sleep can only be used during combat.")
                return
            tile = self._current_tile(session)
            if not any(enemy.life > 0 for enemy in tile.enemies):
                session.log.append("There are no foes to target.")
                return
            self._commit_immediate_attack(session)
            member.inventory = [item for item in member.inventory if item != potion_name]
            session.log.append(f"{member.name} quaffs {potion_name}.")
            active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
            standing_before = {pc.character_id for pc in session.party if pc.current_life > 0}
            outcome = cast_sleep_effect(member, session.party, tile.enemies, show_rolls=show_rolls)
            session.log.extend(outcome.log)
            session.party = outcome.party
            tile.enemies = outcome.enemies
            if outcome.combat_over and session.mode == "combat":
                self._record_peaceful_quest_progress(session)
                result = CombatRound(
                    party=outcome.party,
                    enemies=outcome.enemies,
                    log=[],
                    combat_over=True,
                )
                self._apply_combat_result(
                    session,
                    tile,
                    result,
                    show_rolls=show_rolls,
                    active_enemy_ids=active_enemy_ids,
                    standing_before=standing_before,
                )
            return

        if kind != "healing":
            session.log.append(f"{member.name} does not know how to use {potion_name}.")
            return
        if member.character_id in session.potion_used_character_ids:
            session.log.append(f"{member.name} already drank a Potion of Healing this adventure.")
            return
        member.inventory = [item for item in member.inventory if item != potion_name]
        lost_life = member.max_life - member.current_life
        member.current_life = member.max_life
        session.potion_used_character_ids.append(member.character_id)
        if show_rolls:
            session.log.append(
                f"{member.name} drinks {potion_name} and restores {lost_life} Life "
                f"({member.current_life}/{member.max_life})."
            )

    def _accept_quest(self, session: SessionState, *, show_rolls: bool) -> None:
        if session.mode == "combat":
            session.log.append("Deal with the fight before speaking to the Lady in White.")
            return
        tile = self._current_tile(session)
        if not tile.lady_in_white_available:
            session.log.append("The Lady in White is not here.")
            return
        if session.active_quest is not None:
            session.log.append("A Quest is already in progress.")
            return
        roll = roll_d6()
        if show_rolls:
            session.log.append(f"Quest roll: d6 = {roll}.")
        row = self.table_roller.lookup("quest_table", roll)
        if row is None:
            session.log.append("Quest table lookup failed.")
            return
        gold_required = None
        item_name = None
        if row["key"] == "bring_gold":
            gold_required = roll * 50
            party_gold = sum(member.gold for member in session.party if member.current_life > 0)
            if party_gold >= gold_required:
                gold_required *= 2
                session.log.append(f"Party already has {party_gold}gp; quest gold doubled to {gold_required}gp.")
        if row["key"] == "bring_item":
            magic_row = self.table_roller.lookup("dungeon_magic_treasure_table", roll_d6())
            if magic_row and magic_row.get("items"):
                item_name = magic_row["items"][0]
            elif magic_row:
                item_name = magic_row.get("result", "Magic item")
            else:
                item_name = "Magic item"
        quest = quest_from_row(row, tile_id=tile.id, gold_required=gold_required, item_name=item_name)
        session.active_quest = quest
        tile.lady_in_white_available = False
        session.log.append(f"Quest accepted: {quest.description}")
        if quest.gold_required:
            session.log.append(f"Deliver {quest.gold_required}gp to this tile to complete the Quest.")

    def _refuse_quest(self, session: SessionState) -> None:
        tile = self._current_tile(session)
        if not tile.lady_in_white_available:
            session.log.append("The Lady in White is not here.")
            return
        session.lady_in_white_refused = True
        tile.lady_in_white_available = False
        session.log.append("You refuse the Quest. The Lady in White vanishes and will not return this adventure.")

    def _claim_quest_reward(self, session: SessionState, *, show_rolls: bool) -> None:
        quest = session.active_quest
        if quest is None:
            session.log.append("No active Quest.")
            return
        if quest.reward_claimed:
            session.log.append("Quest reward already claimed.")
            return
        tile = self._current_tile(session)
        if not quest.completed:
            ready, message = quest_ready_to_complete(tile.id, quest, session)
            if not ready:
                session.log.append(message)
                return
            if quest.key == "bring_gold":
                remaining = quest.gold_required
                for member in sorted(session.party, key=lambda item: item.marching_order):
                    if remaining <= 0 or member.current_life <= 0:
                        continue
                    paid = min(member.gold, remaining)
                    member.gold -= paid
                    remaining -= paid
            quest.completed = True
        reward_roll = roll_d6()
        if show_rolls:
            session.log.append(f"Epic reward roll: d6 = {reward_roll}.")
        row = self.table_roller.lookup("epic_rewards_table", reward_roll)
        if row is None:
            session.log.append("Epic Rewards table lookup failed.")
            return
        reward_text = epic_reward_item(row)
        survivors = [member for member in session.party if member.current_life > 0]
        if not survivors:
            session.log.append("There is no survivor to receive the Quest reward.")
            return
        key = row.get("key", "")
        if key not in {"gold_of_kerrak_dar", "enchanted_weapon"}:
            item_label = reward_text.split(".")[0]
            ok, message = can_add_item(survivors[0], item_label)
            if not ok:
                session.log.append(message)
                return
        quest.reward_claimed = True
        session.log.append(f"Quest complete! Epic reward: {reward_text}")
        if key == "gold_of_kerrak_dar":
            session.log.append("Kerrak Dar's hoard: spend 1 Clue while Searching a tile to find 500gp.")
        elif key == "enchanted_weapon":
            survivors[0].statuses.append("Enchanted weapon")
            session.log.append(f"{survivors[0].name}'s weapon is enchanted until adventure end.")
        else:
            item_label = reward_text.split(".")[0]
            survivors[0].inventory.append(item_label)
            session.log.append(f"{survivors[0].inventory[-1]} added to {survivors[0].name}'s inventory.")
        session.active_quest = None

    def _record_peaceful_quest_progress(self, session: SessionState) -> None:
        quest = session.active_quest
        if quest is None or quest.key != "peaceful_way" or quest.completed:
            return
        quest.peaceful_count += 1
        session.log.append(
            f"Peaceful quest progress: {quest.peaceful_count}/{quest.peaceful_required}."
        )
        if quest.peaceful_count >= quest.peaceful_required:
            quest.completed = True
            session.log.append("Peaceful quest objective complete! Claim your Epic reward.")

    def _update_quest_on_combat_end(
        self,
        session: SessionState,
        defeated: list[EnemyState],
        *,
        show_rolls: bool,
    ) -> None:
        quest = session.active_quest
        if quest is None or quest.completed:
            return
        for enemy in defeated:
            if quest.key == "bring_item" and enemy.category in {"weird", "boss"}:
                if roll_d6() == 1:
                    quest.item_collected = True
                    session.log.append(f"Quest item found: {quest.item_name}.")
            if enemy.category == "boss":
                if quest.key == "bring_head" and quest.boss_slay_pending and not enemy.subdued:
                    quest.boss_slay_pending = False
                    quest.completed = True
                    session.log.append("Quest target slain! Return to the Quest-giver for your reward.")
                elif quest.key == "bring_alive" and quest.boss_capture_pending and enemy.subdued:
                    quest.boss_capture_pending = False
                    quest.captured_boss_name = enemy.name
                    quest.completed = True
                    session.log.append(
                        f"{enemy.name} was subdued alive! Return to the Quest-giver for your reward."
                    )
        if quest.key == "slay_all" and session.final_boss_defeated:
            all_clear = all(not any(e.life > 0 for e in tile.enemies) for tile in session.map_state.tiles)
            if all_clear:
                quest.completed = True
                session.log.append("Slay-all quest complete! Claim your Epic reward from the log.")

    def _old_school_level_up(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        show_rolls: bool,
        new_spell: str | None = None,
    ) -> None:
        if session.level_up_spell_pending_character_id:
            session.log.append("Finish the pending spell choice before leveling again.")
            return
        if session.xp_system != "old_school":
            session.log.append("Old School leveling is not active for this adventure.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to advance.")
            return
        if not self._can_assign_level_up(session, character_id or ""):
            session.log.append("Another hero must level next (same PC cannot level twice in a row).")
            return
        cost = old_school_level_cost(member.level)
        if session.old_school_xp_tally < cost:
            session.log.append(f"Need {cost} XP (tally {session.old_school_xp_tally}).")
            return
        session.old_school_xp_tally -= cost
        self._complete_level_up(session, member, new_spell=new_spell)
        if show_rolls:
            session.log.append(f"Old School XP spent: {cost} (tally {session.old_school_xp_tally}).")

    def _slower_xp_spend(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        xp_spent: int | None,
        show_rolls: bool,
        explain_math: bool,
        new_spell: str | None = None,
        advancement_fork: str | None = None,
        expert_skill_id: str | None = None,
        expert_skill_target: str | None = None,
    ) -> None:
        if session.level_up_spell_pending_character_id:
            session.log.append("Finish the pending spell choice before spending more banked XP.")
            return
        if session.xp_system != "slower_advancement":
            session.log.append("Slower Advancement is not active for this adventure.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to advance.")
            return
        if not self._can_assign_level_up(session, character_id or ""):
            session.log.append("Another hero must level next (same PC cannot level twice in a row).")
            return
        target_level = member.level + 1
        minimum = target_level
        spent = xp_spent if xp_spent is not None else minimum
        if spent < minimum:
            session.log.append(f"Spend at least {minimum} banked XP to try for Level {target_level}.")
            return
        if session.slower_xp_bank < spent:
            session.log.append(f"Need {spent} banked XP (have {session.slower_xp_bank}).")
            return

        fork = advancement_fork or "level_up"
        if fork not in {"level_up", "learn_expert_skill"}:
            session.log.append("Choose Level up or Learn expert skill (Level 5+).")
            return
        if fork == "level_up":
            gate = level_up_gate_reason(member, target_level)
            if gate:
                session.log.append(gate)
                return
        else:
            if member.level < 5:
                session.log.append("Expert skills require Level 5+.")
                return
            if not expert_skill_id:
                session.log.append("Choose an expert skill or spell to learn.")
                return
            blocked = validate_expert_skill_choice(member, expert_skill_id, self.rules.expert_skills())
            if blocked:
                session.log.append(blocked)
                return

        purpose = "level_up" if fork == "level_up" else "learn_expert_skill"
        session.slower_xp_bank -= spent
        bonus = spent - minimum
        result = perform_advancement_roll(member, bonus=bonus, purpose=purpose)
        if show_rolls:
            label = "Level-up" if fork == "level_up" else "Expert skill"
            session.log.append(
                f"Slower {label.lower()} for {member.name}: {spent} XP banked, "
                f"{result.die_label} = {result.natural}"
                + (f" + {result.modifier} = {result.total}" if result.modifier else "")
                + f" vs Level {member.level}."
            )
        if explain_math:
            session.log.append(advancement_roll_explain(member))
        if advancement_succeeds(result, member.level):
            if fork == "level_up":
                self._complete_level_up(session, member, new_spell=new_spell)
            else:
                session.log.extend(
                    apply_expert_skill_learn(
                        member,
                        expert_skill_id or "",
                        self.rules.expert_skills(),
                        target=expert_skill_target,
                    )
                )
        elif fork == "level_up":
            session.log.append(f"{member.name} fails to advance (needs > {member.level} with bonus).")
        else:
            session.log.append(f"{member.name} fails to learn the expert skill (needs > {member.level} with bonus).")

    def _enter_tier_training(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        tier: str | None,
        use_xp: bool,
        show_rolls: bool,
    ) -> None:
        if session.mode == "combat":
            session.log.append("Tier training waits until combat ends.")
            return
        if tier not in {"expert", "heroic", "legendary"}:
            session.log.append("Choose Expert, Heroic, or Legendary tier training.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None:
            session.log.append("Choose a hero for tier training.")
            return
        blocked = tier_entry_blocked_reason(member, tier)
        if blocked:
            session.log.append(blocked)
            return
        spec = tier_entry_requirements(tier)
        xp_cost = int(spec.get("xp", 0))
        gold_cost = int(spec.get("gold", 0))

        if tier == "expert" and use_xp:
            xp_alt = int(spec.get("xp_alt", 0))
            if xp_alt <= 0:
                session.log.append("Expert training requires gold payment.")
                return
            if session.xp_rolls_pending < xp_alt:
                session.log.append(f"Need {xp_alt} banked XP roll (have {session.xp_rolls_pending}).")
                return
            session.xp_rolls_pending -= xp_alt
            if show_rolls:
                session.log.append(
                    f"{member.name} enters Expert tier (1 banked XP roll spent; no gold)."
                )
        else:
            if xp_cost > 0:
                if session.xp_rolls_pending < xp_cost:
                    session.log.append(
                        f"Need {xp_cost} banked XP roll(s) for {tier.title()} training "
                        f"(have {session.xp_rolls_pending})."
                    )
                    return
                session.xp_rolls_pending -= xp_cost
            payer = next((item for item in session.party if item.gold >= gold_cost), None)
            if payer is None:
                if xp_cost > 0:
                    session.xp_rolls_pending += xp_cost
                session.log.append(f"Need {gold_cost} gp somewhere in the party for {tier.title()} training.")
                return
            payer.gold -= gold_cost
            if show_rolls:
                parts = [f"{gold_cost} gp from {payer.name}"]
                if xp_cost:
                    parts.append(f"{xp_cost} banked XP roll(s)")
                session.log.append(
                    f"{member.name} enters {tier.title()} tier ({', '.join(parts)})."
                )

        if tier == "expert":
            member.expert_trained = True
        elif tier == "heroic":
            member.heroic_trained = True
        elif tier == "legendary":
            member.legendary_trained = True

    def _touch(self, session: SessionState) -> SessionState:
        session.updated_at = now_utc()
        return session
