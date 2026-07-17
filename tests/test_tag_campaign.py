from __future__ import annotations

import json
from pathlib import Path

from app.db import now_utc
from app.engine import tag_campaign
from app.engine.adventure_import import ADVENTURE_MANIFEST_FILENAME, installed_adventure_dir
from app.engine.tag_campaign import (
    add_adventure_closeout_tasks,
    apply_tag_dragon_reveal_to_latest_adventure,
    build_tag_adventure_manifest,
    check_item_availability,
    create_magic_locker,
    default_campaign,
    follow_treasure_map,
    look_for_clues,
    purchase_tag_service,
    recover_hidden_treasure_trove,
    reroll_guild_availability,
    reset_guild_availability_reroll,
    roll_gambling_house,
    roll_hidden_treasure_trove_risk,
    roll_aspergillum_break_chance,
    roll_flammable_oil_throw,
    roll_horn_wandering_attraction,
    roll_moneylender_follow_chance,
    roll_treasure_map_price,
    run_streetwise_action,
    cast_tag_guild_spell,
    consume_tag_guild_marker,
    convert_character_gold_to_tag_bank,
    resolve_tag_branch_action,
    resolve_tag_closeout_task,
    resolve_tag_finance_action,
    resolve_tag_route_action,
    resolve_tag_scene_action,
    record_tag_signoff_review,
    resolve_tag_xp_action,
    settlement_size_from_roll,
    settlement_service_rows,
    store_tag_treasure,
    summon_magic_locker,
    tag_guild_benefits_active,
    travel_to_new_settlement,
    use_tag_trinket,
    update_troupe,
    withdraw_tag_stored_gold,
)
from app.engine.adventure_manifest import validate_adventure_manifest
from app.engine.dice import AdvancementRollResult
from app.engine.tag_compat import upgrade_tag_manifest
from app.engine.equipment_shop import buy_equipment
from app.rules.repository import RulesRepository
from app.schemas import Character, TagXpMarkerState


def _character(**overrides) -> Character:
    timestamp = now_utc()
    data = {
        "id": "hero-1",
        "name": "Sly Silas",
        "class_id": "rogue",
        "class_name": "Rogue",
        "level": 3,
        "gold": 20,
        "clues": 0,
        "max_life": 4,
        "current_life": 4,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    data.update(overrides)
    return Character(**data)


def test_tag_settlement_size_table() -> None:
    assert [settlement_size_from_roll(roll) for roll in range(1, 7)] == [-2, -1, 0, 1, 2, 3]


def test_tag_availability_success_surcharge_and_unavailable(monkeypatch) -> None:
    campaign = default_campaign()
    campaign.settlement_size = 0

    rolls = iter([6, 5, 4])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    success = check_item_availability(campaign, item_name="Guild item", difficulty=6, base_price_gp=10)
    surcharge = check_item_availability(campaign, item_name="Guild item", difficulty=6, base_price_gp=10)
    unavailable = check_item_availability(campaign, item_name="Guild item", difficulty=6, base_price_gp=10)

    assert success.outcome == "available"
    assert success.final_price_gp == 10
    assert surcharge.outcome == "surcharge"
    assert surcharge.final_price_gp == 12
    assert unavailable.outcome == "unavailable"
    assert unavailable.final_price_gp is None


def test_tag_look_for_clues_spends_bribe_and_uses_rogue_level(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character()
    rolls = iter([4, 3])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    entry = look_for_clues(campaign, hero)

    assert hero.gold == 16
    assert hero.clues == 1
    assert entry.roll == 3
    assert entry.modifier == 3
    assert entry.total == 6


def test_tag_look_for_clues_natural_one_loses_existing_clue(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(clues=1)
    rolls = iter([2, 1])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    entry = look_for_clues(campaign, hero)

    assert hero.gold == 18
    assert hero.clues == 0
    assert "lost 1 Clue" in entry.result_text


def test_tag_simple_travel_rolls_days_and_new_size(monkeypatch) -> None:
    campaign = default_campaign()
    campaign.settlement_name = "Varian"
    rolls = iter([5, 2, 3, 4])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    entry = travel_to_new_settlement(campaign, destination_name="Diram")

    assert entry.from_settlement == "Varian"
    assert entry.to_settlement == "Diram"
    assert entry.days == 6
    assert entry.new_settlement_size == 2
    assert campaign.settlement_name == "Diram"
    assert campaign.settlement_size == 2
    assert campaign.days_passed == 6


def test_tag_hex_travel_logs_road_tithe_and_encounter_checks(monkeypatch) -> None:
    campaign = default_campaign()
    campaign.settlement_name = "Varian"
    rolls = iter([6, 1, 3, 3, 4, 6, 6, 6])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    entry = travel_to_new_settlement(campaign, destination_name="Diram", use_hex_map=True, pay_road_tithe=True)

    assert entry.new_settlement_size == 3
    assert entry.direction_roll == 1
    assert entry.distance_hexes == 8
    assert entry.road_roll == 18
    assert entry.road_exists is True
    assert entry.road_tithe_paid_gp == 3
    assert entry.encounter_checks == 3
    assert campaign.days_passed == 8


def test_tag_service_rows_gate_by_settlement_size_and_mark_availability() -> None:
    campaign = default_campaign()
    campaign.settlement_size = -1
    rows = {row["key"]: row for row in settlement_service_rows(campaign)}

    assert list(rows)[:28] == [
        "bank_account",
        "bank_inheritance",
        "magic_locker",
        "platinum_exchange",
        "hidden_treasure_trove",
        "resurrection_blessing_tags",
        "gems_jewelry_conversion",
        "bag_of_carrying",
        "ten_foot_pole",
        "lantern_hook",
        "very_nutritious_food",
        "poison_resistance_training",
        "martial_arts_training",
        "gambling_house",
        "treasure_maps",
        "moneylenders",
        "good_boots",
        "flammable_oil",
        "horn",
        "wineskin",
        "flail_axe",
        "aspergillum",
        "availability_rolls",
        "streetwise_rules",
        "adventurers_guild_jobs",
        "trinkets",
        "guild_spells",
        "tag_special_foes",
    ]
    assert rows["bank_account"]["status"] == "available"
    assert rows["magic_locker"]["status"] == "unavailable"
    assert rows["platinum_exchange"]["status"] == "church_only"
    assert rows["bag_of_carrying"]["availability_difficulty"] == 6
    assert rows["very_nutritious_food"]["availability_difficulty"] == 4
    assert rows["moneylenders"]["credit_limit_gp"] == 1800
    assert rows["horn"]["action"] == "horn_attract"
    assert rows["aspergillum"]["action"] == "aspergillum_break"
    assert "Adventure module" in rows["adventurers_guild_jobs"]["automation"]
    assert "Power Cookie" in rows["trinkets"]["summary"]
    assert "Wizard's Luck" in rows["guild_spells"]["summary"]
    assert "white gargoyles" in rows["tag_special_foes"]["summary"]

    campaign.settlement_size = 3
    rows = {row["key"]: row for row in settlement_service_rows(campaign)}
    assert rows["magic_locker"]["status"] == "available"
    assert rows["platinum_exchange"]["status"] == "available"


def test_tag_hidden_treasure_trove_risk_roll(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(gold=100, clues=4, save_bonus=1)
    store_tag_treasure(campaign, hero, storage="trove", gold_gp=50, item_name="Ruby", quantity=1)
    rolls = iter([1, 2, 2])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    entry = roll_hidden_treasure_trove_risk(campaign)

    assert entry.action == "hidden_treasure_trove_risk"
    assert entry.total == 5
    assert campaign.tag_hidden_trove_robbed is True
    assert campaign.tag_hidden_trove_stolen_gold_gp == 50
    assert campaign.tag_storage_gold_gp == 0
    assert "discovered and stolen" in entry.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 5)
    recovered = recover_hidden_treasure_trove(campaign, hero)

    assert hero.clues == 0
    assert campaign.tag_hidden_trove_robbed is False
    assert campaign.tag_storage_gold_gp == 50
    assert campaign.tag_hidden_trove_stolen_gold_gp == 0
    assert "hidden trove recovered" in recovered.result_text


def test_tag_treasure_map_price_uses_exploding_sixes(monkeypatch) -> None:
    campaign = default_campaign()
    rolls = iter([6, 2, 1, 3, 4, 5])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    entry = roll_treasure_map_price(campaign)

    assert entry.cost_gp == 21
    assert "6+2+1+3+4+5 = 21 gp" in entry.result_text


def test_tag_moneylender_follow_chance(monkeypatch) -> None:
    campaign = default_campaign()
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 4)

    entry = roll_moneylender_follow_chance(campaign, debt_gp=310)

    assert entry.total == 4
    assert "4-in-6 chance" in entry.result_text
    assert "enforcers follow" in entry.result_text


def test_tag_horn_oil_and_aspergillum_rolls(monkeypatch) -> None:
    campaign = default_campaign()
    rolls = iter([2, 1, 2])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    horn = roll_horn_wandering_attraction(campaign)
    oil = roll_flammable_oil_throw(campaign)
    aspergillum = roll_aspergillum_break_chance(campaign)

    assert "wandering monsters are attracted" in horn.result_text
    assert "sprays a friend" in oil.result_text
    assert "breaks" in aspergillum.result_text


def test_tag_troupe_storage_purchase_and_locker(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(gold=1000)

    update_troupe(
        campaign,
        troupe_name="Varian Guild",
        member_character_ids=["hero-1", "hero-2", "hero-1"],
        active_character_ids=["hero-1", "hero-2", "hero-1"],
        guild_member=True,
        guild_coffers_gp=5000,
    )
    assert campaign.tag_troupe_name == "Varian Guild"
    assert campaign.tag_troupe_member_character_ids == ["hero-1", "hero-2"]
    assert campaign.tag_troupe_active_character_ids == ["hero-1", "hero-2"]
    assert campaign.tag_guild_member is True

    stored = store_tag_treasure(campaign, hero, storage="bank", gold_gp=100, item_name="Ruby", quantity=2)
    assert hero.gold == 890
    assert campaign.tag_storage_gold_gp == 100
    assert campaign.tag_stored_items[0].item_name == "Ruby"
    assert "10 gp bank fee" in stored.result_text

    withdrawn = withdraw_tag_stored_gold(campaign, hero, gold_gp=40)
    assert hero.gold == 930
    assert campaign.tag_storage_gold_gp == 60
    assert "withdraws 40 gp" in withdrawn.result_text

    purchase = purchase_tag_service(campaign, hero, service_key="blessing_tag", quantity=2)
    assert hero.gold == 770
    assert hero.inventory.count("TAG Blessing tag") == 2
    assert "Blessing tag" in purchase.result_text

    campaign.settlement_size = 0
    locker = create_magic_locker(campaign, hero, contents="Silver sword", kind="item")
    assert hero.gold == 720
    assert campaign.tag_magic_lockers[0].contents == "Silver sword"
    assert "magic locker" in locker.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 2)
    summon = summon_magic_locker(campaign, locker_id=campaign.tag_magic_lockers[0].id)
    assert campaign.tag_magic_lockers[0].mishap_locked is True
    assert "mishap" in summon.result_text


def test_tag_troupe_active_party_is_limited_to_troupe_members() -> None:
    campaign = default_campaign()

    update_troupe(
        campaign,
        guild_member=True,
        guild_coffers_gp=0,
        member_character_ids=["hero-1", "hero-2"],
        active_character_ids=["hero-2", "hero-3", "hero-1"],
    )

    assert campaign.tag_guild_coffers_gp == 5000
    assert campaign.tag_troupe_member_character_ids == ["hero-1", "hero-2"]
    assert campaign.tag_troupe_active_character_ids == ["hero-2", "hero-1"]


def test_tag_bank_migration_can_include_legacy_bank_with_optional_fee() -> None:
    campaign = default_campaign()
    hero = _character(gold=120)

    entry = convert_character_gold_to_tag_bank(
        campaign,
        hero,
        include_legacy_bank=True,
        legacy_bank_gold=80,
        apply_deposit_fee=True,
        note="migration",
    )

    assert hero.gold == 0
    assert campaign.tag_bank_accounts[0].gold_gp == 180
    assert campaign.tag_bank_accounts[0].notes == "migration"
    assert "20 gp TAG deposit fee" in entry.result_text


def test_tag_streetwise_gambling_and_treasure_map(monkeypatch) -> None:
    campaign = default_campaign()
    campaign.tag_guild_member = True
    campaign.tag_guild_coffers_gp = 5000
    hero = _character(gold=100, current_life=4)

    rolls = iter([5, 5, 6])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    monkeypatch.setattr(tag_campaign, "roll_d10", lambda: 7)
    monkeypatch.setattr(tag_campaign, "roll_d12", lambda: 6)

    rumor = run_streetwise_action(campaign, hero, action="listen_rumors")
    assert "hears rumor" in rumor.result_text

    gamble = roll_gambling_house(campaign, hero, stake_gp=10)
    assert gamble.total == 8
    assert "wins +10%" in gamble.result_text

    map_entry = follow_treasure_map(campaign, use_guild_cartographer=True)
    assert map_entry.total == 6
    assert "The Map Leads To 6" in map_entry.result_text


def test_tag_adventure_manifest_generation_validates() -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    campaign = default_campaign()
    for lead_type in ("rumor", "treasure_map", "thematic_dungeon", "guild_job"):
        manifest, entry = build_tag_adventure_manifest(campaign, lead_type=lead_type, detail="1")
        result = validate_adventure_manifest(manifest, rules_repo=repo)
        assert result.valid, result.errors
        assert manifest["id"] in campaign.tag_generated_adventure_ids
        assert manifest["source"]["parameters"]["lead_type"] == lead_type
        tag_reference = manifest["source"]["parameters"]["tag_reference"]
        assert tag_reference["lead_type"] == lead_type
        assert tag_reference["how_to"]
        assert tag_reference["mood"]
        assert "lead handoff" in tag_reference["room_prompts"]["tag-lead-entry"]["body"]
        assert "If this room has no scene-specific button" in tag_reference["room_prompts"]["tag-complication"]["body"]
        assert "Adventure section" in entry.result_text


def test_all_tag_generation_options_have_structured_prompt_metadata(monkeypatch) -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 2)
    monkeypatch.setattr(tag_campaign, "roll_d12", lambda: 6)
    cases = {
        "rumor": [str(i) for i in range(1, 13)],
        "treasure_map": [str(i) for i in range(1, 7)],
        "thematic_dungeon": [str(i) for i in range(1, 7)],
        "guild_job": [str(i) for i in range(1, 7)],
    }
    generic_actions = {
        "parley_success",
        "parley_failed",
        "clue_gate_unlocked",
        "clue_gate_blocked",
        "final_route",
        "claim_reward",
        "mark_scene_xp",
        "unlock_scene",
    }
    finale_choice_cases = set()

    for lead_type, details in cases.items():
        for detail in details:
            campaign = default_campaign()
            manifest, _ = build_tag_adventure_manifest(campaign, lead_type=lead_type, detail=detail)
            result = validate_adventure_manifest(manifest, rules_repo=repo)
            assert result.valid, (lead_type, detail, result.errors)
            reference = manifest["source"]["parameters"]["tag_reference"]
            assert isinstance(reference, dict), (lead_type, detail)
            prompts = reference.get("room_prompts")
            assert isinstance(prompts, dict) and prompts, (lead_type, detail)
            assert {"tag-complication", "tag-final-scene"} <= set(prompts), (lead_type, detail)
            complication_actions = prompts["tag-complication"].get("actions") or []
            final_actions = prompts["tag-final-scene"].get("actions") or []
            complication_specific = [
                action
                for action in complication_actions
                if action.get("action_value") and action.get("action_value") not in generic_actions
            ]
            final_specific = [
                action
                for action in final_actions
                if action.get("action_value") and action.get("action_value") not in generic_actions
            ]
            if final_specific and not complication_specific:
                finale_choice_cases.add((lead_type, detail))

    assert ("rumor", "6") in finale_choice_cases
    assert ("thematic_dungeon", "2") in finale_choice_cases
    assert ("guild_job", "5") in finale_choice_cases


def test_tag_rumor_manifest_carries_pdf_rule_profile() -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    campaign = default_campaign()

    manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail="2")
    result = validate_adventure_manifest(manifest, rules_repo=repo)

    assert result.valid, result.errors
    reference = manifest["source"]["parameters"]["tag_reference"]
    assert manifest["title"] == "The Adventures Guild Rumor 2: Medusa in the Hunter's Cabin"
    assert reference["scene"] == "Scene 10 leading to Scene 1"
    assert reference["pdf_pages"] == "TAG pp.22, 25-26"
    assert reference["final_foe_proxy"] == "Medusa"
    assert "Pendant worth 260 gp" in reference["rewards"]
    assert reference["finale_mode"] == "choice"
    assert reference["final_foes"] == [{"name": "Medusa", "count": 1}]
    assert "room_prompts" in reference
    assert reference["room_prompts"]["tag-complication"]["actions"][0]["action_value"] == "parley_success"
    assert not any(action["action_value"] == "claim_reward" for action in reference["room_prompts"]["tag-final-scene"]["actions"])
    assert any(
        action["action_value"] == "medusa_assassin_ambush"
        for action in reference["room_prompts"]["tag-complication"]["actions"]
    )
    assert any(
        action["action_value"] == "medusa_stealth_approach"
        for action in reference["room_prompts"]["tag-final-scene"]["actions"]
    )
    assert any(
        action["action_value"] == "medusa_reaction"
        for action in reference["room_prompts"]["tag-final-scene"]["actions"]
    )
    final_room = next(room for room in manifest["rooms"] if room["id"] == "tag-final-scene")
    assert "encounter" not in final_room["triggers"][0]


def test_tag_manifest_uses_user_editable_narrative_overrides(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    (data_dir / "tag_scene_narrative_overrides.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tag": {
                    "rumor": {
                        "3": {
                            "module_title": "The Adventures Guild Rumor 3: Edited Local Title",
                            "objective": "Edited local objective.",
                            "scene_graph": {
                                "start_scenes": ["Scene 11"],
                                "scenes": {
                                    "Scene 11": {
                                        "description": "Edited local scene body.",
                                        "branches": [
                                            {
                                                "label": "Return to town",
                                                "target_scene": "Scene 18",
                                                "target_scene_number": 18,
                                            }
                                        ],
                                    }
                                },
                            },
                            "rooms": {
                                "tag-lead-entry": {
                                    "title": "Edited Opening",
                                    "description": "Edited opening narrative.",
                                    "log": "Edited opening log.",
                                },
                                "tag-final-scene": {
                                    "title": "Edited Finale",
                                    "description": "Edited finale narrative.",
                                    "log": "Edited finale log.",
                                },
                            },
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    manifest, _entry = build_tag_adventure_manifest(default_campaign(), lead_type="rumor", detail="3")

    assert manifest["title"] == "The Adventures Guild Rumor 3: Edited Local Title"
    assert manifest["quest"]["objective_text"] == "Edited local objective."
    opening = next(room for room in manifest["rooms"] if room["id"] == "tag-lead-entry")
    finale = next(room for room in manifest["rooms"] if room["id"] == "tag-final-scene")
    assert opening["title"] == "Edited Opening"
    assert opening["description"] == "Edited opening narrative."
    assert finale["title"] == "Edited Finale"
    assert finale["description"] == "Edited finale narrative."
    assert finale["triggers"][0]["log"] == "Edited finale log."
    contact = next(npc for npc in manifest["npcs"] if npc["id"] == "tag-contact")
    assert contact["description"] == "Edited opening narrative."
    prompts = manifest["source"]["parameters"]["tag_reference"]["room_prompts"]
    assert prompts["tag-lead-entry"]["body"] == "Edited opening narrative."
    assert "lead handoff" not in prompts["tag-lead-entry"]["body"]
    assert prompts["tag-final-scene"]["body"] == "Edited finale narrative."
    assert manifest["source"]["parameters"]["tag_reference"]["scene_graph"]["scenes"]["Scene 11"]["branches"][0]["target_scene"] == "Scene 18"
    final_actions = manifest["source"]["parameters"]["tag_reference"]["room_prompts"]["tag-final-scene"]["actions"]
    assert any(action["action_type"] == "route" and action["action_value"] == "unlock_scene" for action in final_actions)


def test_tag_manifest_upgrade_repairs_stale_prompts_from_local_narrative_overrides(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    (data_dir / "tag_scene_narrative_overrides.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tag": {
                    "rumor": {
                        "12": {
                            "module_title": "The Adventures Guild Rumor 12: Shinta and Agaratha",
                            "objective": "Accept Shinta's request and recover Agaratha.",
                            "scene_graph": {
                                "start_scenes": ["Scene 4"],
                                "scenes": {
                                    "Scene 4": {
                                        "description": "Choose a worthy sword user, then go to Scene 7.",
                                        "branches": [{"label": "Go to Scene 7", "target_scene": "Scene 7"}],
                                    }
                                },
                            },
                            "rooms": {
                                "tag-lead-entry": {
                                    "title": "Shinta and Agaratha",
                                    "description": "Since she lost her husband, Shinta has lost the will to adventure.",
                                    "log": "Objective: recover Agaratha.",
                                },
                                "tag-final-scene": {
                                    "title": "Agaratha's Quest",
                                    "description": "You may accept a quest from the paladin with a single character.",
                                    "log": "Choose the character who accepts Shinta's quest.",
                                },
                            },
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    manifest = {
        "title": "Generated TAG Rumor 12",
        "quest": {"objective_text": "Old objective"},
        "npcs": [
            {
                "id": "tag-contact",
                "name": "Guild Contact",
                "room_id": "tag-lead-entry",
                "description": "Shinta's story starts as a request and ends at a bandit hideout.",
                "dialogue": "Old dialogue",
            }
        ],
        "rooms": [
            {
                "id": "tag-lead-entry",
                "title": "Lead Trail",
                "description": "The last warmth of the home settlement is behind them now.",
                "triggers": [],
            },
            {
                "id": "tag-final-scene",
                "title": "Finale",
                "description": "This is where the lead comes due.",
                "triggers": [{"log": "Old finale log"}],
            },
        ],
        "source": {
            "parameters": {
                "tag_reference": {
                    "lead_type": "rumor",
                    "lead_detail": "12",
                    "room_prompts": {
                        "tag-lead-entry": {
                            "title": "Lead entry choices",
                            "body": "The rumor has teeth now. This is the handoff from settlement rumor.",
                            "actions": [],
                        },
                        "tag-final-scene": {
                            "title": "Final scene",
                            "body": "Check final foe, route, reward, and XP text.",
                            "actions": [],
                        },
                    },
                }
            }
        },
    }

    upgraded = upgrade_tag_manifest(manifest)
    tag_reference = upgraded["source"]["parameters"]["tag_reference"]
    assert upgraded["title"] == "The Adventures Guild Rumor 12: Shinta and Agaratha"
    assert upgraded["quest"]["objective_text"] == "Accept Shinta's request and recover Agaratha."
    assert upgraded["rooms"][0]["description"] == "Since she lost her husband, Shinta has lost the will to adventure."
    assert upgraded["npcs"][0]["description"] == "Since she lost her husband, Shinta has lost the will to adventure."
    assert tag_reference["room_prompts"]["tag-lead-entry"]["body"] == "Since she lost her husband, Shinta has lost the will to adventure."
    assert "rumor has teeth" not in tag_reference["room_prompts"]["tag-lead-entry"]["body"].lower()
    assert tag_reference["room_prompts"]["tag-final-scene"]["body"] == "You may accept a quest from the paladin with a single character."
    assert tag_reference["scene_graph"]["scenes"]["Scene 4"]["branches"][0]["target_scene"] == "Scene 7"
    assert tag_reference["local_narrative_override_applied"] is True


def test_tag_scene_graph_defers_profile_reward_actions_until_terminal_scene(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    (data_dir / "tag_scene_narrative_overrides.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tag": {
                    "rumor": {
                        "12": {
                            "rooms": {
                                "tag-lead-entry": {
                                    "title": "Shinta and Agaratha",
                                    "description": "Shinta offers Agaratha to a worthy character. If interested, go to Scene 4.",
                                },
                                "tag-final-scene": {
                                    "title": "Choose Shinta's Champion",
                                    "description": "Choose a sword-using character and go to Scene 7.",
                                },
                            },
                            "scene_graph": {
                                "start_scenes": ["Scene 4"],
                                "scenes": {
                                    "Scene 4": {
                                        "description": "Choose a sword-using character and go to Scene 7.",
                                        "branches": [{"label": "Go to Scene 7", "target_scene": "Scene 7"}],
                                    },
                                    "Scene 7": {"description": "Complete the single-character bandit hideout quest.", "branches": []},
                                },
                            },
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    campaign = default_campaign()
    manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail="12")
    tag_reference = manifest["source"]["parameters"]["tag_reference"]

    assert tag_reference["lead_structure"] == "handoff"
    assert "tag-side-clue" not in {room["id"] for room in manifest["rooms"]}
    assert all(exit_def.get("to") != "tag-side-clue" for exit_def in manifest["rooms"][0]["exits"])
    assert tag_reference["module_profile"]["target_rooms"] == "10-room solo Bandit Hideout handoff"

    final_labels = [action["label"] for action in tag_reference["room_prompts"]["tag-final-scene"]["actions"]]
    assert any("Choose a sword-using character" in label for label in final_labels)
    assert "Apply Agaratha" not in final_labels
    assert [action["label"] for action in tag_reference["scene_graph_terminal_actions"]] == ["Apply Agaratha"]

    tag_campaign.resolve_tag_route_action(
        campaign,
        route_action="unlock_scene",
        reference="Scene 4 -> Scene 7: Go to Scene 7",
    )
    change = tag_campaign.apply_tag_route_to_manifest(manifest, campaign)
    assert change == "extracted scene branch target ready"
    unlocked_prompt = tag_reference["room_prompts"]["tag-scene-7"]
    unlocked_labels = [action["label"] for action in unlocked_prompt["actions"]]
    assert "Apply Agaratha" in unlocked_labels
    assert "Apply scene reward" not in unlocked_labels


def test_tag_scene_graph_route_rewrite_uses_unlocked_scene_text(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    (data_dir / "tag_scene_narrative_overrides.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tag": {
                        "rumor": {
                            "1": {
                                "rooms": {
                                    "tag-lead-entry": {
                                        "description": "Bofto the halfling vine dresser has found a strange star-shaped object in his vineyard and has been behaving strangely. If you investigate, go to Scene 9."
                                    }
                                },
                                "scene_graph": {
                                "start_scenes": ["Scene 9"],
                                "scenes": {
                                    "Scene 9": {
                                        "description": (
                                            "Bofto the halfling looks after a large vineyard together with his wife and his two sons. "
                                            "A star-shaped object hangs from his neck. Will you: Try to steal the star shaped object? "
                                            "If so, choose one of your characters to do so and go to Scene 14. "
                                            "Try to talk to Bofto's family? Go to Scene 17. "
                                            "You may decide that you have nothing to do here."
                                        ),
                                        "branches": [
                                            {
                                                "label": "Steal the star object",
                                                "target_scene": "Scene 14",
                                                "target_scene_number": 14,
                                            },
                                            {
                                                "label": "Speak with the family",
                                                "target_scene": "Scene 17",
                                                "target_scene_number": 17,
                                            }
                                        ],
                                    },
                                    "Scene 14": {
                                        "description": "Thievery Save vs L6 text.",
                                        "branches": [
                                            {
                                                "label": "If you fail, go to Scene 18",
                                                "target_scene": "Scene 18",
                                                "target_scene_number": 18,
                                            },
                                            {
                                                "label": "If you succeed, go to Scene 19",
                                                "target_scene": "Scene 19",
                                                "target_scene_number": 19,
                                            }
                                        ],
                                    },
                                    "Scene 17": {"description": "The family explains the star.", "branches": []},
                                    "Scene 18": {"description": "The theft fails.", "branches": []},
                                    "Scene 19": {"description": "The theft succeeds.", "branches": []},
                                },
                            }
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    campaign = default_campaign()
    manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail="1")

    assert manifest["quest"]["complete_when"] == {"type": "tag_scene_resolved", "room_id": "tag-final-scene"}
    assert manifest["quest"]["objective_text"] == "Investigate Bofto's star-shaped object."
    result = validate_adventure_manifest(
        manifest,
        rules_repo=RulesRepository(Path("data/rules"), Path("data/rules/_override")),
    )
    assert result.valid, result.errors
    room_ids = {room["id"] for room in manifest["rooms"]}
    assert {"tag-scene-14", "tag-scene-17", "tag-scene-18", "tag-scene-19"} <= room_ids
    finale = next(room for room in manifest["rooms"] if room["id"] == "tag-final-scene")
    assert [(exit_def["direction"], exit_def["kind"]) for exit_def in finale["exits"]] == [
        ("south", "door"),
        ("north", "door"),
        ("east", "passage"),
    ]
    scene_14 = next(room for room in manifest["rooms"] if room["id"] == "tag-scene-14")
    assert [(exit_def["direction"], exit_def["kind"]) for exit_def in scene_14["exits"]] == [
        ("south", "door"),
        ("north", "passage"),
        ("west", "door"),
    ]
    entry = next(room for room in manifest["rooms"] if room["id"] == "tag-lead-entry")
    assert entry["description"].startswith("You overhear a rumour that")
    assert "go to Scene" not in entry["description"]
    assert [action["label"] for action in manifest["source"]["parameters"]["tag_reference"]["room_prompts"]["tag-lead-entry"]["actions"]] == [
        "Choose to investigate",
        "Don't investigate",
    ]
    final_actions = manifest["source"]["parameters"]["tag_reference"]["room_prompts"]["tag-final-scene"]["actions"]
    final_prompt = manifest["source"]["parameters"]["tag_reference"]["room_prompts"]["tag-final-scene"]
    assert "Will you:" not in final_prompt["body"]
    assert "go to Scene" not in final_prompt["body"]
    assert [action["label"] for action in final_actions] == [
        "Try to steal the star shaped object? If so, choose one of your characters to do so",
        "Try to talk to Bofto's family?",
        "You may decide that you have nothing to do here",
    ]
    assert any(action["action_value"] == "unlock_scene" and "Scene 14" in action["reference"] for action in final_actions)
    assert any(action["action_value"] == "final_route" for action in final_actions)
    scene_14_prompt = manifest["source"]["parameters"]["tag_reference"]["room_prompts"]["tag-scene-14"]
    assert scene_14_prompt["body"].startswith("Thievery Save vs L6")

    tag_campaign.resolve_tag_route_action(
        campaign,
        route_action="unlock_scene",
        reference="Scene 9 -> Scene 14: Steal the star object",
    )
    change = tag_campaign.apply_tag_route_to_manifest(manifest, campaign)

    assert change == "extracted scene branch target ready"
    unlocked = next(room for room in manifest["rooms"] if room["id"] == "tag-scene-14")
    assert unlocked["title"] == "Scene 14"
    assert unlocked["description"].startswith("Thievery Save vs L6")
    prompt = manifest["source"]["parameters"]["tag_reference"]["room_prompts"]["tag-scene-14"]
    assert prompt["title"] == "Scene 14"
    assert any(action["reference"].startswith("Scene 14 -> Scene 18") for action in prompt["actions"])


def test_tag_pdf_rumor_parser_keeps_scene_10_and_continued_entries() -> None:
    text = "\n".join(
        [
            "Rumors (d12)",
            "1",
            "First rumor. Go to Scene 9.",
            "2",
            "Second rumor. Go to Scene 10.",
            "Red Herring Table (d6)",
            "1-2)",
            "Trap text that should not be appended.",
            "24",
            "7",
            "Seventh rumor continues after the red herring table.",
            "8",
            "Eighth rumor.",
            "3",
            "Third rumor. Go to Scene 11.",
            "Scenes",
        ]
    )

    rumors = tag_campaign._extract_tag_pdf_rumors(text)

    assert rumors[2] == "Second rumor. Go to Scene 10."
    assert rumors[3] == "Third rumor. Go to Scene 11."
    assert rumors[7] == "Seventh rumor continues after the red herring table."
    assert rumors[8] == "Eighth rumor."
    assert "Trap text" not in " ".join(rumors.values())


def test_tag_pdf_page_joiner_keeps_wrapped_rumor_paragraph_and_branch() -> None:
    text = tag_campaign._join_tag_pdf_pages(
        [
            "\n".join(
                [
                    "Tales from the Adventurers' Guild",
                    "Rumors (d12)",
                    "2",
                    "A medusa has taken residence in an old hunter's cabin in the nearby woods.",
                    "She is said to wear an emerald necklace worth a fortune, and to be extremely",
                    "easy to bribe, to the point that some members of an assassins' guild are",
                    "trying to hire her for her",
                ]
            ),
            "\n".join(
                [
                    "James Banner Order #123",
                    "services. If you want to investigate, go to Scene 10.",
                    "Scenes",
                    "Scene 10",
                    "As you come closer to the hunter's cabin, have all the characters perform a Stealth Save vs. L6.",
                ]
            ),
        ]
    )

    rumors = tag_campaign._extract_tag_pdf_rumors(text)
    scenes = tag_campaign._extract_tag_pdf_scenes(text)

    assert "for her services. If you want to investigate, go to Scene 10." in rumors[2]
    assert "Scene 10" in rumors[2]
    assert 10 in scenes


def test_tag_pdf_cleaner_ignores_printed_page_numbers_inside_entries() -> None:
    text = tag_campaign._clean_pdf_text(
        "\n".join(
            [
                "Rumors (d12)",
                "2",
                "trying to hire her for her",
                "23",
                "services. If you want to investigate,",
                "go to  Scene 10.",
                "Scenes",
            ]
        )
    )

    rumors = tag_campaign._extract_tag_pdf_rumors(text)

    assert rumors[2] == "trying to hire her for her services. If you want to investigate, go to Scene 10."
    assert tag_campaign._audit_tag_pdf_extraction({2: rumors[2]}, {10: "Complete scene text."})[0].startswith("Missing Rumor")


def test_bundled_tag_pdf_extraction_keeps_medusa_rumor_page_wrap() -> None:
    pdf = Path("Rules/Tales_from_the_adventurers_guild.pdf")
    if not pdf.exists():
        return

    text = tag_campaign._extract_tag_pdf_text(pdf)
    rumors = tag_campaign._extract_tag_pdf_rumors(text)
    scenes = tag_campaign._extract_tag_pdf_scenes(text)
    warnings = tag_campaign._audit_tag_pdf_extraction(rumors, scenes)

    assert "for her services. If you want to investigate, go to Scene 10." in rumors[2]
    assert len(rumors) == 12
    assert len(scenes) == 19
    assert not [warning for warning in warnings if "may be cut off" in warning]


def test_tag_pdf_scene_parser_keeps_inline_scene_branches_inside_current_scene() -> None:
    text = "\n".join(
        [
            "Scenes",
            "Scene 9",
            "Will you try to steal the object? If so, go to Scene 14.",
            "Try to talk to the family? Go to Scene 17.",
            "Scene 10",
            "Once this encounter is over, you may reach the cabin by playing Scene 1 or go home.",
            "Scene 14",
            "If you fail, go to Scene 18. If you succeed, go to Scene 19.",
            "Scene 17",
            "If you insist, continue investigating by playing Scene 9.",
            "Scene 18",
            "The theft fails.",
            "Scene 19",
            "The object is stolen.",
            "Thematic Dungeons",
        ]
    )

    scenes = tag_campaign._extract_tag_pdf_scenes(text)

    assert set(scenes) == {9, 10, 14, 17, 18, 19}
    assert "Scene 14" in scenes[9]
    assert "Scene 17" in scenes[9]
    assert "Scene 1" in scenes[10]
    assert "Scene 18" in scenes[14]
    assert "Scene 19" in scenes[14]
    assert [branch["target_scene"] for branch in tag_campaign._extract_tag_scene_branches(9, scenes[9])] == [
        "Scene 14",
        "Scene 17",
    ]
    assert [branch["target_scene"] for branch in tag_campaign._extract_tag_scene_branches(14, scenes[14])] == [
        "Scene 18",
        "Scene 19",
    ]


def test_tag_scene_graph_follows_reachable_scene_branches_from_profile() -> None:
    scenes = {
        9: "Will you steal the object? Go to Scene 14. Talk to the family? Go to Scene 17.",
        14: "If you fail, go to Scene 18. If you succeed, go to Scene 19.",
        17: "If you insist, continue investigating by playing Scene 9.",
        18: "The theft fails.",
        19: "The object is stolen.",
    }

    graph = tag_campaign._scene_graph_for_profile(tag_campaign.TAG_RUMOR_PROFILES[1], scenes, "Tales.pdf")

    assert graph["start_scenes"] == ["Scene 9", "Scene 17", "Scene 14", "Scene 19"]
    assert set(graph["scenes"]) == {"Scene 9", "Scene 14", "Scene 17", "Scene 18", "Scene 19"}
    assert graph["scenes"]["Scene 9"]["branches"][0]["target_scene"] == "Scene 14"
    assert graph["scenes"]["Scene 14"]["branches"][1]["target_scene"] == "Scene 19"


def test_tag_leprechaun_rumor_is_vendor_scene_not_proxy_combat() -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    campaign = default_campaign()

    manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail="6")
    result = validate_adventure_manifest(manifest, rules_repo=repo)

    assert result.valid, result.errors
    reference = manifest["source"]["parameters"]["tag_reference"]
    assert reference["finale_mode"] == "vendor"
    assert "100 gp, or free if at least three pairs" in reference["rewards"]
    assert reference["final_foes"] == []
    assert manifest["quest"]["complete_when"] == {"type": "room_reached", "room_id": "tag-final-scene"}
    complication = next(room for room in manifest["rooms"] if room["id"] == "tag-complication")
    assert "Tiny footprints loop" in complication["description"]
    assert "The lead stops behaving" not in complication["description"]
    assert "encounter" not in complication["triggers"][0]
    final_room = next(room for room in manifest["rooms"] if room["id"] == "tag-final-scene")
    assert "encounter" not in final_room["triggers"][0]
    final_prompt = reference["room_prompts"]["tag-final-scene"]
    assert final_prompt["title"] == "Bargain choices"
    assert "per Scene 2" not in final_prompt["body"]
    assert "Reward note:" not in final_prompt["body"]
    assert [action["action_value"] for action in final_prompt["actions"]] == [
        "leprechaun_shoes",
        "leprechaun_illusion_spell",
    ]
    assert final_prompt["actions"][1]["amount"] == 100


def test_tag_generated_noncombat_finales_do_not_install_proxy_fights(monkeypatch) -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    campaign = default_campaign()
    expected = {
        ("rumor", "1"): ("choice", "Scene choices", {"bofto_scene_choice", "bofto_theft_save"}),
        ("rumor", "3"): ("procedure", "Scene procedure", {"tag_ambush_chance"}),
        ("rumor", "9"): ("procedure", "Scene procedure", {"daroc_cat"}),
        ("rumor", "11"): ("service", "Service choices", {"deoldyn_training", "mark_training_xp_roll"}),
    }

    for (lead_type, detail), (mode, title, actions) in expected.items():
        manifest, _entry = build_tag_adventure_manifest(campaign, lead_type=lead_type, detail=detail)
        result = validate_adventure_manifest(manifest, rules_repo=repo)

        assert result.valid, result.errors
        reference = manifest["source"]["parameters"]["tag_reference"]
        assert reference["finale_mode"] == mode
        assert reference["final_foes"] == []
        assert reference["final_foe_proxy"] == ""
        assert manifest["quest"]["complete_when"] == {"type": "room_reached", "room_id": "tag-final-scene"}
        final_room = next(room for room in manifest["rooms"] if room["id"] == "tag-final-scene")
        assert "encounter" not in final_room["triggers"][0]
        final_prompt = reference["room_prompts"]["tag-final-scene"]
        assert final_prompt["title"] == title
        assert actions <= {action["action_value"] for action in final_prompt["actions"]}
        assert not any(action["action_value"] == "claim_reward" for action in final_prompt["actions"])

    deoldyn, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail="11")
    deoldyn_ref = deoldyn["source"]["parameters"]["tag_reference"]
    assert deoldyn_ref["lead_structure"] == "trainer"
    assert deoldyn_ref["module_profile"]["target_rooms"] == "trainer downtime scene"
    entry_actions = deoldyn_ref["room_prompts"]["tag-lead-entry"]["actions"]
    assert any(action["action_value"] == "deoldyn_training" for action in entry_actions)

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 4)
    portrait, _entry = build_tag_adventure_manifest(campaign, lead_type="guild_job", detail="1")
    portrait_result = validate_adventure_manifest(portrait, rules_repo=repo)
    assert portrait_result.valid, portrait_result.errors
    portrait_ref = portrait["source"]["parameters"]["tag_reference"]
    assert portrait_ref["finale_mode"] == "procedure"
    assert portrait_ref["final_foes"] == []
    assert portrait["quest"]["complete_when"] == {"type": "room_reached", "room_id": "tag-final-scene"}
    assert "portrait_return_snatch" in {
        action["action_value"]
        for prompt in portrait_ref["room_prompts"].values()
        for action in prompt.get("actions", [])
    }


def test_tag_thematic_and_guild_job_manifests_use_profiles(monkeypatch) -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    campaign = default_campaign()

    dragon, _entry = build_tag_adventure_manifest(campaign, lead_type="thematic_dungeon", detail="3")
    dragon_result = validate_adventure_manifest(dragon, rules_repo=repo)
    assert dragon_result.valid, dragon_result.errors
    dragon_ref = dragon["source"]["parameters"]["tag_reference"]
    assert dragon["title"] == "The Adventures Guild Thematic Dungeon: Dragon's Lair"
    assert dragon_ref["pdf_pages"] == "TAG pp.39-40"
    assert dragon_ref["final_foe_proxy"] == "Young Dragon"
    assert dragon_ref["module_profile"]["target_rooms"] == "4-room dungeon"
    assert "Complete exactly four rooms" in dragon_ref["module_profile"]["procedure"][0]
    assert any("Four-room target" in rule for rule in dragon_ref["rules"])
    dragon_actions = dragon_ref["room_prompts"]["tag-complication"]["actions"]
    assert any(
        action["action_value"] == "clue_gate_unlocked" and action["amount"] == 2 and "dragon type" in action["label"].lower()
        for action in dragon_actions
    )
    assert any(action["action_value"] == "dragon_type_reveal" for action in dragon_actions)

    bandit, _entry = build_tag_adventure_manifest(campaign, lead_type="thematic_dungeon", detail="6")
    bandit_result = validate_adventure_manifest(bandit, rules_repo=repo)
    assert bandit_result.valid, bandit_result.errors
    bandit_ref = bandit["source"]["parameters"]["tag_reference"]
    bandit_actions = bandit_ref["room_prompts"]["tag-complication"]["actions"]
    assert any(
        action["action_value"] == "bandit_stolen_goods_check" and "stolen-goods" in action["tooltip"]
        for action in bandit_actions
    )

    rolls = iter([2])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    job, _entry = build_tag_adventure_manifest(campaign, lead_type="guild_job", detail="1")
    job_result = validate_adventure_manifest(job, rules_repo=repo)
    assert job_result.valid, job_result.errors
    job_ref = job["source"]["parameters"]["tag_reference"]
    assert job["title"] == "The Adventures Guild Job 1: Gorungar the Mighty"
    assert job_ref["pdf_pages"] == "TAG p.55"
    assert job_ref["final_foe_proxy"] == "Gorungar the Mighty"
    assert "50 gp for his head" in job_ref["rewards"]
    assert job_ref["module_profile"]["target_rooms"] == "single guild-job encounter"
    assert job_ref["room_prompts"]["tag-final-scene"]["title"] == "Gorungar's Ambush"
    assert any(action["action_value"] == "gorungar_alive" for action in job_ref["room_prompts"]["tag-final-scene"]["actions"])
    final_room = next(room for room in job["rooms"] if room["id"] == "tag-final-scene")
    assert final_room["triggers"][0]["encounter"]["foes"] == [
        {"name": "Gorungar the Mighty", "count": 1},
        {"name": "Gorungar's Goblin Archers", "count": 8},
    ]


def test_tag_special_foes_are_allowlisted_and_used_in_generated_adventures() -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    campaign = default_campaign()

    shaura, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail="8")
    assert validate_adventure_manifest(shaura, rules_repo=repo).valid
    shaura_ref = shaura["source"]["parameters"]["tag_reference"]
    assert shaura_ref["module_profile"]["target_rooms"] == "10-room dungeon"
    assert shaura_ref["final_foes"] == [
        {"name": "Silent Scream Priestess", "count": 1},
        {"name": "Silent Scream Cultists", "count": 9},
    ]
    assert any(action["action_value"] == "shaura_reward" for action in shaura_ref["room_prompts"]["tag-final-scene"]["actions"])

    rumor, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail="10")
    assert validate_adventure_manifest(rumor, rules_repo=repo).valid
    rumor_ref = rumor["source"]["parameters"]["tag_reference"]
    assert rumor_ref["final_foes"] == [{"name": "White Gargoyles", "count": 8}]

    theme, _entry = build_tag_adventure_manifest(campaign, lead_type="thematic_dungeon", detail="6")
    assert validate_adventure_manifest(theme, rules_repo=repo).valid
    theme_ref = theme["source"]["parameters"]["tag_reference"]
    assert theme_ref["final_foes"] == [
        {"name": "Bandit Chieftain", "count": 1},
        {"name": "TAG Bandits", "count": 6},
    ]
    assert theme_ref["module_profile"]["target_rooms"] == "HCL+3 rooms"
    assert any(action["action_value"] == "bandit_chieftain_capture" for action in theme_ref["room_prompts"]["tag-final-scene"]["actions"])


def test_tag_rumor_manifests_include_contextual_scene_procedure_prompts() -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    campaign = default_campaign()
    expected_actions = {
        "1": {"bofto_scene_choice", "bofto_theft_save", "star_object_will_save", "star_slayer_check"},
        "3": {"tag_ambush_chance"},
        "4": {"mutant_fish_hypnosis", "mutant_fish_rations", "mark_minor_encounters"},
        "5": {"dragon_type_reveal"},
        "6": {"leprechaun_shoes", "leprechaun_illusion_spell"},
        "7": {"temple_dungeon_handoff"},
        "9": {"daroc_cat"},
        "10": {"gargoyle_count", "gargoyle_surprise", "gargoyle_skin", "gargoyle_bounty"},
        "11": {"deoldyn_training", "mark_training_xp_roll"},
        "12": {"solo_restriction", "agaratha"},
    }
    for detail, expected in expected_actions.items():
        manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail=detail)
        assert validate_adventure_manifest(manifest, rules_repo=repo).valid
        prompts = manifest["source"]["parameters"]["tag_reference"]["room_prompts"]
        assert "tag-return-road" in prompts
        found = {
            str(action.get("action_value"))
            for prompt in prompts.values()
            for action in prompt.get("actions", [])
            if action.get("action_value")
        }
        assert expected <= found

    temple, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail="7")
    reference = temple["source"]["parameters"]["tag_reference"]
    assert reference["module_profile"]["target_rooms"] == "seven-room temple dungeon"


def test_mutant_fish_rumor_is_hypnosis_procedure_not_proxy_boss() -> None:
    manifest, _entry = build_tag_adventure_manifest(default_campaign(), lead_type="rumor", detail="4")
    reference = manifest["source"]["parameters"]["tag_reference"]
    assert reference["finale_mode"] == "procedure"
    assert reference["final_foes"] == []
    assert manifest["quest"]["complete_when"] == {"type": "room_reached", "room_id": "tag-final-scene"}
    final_room = next(room for room in manifest["rooms"] if room["id"] == "tag-final-scene")
    assert "encounter" not in final_room["triggers"][0]
    assert "no combat stats" in final_room["description"]
    assert "bridge pool scene is active" in final_room["triggers"][0]["log"].lower()


def test_all_tag_rumor_manifests_include_playthrough_audit_guidance() -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    campaign = default_campaign()

    for number in range(1, 13):
        manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail=str(number))
        assert validate_adventure_manifest(manifest, rules_repo=repo).valid
        reference = manifest["source"]["parameters"]["tag_reference"]
        prompts = reference["room_prompts"]

        assert reference["audit_family"] == "rumor_playthrough"
        assert reference["rumor_number"] == number
        assert reference["playthrough_focus"]
        assert reference["signoff_checks"]
        assert "Rumor audit focus" in reference["module_profile"]["procedure"][-1]
        assert "Confirm the printed scene/result" in reference["module_profile"]["signoff_checks"][-3]
        assert "you walk into a room" not in " ".join(prompt["body"].lower() for prompt in prompts.values())
        assert "Prompt checklist" not in prompts["tag-final-scene"]["body"]
        assert prompts["tag-lead-entry"]["checklist"]
        assert prompts["tag-complication"]["checklist"]
        assert prompts["tag-final-scene"]["checklist"]
        assert any("Guild" in item or "banking" in item for item in prompts["tag-final-scene"]["checklist"])
        assert any(action["tooltip"] for prompt in prompts.values() for action in prompt.get("actions", []))


def test_tag_treasure_map_manifests_include_destination_procedure_prompts() -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    campaign = default_campaign()
    expected_actions = {
        "1": {"map_cave_room_count"},
        "2": {"map_temple_idol", "map_temple_scroll"},
        "3": {"map_humanoid_report", "map_humanoid_stealth", "map_humanoid_forces"},
        "4": {"map_structure_rooms"},
        "5": {"map_structure_rooms"},
        "6": {"map_lich_death_magic", "map_lich_life", "map_lich_treasure"},
    }
    expected_targets = {
        "1": "d6+3-room standard dungeon",
        "2": "forgotten wilderness temple",
        "3": "hostile humanoid camp",
        "4": "2d6-room underground structure",
        "5": "2d6-room boss-only underground structure",
        "6": "one-room lich sepulchral chamber",
    }
    for detail, expected in expected_actions.items():
        manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="treasure_map", detail=detail)
        assert validate_adventure_manifest(manifest, rules_repo=repo).valid
        reference = manifest["source"]["parameters"]["tag_reference"]
        assert reference["pdf_pages"] == "TAG pp.32-33"
        assert reference["audit_family"] == "treasure_map_playthrough"
        assert reference["treasure_map_destination"] == int(detail)
        assert reference["playthrough_focus"]
        assert reference["signoff_checks"]
        assert reference["module_profile"]["target_rooms"] == expected_targets[detail]
        assert "Treasure Map audit focus" in reference["module_profile"]["procedure"][-1]
        assert "Confirm the Follow Treasure Map result" in reference["module_profile"]["signoff_checks"][-3]
        assert reference["room_prompts"]["tag-lead-entry"]["checklist"]
        assert reference["room_prompts"]["tag-final-scene"]["checklist"]
        assert any("Guild" in item or "banking" in item for item in reference["room_prompts"]["tag-final-scene"]["checklist"])
        assert "you walk into a room" not in " ".join(prompt["body"].lower() for prompt in reference["room_prompts"].values())
        descriptions = " ".join(str(room.get("description", "")) for room in manifest["rooms"])
        assert "last warmth of the home settlement" not in descriptions
        assert "This is where the lead comes due" not in descriptions
        assert "Apply The Map Leads To" not in reference["rewards"]
        assert "procedure" in reference["rewards"]
        assert reference["side_reward_note"]
        if detail == "1":
            assert "Claim Treasure" in reference["side_reward_note"]
            assert "Underground caves" in reference["final_reward_note"]
        found = {
            str(action.get("action_value"))
            for prompt in reference["room_prompts"].values()
            for action in prompt.get("actions", [])
            if action.get("action_value")
        }
        assert expected <= found


def test_tag_remaining_themes_carry_pdf_module_profiles() -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    campaign = default_campaign()

    expected = {
        "1": ("Ghastly Mine", "9-room dungeon", "cave-ins"),
        "2": ("Giant's Lair", "HCL+5 rooms", "boulder"),
        "3": ("Dragon's Lair", "4-room dungeon", "dragon"),
        "4": ("Fiendish Abyss", "HCL+5 rooms", "Prisoner Table"),
        "5": ("Minotaur Maze", "d6+5 rooms", "lost"),
        "6": ("Bandit Hideout", "HCL+3 rooms", "stolen-goods"),
    }
    for detail, (title, target, keyword) in expected.items():
        manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="thematic_dungeon", detail=detail)
        assert validate_adventure_manifest(manifest, rules_repo=repo).valid
        reference = manifest["source"]["parameters"]["tag_reference"]
        assert reference["title"] == title
        assert reference["audit_family"] == "thematic_dungeon_playthrough"
        assert reference["thematic_dungeon_number"] == int(detail)
        assert reference["playthrough_focus"]
        assert reference["signoff_checks"]
        assert reference["module_profile"]["target_rooms"] == target
        assert "Thematic Dungeon audit focus" in reference["module_profile"]["procedure"][-1]
        assert "Confirm the Thematic Dungeon result" in reference["module_profile"]["signoff_checks"][-3]
        assert reference["room_prompts"]["tag-lead-entry"]["checklist"]
        assert reference["room_prompts"]["tag-complication"]["checklist"]
        assert reference["room_prompts"]["tag-final-scene"]["checklist"]
        assert any("Guild" in item or "banking" in item for item in reference["room_prompts"]["tag-final-scene"]["checklist"])
        assert "you walk into a room" not in " ".join(prompt["body"].lower() for prompt in reference["room_prompts"].values())
        descriptions = " ".join(str(room.get("description", "")) for room in manifest["rooms"])
        assert "lead stops behaving like a route" not in descriptions
        assert "Complication" in descriptions or keyword.lower() in descriptions.lower()
        assert "This is where the lead comes due" not in descriptions
        joined = " ".join(reference["module_profile"]["procedure"] + reference["module_profile"]["signoff_checks"])
        assert keyword.lower() in joined.lower()
        actions = reference["room_prompts"]["tag-complication"]["actions"] + reference["room_prompts"]["tag-final-scene"]["actions"]
        action_values = {action["action_value"] for action in actions}
        if detail == "1":
            assert {"ghastly_mine_minion_replacement", "ghastly_mine_major_replacement", "ghastly_mine_cave_in", "ghastly_mine_treasure_conversion"} <= action_values
        if detail == "2":
            assert {"giant_lair_boulder", "giant_lair_treasure"} <= action_values
        if detail == "3":
            assert "dragon_type_reveal" in action_values
        if detail == "4":
            assert "fiendish_abyss_prisoner" in action_values
        if detail == "5":
            assert {"minotaur_maze_lost_check", "minotaur_maze_wandering", "minotaur_maze_event", "unlock_scene"} <= action_values
        if detail == "6":
            assert {"bandit_stolen_goods_check", "capture_alive", "bandit_chieftain_capture"} <= action_values


def test_tag_guild_job_manifests_include_playthrough_audit_guidance(monkeypatch) -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    campaign = default_campaign()
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 3)
    monkeypatch.setattr(tag_campaign, "roll_d12", lambda: 6)

    for detail in range(1, 7):
        manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="guild_job", detail=str(detail))
        assert validate_adventure_manifest(manifest, rules_repo=repo).valid
        reference = manifest["source"]["parameters"]["tag_reference"]

        assert reference["lead_type"] == "guild_job"
        assert reference["audit_family"] == "guild_job_playthrough"
        assert reference["guild_job_result"] == detail
        assert reference["playthrough_focus"]
        assert reference["signoff_checks"]
        assert "Guild Job audit focus" in reference["module_profile"]["procedure"][-1]
        assert "Confirm the printed Guild Job result" in reference["module_profile"]["signoff_checks"][-3]
        assert reference["room_prompts"]["tag-lead-entry"]["checklist"]
        assert reference["room_prompts"]["tag-complication"]["checklist"]
        assert reference["room_prompts"]["tag-final-scene"]["checklist"]
        assert any("Guild" in item or "banking" in item for item in reference["room_prompts"]["tag-final-scene"]["checklist"])
        assert "you walk into a room" not in " ".join(prompt["body"].lower() for prompt in reference["room_prompts"].values())


def test_all_generated_tag_modules_have_playable_scene_actions_and_clean_room_copy(monkeypatch) -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    cases = {
        "rumor": [str(i) for i in range(1, 13)],
        "treasure_map": [str(i) for i in range(1, 7)],
        "thematic_dungeon": [str(i) for i in range(1, 7)],
        "guild_job": [str(i) for i in range(1, 7)],
    }
    stale_phrases = [
        "The lead stops behaving",
        "TAG guidance",
        "TAG source",
        "Adventures Guild guidance",
        "Adventures Guild actions here",
        "Check final foe",
        "Reward note:",
        "you walk into a room",
        "This is where the lead comes due",
        "last warmth of the home settlement",
    ]
    generic_actions = {
        "social_choice",
        "skip_scene",
        "claim_reward",
        "mark_scene_xp",
        "parley_success",
        "parley_failed",
        "clue_gate_unlocked",
        "clue_gate_blocked",
        "final_route",
        "unlock_scene",
    }
    reward_policy_classes = {
        "no_loot",
        "scene_reward_button",
        "purchase_or_service",
        "compact_module_no_random_loot",
        "handoff_dungeon_has_own_loot",
    }

    for lead_type, details in cases.items():
        for detail in details:
            campaign = default_campaign()
            clean_detail = detail
            if lead_type == "guild_job":
                monkeypatch.setattr(tag_campaign, "roll_d6", lambda roll=int(detail): roll)
                clean_detail = "1"
            manifest, _entry = build_tag_adventure_manifest(campaign, lead_type=lead_type, detail=clean_detail)
            result = validate_adventure_manifest(manifest, rules_repo=repo)
            assert result.valid, (lead_type, detail, result.errors)
            reference = manifest["source"]["parameters"]["tag_reference"]
            reward_policy = reference.get("reward_policy")
            assert isinstance(reward_policy, dict), (lead_type, detail)
            assert reward_policy["class"] in reward_policy_classes, (lead_type, detail, reward_policy)
            assert reward_policy["label"], (lead_type, detail, reward_policy)
            assert reward_policy["expectation"], (lead_type, detail, reward_policy)
            prompts = reference["room_prompts"]
            room_text = " ".join(
                " ".join(
                    [
                        str(room.get("title", "")),
                        str(room.get("description", "")),
                        " ".join(str(trigger.get("log", "")) for trigger in room.get("triggers", []) if isinstance(trigger, dict)),
                    ]
                )
                for room in manifest["rooms"]
            )
            prompt_text = " ".join(str(prompt.get("body", "")) for prompt in prompts.values())
            for phrase in stale_phrases:
                assert phrase.lower() not in room_text.lower(), (lead_type, detail, phrase)
                assert phrase.lower() not in prompt_text.lower(), (lead_type, detail, phrase)

            actions = prompts["tag-complication"]["actions"] + prompts["tag-final-scene"]["actions"]
            specific = [
                action.get("action_value")
                for action in actions
                if action.get("action_value") and action.get("action_value") not in generic_actions
            ]
            assert specific, (lead_type, detail)

            if lead_type == "rumor" and detail == "2":
                final_room = next(room for room in manifest["rooms"] if room["id"] == "tag-final-scene")
                assert "encounter" not in final_room["triggers"][0]


def test_generated_tag_reward_policy_boundaries_are_explicit() -> None:
    rumor4, _entry = build_tag_adventure_manifest(default_campaign(), lead_type="rumor", detail="4")
    fish_policy = rumor4["source"]["parameters"]["tag_reference"]["reward_policy"]
    assert fish_policy["class"] == "scene_reward_button"
    assert "Fish rations" in fish_policy["actions"]
    assert "ordinary" not in fish_policy["expectation"].lower()

    rumor11, _entry = build_tag_adventure_manifest(default_campaign(), lead_type="rumor", detail="11")
    trainer_policy = rumor11["source"]["parameters"]["tag_reference"]["reward_policy"]
    assert trainer_policy["class"] == "purchase_or_service"

    rumor12, _entry = build_tag_adventure_manifest(default_campaign(), lead_type="rumor", detail="12")
    handoff_policy = rumor12["source"]["parameters"]["tag_reference"]["reward_policy"]
    assert handoff_policy["class"] == "handoff_dungeon_has_own_loot"
    assert handoff_policy["normal_random_loot"] is True


def test_tag_remaining_guild_jobs_carry_pdf_module_profiles(monkeypatch) -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    expected = {
        1: ("Clean Up My Castle", "exactly 10 rooms", "portrait cache", "clue_gate_unlocked"),
        3: ("Griffin Omelets, Anyone?", "mountain approach and nest", "70 gp per intact egg", None),
        4: ("A Portrait in Red", "outbound and return wilderness escort", "painting", None),
        5: ("Sewers Search", "small sewer dungeon", "3 Clues", "clue_gate_unlocked"),
        6: ("Monoceros Hunt", "wilderness hunt and capture encounter", "3 Clues", "capture_alive"),
    }
    for quest_roll, (title, target, keyword, action_value) in expected.items():
        campaign = default_campaign()
        monkeypatch.setattr(tag_campaign, "roll_d6", lambda roll=quest_roll: roll)
        manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="guild_job", detail="1")
        assert validate_adventure_manifest(manifest, rules_repo=repo).valid
        reference = manifest["source"]["parameters"]["tag_reference"]
        assert reference["title"] == title
        assert reference["module_profile"]["target_rooms"] == target
        joined = " ".join(reference["module_profile"]["procedure"] + reference["module_profile"]["signoff_checks"] + [reference["rewards"]])
        assert keyword.lower() in joined.lower()
        actions = reference["room_prompts"]["tag-complication"]["actions"] + reference["room_prompts"]["tag-final-scene"]["actions"]
        action_values = {action["action_value"] for action in actions}
        if action_value:
            assert any(action["action_value"] == action_value for action in actions)
        if quest_roll == 1:
            assert {"castle_cleanup_pay", "clue_gate_unlocked"} <= action_values
        if quest_roll == 3:
            assert {"griffin_mountain_check", "griffin_nest_search", "griffin_egg_count", "griffin_egg_break"} <= action_values
        if quest_roll == 4:
            assert {"portrait_outbound_check", "portrait_persuasion", "portrait_return_snatch"} <= action_values
            assert reference["finale_mode"] == "procedure"
            assert reference["final_foes"] == []
        if quest_roll == 5:
            assert {"sewers_vermin", "sewers_minions", "sewers_disease", "clue_gate_unlocked", "capture_alive"} <= action_values
            assert reference["final_foes"] == [{"name": "Sewer Thief", "count": 1}]
        if quest_roll == 6:
            assert {"monoceros_tracking", "monoceros_clue_encounter", "monoceros_hide", "capture_alive"} <= action_values


def test_tag_branch_trinket_guild_spell_and_finance_actions(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(
        gold=10,
        clues=5,
        current_life=1,
        inventory=["Potion of Healing", "Scroll of Wizard's Luck"],
        spells=["Look Tough"],
        statuses=["Poisoned"],
    )

    branch = resolve_tag_branch_action(
        campaign,
        hero,
        branch_action="spend_clues",
        reference="Scene 16 clue spend",
        clue_cost=2,
    )
    assert hero.clues == 3
    assert "spends 2 Clue" in branch.result_text

    trinket = use_tag_trinket(campaign, hero, trinket_key="potion_of_healing")
    assert hero.current_life == hero.max_life
    assert "Poisoned" not in hero.statuses
    assert "Potion of Healing" not in hero.inventory
    assert "uses Potion of Healing" in trinket.result_text

    spell = cast_tag_guild_spell(campaign, hero, spell_key="wizards_luck")
    assert "Scroll of Wizard's Luck" not in hero.inventory
    assert "TAG Wizard's Luck gambling cheat pending" in hero.statuses
    assert "scroll consumed" in spell.result_text

    hero.current_life = 1
    hero.inventory.append("Scroll of Speedy Recovery")
    recovery_spell = cast_tag_guild_spell(campaign, hero, spell_key="speedy_recovery")
    assert hero.current_life == 1
    assert "TAG Speedy Recovery settlement healing 2/day" in hero.statuses
    assert "2 Life per day" in recovery_spell.result_text
    assert "scroll consumed" in recovery_spell.result_text

    clear_marker = consume_tag_guild_marker(campaign, hero, marker_key="speedy_recovery")
    assert "TAG Speedy Recovery settlement healing 2/day" not in hero.statuses
    assert "clears TAG Guild marker" in clear_marker.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 1)
    risk = resolve_tag_finance_action(campaign, hero, finance_action="robbery_risk")
    assert risk.total == 3
    assert "robbery or theft occurs" in risk.result_text

    recovery = resolve_tag_finance_action(campaign, hero, finance_action="robbery_recovery")
    assert "spends 3 Clues" in recovery.result_text

    campaign.tag_guild_coffers_gp = 1000
    upkeep = resolve_tag_finance_action(campaign, finance_action="guild_upkeep")
    assert campaign.tag_guild_coffers_gp == 900
    assert "100 gp paid" in upkeep.result_text


def test_tag_bank_robbery_risk_marks_and_recovery_clears_account(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(clues=3, gold=40)
    resolve_tag_finance_action(campaign, hero, finance_action="bank_deposit", amount_gp=10)

    monkeypatch.setattr(tag_campaign, "roll_3d6", lambda: (5, [1, 2, 2]))
    risk = resolve_tag_finance_action(campaign, hero, finance_action="robbery_risk")

    account = next(item for item in campaign.tag_bank_accounts if item.owner_character_id == hero.id)
    assert account.robbed is True
    assert "marked robbed" in risk.result_text

    recovery = resolve_tag_finance_action(campaign, hero, finance_action="robbery_recovery")
    assert account.robbed is False
    assert hero.clues == 0
    assert "Bandit Hideout lead" in recovery.result_text


def test_tag_look_tough_spell_bonus_is_consumed_on_next_streetwise(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(class_id="rogue", class_name="Rogue", level=5, clues=0, statuses=[])
    cast_tag_guild_spell(campaign, hero, spell_key="look_tough")

    rolls = iter([1, 3])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    entry = look_for_clues(campaign, hero)

    assert "TAG Look Tough next Streetwise bonus" not in hero.statuses
    assert entry.modifier == 7
    assert entry.total == 10
    assert hero.clues == 1
    assert "tier-number bonus" in entry.result_text


def test_tag_wizards_luck_resolves_gambling_success_and_natural_one(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(class_id="wizard", class_name="Wizard", level=5, gold=100, statuses=[])
    cast_tag_guild_spell(campaign, hero, spell_key="wizards_luck")

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 5)
    success = roll_gambling_house(campaign, hero, stake_gp=20)

    assert "TAG Wizard's Luck gambling cheat pending" not in hero.statuses
    assert hero.gold == 110
    assert "choose Gambling House result 10" in success.result_text
    assert "succeeds" in success.result_text

    cast_tag_guild_spell(campaign, hero, spell_key="wizards_luck")
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 1)
    jailed = roll_gambling_house(campaign, hero, stake_gp=20)

    assert hero.gold == 0
    assert any(status.startswith("TAG Wizard's Luck jail fine debt") for status in hero.statuses)
    assert "natural 1" in jailed.result_text
    assert "fine" in jailed.result_text


def test_tag_guild_spell_target_workflows() -> None:
    campaign = default_campaign()
    caster = _character(
        id="caster-1",
        name="Merga",
        class_id="wizard",
        class_name="Wizard",
        inventory=["Hand weapon", "Scroll of Temporary Weapon Enchantment"],
        spells=["Troupe Switch", "Silence of the Mouse"],
        statuses=[],
    )
    target = _character(id="target-1", name="Dargo", class_id="rogue", class_name="Rogue", statuses=[])

    weapon = cast_tag_guild_spell(
        campaign,
        caster,
        spell_key="temporary_weapon_enchantment",
        target_weapon="Hand weapon",
    )
    assert "Scroll of Temporary Weapon Enchantment" not in caster.inventory
    assert any(status == "TAG Temporary Weapon Enchantment: Hand weapon is magical, no Attack bonus" for status in caster.statuses)
    assert "Target weapon: Hand weapon" in weapon.result_text

    troupe = cast_tag_guild_spell(campaign, caster, spell_key="troupe_switch", target_character=target)
    assert any(status.startswith("TAG Troupe Switch caster: may swap with Dargo") for status in caster.statuses)
    assert any(status.startswith("TAG Troupe Switch recipient for Merga") for status in target.statuses)
    assert "Recipient: Dargo" in troupe.result_text

    silence = cast_tag_guild_spell(campaign, caster, spell_key="silence_of_the_mouse", target_character=target)
    assert any(status.startswith("TAG Silence of the Mouse: Stealth switched with Dargo") for status in caster.statuses)
    assert any(status.startswith("TAG Silence of the Mouse: Stealth switched with Merga") for status in target.statuses)
    assert "Paired character: Dargo" in silence.result_text

    clear_weapon = consume_tag_guild_marker(campaign, caster, marker_key="temporary_weapon_enchantment")
    assert not any(status.startswith("TAG Temporary Weapon Enchantment:") for status in caster.statuses)
    assert "Hand weapon is magical" in clear_weapon.result_text

    clear_silence = consume_tag_guild_marker(campaign, target, marker_key="silence_of_the_mouse")
    assert not any(status.startswith("TAG Silence of the Mouse:") for status in target.statuses)
    assert "clears TAG Guild marker" in clear_silence.result_text


def test_tag_route_and_xp_actions_persist_structured_signoff_state() -> None:
    campaign = default_campaign()
    hero = _character(clues=3, xp=2, statuses=[])

    route = resolve_tag_route_action(
        campaign,
        hero,
        route_action="clue_gate_unlocked",
        reference="Scene 16 cult hideout",
        clue_cost=2,
    )
    assert hero.clues == 1
    assert campaign.tag_adventure_routes[-1].route_action == "clue_gate_unlocked"
    assert campaign.tag_adventure_routes[-1].resolved is True
    assert "route is unlocked" in route.result_text

    blocked = resolve_tag_route_action(
        campaign,
        hero,
        route_action="clue_gate_blocked",
        reference="Dragon lair reveal",
        clue_cost=2,
    )
    assert campaign.tag_adventure_routes[-1].resolved is False
    assert "Route remains blocked" in blocked.result_text

    xp = resolve_tag_xp_action(campaign, hero, xp_action="award_scene_xp", reference="Daroc's cat", xp=1)
    assert hero.xp == 3
    assert campaign.tag_xp_markers[-1].applied is True
    assert "gains 1 XP" in xp.result_text

    training = resolve_tag_xp_action(campaign, hero, xp_action="mark_training_xp_roll", reference="Deoldyn", xp=0)
    assert "TAG Deoldyn archery XP roll pending" in hero.statuses
    assert campaign.tag_xp_markers[-1].xp_action == "mark_training_xp_roll"
    assert "Training XP roll marker" in training.result_text


def test_tag_scene_rewards_and_bank_ledgers(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(class_id="warrior", class_name="Warrior", gold=500, clues=3, level=2, inventory=[], statuses=[])

    bounty = resolve_tag_scene_action(campaign, hero, scene_action="gargoyle_bounty", amount=3)
    assert hero.gold == 545
    assert "45 gp" in bounty.result_text

    agaratha = resolve_tag_scene_action(campaign, hero, scene_action="agaratha")
    assert any(item.startswith("Agaratha") for item in hero.inventory)
    assert "TAG Agaratha Luck-on-major-kill" in hero.statuses
    assert "Luck-on-major-kill" in agaratha.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 4)
    reveal = resolve_tag_scene_action(campaign, hero, scene_action="dragon_type_reveal")
    assert hero.clues == 1
    assert "Dragon's Lair" in reveal.result_text

    deposit = resolve_tag_finance_action(campaign, hero, finance_action="bank_deposit", amount_gp=100, note="Sister Joyce")
    assert hero.gold == 435
    assert campaign.tag_bank_accounts[0].gold_gp == 100
    assert campaign.tag_bank_accounts[0].notes == "Sister Joyce"
    assert "10 gp fee" in deposit.result_text

    inheritance = resolve_tag_finance_action(campaign, hero, finance_action="inheritance", note="Sister Joyce")
    assert campaign.tag_bank_accounts[0].heir_name == "Sister Joyce"
    assert "20% inheritance tax" in inheritance.result_text

    heir = _character(id="heir-1", name="Sister Joyce", gold=0)
    transfer = resolve_tag_finance_action(campaign, heir, finance_action="inheritance_transfer")
    assert heir.gold == 80
    assert campaign.tag_bank_accounts[0].gold_gp == 0
    assert "20 gp inheritance tax" in transfer.result_text


def test_shinta_solo_route_requires_valid_sword_capable_champion() -> None:
    campaign = default_campaign()
    rogue = _character(class_id="rogue", class_name="Rogue")
    blocked = resolve_tag_route_action(
        campaign,
        rogue,
        route_action="solo_restriction",
        reference="Scene 4 Shinta champion -> Scene 7 solo Bandit Hideout",
    )
    assert campaign.tag_adventure_routes[-1].resolved is False
    assert "may not use this type of equipment" in blocked.result_text

    paladin = _character(class_id="paladin", class_name="Paladin")
    accepted = resolve_tag_route_action(
        campaign,
        paladin,
        route_action="solo_restriction",
        reference="Scene 4 Shinta champion -> Scene 7 solo Bandit Hideout",
    )
    assert campaign.tag_adventure_routes[-1].resolved is True
    assert "single-character quest" in accepted.result_text
    assert "solo ten-room Bandit Hideout" in accepted.result_text


def test_agaratha_rejects_invalid_wielder() -> None:
    campaign = default_campaign()
    rogue = _character(class_id="rogue", class_name="Rogue")
    result = resolve_tag_scene_action(campaign, rogue, scene_action="agaratha")
    assert not any(item.startswith("Agaratha") for item in rogue.inventory)
    assert "may not use this type of equipment" in result.result_text


def test_deoldyn_training_pays_rolls_and_applies_selected_archery_skill(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(class_id="warrior", class_name="Warrior", level=3, gold=200, inventory=[])

    monkeypatch.setattr(
        tag_campaign,
        "roll_advancement",
        lambda level, member=None, purpose="level_up": AdvancementRollResult(
            natural=6, total=6, sides=6, purpose=purpose
        ),
    )

    result = resolve_tag_scene_action(
        campaign,
        hero,
        scene_action="deoldyn_training",
        reference="Scene 3 Deoldyn training: Dead Shot",
    )

    assert hero.gold == 20
    assert "dead_shot" in hero.learned_expert_skills
    assert "Dead Shot" in hero.abilities
    assert "succeeds" in result.result_text


def test_deoldyn_training_rejects_non_bow_capable_character(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(class_id="rogue", class_name="Rogue", level=3, gold=200, inventory=[])

    result = resolve_tag_scene_action(
        campaign,
        hero,
        scene_action="deoldyn_training",
        reference="Scene 3 Deoldyn training: Deadly Accuracy",
    )

    assert hero.gold == 200
    assert "deadly_accuracy" not in hero.learned_expert_skills
    assert "cannot" in result.result_text.lower() or "not" in result.result_text.lower()


def test_tag_bandit_stolen_goods_branch_rolls_room_goods(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(clues=0)
    starting_gold = hero.gold

    rolls = iter([1, 2, 3, 4, 5, 6, 1, 2, 3, 2])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    found = resolve_tag_branch_action(
        campaign,
        hero,
        branch_action="bandit_stolen_goods_check",
        reference="Bandit Hideout room 2",
    )
    assert found.roll == 1
    assert found.total == 26
    assert "Stolen goods found: 8d6=26 gp" in found.result_text
    assert "trapdoor protection is present" in found.result_text
    assert hero.gold == starting_gold

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 4)
    missed = resolve_tag_branch_action(campaign, hero, branch_action="bandit_stolen_goods_check")
    assert missed.roll == 4
    assert missed.total is None
    assert "no stolen goods" in missed.result_text


def test_tag_rumor_branch_actions_roll_scene_procedures(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(gold=500, clues=0, inventory=[], statuses=[])

    bofto = resolve_tag_branch_action(campaign, hero, branch_action="bofto_scene_choice", reference="talk to family")
    assert "Scene 9 choice recorded" in bofto.result_text
    assert "Scene 17" in bofto.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 2)
    ambush = resolve_tag_branch_action(campaign, hero, branch_action="tag_ambush_chance", clue_cost=2)
    assert ambush.roll == 2
    assert "encounter occurs" in ambush.result_text

    monkeypatch.setattr(tag_campaign, "roll_d3", lambda: 2)
    assassins = resolve_tag_branch_action(campaign, hero, branch_action="medusa_assassin_ambush", clue_cost=1)
    assert assassins.roll == 2
    assert assassins.total == 4
    assert "4 assassin agents" in assassins.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 5)
    stealth = resolve_tag_branch_action(campaign, hero, branch_action="medusa_stealth_approach", reference="mod=1")
    assert stealth.total == 6
    assert "attacks once before Xasartha" in stealth.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 1)
    reaction = resolve_tag_branch_action(campaign, hero, branch_action="medusa_reaction")
    assert "6d6 gp" in reaction.result_text

    shoes = resolve_tag_branch_action(campaign, hero, branch_action="leprechaun_shoes", clue_cost=2)
    assert hero.gold == 100
    assert hero.inventory.count("Shoes of Fast Walk") == 2
    assert "400 gp" in shoes.result_text

    spell = resolve_tag_branch_action(campaign, hero, branch_action="leprechaun_illusion_spell", reference="free silent image")
    assert any("silent image" in status for status in hero.statuses)
    assert hero.gold == 100

    fish = resolve_tag_branch_action(campaign, hero, branch_action="mutant_fish_hypnosis", reference="chaos")
    assert "fails automatically" in fish.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 4)
    count = resolve_tag_branch_action(campaign, hero, branch_action="gargoyle_count")
    assert count.total == 6
    assert "6 gargoyles" in count.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 3)
    surprise = resolve_tag_branch_action(campaign, hero, branch_action="gargoyle_surprise")
    assert "surprise the party" in surprise.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 2)
    skin = resolve_tag_branch_action(campaign, hero, branch_action="gargoyle_skin")
    assert "bounces off" in skin.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 5)
    theft = resolve_tag_branch_action(campaign, hero, branch_action="bofto_theft_save", reference="mod=1")
    assert theft.total == 6
    assert "Go to Scene 19" in theft.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 2)
    will = resolve_tag_branch_action(campaign, hero, branch_action="star_object_will_save", reference="mod=3")
    assert will.total == 5
    assert "TAG star-shaped object curse carrier" in hero.statuses

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 1)
    slayer = resolve_tag_branch_action(campaign, hero, branch_action="star_slayer_check")
    assert "Star-Slayer from Beyond" in slayer.result_text


def test_tag_treasure_map_branch_actions_roll_destination_procedures(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(gold=500, clues=0)

    rolls = iter([4])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    follow = resolve_tag_branch_action(campaign, hero, branch_action="treasure_map_follow")
    assert "Accurate but incomplete" in follow.result_text
    assert campaign.tag_map_bonus == 1

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 3)
    cave = resolve_tag_branch_action(campaign, hero, branch_action="map_cave_room_count")
    assert cave.total == 6
    assert "6 rooms" in cave.result_text

    monkeypatch.setattr(tag_campaign, "roll_d3", lambda: 2)
    idol = resolve_tag_branch_action(campaign, hero, branch_action="map_temple_idol")
    assert idol.total == 200
    assert "200 gp" in idol.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 3)
    scroll = resolve_tag_branch_action(campaign, hero, branch_action="map_temple_scroll")
    assert "random scroll" in scroll.result_text

    rolls = iter([1, 2, 3, 4])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    report = resolve_tag_branch_action(campaign, hero, branch_action="map_humanoid_report")
    assert report.total == 10
    assert "no XP" in report.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 4)
    stealth = resolve_tag_branch_action(campaign, hero, branch_action="map_humanoid_stealth")
    assert "Steal camp loot" in stealth.result_text

    rolls = iter([2, 3, 2, 1])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    monkeypatch.setattr(tag_campaign, "roll_d3", lambda: 2)
    forces = resolve_tag_branch_action(campaign, hero, branch_action="map_humanoid_forces")
    assert forces.total == 8
    assert "2 Orc Boss" in forces.result_text
    assert "black ogre present" in forces.result_text

    rolls = iter([5, 4])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    structure = resolve_tag_branch_action(campaign, hero, branch_action="map_structure_rooms")
    assert structure.total == 9

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 5)
    death = resolve_tag_branch_action(campaign, hero, branch_action="map_lich_death_magic", reference="mod=2")
    assert death.total == 7
    assert "success" in death.result_text

    life = resolve_tag_branch_action(campaign, hero, branch_action="map_lich_life", clue_cost=3)
    assert life.total == 7
    assert "3+4 = 7" in life.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 4)
    treasure = resolve_tag_branch_action(campaign, hero, branch_action="map_lich_treasure")
    assert treasure.total == 40
    assert "3 random scrolls" in treasure.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 4)
    boulder = resolve_tag_branch_action(campaign, hero, branch_action="giant_lair_boulder")
    assert boulder.roll == 4
    assert "throws a boulder" in boulder.result_text

    giant_treasure = resolve_tag_branch_action(campaign, hero, branch_action="giant_lair_treasure")
    assert "three treasure rolls" in giant_treasure.result_text
    assert "nine squares" in giant_treasure.result_text


def test_legacy_treasure_map_notes_are_translated_for_resumed_games() -> None:
    from app.engine.tag_compat import generated_tag_manifest_diagnostics, normalize_tag_log_line, upgrade_tag_manifest

    old_line = "TAG note: Apply The Map Leads To 1 reward/procedure text for Underground caves; confirm exact amounts and treasure handling from the PDF/player signoff."
    translated = normalize_tag_log_line(old_line)
    assert "Apply The Map Leads To" not in translated
    assert "Claim Treasure" in translated
    assert "Underground caves room target" in translated

    manifest = {
        "source": {
            "parameters": {
                "tag_reference": {
                    "lead_type": "treasure_map",
                    "treasure_map_destination": 1,
                    "rewards": old_line,
                    "room_prompts": {
                        "tag-complication": {
                            "actions": [
                                {"action_value": "treasure_map_follow"},
                                {"action_value": "map_cave_room_count"},
                            ]
                        }
                    },
                }
            }
        },
        "rooms": [{"id": "tag-side-clue", "triggers": [{"when": "on_search", "log": old_line}]}],
    }
    upgraded = upgrade_tag_manifest(manifest)
    reference = upgraded["source"]["parameters"]["tag_reference"]
    trigger_log = upgraded["rooms"][0]["triggers"][0]["log"]
    assert "Apply The Map Leads To" not in reference["rewards"]
    assert "Claim Treasure" in reference["side_reward_note"]
    assert "Apply The Map Leads To" not in trigger_log
    assert "Underground caves room target" in trigger_log
    actions = reference["room_prompts"]["tag-complication"]["actions"]
    assert {"action_value": "treasure_map_follow"} not in actions
    assert {"action_value": "map_cave_room_count"} in actions

    old_manifest = {
        "title": "Old TAG Rumor",
        "source": {
            "parameters": {
                "tag_reference": {
                    "lead_type": "rumor",
                    "title": "Old Rumor",
                }
            }
        },
        "rooms": [{"id": "tag-complication", "triggers": []}],
    }
    repaired = upgrade_tag_manifest(old_manifest)
    repaired_reference = repaired["source"]["parameters"]["tag_reference"]
    assert repaired_reference["prompt_repair_note"]
    assert repaired_reference["room_prompts"]["tag-complication"]["actions"][0]["action_type"] == "route"
    assert "older generated Adventures Guild module" in repaired_reference["room_prompts"]["tag-final-scene"]["body"]

    diagnostics = generated_tag_manifest_diagnostics(
        repaired,
        current_room_id="tag-complication",
        active_quest_state={"next_action": "Use visible room buttons first."},
    )
    assert diagnostics["is_generated"] is True
    assert diagnostics["current_prompt_found"] is True
    assert diagnostics["manual_fallback_needed"] is False
    assert diagnostics["prompt_count"] >= 4


def test_generated_tag_diagnostics_flags_missing_current_prompt_and_scene_target() -> None:
    from app.engine.tag_compat import generated_tag_manifest_diagnostics

    manifest = {
        "title": "Broken Generated Lead",
        "source": {
            "parameters": {
                "tag_reference": {
                    "lead_type": "rumor",
                    "lead_detail": "12",
                    "room_prompts": {
                        "tag-lead-entry": {
                            "title": "Entry",
                            "body": "Start here.",
                            "actions": [],
                        }
                    },
                    "scene_graph": {
                        "scenes": {
                            "Scene 4": {
                                "branches": [{"label": "Go to missing scene", "target_scene": "Scene 7"}]
                            }
                        }
                    },
                }
            }
        },
        "rooms": [{"id": "tag-lead-entry"}, {"id": "tag-final-scene"}],
    }
    diagnostics = generated_tag_manifest_diagnostics(manifest, current_room_id="tag-final-scene")
    assert diagnostics["is_generated"] is True
    assert diagnostics["manual_fallback_needed"] is True
    assert any("tag-final-scene" in error for error in diagnostics["errors"])
    assert any("Scene 4->Scene 7" in error for error in diagnostics["errors"])


def test_tag_theme_procedure_branch_actions_roll_exact_tables(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(clues=0)

    rolls = iter([4, 6])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    minions = resolve_tag_branch_action(campaign, hero, branch_action="ghastly_mine_minion_replacement")
    assert minions.roll == 4
    assert minions.total == 6
    assert "2d6+1 minor ghouls" in minions.result_text

    rolls = iter([2, 4])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    major = resolve_tag_branch_action(campaign, hero, branch_action="ghastly_mine_major_replacement")
    assert major.roll == 2
    assert major.total == 4
    assert "Minor Wraith" in major.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 3)
    treasure = resolve_tag_branch_action(campaign, hero, branch_action="ghastly_mine_treasure_conversion")
    assert "gem or nugget" in treasure.result_text

    cave = resolve_tag_branch_action(campaign, hero, branch_action="ghastly_mine_cave_in", clue_cost=3)
    assert cave.total == 4
    assert "L6 and deals 2 damage" in cave.result_text

    rolls = iter([5, 2])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    prisoner = resolve_tag_branch_action(campaign, hero, branch_action="fiendish_abyss_prisoner")
    assert prisoner.roll == 5
    assert prisoner.total == 50
    assert "merchant pays 50 gp" in prisoner.result_text
    assert "Riff-Raff encounter occurs" in prisoner.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 2)
    lost = resolve_tag_branch_action(campaign, hero, branch_action="minotaur_maze_lost_check", clue_cost=1)
    assert lost.roll == 2
    assert "with dungeon guide" in lost.result_text
    assert "party is lost" in lost.result_text

    rolls = iter([6, 2, 5, 1, 4, 3, 2, 1])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    wandering = resolve_tag_branch_action(campaign, hero, branch_action="minotaur_maze_wandering")
    assert wandering.roll == 6
    assert wandering.total == 10
    assert "gem worth 4d6=10 gp" in wandering.result_text

    rolls = iter([2, 4, 5])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    event = resolve_tag_branch_action(campaign, hero, branch_action="minotaur_maze_event")
    assert event.roll == 2
    assert event.total == 5
    assert "5 young minotaurs" in event.result_text


def test_tag_guild_job_branch_actions_roll_exact_workflows(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(clues=0)

    castle = resolve_tag_branch_action(
        campaign,
        hero,
        branch_action="castle_cleanup_pay",
        reference="party=4 boss=2 cache",
        clue_cost=10,
    )
    assert castle.total == 260
    assert "party 4 x25 gp" in castle.result_text
    assert "portrait cache 100 gp" in castle.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 2)
    mountain = resolve_tag_branch_action(campaign, hero, branch_action="griffin_mountain_check")
    assert mountain.roll == 2
    assert "wandering monster" in mountain.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 1)
    search = resolve_tag_branch_action(campaign, hero, branch_action="griffin_nest_search")
    assert "L7 Stealth" in search.result_text

    monkeypatch.setattr(tag_campaign, "roll_d3", lambda: 2)
    eggs = resolve_tag_branch_action(campaign, hero, branch_action="griffin_egg_count")
    assert eggs.total == 3
    assert "3 eggs" in eggs.result_text

    rolls = iter([1, 3, 4, 5])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    broken = resolve_tag_branch_action(campaign, hero, branch_action="griffin_egg_break", clue_cost=2)
    assert broken.total == 7
    assert "1 broken" in broken.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 2)
    outbound = resolve_tag_branch_action(campaign, hero, branch_action="portrait_outbound_check", clue_cost=5)
    assert "Weird Monsters Around Town encounter" in outbound.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 4)
    persuade = resolve_tag_branch_action(campaign, hero, branch_action="portrait_persuasion", reference="mod=-1")
    assert persuade.total == 3
    assert "failed" in persuade.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 1)
    snatch = resolve_tag_branch_action(campaign, hero, branch_action="portrait_return_snatch")
    assert "one turn to stop" in snatch.result_text

    rolls = iter([2, 4, 5])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    vermin = resolve_tag_branch_action(campaign, hero, branch_action="sewers_vermin")
    assert vermin.total == 9
    assert "rats" in vermin.result_text

    rolls = iter([5, 3])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    minions = resolve_tag_branch_action(campaign, hero, branch_action="sewers_minions")
    assert minions.total == 3
    assert "crocodile men" in minions.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 2)
    disease = resolve_tag_branch_action(campaign, hero, branch_action="sewers_disease", clue_cost=1)
    assert disease.total == 3
    assert "infection" in disease.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 6)
    track = resolve_tag_branch_action(campaign, hero, branch_action="monoceros_tracking", reference="mod=-1")
    assert track.total == 5
    assert "does not find" in track.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 2)
    shortcut = resolve_tag_branch_action(campaign, hero, branch_action="monoceros_clue_encounter")
    assert "Weird Monster Around Town" in shortcut.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 5)
    hide = resolve_tag_branch_action(campaign, hero, branch_action="monoceros_hide")
    assert "turns the blow" in hide.result_text


def test_tag_dragon_reveal_updates_latest_installed_dragon_lair(tmp_path: Path) -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    campaign = default_campaign()
    manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="thematic_dungeon", detail="3")
    campaign.tag_generated_adventure_ids.append(manifest["id"])
    install_dir = installed_adventure_dir(tmp_path, manifest["id"])
    install_dir.mkdir(parents=True)
    (install_dir / ADVENTURE_MANIFEST_FILENAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    result = apply_tag_dragon_reveal_to_latest_adventure(
        tmp_path,
        campaign,
        dragon_key="young_red_dragon",
        dragon_label="Hero spends 2 Clues and reveals Young Red Dragon.",
    )

    assert "Updated" in result
    updated = json.loads((install_dir / ADVENTURE_MANIFEST_FILENAME).read_text(encoding="utf-8"))
    validation = validate_adventure_manifest(updated, rules_repo=repo)
    assert validation.valid, validation.errors
    tag_ref = updated["source"]["parameters"]["tag_reference"]
    assert tag_ref["dragon_type_revealed"] == "Hero spends 2 Clues and reveals Young Red Dragon."
    assert tag_ref["final_foe_proxy"] == "Young Dragon"
    final_room = next(room for room in updated["rooms"] if room["id"] == "tag-final-scene")
    assert final_room["title"] == "Young Red Dragon"
    assert final_room["triggers"][0]["encounter"]["foes"] == [{"name": "Young Dragon", "count": 1}]


def test_tag_guild_ledger_deposit_and_martial_training_are_free() -> None:
    campaign = default_campaign()
    campaign.tag_guild_member = True
    campaign.tag_guild_coffers_gp = 5000
    hero = _character(gold=125, statuses=[])

    deposit = resolve_tag_finance_action(campaign, hero, finance_action="bank_deposit", amount_gp=100, note="Guild ledger")
    assert hero.gold == 25
    assert campaign.tag_bank_accounts[0].gold_gp == 100
    assert "for free under the TAG Guild ledger rule" in deposit.result_text

    training = purchase_tag_service(campaign, hero, service_key="martial_arts_training")
    assert hero.gold == 25
    assert "TAG martial arts training" in hero.statuses
    assert "train for free" in training.result_text

    campaign.tag_guild_coffers_gp = 0
    assert tag_guild_benefits_active(campaign) is False
    suspended = resolve_tag_finance_action(campaign, hero, finance_action="bank_deposit", amount_gp=10)
    assert "pays 1 gp fee" in suspended.result_text


def test_tag_guild_loot_share_resurrection_and_availability_reroll(monkeypatch) -> None:
    campaign = default_campaign()
    campaign.tag_guild_member = True
    campaign.tag_guild_coffers_gp = 1000
    hero = _character(level=2, gold=0, clues=0, inventory=[], statuses=[])

    share = resolve_tag_finance_action(campaign, finance_action="guild_loot_share", amount_gp=101)
    assert campaign.tag_guild_coffers_gp == 1050
    assert "50 gp to Guild coffers" in share.result_text
    assert "51 gp remains" in share.result_text

    resurrection = resolve_tag_finance_action(campaign, hero, finance_action="guild_resurrection_fund", amount_gp=200)
    assert campaign.tag_guild_coffers_gp == 850
    assert "pays 200 gp toward" in resurrection.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 6)
    reroll = reroll_guild_availability(campaign, item_name="Guild bow", difficulty=6, base_price_gp=20)
    assert campaign.tag_guild_availability_reroll_used is True
    assert "Guild availability reroll used" in reroll.result_text

    second = reroll_guild_availability(campaign, item_name="Guild shield", difficulty=6)
    assert "already used" in second.result_text

    reset = reset_guild_availability_reroll(campaign)
    assert campaign.tag_guild_availability_reroll_used is False
    assert "reset" in reset.result_text


def test_tag_guild_leaving_blocks_when_coffers_below_requirement() -> None:
    campaign = default_campaign()
    campaign.tag_guild_member = True
    campaign.tag_guild_coffers_gp = 4999

    update_troupe(campaign, guild_member=False, guild_coffers_gp=4999)

    assert campaign.tag_guild_member is True
    assert campaign.tag_downtime_log[-1].action == "guild_leaving_restriction"
    assert "restore coffers to at least 5000 gp" in campaign.tag_downtime_log[-1].result_text

    campaign.tag_guild_coffers_gp = 5000
    update_troupe(campaign, guild_member=False, guild_coffers_gp=5000)
    assert campaign.tag_guild_member is False


def test_tag_adventure_closeout_tasks_are_created_and_resolved(monkeypatch) -> None:
    campaign = default_campaign()
    campaign.adventures_completed = 4
    campaign.tag_guild_member = True
    campaign.tag_guild_coffers_gp = 1000
    campaign.tag_guild_availability_reroll_used = True
    campaign.tag_storage_gold_gp = 25
    campaign.tag_xp_markers.append(
        TagXpMarkerState(
            xp_action="mark_scene_xp",
            reference="Scene 4",
            xp=1,
            applied=False,
            result_text="Scene XP marker recorded.",
            created_at=now_utc(),
        )
    )

    created = add_adventure_closeout_tasks(campaign)
    actions = {task.task_action for task in created}

    assert {
        "guild_loot_share",
        "guild_upkeep",
        "guild_leaving_restriction",
        "guild_availability_reroll_reset",
        "tag_xp_closeout",
        "hidden_trove_risk",
    } <= actions

    duplicate = add_adventure_closeout_tasks(campaign)
    assert duplicate == []

    resolve_tag_finance_action(campaign, finance_action="guild_loot_share", amount_gp=100)
    assert next(task for task in campaign.tag_closeout_tasks if task.task_action == "guild_loot_share").resolved is True

    resolve_tag_finance_action(campaign, finance_action="guild_upkeep")
    assert next(task for task in campaign.tag_closeout_tasks if task.task_action == "guild_upkeep").resolved is True
    assert next(task for task in campaign.tag_closeout_tasks if task.task_action == "guild_availability_reroll_reset").resolved is True

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 6)
    roll_hidden_treasure_trove_risk(campaign)
    assert next(task for task in campaign.tag_closeout_tasks if task.task_action == "hidden_trove_risk").resolved is True

    manual = resolve_tag_closeout_task(campaign, task_action="guild_leaving_restriction", note="Checked")
    assert "resolved" in manual.result_text
    assert next(task for task in campaign.tag_closeout_tasks if task.task_action == "guild_leaving_restriction").resolved is True


def test_tag_signoff_review_logs_unresolved_state_and_completes_clear_guidance() -> None:
    campaign = default_campaign()
    campaign.tag_generated_adventure_ids.append("tag-rumor-1")
    campaign.tag_xp_markers.append(
        TagXpMarkerState(
            xp_action="award_scene_xp",
            character_id="hero-1",
            character_name="Sly Silas",
            reference="Scene XP",
            xp=1,
            applied=False,
            result_text="Pending XP",
            created_at=now_utc(),
        )
    )
    guidance = tag_campaign.add_guidance_task(
        campaign,
        title="Review adventure 1 closeout",
        body="Review generated TAG signoff.",
        category="closeout",
        priority="required",
    )
    assert guidance is not None

    first = record_tag_signoff_review(campaign, note="checked route")
    assert "1 pending XP marker" in first.result_text
    assert guidance.status == "open"

    campaign.tag_xp_markers[0].applied = True
    second = record_tag_signoff_review(campaign)
    assert "0 pending XP marker" in second.result_text
    assert guidance.status == "completed"


def test_tag_guild_mundane_equipment_discount() -> None:
    catalog = RulesRepository(Path("data/rules"), Path("data/rules/_override")).equipment_shop()
    hero = _character(class_id="warrior", class_name="Warrior", gold=10)

    ok, message = buy_equipment(hero, catalog, item_key="shield", tag_guild_discount=True)

    assert ok, message
    assert hero.gold == 5
    assert "TAG Guild mundane equipment discount" in message
