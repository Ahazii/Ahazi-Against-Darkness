"""Find identifiers used with optional chaining that are never declared in app.js."""
from __future__ import annotations

import re
from pathlib import Path

APP_JS = Path(__file__).resolve().parents[1] / "src" / "app" / "static" / "app.js"

SKIP = frozenset(
    """
    session state member tile item actions row button select details summary option target parent
    event console document window Math JSON Array Object String Number Boolean Date RegExp Set Map
    Promise Error fetch localStorage sessionStorage HTMLElement Node Intl index value checked btn
    input hero ally foe enemy spell key name type label closest classList parentNode files catalog
    context entry errors keywords abilities description items extra tags onComplete onReset
    preserveValue showHeroSelect buttonLabel buttonTooltip actionName characterId payloadKind
    profile adventure party character rulesTables expertSkillsCatalog spellAimModes spellFoeTargets
    abilityAllyTargets abilityFoeTargets map_state imported_manifest active_quest save_label
    combatAbilities combatGuardTargets combatSecondaryTargets doubleKickTargets protectiveIncenseTargets
    hirelings class_id tiles rulesTables class_traits starting_inventory starting_spells abilities
    campaign sessionRenderCache icons expended_spells healing_prayer_uses rage_uses_spent
    luck_points_spent paladin_prayer_spent hunger_rounds fd_forgotten_spells pending_save_reroll
    expert_encounter_spent expert_spore_doses wielded_melee_weapons mushroom_spore_uses panache_points
    firearm_reload_turns firearm_broken gladiator_counter_pending wandPowerCharges bandageTargets
    spellLifeTransfer secretFoeTargets enchantedPaintOptions teleportTileId teleportAllies
    furnaceGemItems usePrayerBead echoSpellFoeTargets echoSpellSecondaryFoeTargets
    professional_skill_uses inventory professional_buffs cargo_items scout_encounter_origin_tile_ids
    pending_defense_reroll pending_fd_cairn_natural_one lastSessionActionButton sessionActionButton
    null undefined true false this arguments async await return
    """.split()
)


def main() -> None:
    js = APP_JS.read_text(encoding="utf-8")
    declared = set(re.findall(r"\b(?:const|let|var|function)\s+(\w+)", js))
    declared.update(re.findall(r"\((\w+)\)\s*=>", js))
    declared.update(re.findall(r"\((\w+),\s*(\w+)\)\s*=>", js))

    optional_ids = sorted({m.group(1) for m in re.finditer(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\?\.", js)})

    print("=== Optional-chain identifiers never declared in app.js ===")
    hits = []
    for ident in optional_ids:
        if ident in declared or ident in SKIP:
            continue
        # property chains like session.map_state?.tiles - skip lowercase single words that are likely props
        if ident[0].islower() and ident not in {"heroSelect", "itemSelect", "tabBtn"}:
            continue
        lines = [i + 1 for i, line in enumerate(js.splitlines()) if f"{ident}?." in line]
        hits.append((ident, lines))

    for ident, lines in sorted(hits, key=lambda pair: pair[0]):
        print(f"  {ident}: lines {lines[:5]}")

    if not hits:
        print("  none")


if __name__ == "__main__":
    main()
