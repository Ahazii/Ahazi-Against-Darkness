"""Four Against the Abyss tactical combat rules."""

from __future__ import annotations

from app.schemas import EnemyState, PartyMemberState


def foe_tags(enemy: EnemyState) -> set[str]:
    return {str(tag).lower() for tag in enemy.tags}


def is_abyss_foe(enemy: EnemyState) -> bool:
    tags = foe_tags(enemy)
    return "abyss" in tags or any(tag.startswith("reaction_table:abyss ") for tag in tags)


def is_abyss_leader(enemy: EnemyState) -> bool:
    return enemy.life > 0 and "abyss_leader" in foe_tags(enemy)


def is_abyss_minion(enemy: EnemyState) -> bool:
    return enemy.life > 0 and enemy.category == "minions" and is_abyss_foe(enemy) and not is_abyss_leader(enemy)


def is_horde(enemy: EnemyState) -> bool:
    tags = foe_tags(enemy)
    return enemy.category == "horde" or "horde" in tags


def horde_attacks_per_character(enemy: EnemyState) -> int:
    return max(1, int(enemy.attacks or 1))


def living_abyss_leaders(enemies: list[EnemyState]) -> list[EnemyState]:
    return [enemy for enemy in enemies if is_abyss_leader(enemy)]


def living_abyss_minions(enemies: list[EnemyState]) -> list[EnemyState]:
    return [enemy for enemy in enemies if is_abyss_minion(enemy)]


def living_abyss_bosses(enemies: list[EnemyState]) -> list[EnemyState]:
    return [
        enemy
        for enemy in enemies
        if enemy.life > 0 and enemy.category == "boss" and is_abyss_foe(enemy)
    ]


def abyss_leader_champion(party: list[PartyMemberState]) -> PartyMemberState | None:
    living = [member for member in party if member.current_life > 0]
    if not living:
        return None
    return sorted(living, key=lambda member: member.marching_order)[0]


def legal_abyss_attack_targets(
    member: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    *,
    tile_type: str,
) -> list[EnemyState]:
    living = [enemy for enemy in enemies if enemy.life > 0]
    leaders = living_abyss_leaders(living)
    minions = living_abyss_minions(living)
    if not leaders or not minions:
        return living
    if tile_type == "corridor":
        return [enemy for enemy in living if not is_abyss_leader(enemy)] or living
    champion = abyss_leader_champion(party)
    if champion is not None and member.character_id == champion.character_id:
        return leaders
    return minions


def _foe_name(enemy: EnemyState | None) -> str:
    return enemy.name if enemy is not None else "the selected foe"


def coerce_abyss_attack_targets(
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    *,
    tile_type: str,
    attack_targets: dict[str, str] | None,
    label: str = "target",
) -> tuple[dict[str, str] | None, list[str]]:
    living = [enemy for enemy in enemies if enemy.life > 0]
    if not living:
        return attack_targets, []
    if not living_abyss_leaders(living) or not living_abyss_minions(living):
        return attack_targets, []

    chosen = dict(attack_targets or {})
    log: list[str] = []
    for member in sorted((pc for pc in party if pc.current_life > 0), key=lambda pc: pc.marching_order):
        legal = legal_abyss_attack_targets(member, party, living, tile_type=tile_type)
        if not legal:
            continue
        legal_ids = {enemy.id for enemy in legal}
        requested_id = chosen.get(member.character_id)
        requested = next((enemy for enemy in living if enemy.id == requested_id), None)
        if requested_id in legal_ids:
            continue
        replacement = legal[0]
        chosen[member.character_id] = replacement.id
        if requested is not None:
            if tile_type == "corridor" and is_abyss_leader(requested):
                log.append(
                    f"Abyss leader lock: {member.name}'s {label} is redirected from "
                    f"{requested.name} to {replacement.name}; corridor leaders cannot be attacked "
                    "until the minions are defeated."
                )
            else:
                champion = abyss_leader_champion(party)
                if champion is not None and member.character_id == champion.character_id:
                    log.append(
                        f"Abyss leader lock: {member.name} is the champion and must fight "
                        f"{replacement.name} while minions remain."
                    )
                else:
                    log.append(
                        f"Abyss leader lock: {member.name}'s {label} is redirected from "
                        f"{_foe_name(requested)} to {replacement.name}; non-champions fight minions "
                        "until they are defeated."
                    )
    return (chosen or None), log


def apply_abyss_multiple_boss_defaults(
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    *,
    tile_type: str,
    attack_targets: dict[str, str] | None,
) -> tuple[dict[str, str] | None, list[str]]:
    if tile_type != "room":
        return attack_targets, []
    bosses = living_abyss_bosses(enemies)
    if len(bosses) < 2 or living_abyss_minions(enemies):
        return attack_targets, []
    living_party = sorted(
        [member for member in party if member.current_life > 0],
        key=lambda member: member.marching_order,
    )
    if not living_party:
        return attack_targets, []
    chosen = dict(attack_targets or {})
    changed = False
    for index, member in enumerate(living_party):
        if chosen.get(member.character_id):
            continue
        chosen[member.character_id] = bosses[index % len(bosses)].id
        changed = True
    if not changed:
        return attack_targets, []
    return chosen, [
        "Abyss multiple bosses: unset party targets are spread across the bosses; "
        "when one boss falls, survivors can retarget next round."
    ]


def abyss_single_hero_secondary_boss_penalty(
    member: PartyMemberState,
    enemy: EnemyState,
    *,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    attack_targets: dict[str, str] | None,
) -> int:
    if member.current_life <= 0:
        return 0
    living_party = [pc for pc in party if pc.current_life > 0]
    bosses = living_abyss_bosses(enemies)
    if len(living_party) != 1 or len(bosses) < 2 or enemy.id not in {boss.id for boss in bosses}:
        return 0
    main_id = (attack_targets or {}).get(member.character_id) or bosses[0].id
    return -1 if enemy.id != main_id else 0


def abyss_tactical_notes(party: list[PartyMemberState], enemies: list[EnemyState], *, tile_type: str) -> list[str]:
    living = [enemy for enemy in enemies if enemy.life > 0]
    notes: list[str] = []
    leaders = living_abyss_leaders(living)
    minions = living_abyss_minions(living)
    if leaders and minions:
        if tile_type == "corridor":
            notes.append("Abyss leader lock: in corridors, leaders cannot be targeted until their minions are defeated.")
        else:
            champion = abyss_leader_champion(party)
            champion_text = f" #{champion.marching_order} {champion.name}" if champion is not None else ""
            notes.append(
                f"Abyss leader lock: champion{champion_text} fights the leader; the rest fight minions until none remain."
            )
    bosses = living_abyss_bosses(living)
    if tile_type == "room" and len(bosses) >= 2:
        if len([member for member in party if member.current_life > 0]) == 1:
            notes.append("Abyss multiple bosses: a lone hero chooses a main boss and has -1 Defense against the others.")
        else:
            notes.append("Abyss multiple bosses: split party targets across bosses; retarget next round when one falls.")
    hordes = [enemy for enemy in living if is_horde(enemy)]
    for horde in hordes:
        attacks = horde_attacks_per_character(horde)
        if attacks == 1:
            notes.append(f"Horde: {horde.name} attacks once per living character each round.")
        else:
            notes.append(f"Horde: {horde.name} attacks {attacks} times per living character each round.")
    return notes
