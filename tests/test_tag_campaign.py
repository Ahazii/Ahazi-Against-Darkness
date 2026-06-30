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
        assert "Record the party's printed approach" in tag_reference["room_prompts"]["tag-lead-entry"]["body"]
        assert "Adventure section" in entry.result_text


def test_tag_rumor_manifest_carries_pdf_rule_profile() -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    campaign = default_campaign()

    manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail="2")
    result = validate_adventure_manifest(manifest, rules_repo=repo)

    assert result.valid, result.errors
    reference = manifest["source"]["parameters"]["tag_reference"]
    assert manifest["title"] == "TAG Rumor 2: Medusa in the Hunter's Cabin"
    assert reference["scene"] == "Scene 10 leading to Scene 1"
    assert reference["pdf_pages"] == "TAG pp.22, 25-26"
    assert reference["final_foe_proxy"] == "Medusa"
    assert "Pendant worth 260 gp" in reference["rewards"]
    assert "room_prompts" in reference
    assert reference["room_prompts"]["tag-complication"]["actions"][0]["action_value"] == "parley_success"
    assert any(
        action["action_type"] == "branch" and action["action_value"] == "claim_reward"
        for action in reference["room_prompts"]["tag-final-scene"]["actions"]
    )
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
    assert final_room["triggers"][0]["encounter"]["foes"] == [{"name": "Medusa", "count": 1}]


def test_tag_thematic_and_guild_job_manifests_use_profiles(monkeypatch) -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    campaign = default_campaign()

    dragon, _entry = build_tag_adventure_manifest(campaign, lead_type="thematic_dungeon", detail="3")
    dragon_result = validate_adventure_manifest(dragon, rules_repo=repo)
    assert dragon_result.valid, dragon_result.errors
    dragon_ref = dragon["source"]["parameters"]["tag_reference"]
    assert dragon["title"] == "TAG Thematic Dungeon: Dragon's Lair"
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
    assert job["title"] == "TAG Guild Job 1: Gorungar the Mighty"
    assert job_ref["pdf_pages"] == "TAG p.55"
    assert job_ref["final_foe_proxy"] == "Gorungar the Mighty"
    assert "50 gp for his head" in job_ref["rewards"]
    assert job_ref["module_profile"]["target_rooms"] == "single guild-job encounter"
    assert job_ref["room_prompts"]["tag-final-scene"]["title"] == "Final scene closeout"
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
        "9": {"daroc_cat"},
        "10": {"gargoyle_count", "gargoyle_surprise", "gargoyle_skin", "gargoyle_bounty"},
        "11": {"deoldyn_training", "mark_training_xp_roll"},
        "12": {"solo_restriction", "agaratha"},
    }
    for detail, expected in expected_actions.items():
        manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail=detail)
        assert validate_adventure_manifest(manifest, rules_repo=repo).valid
        prompts = manifest["source"]["parameters"]["tag_reference"]["room_prompts"]
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
        if quest_roll == 5:
            assert {"sewers_vermin", "sewers_minions", "sewers_disease", "clue_gate_unlocked", "capture_alive"} <= action_values
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
    hero = _character(gold=500, clues=3, level=2, inventory=[], statuses=[])

    bounty = resolve_tag_scene_action(campaign, hero, scene_action="gargoyle_bounty", amount=3)
    assert hero.gold == 545
    assert "45 gp" in bounty.result_text

    agaratha = resolve_tag_scene_action(campaign, hero, scene_action="agaratha")
    assert "Agaratha" in hero.inventory
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
    from app.engine.tag_compat import normalize_tag_log_line, upgrade_tag_manifest

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
