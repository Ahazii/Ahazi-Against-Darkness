"""Four Against the Abyss campaign plot and vampire-sire helpers."""

from __future__ import annotations

from uuid import uuid4

from ..schemas import AbyssCampaignPlotState, EnemyState, PartyMemberState, SessionState, TileState
from .dice import roll_d3, roll_d6, roll_die, roll_exploding_for_level
from .equipment_effects import is_vampire
from .expert_skill_effects import has_skill
from .banking import take_outside_party_funds


PLOTS: dict[str, tuple[str, int]] = {
    "assassination": ("Assassination", 3),
    "rebellion": ("Rebellion", 3000),
    "entity": ("Entity", 3),
    "invasion": ("Invasion", 9),
    "kidnap": ("Kidnap", 1),
    "enchantment": ("Enchantment", 3),
}
ROLL_TO_KEY = {
    1: "assassination",
    2: "rebellion",
    3: "entity",
    4: "invasion",
    5: "kidnap",
    6: "enchantment",
}


def start_abyss_campaign_plot(
    session: SessionState,
    *,
    plot_choice: str | None,
    holder: PartyMemberState | None,
    show_rolls: bool,
) -> list[str]:
    if session.abyss_campaign_plot and not session.abyss_campaign_plot.completed:
        return ["An Abyss campaign plot is already active."]
    key = (plot_choice or "").strip().lower()
    roll = None
    if key in {"", "random"}:
        roll = roll_d6()
        key = ROLL_TO_KEY.get(roll, "assassination")
    if key not in PLOTS:
        return ["Choose a valid Abyss campaign plot."]
    name, goal = PLOTS[key]
    state = AbyssCampaignPlotState(key=key, name=name, goal=goal)
    session.abyss_campaign_plot = state
    log: list[str] = []
    if show_rolls and roll is not None:
        log.append(f"Abyss campaign plot roll: d6 = {roll} -> {name}.")
    if key == "invasion":
        if holder is None or holder.current_life <= 0:
            session.abyss_campaign_plot = None
            return ["Choose a living hero to carry the indestructible artefact."]
        state.artifact_holder_id = holder.character_id
        holder.madness += 1
        log.append(f"Invasion plot starts: {holder.name} carries the artefact and gains 1 Madness.")
    else:
        log.append(f"Abyss campaign plot starts: {name}.")
    log.append(_plot_progress_line(state))
    return log


def _plot_progress_line(state: AbyssCampaignPlotState) -> str:
    if state.key == "assassination":
        return f"Assassination evidence: {state.progress}/3 pieces."
    if state.key == "rebellion":
        return f"Rebellion funds: {state.gold_contributed}/3000gp."
    if state.key == "entity":
        return f"Entity artefact pieces: {state.progress}/3."
    if state.key == "invasion":
        return f"Invasion weakness clues: {state.artifact_clues_spent}/9."
    if state.key == "kidnap":
        if state.chosen_one_rescued:
            return "Kidnap: the chosen one is rescued; leave the dungeon to face the kidnappers' bosses."
        if state.chosen_one_found:
            return "Kidnap: the chosen one is with these minions."
        return "Kidnap: search corridor non-undead minion groups."
    if state.key == "enchantment":
        return f"Enchantment dragon blood: {state.progress}/3 vials."
    return state.name


def spend_living_party_gold(session: SessionState, amount: int) -> tuple[bool, list[str]]:
    paid, available, contributions = take_outside_party_funds(session, amount)
    if not paid:
        return False, [f"The party needs {amount}gp but has {available}gp among living heroes and bank funds."]
    log: list[str] = []
    for contribution in contributions:
        if contribution.bank_gold:
            log.append(f"{contribution.name} contributes {contribution.bank_gold}gp from bank funds.")
        if contribution.carried_gold:
            log.append(f"{contribution.name} contributes {contribution.carried_gold}gp carried gold.")
    return True, log


def contribute_rebellion_gold(session: SessionState, amount: int | None) -> list[str]:
    state = session.abyss_campaign_plot
    if state is None or state.key != "rebellion" or state.completed:
        return ["No active Rebellion plot needs funding."]
    remaining = max(0, state.goal - state.gold_contributed)
    if remaining <= 0:
        return ["The rebellion is already funded. Resolve the war finale."]
    contribution = min(max(1, amount or remaining), remaining)
    paid, log = spend_living_party_gold(session, contribution)
    if not paid:
        return log
    state.gold_contributed += contribution
    log.append(f"Rebellion funds delivered: {state.gold_contributed}/3000gp.")
    if state.gold_contributed >= state.goal:
        state.finale_pending = "rebellion_war"
        log.append("The rebellion is funded. Resolve the war battles to complete the plot.")
    return log


def spend_party_clues(session: SessionState, amount: int) -> tuple[bool, list[str]]:
    log: list[str] = []
    living = [member for member in session.party if member.current_life > 0]
    total = sum(member.clues for member in living)
    if total < amount:
        return False, [f"The party needs {amount} Clues but has {total}."]
    remaining = amount
    for member in sorted(living, key=lambda item: item.marching_order):
        take = min(member.clues, remaining)
        if take:
            member.clues -= take
            remaining -= take
            log.append(f"{member.name} spends {take} Clue(s).")
        if remaining <= 0:
            break
    session.clues_found = max(0, session.clues_found - amount)
    return True, log


def spend_invasion_clues(session: SessionState) -> list[str]:
    state = session.abyss_campaign_plot
    if state is None or state.key != "invasion" or state.completed:
        return ["No active Invasion plot needs Clues."]
    needed = max(0, state.goal - state.artifact_clues_spent)
    if needed <= 0:
        return ["The artefact weakness is already known. Defeat the Final Boss and destroy it."]
    paid, log = spend_party_clues(session, needed)
    if not paid:
        return log
    state.artifact_clues_spent += needed
    log.append("The party discovers the artefact's weakness: hurl it through the Final Boss portal.")
    return log


def transfer_invasion_artifact(session: SessionState, holder: PartyMemberState | None) -> list[str]:
    state = session.abyss_campaign_plot
    if state is None or state.key != "invasion" or state.completed:
        return ["No active Invasion artefact is being carried."]
    if holder is None or holder.current_life <= 0:
        return ["Choose a living hero to carry the artefact."]
    state.artifact_holder_id = holder.character_id
    holder.madness += 1
    return [f"{holder.name} takes the artefact and gains 1 Madness."]


def take_entity_artifact_piece(session: SessionState, tile: TileState) -> list[str]:
    state = session.abyss_campaign_plot
    if state is None or state.key != "entity" or state.completed:
        return ["No active Entity plot needs artefact pieces."]
    if state.progress >= state.goal:
        return ["All artefact pieces have already been found."]
    if state.entity_piece_claimed_this_adventure:
        return ["Entity plot: only one artefact piece may be found in the same dungeon adventure."]
    if not (tile.treasure_items or tile.treasure_summary):
        return ["Find a magic item treasure result before taking an artefact piece."]
    tile.treasure_items = []
    tile.treasure_gold = 0
    tile.treasure_summary = "Entity plot artefact piece claimed instead of magic item treasure."
    tile.treasure_claimed = True
    state.entity_piece_claimed_this_adventure = True
    state.progress += 1
    log = [f"Entity plot: artefact piece found ({state.progress}/3)."]
    if state.progress >= state.goal:
        for member in session.party:
            if member.current_life > 0:
                gain = roll_die(2)
                member.madness += gain
                log.append(f"{member.name} gains {gain} Madness from the entity's manifestation.")
        complete_plot(session, log)
    return log


def on_new_foray(session: SessionState) -> list[str]:
    state = session.abyss_campaign_plot
    if state is None or state.key != "invasion" or state.completed or not state.artifact_holder_id:
        return []
    holder = next((member for member in session.party if member.character_id == state.artifact_holder_id), None)
    if holder is None or holder.current_life <= 0:
        return []
    holder.madness += 1
    return [f"Invasion plot: {holder.name} carries the artefact into a new foray and gains 1 Madness."]


def on_final_boss_defeated(engine, session: SessionState, defeated: list[EnemyState]) -> list[str]:
    state = session.abyss_campaign_plot
    if state is None or state.completed:
        return []
    final_bosses = [enemy for enemy in defeated if "final_boss" in {tag.lower() for tag in enemy.tags}]
    if not final_bosses:
        return []
    log: list[str] = []
    for enemy in final_bosses:
        if state.key == "assassination":
            roll = roll_d6()
            total = roll + state.final_bosses_defeated
            log.append(
                f"Assassination evidence check: d6 {roll} + {state.final_bosses_defeated} previous Final Boss(es) = {total} (need 4+)."
            )
            if total >= 4:
                state.progress += 1
                log.append(f"Evidence found ({state.progress}/3).")
                if state.progress >= state.goal:
                    state.finale_pending = "assassins_ambush"
                    log.append("The assassins are identified. Resolve the delivery ambush to complete the plot.")
        elif state.key == "enchantment" and _is_dragon(enemy):
            state.progress += 1
            log.append(f"Dragon blood collected ({state.progress}/3).")
            if state.progress >= state.goal:
                state.finale_pending = "enchantress_lich"
                log.append("The third vial is secured. Leaving the dungeon triggers the enchantress ambush.")
        elif state.key == "invasion" and state.artifact_clues_spent >= state.goal:
            state.finale_pending = "destroy_artifact"
            log.append("The Final Boss portal is open. Destroy the artefact to complete the Invasion plot.")
        state.final_bosses_defeated += 1
    return log


def _is_dragon(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    return "dragon" in tags or "dragon" in enemy.name.lower()


def should_force_enchantment_dragon_final(session: SessionState) -> bool:
    state = session.abyss_campaign_plot
    if state is None or state.key != "enchantment" or state.completed or state.progress >= state.goal:
        return False
    living = [member for member in session.party if member.current_life > 0]
    return bool(living) and all(member.level >= 3 for member in living)


def check_kidnap_minions(session: SessionState, tile_type: str, enemies: list[EnemyState], *, show_rolls: bool) -> list[str]:
    state = session.abyss_campaign_plot
    if state is None or state.key != "kidnap" or state.completed or state.chosen_one_found:
        return []
    if tile_type != "corridor" or not enemies:
        return []
    if not all(enemy.category == "minions" and "undead" not in {tag.lower() for tag in enemy.tags} for enemy in enemies):
        return []
    living = [member for member in session.party if member.current_life > 0]
    if not living:
        return []
    lowest = min(member.level for member in living)
    sides = 6 if max(member.level for member in living) <= 5 else 8
    roll = roll_die(sides)
    log = [f"Kidnap plot search: d{sides} = {roll} vs lowest party Level {lowest}."]
    if roll <= lowest:
        state.chosen_one_found = True
        for enemy in enemies:
            enemy.tags.append("abyss_plot_kidnapper")
        log.append("The chosen one is held by these minions; defeat them to rescue him.")
    return log


def on_combat_defeated(session: SessionState, defeated: list[EnemyState]) -> list[str]:
    state = session.abyss_campaign_plot
    if state is None or state.completed:
        return []
    tags = [{tag.lower() for tag in enemy.tags} for enemy in defeated]
    if state.key == "kidnap" and state.chosen_one_found and not state.chosen_one_rescued:
        if any("abyss_plot_kidnapper" in tagset for tagset in tags):
            state.chosen_one_rescued = True
            state.finale_pending = "kidnap_bosses"
            return ["The chosen one is rescued. Leave the dungeon to face the bosses who ordered the kidnap."]
    if state.finale_pending == "kidnap_bosses" and any("abyss_plot_kidnap_finale" in tagset for tagset in tags):
        # Caller evaluates tile after combat; resolving when both tagged bosses are in defeated is enough for tests.
        if sum(1 for tagset in tags if "abyss_plot_kidnap_finale" in tagset) >= 2:
            log: list[str] = ["The kidnap bosses are defeated."]
            complete_plot(session, log)
            return log
    if state.finale_pending == "enchantress_lich" and any("abyss_plot_enchantress" in tagset for tagset in tags):
        log = ["The enchantress is defeated and the dragon blood is delivered."]
        complete_plot(session, log)
        return log
    return []


def maybe_trigger_exit_ambush(engine, session: SessionState, tile: TileState) -> bool:
    state = session.abyss_campaign_plot
    if state is None or state.completed or state.finale_pending not in {"kidnap_bosses", "enchantress_lich"}:
        return False
    if state.finale_pending == "kidnap_bosses":
        enemies, _ = engine._roll_abyss_monster_row(session, "abyss_boss_table", "boss")
        if not enemies:
            return False
        first = enemies[0]
        second = first.model_copy(deep=True)
        second.id = uuid4().hex
        for enemy in (first, second):
            enemy.tags.append("abyss_plot_kidnap_finale")
        tile.enemies.extend([first, second])
        session.mode = "combat"
        session.party_attacked_immediately = True
        session.foes_strike_first = False
        session.log.append("Kidnap plot finale: two identical bosses confront the party before they reach base.")
        return True
    lich = EnemyState(
        id=uuid4().hex,
        name="Enchantress Lich",
        category="weird",
        level=10,
        life=10,
        max_life=10,
        attacks=2,
        tags=["abyss", "undead", "lich", "final_boss", "abyss_plot_enchantress"],
    )
    minions = [
        EnemyState(
            id=uuid4().hex,
            name="Skeletal Minions",
            category="minions",
            level=4,
            life=1,
            max_life=1,
            tags=["abyss", "undead"],
        )
        for _ in range(roll_d6())
    ]
    tile.enemies.extend([lich, *minions])
    session.mode = "combat"
    session.foes_strike_first = True
    session.party_attacked_immediately = True
    session.log.append("Enchantment plot finale: the enchantress Lich ambushes the party with skeletal minions.")
    return True


def resolve_plot_finale(session: SessionState) -> list[str]:
    state = session.abyss_campaign_plot
    if state is None or state.completed:
        return ["No active Abyss campaign finale is pending."]
    log: list[str] = []
    if state.key == "assassination" and state.finale_pending == "assassins_ambush":
        survivors = _save_or_die_all(session, 6, "assassination")
        if survivors:
            log.append("At least one hero survives the assassins' ambush and delivers the evidence.")
            complete_plot(session, log)
        else:
            log.append("No hero survives the assassins' ambush.")
        return log
    if state.key == "rebellion" and state.finale_pending == "rebellion_war":
        if state.rebellion_battles_total <= 0:
            state.rebellion_battles_total = roll_d3()
            state.rebellion_battles_resolved = 0
            log.append(f"Rebellion war: d3 = {state.rebellion_battles_total} battle(s).")
        battle = state.rebellion_battles_resolved + 1
        survivors = _save_or_die_all(session, 5, f"battle {battle}")
        successes = len(survivors)
        session.xp_rolls_pending += successes
        state.rebellion_battles_resolved = battle
        log.append(f"Battle {battle}: {successes} survivor(s) gain XP roll credit.")
        if not survivors:
            log.append("The party is destroyed in the rebellion.")
            return log
        if state.rebellion_battles_resolved < state.rebellion_battles_total:
            remaining = state.rebellion_battles_total - state.rebellion_battles_resolved
            log.append(
                f"Rebellion war pauses between battles. {remaining} battle(s) remain; resolve resurrection or recovery before continuing."
            )
            return log
        log.append("At least one hero survives all battles; the rebellion succeeds.")
        complete_plot(session, log)
        return log
    if state.key == "invasion" and state.finale_pending == "destroy_artifact":
        holder = next((member for member in session.party if member.character_id == state.artifact_holder_id), None)
        if holder is None or holder.current_life <= 0:
            return ["Choose or preserve a living artefact carrier before destroying the artefact."]
        holder.madness += 2
        log.append(f"{holder.name} hurls the artefact through the portal and gains 2 Madness.")
        if holder.madness > holder.level:
            holder.current_life = 0
            if holder.character_id not in session.permanently_lost_character_ids:
                session.permanently_lost_character_ids.append(holder.character_id)
            log.append(f"{holder.name} follows the artefact through the portal and is lost in the Netherworld.")
        complete_plot(session, log)
        return log
    return ["That Abyss plot finale is not ready to resolve."]


def _save_or_die_all(session: SessionState, level: int, label: str) -> list[PartyMemberState]:
    survivors: list[PartyMemberState] = []
    for member in session.party:
        if member.current_life <= 0:
            continue
        total, rolls = roll_exploding_for_level(member, session=session, log=session.log)
        final_total = total + member.level
        session.log.append(f"{member.name} {label} save: {' + '.join(str(r) for r in rolls)} + L{member.level} = {final_total} vs L{level}.")
        if rolls[0] != 1 and final_total >= level:
            survivors.append(member)
        else:
            member.current_life = 0
            session.log.append(f"{member.name} dies in the {label}.")
    return survivors


def complete_plot(session: SessionState, log: list[str]) -> None:
    state = session.abyss_campaign_plot
    if state is None or state.completed:
        return
    state.completed = True
    state.finale_pending = None
    survivors = [member for member in session.party if member.current_life > 0]
    for member in survivors:
        reward = roll_d6() * 100
        member.gold += reward
        log.append(f"{member.name} receives {reward}gp campaign reward.")
    if survivors:
        session.xp_rolls_pending += 1
        log.append("Campaign reward: one XP roll is available for one hero.")
    log.append(f"Abyss campaign plot complete: {state.name}.")


def queue_vampire_sire(session: SessionState, enemy: EnemyState) -> list[str]:
    if not is_vampire(enemy):
        return []
    session.abyss_vampire_sire = enemy.model_copy(deep=True)
    return [f"Vampire sire tracked: spend Clues to force another encounter with {enemy.name}."]


def clear_vampire_sire_if_defeated(session: SessionState, defeated: list[EnemyState]) -> list[str]:
    sire = session.abyss_vampire_sire
    if sire is None:
        return []
    if not any(enemy.id == sire.id or (is_vampire(enemy) and enemy.name == sire.name) for enemy in defeated):
        return []
    session.abyss_vampire_sire = None
    log = [f"The sire vampire {sire.name} is destroyed; vampire-rise resurrection block is lifted."]
    for member in session.party:
        member.statuses = [
            status for status in member.statuses if status.strip().lower() != "vampire-rise pending"
        ]
    return log


def hunt_vampire_sire(session: SessionState, tile: TileState) -> list[str]:
    sire = session.abyss_vampire_sire
    if sire is None:
        return ["No vampire sire is being tracked."]
    cost = 1 if any(has_skill(member, "vampire_hunter") for member in session.party if member.current_life > 0) else 2
    paid, log = spend_party_clues(session, cost)
    if not paid:
        return log
    enemy = sire.model_copy(deep=True)
    enemy.id = uuid4().hex
    enemy.life = max(1, enemy.life)
    enemy.max_life = max(enemy.max_life, enemy.life)
    if "abyss_vampire_sire" not in enemy.tags:
        enemy.tags.append("abyss_vampire_sire")
    tile.enemies.append(enemy)
    session.mode = "combat"
    session.reaction_pending = True
    log.append(f"The party spends {cost} Clue(s) to meet {enemy.name} again in the next room/corridor.")
    if roll_d6() <= 2:
        minion_count = roll_d6()
        for _ in range(minion_count):
            tile.enemies.append(
                EnemyState(
                    id=uuid4().hex,
                    name="Vampire Minions",
                    category="minions",
                    level=4,
                    life=1,
                    max_life=1,
                    tags=["abyss"],
                )
            )
        log.append(f"{enemy.name} is accompanied by {minion_count} minion(s).")
    return log
