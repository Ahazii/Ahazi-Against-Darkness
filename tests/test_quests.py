from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from app import main
from app.engine.adventure_allowlists import major_foe_table_keys
from app.engine.adventure_session import create_session_from_manifest
from app.engine.dice import AdvancementRollResult
from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.tag_campaign import build_tag_adventure_manifest, default_campaign, load_campaign, save_campaign
from app.engine.tag_compat import repair_required_tag_scene_lifecycle, upgrade_tag_manifest
from app.engine.tag_daroc import DAROC_FAMILIAR_REWARD_GP, TAG_TOWN_STREETWISE_CLUE
from app.engine.tag_scene_lifecycle import (
    TAG_GENERATED_CLOSEOUT_ACTION_LABEL,
    TAG_GENERATED_CLOSEOUT_LOG_MESSAGE,
    TAG_GENERATED_CLOSEOUT_REMINDER,
    generated_tag_rumor_entry_choice_pending,
)
from app.rules.repository import RulesRepository
from app.schemas import (
    ActiveQuestState,
    Character,
    CombatBodyguardPauseState,
    EnemyState,
    ExitState,
    HirelingState,
    MapState,
    PartyMemberState,
    PendingBodyguardInterceptState,
    PendingCombatFoeAttack,
    SessionState,
    TileState,
)


def engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def base_session(**kwargs) -> SessionState:
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="R",
        description="R",
        lady_in_white_available=True,
    )
    defaults = dict(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=200,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
                inventory=["Potion of Healing"],
            )
        ],
        map_state=MapState(tiles=[tile], current_tile_id="t"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    defaults.update(kwargs)
    return SessionState(**defaults)


def _save_daroc_generated_session(
    session_id: str,
) -> tuple[dict, Character, Character]:
    campaign = default_campaign()
    manifest, _entry = build_tag_adventure_manifest(
        campaign,
        lead_type="rumor",
        detail="9",
    )
    searcher = Character(
        id=f"{session_id}-searcher",
        name="Daroc Searcher",
        class_id="rogue",
        class_name="Rogue",
        level=3,
        xp=0,
        gold=50,
        max_life=8,
        current_life=8,
        attack_bonus=1,
        defense_bonus=1,
        save_bonus=0,
        inventory=[],
        active_session_id=session_id,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    recipient = Character(
        id=f"{session_id}-recipient",
        name="Daroc Reward Recipient",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=10,
        max_life=8,
        current_life=8,
        attack_bonus=1,
        defense_bonus=1,
        save_bonus=0,
        inventory=[],
        active_session_id=session_id,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    for character in (searcher, recipient):
        main.store.save("characters", character)
    session = create_session_from_manifest(
        main.random_engine,
        session_id,
        "daroc-party",
        [main._member_state(searcher), main._member_state(recipient)],
        manifest,
        adventure_id=manifest["id"],
    )
    save_campaign(main.store, campaign)
    main.store.save("sessions", session)
    return manifest, searcher, recipient


def _save_repeatable_tag_service_session(
    session_id: str,
    rumor_number: int,
    character_specs: list[tuple[str, str, int, int]],
    *,
    start_camped_outside: bool = False,
) -> tuple[dict, list[Character]]:
    campaign = default_campaign()
    manifest, _entry = build_tag_adventure_manifest(
        campaign,
        lead_type="rumor",
        detail=str(rumor_number),
    )
    characters: list[Character] = []
    for suffix, class_id, level, gold in character_specs:
        character = Character(
            id=f"{session_id}-{suffix}",
            name=f"{class_id.replace('_', ' ').title()} {suffix.title()}",
            class_id=class_id,
            class_name=class_id.replace("_", " ").title(),
            level=level,
            xp=0,
            gold=gold,
            max_life=10,
            current_life=10,
            attack_bonus=1,
            defense_bonus=1,
            save_bonus=0,
            inventory=[],
            active_session_id=session_id,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        main.store.save("characters", character)
        characters.append(character)
    session = create_session_from_manifest(
        main.random_engine,
        session_id,
        f"{session_id}-party",
        [main._member_state(character) for character in characters],
        manifest,
        adventure_id=manifest["id"],
        start_camped_outside=start_camped_outside,
    )
    save_campaign(main.store, campaign)
    main.store.save("sessions", session)
    return manifest, characters


def _enter_repeatable_tag_service(client, session_id: str, manifest: dict) -> dict:
    entry_actions = manifest["source"]["parameters"]["tag_reference"]["room_prompts"][
        "tag-lead-entry"
    ]["actions"]
    investigate = next(action for action in entry_actions if action["label"] == "Investigate")
    entered = client.post(
        f"/api/sessions/{session_id}/tag-route-action",
        json={"route_action": "unlock_scene", "reference": investigate["reference"]},
    )
    assert entered.status_code == 200, entered.text
    payload = entered.json()
    current_id = payload["session"]["map_state"]["current_tile_id"]
    current = next(
        tile for tile in payload["session"]["map_state"]["tiles"] if tile["id"] == current_id
    )
    assert current["content_key"] == "imported:tag-final-scene"
    return payload


def test_refuse_quest_blocks_lady() -> None:
    eng = engine()
    session = base_session()
    eng.advance(session, "refuse_quest")
    assert session.lady_in_white_refused is True
    assert session.map_state.tiles[0].lady_in_white_available is False


def test_accept_quest_sets_active_quest(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    session.party[0].gold = 0
    monkeypatch.setattr(
        "app.engine.random_dungeon.roll_d6",
        lambda: 2,
    )
    monkeypatch.setattr(
        "app.engine.class_abilities.roll_exploding_for_level",
        lambda _level: (6, [6]),
    )
    eng.advance(session, "accept_quest")
    assert session.active_quest is not None
    assert session.active_quest.key == "bring_gold"
    assert session.active_quest.gold_required == 100


def test_active_quest_can_persist_tag_treasure_map_procedure_state() -> None:
    quest = ActiveQuestState(
        tile_id="t",
        key="tag_treasure_map",
        description="Follow the purchased TAG treasure map to the underground caves.",
    )
    quest.tag_treasure_map_destination = 1
    quest.tag_procedure_signoff = True
    quest.tag_generated_lead_signoff = True
    quest.tag_generated_lead_state["entry_seen"] = True
    quest.tag_generated_lead_state["route_recorded"] = True
    quest.tag_generated_lead_state["closeout_warnings"] = ["1 pending TAG XP marker still needs review."]
    quest.tag_generated_lead_state["closeout"] = {
        "completed": True,
        "result": "Reviewed",
        "warnings": ["1 pending TAG XP marker still needs review."],
    }
    quest.tag_procedure_state["map_cave_room_count"] = {
        "completed": True,
        "total": 6,
        "result": "Map cave complex room count: dungeon ends after 6 rooms.",
    }
    quest.tag_procedure_state["next_action"] = "Explore until the room target is reached."

    restored = ActiveQuestState.model_validate(quest.model_dump())
    assert restored.tag_treasure_map_destination == 1
    assert restored.tag_procedure_signoff is True
    assert restored.tag_generated_lead_signoff is True
    assert restored.tag_generated_lead_state["entry_seen"] is True
    assert restored.tag_generated_lead_state["route_recorded"] is True
    assert restored.tag_generated_lead_state["closeout"]["completed"] is True
    assert "pending TAG XP" in restored.tag_generated_lead_state["closeout"]["warnings"][0]
    assert restored.tag_procedure_state["map_cave_room_count"]["completed"] is True
    assert restored.tag_procedure_state["map_cave_room_count"]["total"] == 6
    assert "room target" in restored.tag_procedure_state["next_action"]


def test_generated_tag_guidance_repair_endpoint_rebuilds_prompt_metadata(client) -> None:
    session = base_session(
        id="repair-session",
        adventure_id="tag-old-rumor",
        adventure_type="imported",
        imported_manifest={
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
        },
        active_quest=ActiveQuestState(tile_id="t", key="imported_boss", description="Resolve old TAG lead."),
        log=[
            "TAG note: Apply The Map Leads To 1 reward/procedure text for Underground caves; confirm exact amounts and treasure handling from the PDF/player signoff."
        ],
    )
    main.store.save("sessions", session)

    response = client.post("/api/sessions/repair-session/tag-repair-guidance")
    assert response.status_code == 200
    payload = response.json()
    reference = payload["imported_manifest"]["source"]["parameters"]["tag_reference"]
    assert reference["prompt_repair_note"]
    assert reference["room_prompts"]["tag-complication"]["actions"][0]["action_type"] == "route"
    assert "Apply The Map Leads To" not in " ".join(payload["log"])
    assert payload["active_quest"]["tag_generated_lead_state"]["guidance_repaired"] is True


def test_generated_tag_route_action_moves_without_debug_route_log(client, monkeypatch, tmp_path) -> None:
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
                            "scene_graph": {
                                "start_scenes": ["Scene 9"],
                                "scenes": {
                                    "Scene 9": {
                                        "description": "Star object scene. Will you: Talk to the family? Go to Scene 17.",
                                        "branches": [
                                            {
                                                "label": "Talk to the family",
                                                "target_scene": "Scene 17",
                                                "target_scene_number": 17,
                                            }
                                        ],
                                    },
                                    "Scene 17": {
                                        "description": (
                                            "You talk to Bofto family. They kindly ask you to leave. "
                                            "If you insist, you may continue investigating by playing Scene 9."
                                        ),
                                        "branches": [
                                            {
                                                "label": "If you insist, you may continue investigating by playing Scene 9",
                                                "target_scene": "Scene 9",
                                                "target_scene_number": 9,
                                            }
                                        ],
                                    },
                                },
                            }
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    manifest, _entry = build_tag_adventure_manifest(default_campaign(), lead_type="rumor", detail="1")
    session = create_session_from_manifest(
        engine(),
        "tag-route-session",
        "party-1",
        [base_session().party[0]],
        manifest,
        adventure_id=manifest["id"],
    )
    session.active_quest = ActiveQuestState(
        tile_id=session.map_state.current_tile_id,
        key="tag_generated_lead",
        description="Resolve generated Adventures Guild lead.",
    )
    main.store.save("sessions", session)

    response = client.post(
        "/api/sessions/tag-route-session/tag-route-action",
        json={"route_action": "unlock_scene", "reference": "Scene 9 -> Scene 17: Talk to the family"},
    )

    assert response.status_code == 200
    payload = response.json()["session"]
    assert payload["map_state"]["current_tile_id"] != session.map_state.current_tile_id
    log_text = "\n".join(payload["log"])
    assert "You talk to Bofto family" in log_text
    assert "TAG route:" not in log_text


def test_generated_bofto_theft_roll_moves_to_result_scene(client, monkeypatch, tmp_path) -> None:
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
                            "scene_graph": {
                                "start_scenes": ["Scene 9"],
                                "scenes": {
                                    "Scene 9": {
                                        "description": "Star object scene. Will you: Try to steal it? Go to Scene 14.",
                                        "branches": [
                                            {
                                                "label": "Try to steal it",
                                                "target_scene": "Scene 14",
                                                "target_scene_number": 14,
                                            }
                                        ],
                                    },
                                    "Scene 14": {
                                        "description": "Choose one character to steal the star-shaped object. If you fail, go to Scene 18. If you succeed, go to Scene 19.",
                                        "branches": [
                                            {"label": "If you fail, go to Scene 18", "target_scene": "Scene 18", "target_scene_number": 18},
                                            {"label": "If you succeed, go to Scene 19", "target_scene": "Scene 19", "target_scene_number": 19},
                                        ],
                                    },
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
    manifest, _entry = build_tag_adventure_manifest(default_campaign(), lead_type="rumor", detail="1")
    character = Character(
        id="h",
        name="Hero",
        class_id="rogue",
        class_name="Rogue",
        level=1,
        gold=0,
        clues=0,
        max_life=3,
        current_life=3,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    main.store.save("characters", character)
    session = create_session_from_manifest(
        engine(),
        "bofto-theft-session",
        "party-1",
        [base_session().party[0]],
        manifest,
        adventure_id=manifest["id"],
    )
    scene_14_tile = next(tile for tile in session.map_state.tiles if tile.content_key == "imported:tag-scene-14")
    session.map_state.current_tile_id = scene_14_tile.id
    session.active_quest = ActiveQuestState(
        tile_id=session.map_state.current_tile_id,
        key="tag_generated_lead",
        description="Resolve generated Adventures Guild lead.",
    )
    main.store.save("sessions", session)
    monkeypatch.setattr(
        "app.engine.tag_campaign.roll_exploding_for_level",
        lambda *_args, **_kwargs: (6, [6]),
    )
    monkeypatch.setattr(
        "app.engine.star_object_curse.roll_exploding_for_level",
        lambda *_args, **_kwargs: (8, [6, 2]),
    )

    premature_scene_19_response = client.post(
        "/api/sessions/bofto-theft-session/tag-branch-action",
        json={"character_id": "h", "branch_action": "star_object_will_save"},
    )

    assert premature_scene_19_response.status_code == 400
    assert "Scene 19 is not active" in premature_scene_19_response.json()["detail"]

    missing_character_response = client.post(
        "/api/sessions/bofto-theft-session/tag-branch-action",
        json={"branch_action": "bofto_theft_save", "reference": "Scene 14 star-object theft"},
    )

    assert missing_character_response.status_code == 400
    assert "Choose the character" in missing_character_response.json()["detail"]
    stored_session = main.store.get("sessions", "bofto-theft-session", SessionState.model_validate)
    assert stored_session is not None
    assert stored_session.map_state.current_tile_id == scene_14_tile.id

    response = client.post(
        "/api/sessions/bofto-theft-session/tag-branch-action",
        json={"character_id": "h", "branch_action": "bofto_theft_save", "reference": "Scene 14 star-object theft"},
    )

    assert response.status_code == 200
    payload = response.json()["session"]
    current_tile = next(tile for tile in payload["map_state"]["tiles"] if tile["id"] == payload["map_state"]["current_tile_id"])
    assert current_tile["content_key"] == "imported:tag-scene-19"
    assert payload["mode"] == "exploration"
    assert payload["active_quest"]["completed"] is True
    assert payload["tag_generated_completion_pending"] is True
    assert payload["summary"] == []
    assert "successfully steals" in payload["tag_generated_completion_body"]
    assert "against L8" in payload["tag_generated_completion_body"]
    assert TAG_GENERATED_CLOSEOUT_ACTION_LABEL in payload["log"][-1]
    assert "Bofto's Star-Shaped Cursed Object" in payload["party"][0]["inventory"]
    assert "Bofto's Star-Shaped Object Curse" in payload["party"][0]["statuses"]
    log_text = "\n".join(payload["log"])
    assert "thievery Save is 6 + 1 = 7 against L6 and succeeds" in log_text
    assert "Scene 19 Will Save:" not in log_text
    assert "The theft succeeds." in log_text
    assert "If you succeed" not in log_text
    assert "Adventures Guild procedure:" not in log_text

    stored_pending = main.store.get("sessions", "bofto-theft-session", SessionState.model_validate)
    assert stored_pending is not None
    reloaded_pending = SessionState.model_validate(stored_pending.model_dump())
    assert reloaded_pending.tag_generated_completion_pending is True
    assert reloaded_pending.tag_generated_completion_body == payload["tag_generated_completion_body"]

    continued = client.post("/api/sessions/bofto-theft-session/tag-generated-lead-continue")

    assert continued.status_code == 200
    completed = continued.json()
    assert completed["mode"] == "complete"
    assert completed["tag_generated_completion_pending"] is False
    assert completed["tag_generated_completion_body"] is None
    assert completed["active_quest"]["tag_generated_lead_signoff"] is True
    assert completed["summary"]


def test_generated_tag_result_pause_blocks_dungeon_actions() -> None:
    session = base_session()
    session.tag_generated_completion_pending = True
    session.tag_generated_completion_title = "Bofto's Star-Shaped Find resolved"
    session.tag_generated_completion_body = "The resolved scene remains available until Continue is chosen."
    current_tile_id = session.map_state.current_tile_id

    updated = engine().advance(session, "search_room")

    assert updated.mode == "exploration"
    assert updated.map_state.current_tile_id == current_tile_id
    assert updated.tag_generated_completion_pending is True
    assert updated.log[-1] == TAG_GENERATED_CLOSEOUT_REMINDER


def test_generated_tag_continue_keeps_closeout_pending_when_xp_blocks_completion(client) -> None:
    session = base_session(
        id="tag-closeout-xp-blocked",
        active_quest=ActiveQuestState(
            tile_id="t",
            key="tag_generated_scene",
            description="Resolved scene.",
            completed=True,
        ),
        tag_generated_completion_pending=True,
        tag_generated_completion_title="Resolved scene",
        tag_generated_completion_body="Return to town when ready.",
        xp_rolls_pending=1,
    )
    main.store.save("sessions", session)

    response = client.post(
        "/api/sessions/tag-closeout-xp-blocked/tag-generated-lead-continue"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "exploration"
    assert payload["tag_generated_completion_pending"] is True
    assert payload["tag_generated_completion_title"] == "Resolved scene"
    assert any("XP roll" in line and "before completing" in line for line in payload["log"])


def test_legacy_leprechaun_manifest_upgrades_to_vendor_finale() -> None:
    manifest = {
        "title": "TAG Guild Job 4: Leprechauns at Blackbird Hill",
        "source": {
            "parameters": {
                "tag_reference": {
                    "lead_type": "rumor",
                    "title": "Leprechauns at Blackbird Hill",
                    "final_foes": [{"name": "Goblins", "count": 4}],
                }
            }
        },
        "quest": {
            "key": "tag_lead",
            "objective_text": "Find the leprechauns and decide whether to buy Shoes of Fast Walk or learn their illusion spell.",
            "complete_when": {"type": "boss_defeated", "boss_name": "Goblins", "room_id": "tag-final-scene"},
        },
        "rooms": [
            {
                "id": "tag-final-scene",
                "title": "Blackbird Hill",
                "description": "Old proxy fight.",
                "triggers": [{"when": "on_enter", "encounter": {"foes": [{"name": "Goblins", "count": 4}]}}],
            }
        ],
    }

    upgraded = upgrade_tag_manifest(manifest)
    reference = upgraded["source"]["parameters"]["tag_reference"]
    final_room = upgraded["rooms"][0]

    assert upgraded["quest"]["complete_when"] == {"type": "tag_scene_resolved", "room_id": "tag-final-scene"}
    assert reference["finale_mode"] == "vendor"
    assert reference["final_foes"] == []
    assert reference["legacy_service_proxy_foe_names"] == ["Goblins"]
    assert reference["room_prompts"]["tag-final-scene"]["title"] == "Bargain choices"
    assert [action["action_value"] for action in reference["room_prompts"]["tag-final-scene"]["actions"]] == [
        "leprechaun_shoes",
        "leprechaun_illusion_spell",
        "tag_repeatable_service_done",
    ]
    assert reference["room_prompts"]["tag-final-scene"]["actions"][-1]["required_for_completion"] is True
    assert "encounter" not in final_room["triggers"][0]
    first_upgrade = json.dumps(upgraded, sort_keys=True)
    assert json.dumps(upgrade_tag_manifest(upgraded), sort_keys=True) == first_upgrade


def test_legacy_deoldyn_manifest_upgrades_to_repeatable_batch_service() -> None:
    manifest = {
        "title": "The Adventures Guild Rumor 11: Deoldyn's Archery Training",
        "source": {
            "parameters": {
                "tag_reference": {
                    "lead_type": "rumor",
                    "rumor_number": 11,
                    "title": "Deoldyn's Archery Training",
                    "final_foes": [{"name": "Orcs", "count": 4}],
                }
            }
        },
        "quest": {
            "key": "tag_lead",
            "objective_text": "Old training objective.",
            "complete_when": {
                "type": "boss_defeated",
                "boss_name": "Orcs",
                "room_id": "tag-final-scene",
            },
        },
        "rooms": [
            {
                "id": "tag-final-scene",
                "title": "Old training interruption",
                "description": "Old proxy fight.",
                "triggers": [
                    {
                        "when": "on_enter",
                        "log": "Old training encounter.",
                        "encounter": {"foes": [{"name": "Orcs", "count": 4}]},
                    }
                ],
            }
        ],
    }

    upgraded = upgrade_tag_manifest(manifest)
    reference = upgraded["source"]["parameters"]["tag_reference"]
    final_prompt = reference["room_prompts"]["tag-final-scene"]
    final_room = upgraded["rooms"][0]

    assert upgraded["quest"]["complete_when"] == {
        "type": "tag_scene_resolved",
        "room_id": "tag-final-scene",
    }
    assert reference["finale_mode"] == "service"
    assert reference["final_foes"] == []
    assert reference["final_foe_proxy"] == ""
    assert reference["legacy_service_proxy_foe_names"] == ["Orcs"]
    assert final_prompt["title"] == "Service choices"
    assert [action["action_value"] for action in final_prompt["actions"]] == [
        "deoldyn_training",
        "tag_repeatable_service_done",
    ]
    assert "required_for_completion" not in final_prompt["actions"][0]
    assert final_prompt["actions"][1]["label"] == "Done — finish training"
    assert final_prompt["actions"][1]["required_for_completion"] is True
    assert "all payments" in reference["finale_instruction"]
    assert "automatic" in reference["finale_instruction"]
    assert "base Elf" in reference["finale_instruction"]
    assert "mark_training_xp_roll" not in {
        action["action_value"]
        for prompt in reference["room_prompts"].values()
        for action in prompt.get("actions", [])
    }
    assert [action["label"] for action in reference["room_prompts"]["tag-lead-entry"]["actions"]] == [
        "Investigate",
        "Not now — return to town",
    ]
    assert "encounter" not in final_room["triggers"][0]
    first_upgrade = json.dumps(upgraded, sort_keys=True)
    assert json.dumps(upgrade_tag_manifest(upgraded), sort_keys=True) == first_upgrade


def test_repeatable_service_lifecycle_repair_retains_existing_procedure_state() -> None:
    manifest, _entry = build_tag_adventure_manifest(
        default_campaign(),
        lead_type="rumor",
        detail="11",
    )
    prior_procedure_state = {
        "tag_repeatable_service": {
            "phase": "selecting",
            "transactions": [
                {"character_id": "h", "cost": 180, "choice": "dead_shot"},
            ],
        }
    }
    session = base_session(
        adventure_id="tag-rumor-11-legacy-session",
        adventure_type="imported",
        imported_manifest=manifest,
        imported_quest_complete_when={"type": "room_reached", "room_id": "tag-final-scene"},
        active_quest=ActiveQuestState(
            tile_id="t",
            key="imported_room",
            description="Train with Deoldyn.",
            completed=True,
            tag_procedure_state=prior_procedure_state,
        ),
        log=["Quest complete: objective location reached."],
    )
    session.map_state.tiles[0].content_key = "imported:tag-final-scene"

    assert repair_required_tag_scene_lifecycle(session) is True
    assert session.imported_quest_complete_when == {
        "type": "tag_scene_resolved",
        "room_id": "tag-final-scene",
    }
    assert session.active_quest is not None
    assert session.active_quest.key == "tag_generated_scene"
    assert session.active_quest.completed is False
    assert session.active_quest.tag_procedure_state == prior_procedure_state
    assert repair_required_tag_scene_lifecycle(session) is False
    assert session.active_quest.tag_procedure_state == prior_procedure_state


def _legacy_repeatable_service_manifest(
    rumor_number: int,
    proxy_name: str,
) -> dict:
    leprechaun = rumor_number == 6
    title = (
        "The Adventures Guild Rumor 6: Leprechauns at Blackbird Hill"
        if leprechaun
        else "The Adventures Guild Rumor 11: Deoldyn's Archery Training"
    )
    return {
        "id": f"legacy-tag-rumor-{rumor_number}",
        "title": title,
        "entrance_room_id": "tag-lead-entry",
        "source": {
            "parameters": {
                "tag_reference": {
                    "lead_type": "rumor",
                    "rumor_number": rumor_number,
                    "title": title,
                    "final_foe_proxy": proxy_name,
                    "final_foes": [{"name": proxy_name, "count": 4}],
                }
            }
        },
        "quest": {
            "key": "tag_lead",
            "giver_room_id": "tag-lead-entry",
            "objective_text": "Old proxy objective.",
            "complete_when": {
                "type": "boss_defeated",
                "boss_name": proxy_name,
                "room_id": "tag-final-scene",
            },
        },
        "rooms": [
            {
                "id": "tag-lead-entry",
                "title": "Lead entry",
                "description": "Old lead entry.",
                "triggers": [],
            },
            {
                "id": "tag-final-scene",
                "title": "Old proxy fight",
                "description": "Old proxy fight.",
                "triggers": [
                    {
                        "when": "on_enter",
                        "log": "Old proxy encounter.",
                        "encounter": {
                            "foes": [{"name": proxy_name, "count": 4}],
                        },
                    }
                ],
            },
        ],
    }


def test_repeatable_service_legacy_imported_boss_reopens_and_cleans_exact_proxy() -> None:
    manifest = upgrade_tag_manifest(
        _legacy_repeatable_service_manifest(11, "Orcs")
    )
    stale_body = "The obsolete proxy Quest is complete. Continue to finish."
    session = base_session(
        adventure_id="tag-rumor-11-legacy-proxy",
        adventure_type="imported",
        imported_manifest=manifest,
        imported_quest_complete_when={
            "type": "boss_defeated",
            "boss_name": "Orcs",
            "room_id": "tag-final-scene",
        },
        active_quest=ActiveQuestState(
            tile_id="t",
            key="imported_boss",
            description="Defeat the old proxy.",
            boss_slay_pending=True,
            boss_target_name="Orcs",
            completed=True,
        ),
        mode="combat",
        tag_generated_completion_pending=True,
        tag_generated_completion_title="Old proxy resolved",
        tag_generated_completion_body=stale_body,
        log=["Quest complete: Orcs has been destroyed.", stale_body],
    )
    tile = session.map_state.tiles[0]
    tile.content_key = "imported:tag-final-scene"
    tile.enemies = [
        EnemyState(
            id="legacy-orcs",
            name="Orcs",
            category="minion",
            level=4,
            life=4,
            max_life=4,
            initial_count=4,
        )
    ]
    tile.initial_enemy_count = 4

    assert repair_required_tag_scene_lifecycle(session) is True
    assert session.active_quest is not None
    assert session.active_quest.key == "tag_generated_scene"
    assert session.active_quest.completed is False
    assert session.active_quest.boss_target_name is None
    assert session.active_quest.boss_slay_pending is False
    assert session.mode == "exploration"
    assert tile.enemies == []
    assert tile.initial_enemy_count == 0
    final_room = next(room for room in manifest["rooms"] if room["id"] == "tag-final-scene")
    assert tile.title == final_room["title"]
    assert tile.description == final_room["description"]
    assert session.tag_generated_completion_pending is False
    assert stale_body not in session.log
    assert not any(line.startswith("Quest complete: Orcs") for line in session.log)
    marker = session.active_quest.tag_procedure_state[
        "tag_repeatable_service_legacy_migration"
    ]
    assert marker["proxy_cleanup"] == "cleared_exact_known_proxy"
    first_state = session.model_dump(mode="json")
    assert repair_required_tag_scene_lifecycle(session) is False
    assert session.model_dump(mode="json") == first_state


def test_repeatable_service_legacy_paused_proxy_clears_bodyguard_prompt_state() -> None:
    manifest = upgrade_tag_manifest(
        _legacy_repeatable_service_manifest(11, "Orcs")
    )
    session = base_session(
        adventure_id="tag-rumor-11-legacy-paused-proxy",
        adventure_type="imported",
        imported_manifest=manifest,
        active_quest=ActiveQuestState(
            tile_id="t",
            key="imported_boss",
            description="Defeat the old proxy.",
            boss_target_name="Orcs",
            completed=True,
        ),
        mode="combat",
        pending_bodyguard_intercept=PendingBodyguardInterceptState(
            protectee_id="h",
            hireling_id="legacy-bodyguard",
            enemy_id="legacy-orc",
        ),
        combat_bodyguard_pause=CombatBodyguardPauseState(
            phase_index=0,
            phases=["foes"],
            remaining_attacks=[
                PendingCombatFoeAttack(
                    enemy_id="legacy-orc",
                    target_character_id="h",
                )
            ],
            escape_context={
                "active_enemy_ids": ["legacy-orc"],
                "serialized_prompt": "bodyguard intercept",
            },
        ),
    )
    tile = session.map_state.tiles[0]
    tile.content_key = "imported:tag-final-scene"
    tile.enemies = [
        EnemyState(
            id="legacy-orc",
            name="Orcs",
            category="minion",
            level=4,
            life=4,
            max_life=4,
        )
    ]

    assert repair_required_tag_scene_lifecycle(session) is True
    assert tile.enemies == []
    assert session.pending_bodyguard_intercept is None
    assert session.combat_bodyguard_pause is None
    first_state = session.model_dump(mode="json")
    assert repair_required_tag_scene_lifecycle(session) is False
    assert session.model_dump(mode="json") == first_state


def test_repeatable_service_legacy_unknown_foe_is_preserved() -> None:
    manifest = upgrade_tag_manifest(
        _legacy_repeatable_service_manifest(11, "Orcs")
    )
    session = base_session(
        adventure_id="tag-rumor-11-legacy-unknown-foe",
        adventure_type="imported",
        imported_manifest=manifest,
        active_quest=ActiveQuestState(
            tile_id="t",
            key="imported_boss",
            description="Defeat the old proxy.",
            boss_slay_pending=True,
            boss_target_name="Orcs",
            completed=True,
        ),
        mode="combat",
        pending_bodyguard_intercept=PendingBodyguardInterceptState(
            protectee_id="h",
            hireling_id="current-bodyguard",
            enemy_id="unexpected-dragon",
        ),
        combat_bodyguard_pause=CombatBodyguardPauseState(
            phase_index=0,
            phases=["foes"],
            remaining_attacks=[
                PendingCombatFoeAttack(
                    enemy_id="unexpected-dragon",
                    target_character_id="h",
                )
            ],
            escape_context={"active_enemy_ids": ["unexpected-dragon"]},
        ),
    )
    tile = session.map_state.tiles[0]
    tile.content_key = "imported:tag-final-scene"
    tile.enemies = [
        EnemyState(
            id="unexpected-dragon",
            name="Dragon",
            category="boss",
            level=8,
            life=8,
            max_life=8,
        )
    ]

    assert repair_required_tag_scene_lifecycle(session) is True
    assert [enemy.name for enemy in tile.enemies] == ["Dragon"]
    assert session.mode == "combat"
    assert session.pending_bodyguard_intercept is not None
    assert session.pending_bodyguard_intercept.enemy_id == "unexpected-dragon"
    assert session.combat_bodyguard_pause is not None
    assert session.combat_bodyguard_pause.escape_context == {
        "active_enemy_ids": ["unexpected-dragon"]
    }
    assert session.active_quest is not None
    marker = session.active_quest.tag_procedure_state[
        "tag_repeatable_service_legacy_migration"
    ]
    assert marker["proxy_cleanup"] == "preserved_unknown_or_mixed_foes"
    assert marker["preserved_unknown_foes"] == ["dragon"]
    first_state = session.model_dump(mode="json")
    assert repair_required_tag_scene_lifecycle(session) is False
    assert session.model_dump(mode="json") == first_state


def test_repeatable_service_legacy_epic_reward_is_preserved_while_service_reopens() -> None:
    manifest = upgrade_tag_manifest(
        _legacy_repeatable_service_manifest(6, "Goblins")
    )
    reward_line = "Quest complete! Epic reward: Magic shield."
    stale_body = "The old Quest is complete. Continue to finish."
    session = base_session(
        adventure_id="tag-rumor-6-legacy-reward",
        adventure_type="imported",
        imported_manifest=manifest,
        active_quest=None,
        tag_generated_completion_pending=True,
        tag_generated_completion_title="Old Quest resolved",
        tag_generated_completion_body=stale_body,
        log=[reward_line, stale_body],
    )
    tile = session.map_state.tiles[0]
    tile.content_key = "imported:tag-final-scene"

    assert repair_required_tag_scene_lifecycle(session) is True
    assert session.active_quest is not None
    assert session.active_quest.key == "tag_generated_scene"
    assert session.active_quest.completed is False
    assert session.active_quest.reward_claimed is True
    assert session.tag_generated_completion_pending is False
    assert reward_line in session.log
    assert stale_body not in session.log
    marker = session.active_quest.tag_procedure_state[
        "tag_repeatable_service_legacy_migration"
    ]
    assert marker["reward_preserved"] is True
    assert marker["preserved_reward_log"] == reward_line
    first_state = session.model_dump(mode="json")
    assert repair_required_tag_scene_lifecycle(session) is False
    assert session.model_dump(mode="json") == first_state


def test_repeatable_service_legacy_leprechaun_evidence_migrates_once() -> None:
    manifest = upgrade_tag_manifest(
        _legacy_repeatable_service_manifest(6, "Goblins")
    )
    session = base_session(
        adventure_id="tag-rumor-6-legacy-evidence",
        adventure_type="imported",
        imported_manifest=manifest,
        active_quest=ActiveQuestState(
            tile_id="t",
            key="imported_boss",
            description="Defeat the old proxy.",
            boss_target_name="Goblins",
            completed=True,
        ),
        log=[
            "Adventures Guild procedure: Hero buys 3 pair(s) of Shoes of Fast Walk for 600 gp; add +Tier to Defense.",
            "Adventures Guild procedure: Hero learns or records Scene 2 illusion spell - Illusionary Armor from the leprechauns for free after buying at least three pairs of magical shoes.",
        ],
    )
    tile = session.map_state.tiles[0]
    tile.content_key = "imported:tag-final-scene"
    session.party[0].inventory = ["Shoes of Fast Walk"] * 3
    session.party[0].statuses.append(
        "TAG leprechaun illusion spell pending: Scene 2 illusion spell - Illusionary Armor"
    )

    assert repair_required_tag_scene_lifecycle(session) is True
    assert session.active_quest is not None
    state = session.active_quest.tag_procedure_state["tag_repeatable_service"]
    assert len(state["shoe_assignments"]) == 3
    assert state["illusion_lesson"]["spell_name"] == "Illusionary Armor"
    assert state["illusion_lesson"]["cost_gp"] == 0
    assert state["illusion_lesson"]["legacy_pending"] is True
    assert len(state["transactions"]) == 2
    first_state = session.model_dump(mode="json")
    assert repair_required_tag_scene_lifecycle(session) is False
    assert session.model_dump(mode="json") == first_state


def test_repeatable_service_legacy_deoldyn_failure_closes_prior_training_batch() -> None:
    manifest = upgrade_tag_manifest(
        _legacy_repeatable_service_manifest(11, "Orcs")
    )
    session = base_session(
        adventure_id="tag-rumor-11-legacy-evidence",
        adventure_type="imported",
        imported_manifest=manifest,
        active_quest=ActiveQuestState(
            tile_id="t",
            key="imported_boss",
            description="Defeat the old proxy.",
            boss_target_name="Orcs",
            completed=True,
        ),
        log=[
            "Adventures Guild procedure: Hero pays 60 gp to Deoldyn but fails at the Scene 3 training XP roll (d6=2 vs Level 1); Dead Shot is not learned."
        ],
    )
    session.map_state.tiles[0].content_key = "imported:tag-final-scene"

    assert repair_required_tag_scene_lifecycle(session) is True
    assert session.active_quest is not None
    state = session.active_quest.tag_procedure_state["tag_repeatable_service"]
    assert state["training_batch_resolved"] is True
    assert state["trained_character_ids"] == ["h"]
    assert len(state["training_results"]) == 1
    assert state["training_results"][0]["outcome"] == "dead_shot"
    assert state["training_results"][0]["success"] is False
    assert len(state["transactions"]) == 1
    first_state = session.model_dump(mode="json")
    assert repair_required_tag_scene_lifecycle(session) is False
    assert session.model_dump(mode="json") == first_state


def test_repeatable_service_legacy_inventory_only_shoes_are_recovered_once() -> None:
    manifest = upgrade_tag_manifest(
        _legacy_repeatable_service_manifest(6, "Goblins")
    )
    session = base_session(
        adventure_id="tag-rumor-6-legacy-inventory-evidence",
        adventure_type="imported",
        imported_manifest=manifest,
        active_quest=ActiveQuestState(
            tile_id="t",
            key="imported_boss",
            description="Defeat the old proxy.",
            boss_target_name="Goblins",
            completed=True,
        ),
        log=["Quest complete: Goblins has been destroyed."],
    )
    session.map_state.tiles[0].content_key = "imported:tag-final-scene"
    session.party[0].inventory = ["Shoes of Fast Walk", "Shoes of Fast Walk"]

    assert repair_required_tag_scene_lifecycle(session) is True
    assert session.active_quest is not None
    state = session.active_quest.tag_procedure_state["tag_repeatable_service"]
    assert len(state["shoe_assignments"]) == 2
    assert all(item["legacy_inventory_only"] for item in state["shoe_assignments"])
    assert state["transactions"][0]["pair_count"] == 2
    first_state = session.model_dump(mode="json")
    assert repair_required_tag_scene_lifecycle(session) is False
    assert session.model_dump(mode="json") == first_state


def test_repeatable_service_fresh_visit_does_not_attribute_preowned_shoes() -> None:
    manifest = upgrade_tag_manifest(
        _legacy_repeatable_service_manifest(6, "Goblins")
    )
    session = base_session(
        adventure_id="tag-rumor-6-fresh-preowned-shoes",
        adventure_type="imported",
        imported_manifest=manifest,
        active_quest=ActiveQuestState(
            tile_id="t",
            key="imported_room",
            description="Reach Blackbird Hill.",
            completed=True,
        ),
    )
    session.map_state.tiles[0].content_key = "imported:tag-final-scene"
    session.party[0].inventory = ["Shoes of Fast Walk", "Shoes of Fast Walk"]

    assert repair_required_tag_scene_lifecycle(session) is True
    assert session.active_quest is not None
    assert session.active_quest.completed is False
    assert "tag_repeatable_service" not in session.active_quest.tag_procedure_state
    assert "tag_repeatable_service_legacy_migration" not in (
        session.active_quest.tag_procedure_state
    )
    assert session.party[0].inventory == [
        "Shoes of Fast Walk",
        "Shoes of Fast Walk",
    ]
    first_state = session.model_dump(mode="json")
    assert repair_required_tag_scene_lifecycle(session) is False
    assert session.model_dump(mode="json") == first_state


def test_repeatable_service_fresh_visit_does_not_attribute_prior_deoldyn_skill() -> None:
    manifest = upgrade_tag_manifest(
        _legacy_repeatable_service_manifest(11, "Orcs")
    )
    session = base_session(
        adventure_id="tag-rumor-11-fresh-prior-training",
        adventure_type="imported",
        imported_manifest=manifest,
        active_quest=ActiveQuestState(
            tile_id="t",
            key="imported_boss",
            description="Meet Deoldyn.",
            boss_target_name="Orcs",
            completed=True,
        ),
    )
    session.map_state.tiles[0].content_key = "imported:tag-final-scene"
    session.party[0].learned_expert_skills = ["dead_shot"]
    session.party[0].expert_skill_targets = {"dead_shot": "tag_deoldyn"}

    assert repair_required_tag_scene_lifecycle(session) is True
    assert session.active_quest is not None
    assert session.active_quest.completed is False
    assert "tag_repeatable_service" not in session.active_quest.tag_procedure_state
    assert "tag_repeatable_service_legacy_migration" not in (
        session.active_quest.tag_procedure_state
    )
    assert session.party[0].learned_expert_skills == ["dead_shot"]
    assert session.party[0].expert_skill_targets == {"dead_shot": "tag_deoldyn"}
    first_state = session.model_dump(mode="json")
    assert repair_required_tag_scene_lifecycle(session) is False
    assert session.model_dump(mode="json") == first_state


def test_repeatable_service_resolved_deoldyn_marker_synthesizes_continue() -> None:
    manifest = upgrade_tag_manifest(
        _legacy_repeatable_service_manifest(11, "Orcs")
    )
    session = base_session(
        adventure_id="tag-rumor-11-legacy-resolved-marker",
        adventure_type="imported",
        imported_manifest=manifest,
        active_quest=ActiveQuestState(
            tile_id="t",
            key="imported_boss",
            description="Defeat the old proxy.",
            boss_target_name="Orcs",
            completed=True,
            tag_procedure_state={
                "tag_repeatable_service": {
                    "kind": "deoldyn",
                    "phase": "resolved",
                    "resolved": True,
                    "transactions": [],
                    "result_text": "The party has finished Deoldyn's training visit.",
                }
            },
        ),
    )
    session.map_state.tiles[0].content_key = "imported:tag-final-scene"
    session.party[0].learned_expert_skills = ["dead_shot"]
    session.party[0].expert_skill_targets = {"dead_shot": "tag_deoldyn"}

    assert repair_required_tag_scene_lifecycle(session) is True
    assert session.active_quest is not None
    state = session.active_quest.tag_procedure_state["tag_repeatable_service"]
    assert state["phase"] == "resolved"
    assert state["training_batch_resolved"] is True
    assert state["training_results"][0]["outcome"] == "dead_shot"
    assert state["training_results"][0]["legacy_durable_marker"] is True
    assert session.active_quest.completed is True
    assert session.tag_generated_completion_pending is True
    assert session.tag_generated_completion_title == "Deoldyn's archery training resolved"
    assert session.tag_generated_completion_body == state["result_text"]
    assert TAG_GENERATED_CLOSEOUT_LOG_MESSAGE in session.log
    first_state = session.model_dump(mode="json")
    assert repair_required_tag_scene_lifecycle(session) is False
    assert session.model_dump(mode="json") == first_state


def test_rumor_6_repeatable_service_api_persists_purchase_lesson_done_and_closeout(client) -> None:
    session_id = "tag-rumor-6-repeatable-api"
    manifest, characters = _save_repeatable_tag_service_session(
        session_id,
        6,
        [("learner", "paladin", 3, 500)],
    )
    learner = characters[0]
    entered = _enter_repeatable_tag_service(client, session_id, manifest)
    service = entered["session"]["tag_repeatable_service_state"]
    assert service["kind"] == "leprechaun"
    assert service["phase"] == "open"
    assert any(option["name"] == "Illusionary Armor" for option in service["spell_options"])

    bought = client.post(
        f"/api/sessions/{session_id}/tag-repeatable-service",
        json={
            "action": "buy_shoes",
            "payer_character_id": learner.id,
            "recipient_kind": "hero",
            "recipient_id": learner.id,
        },
    )
    assert bought.status_code == 200, bought.text
    bought_member = bought.json()["session"]["party"][0]
    assert bought_member["gold"] + bought_member["bank_gold"] == 300
    assert bought_member["inventory"] == ["Shoes of Fast Walk"]
    assert bought.json()["session"]["active_quest"]["completed"] is False

    learned = client.post(
        f"/api/sessions/{session_id}/tag-repeatable-service",
        json={
            "action": "learn_spell",
            "payer_character_id": learner.id,
            "learner_character_id": learner.id,
            "spell_name": "Illusionary Armor",
        },
    )
    assert learned.status_code == 200, learned.text
    learned_member = learned.json()["session"]["party"][0]
    assert learned_member["gold"] + learned_member["bank_gold"] == 200
    assert learned_member["spells"] == ["Illusionary Armor"]
    assert learned_member["expert_skill_targets"]["tag_leprechaun_illusion_spell"] == "Illusionary Armor"
    learned_service = learned.json()["session"]["tag_repeatable_service_state"]
    assert learned_service["illusion_lesson"]["spellcasting_modifier"] == "+1"
    assert learned_service["lesson_used"] is True

    done = client.post(
        f"/api/sessions/{session_id}/tag-repeatable-service",
        json={"action": "done"},
    )
    assert done.status_code == 200, done.text
    done_session = done.json()["session"]
    assert done_session["active_quest"]["completed"] is True
    assert done_session["tag_generated_completion_pending"] is True
    assert done_session["tag_repeatable_service_state"]["phase"] == "resolved"
    rumor = next(
        state for state in done.json()["campaign"]["tag_rumor_states"] if state["rumor_number"] == 6
    )
    assert rumor["status"] == "resolved"

    repeated_done = client.post(
        f"/api/sessions/{session_id}/tag-repeatable-service",
        json={"action": "done"},
    )
    assert repeated_done.status_code == 400
    assert "Continue" in repeated_done.json()["detail"]
    stale_purchase = client.post(
        f"/api/sessions/{session_id}/tag-repeatable-service",
        json={
            "action": "buy_shoes",
            "payer_character_id": learner.id,
            "recipient_kind": "hero",
            "recipient_id": learner.id,
        },
    )
    assert stale_purchase.status_code == 400
    assert "Continue" in stale_purchase.json()["detail"]

    completed = client.post(f"/api/sessions/{session_id}/tag-generated-lead-continue")
    assert completed.status_code == 200, completed.text
    assert completed.json()["mode"] == "complete"
    roster = main.store.get("characters", learner.id, Character.model_validate)
    assert roster is not None
    assert roster.gold == 200
    assert roster.inventory == ["Shoes of Fast Walk"]
    assert roster.spells == ["Illusionary Armor"]
    assert roster.expert_skill_targets["tag_leprechaun_illusion_spell"] == "Illusionary Armor"
    assert roster.active_session_id is None


def test_rumor_11_repeatable_service_api_batches_training_and_requires_done(
    client,
    monkeypatch,
) -> None:
    session_id = "tag-rumor-11-repeatable-api"
    manifest, characters = _save_repeatable_tag_service_session(
        session_id,
        11,
        [("archer", "warrior", 2, 500)],
    )
    archer = characters[0]
    entered = _enter_repeatable_tag_service(client, session_id, manifest)
    service = entered["session"]["tag_repeatable_service_state"]
    assert service["kind"] == "deoldyn"
    assert service["trainees"][0]["cost_gp"] == 120
    assert entered["session"]["active_quest"]["completed"] is False

    monkeypatch.setattr(
        "app.engine.tag_repeatable_services.roll_advancement",
        lambda *_args, **_kwargs: AdvancementRollResult(
            natural=6,
            total=6,
            sides=6,
            modifier=0,
            purpose="level_up",
        ),
    )
    trained = client.post(
        f"/api/sessions/{session_id}/tag-repeatable-service",
        json={
            "action": "train",
            "trainings": [
                {
                    "character_id": archer.id,
                    "outcome": "dead_shot",
                    "new_spell": "",
                }
            ],
        },
    )
    assert trained.status_code == 200, trained.text
    trained_session = trained.json()["session"]
    trained_member = trained_session["party"][0]
    assert trained_member["gold"] + trained_member["bank_gold"] == 380
    assert trained_member["learned_expert_skills"] == ["dead_shot"]
    assert trained_member["expert_skill_targets"]["dead_shot"] == "tag_deoldyn"
    assert trained_session["active_quest"]["completed"] is False
    assert trained_session["tag_generated_completion_pending"] is False
    assert trained_session["tag_repeatable_service_state"]["training_batch_resolved"] is True
    assert trained_session["tag_repeatable_service_state"]["trainees"][0]["eligible"] is False

    duplicate_batch = client.post(
        f"/api/sessions/{session_id}/tag-repeatable-service",
        json={
            "action": "train",
            "trainings": [{"character_id": archer.id, "outcome": "deadly_accuracy"}],
        },
    )
    assert duplicate_batch.status_code == 400
    assert "simultaneous training batch has already" in duplicate_batch.json()["detail"]

    blocked_legacy = client.post(
        f"/api/sessions/{session_id}/tag-scene-action",
        json={"scene_action": "deoldyn_training", "character_id": archer.id},
    )
    assert blocked_legacy.status_code == 400
    assert "visible Deoldyn batch host" in blocked_legacy.json()["detail"]

    done = client.post(
        f"/api/sessions/{session_id}/tag-repeatable-service",
        json={"action": "done"},
    )
    assert done.status_code == 200, done.text
    assert done.json()["session"]["tag_generated_completion_pending"] is True
    assert done.json()["session"]["active_quest"]["completed"] is True

    completed = client.post(f"/api/sessions/{session_id}/tag-generated-lead-continue")
    assert completed.status_code == 200, completed.text
    assert completed.json()["mode"] == "complete"
    roster = main.store.get("characters", archer.id, Character.model_validate)
    assert roster is not None
    assert roster.gold == 380
    assert roster.learned_expert_skills == ["dead_shot"]
    assert roster.expert_skill_targets["dead_shot"] == "tag_deoldyn"


def test_repeatable_service_actions_are_blocked_during_combat(client) -> None:
    rumor_6_id = "tag-rumor-6-combat-service-guard"
    manifest_6, characters_6 = _save_repeatable_tag_service_session(
        rumor_6_id,
        6,
        [("illusionist", "illusionist", 2, 500)],
    )
    hero_6 = characters_6[0]
    _enter_repeatable_tag_service(client, rumor_6_id, manifest_6)
    stored_6 = main.store.get("sessions", rumor_6_id, SessionState.model_validate)
    assert stored_6 is not None
    stored_6.mode = "combat"
    before_6 = stored_6.model_dump(mode="json")
    main.store.save("sessions", stored_6)

    rumor_6_actions = [
        {
            "action": "buy_shoes",
            "payer_character_id": hero_6.id,
            "recipient_kind": "hero",
            "recipient_id": hero_6.id,
        },
        {
            "action": "learn_spell",
            "payer_character_id": hero_6.id,
            "learner_character_id": hero_6.id,
            "spell_name": "Illusionary Armor",
        },
        {"action": "done"},
    ]
    for payload in rumor_6_actions:
        blocked = client.post(
            f"/api/sessions/{rumor_6_id}/tag-repeatable-service",
            json=payload,
        )
        assert blocked.status_code == 400
        assert "Resolve the current encounter" in blocked.json()["detail"]
    after_6 = main.store.get("sessions", rumor_6_id, SessionState.model_validate)
    assert after_6 is not None
    assert after_6.model_dump(mode="json") == before_6

    rumor_11_id = "tag-rumor-11-combat-service-guard"
    manifest_11, characters_11 = _save_repeatable_tag_service_session(
        rumor_11_id,
        11,
        [("archer", "warrior", 2, 500)],
    )
    hero_11 = characters_11[0]
    _enter_repeatable_tag_service(client, rumor_11_id, manifest_11)
    stored_11 = main.store.get("sessions", rumor_11_id, SessionState.model_validate)
    assert stored_11 is not None
    stored_11.mode = "combat"
    before_11 = stored_11.model_dump(mode="json")
    main.store.save("sessions", stored_11)

    for payload in (
        {
            "action": "train",
            "trainings": [{"character_id": hero_11.id, "outcome": "dead_shot"}],
        },
        {"action": "done"},
    ):
        blocked = client.post(
            f"/api/sessions/{rumor_11_id}/tag-repeatable-service",
            json=payload,
        )
        assert blocked.status_code == 400
        assert "Resolve the current encounter" in blocked.json()["detail"]
    after_11 = main.store.get("sessions", rumor_11_id, SessionState.model_validate)
    assert after_11 is not None
    assert after_11.model_dump(mode="json") == before_11


def test_rumor_6_hireling_assigned_shoes_cannot_be_transferred_or_sold(client) -> None:
    session_id = "tag-rumor-6-hireling-shoes-lock"
    manifest, characters = _save_repeatable_tag_service_session(
        session_id,
        6,
        [
            ("owner", "warrior", 3, 300),
            ("receiver", "wizard", 3, 0),
        ],
    )
    owner, receiver = characters
    stored = main.store.get("sessions", session_id, SessionState.model_validate)
    assert stored is not None
    stored.hirelings.append(
        HirelingState(
            id="tag-shoes-hireling",
            retainer_type="porter",
            name="Pip",
            life=3,
            max_life=3,
            marching_order=5,
        )
    )
    main.store.save("sessions", stored)
    _enter_repeatable_tag_service(client, session_id, manifest)

    bought = client.post(
        f"/api/sessions/{session_id}/tag-repeatable-service",
        json={
            "action": "buy_shoes",
            "payer_character_id": owner.id,
            "recipient_kind": "hireling",
            "recipient_id": "tag-shoes-hireling",
        },
    )
    assert bought.status_code == 200, bought.text
    assigned_session = main.store.get("sessions", session_id, SessionState.model_validate)
    assert assigned_session is not None
    assigned_session.camped_outside = True
    main.store.save("sessions", assigned_session)

    quote = client.get(
        f"/api/characters/{owner.id}/sell-quote",
        params={"item_name": "Shoes of Fast Walk"},
    )
    assert quote.status_code == 200, quote.text
    assert quote.json()["kind"] == "blocked"
    assert "assigned to a living hireling" in quote.json()["note"]

    sold = client.post(
        f"/api/characters/{owner.id}/sell-item",
        json={"item_name": "Shoes of Fast Walk"},
    )
    assert sold.status_code == 400
    assert "cannot be transferred or sold" in sold.json()["detail"]

    roster_transfer = client.post(
        f"/api/characters/{owner.id}/transfer",
        json={
            "target_character_id": receiver.id,
            "item_name": "Shoes of Fast Walk",
        },
    )
    assert roster_transfer.status_code == 400
    assert "cannot be transferred or sold" in roster_transfer.json()["detail"]

    party_transfer = client.post(
        f"/api/sessions/{session_id}/advance",
        json={
            "action": "transfer_item",
            "character_id": owner.id,
            "target_character_id": receiver.id,
            "item_name": "Shoes of Fast Walk",
            "show_rolls": False,
        },
    )
    assert party_transfer.status_code == 200, party_transfer.text
    party = party_transfer.json()["party"]
    assert "Shoes of Fast Walk" in next(
        member for member in party if member["character_id"] == owner.id
    )["inventory"]
    assert "Shoes of Fast Walk" not in next(
        member for member in party if member["character_id"] == receiver.id
    )["inventory"]
    assert "cannot be transferred or sold" in party_transfer.json()["log"][-1]


def test_generated_tag_direct_procedure_is_single_run(client, monkeypatch) -> None:
    rolls = iter([2, 6])
    monkeypatch.setattr("app.engine.tag_campaign.roll_d6", lambda: next(rolls))
    session = base_session(
        id="tag-procedure-session",
        adventure_id="tag-treasure-map-1",
        adventure_type="imported",
        imported_manifest={
            "title": "TAG Treasure Map 1",
            "source": {
                "parameters": {
                    "tag_reference": {
                        "lead_type": "treasure_map",
                        "title": "Underground caves",
                        "room_prompts": {},
                    }
                }
            },
            "rooms": [{"id": "tag-complication", "triggers": []}],
        },
        active_quest=ActiveQuestState(tile_id="t", key="imported_boss", description="Resolve TAG Treasure Map 1."),
    )
    main.store.save("sessions", session)

    first = client.post(
        "/api/sessions/tag-procedure-session/tag-branch-action",
        json={"branch_action": "map_cave_room_count", "reference": "Map Leads To 1"},
    )
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["entry"]["total"] == 5
    procedure_state = first_payload["session"]["active_quest"]["tag_generated_lead_state"]["procedures"]
    assert procedure_state["map_cave_room_count"]["total"] == 5
    assert "the app counts rooms" in first_payload["session"]["active_quest"]["tag_generated_lead_state"]["next_action"]
    assert any("TAG next:" in line and "room 5" in line for line in first_payload["session"]["log"])

    second = client.post(
        "/api/sessions/tag-procedure-session/tag-branch-action",
        json={"branch_action": "map_cave_room_count", "reference": "Map Leads To 1"},
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["entry"]["total"] == 5
    assert "already recorded" in second_payload["entry"]["result_text"]
    assert second_payload["session"]["active_quest"]["tag_generated_lead_state"]["procedures"]["map_cave_room_count"]["total"] == 5


def test_active_treasure_map_procedure_does_not_reroll(client, monkeypatch) -> None:
    rolls = iter([2, 6])
    monkeypatch.setattr("app.engine.tag_campaign.roll_d6", lambda: next(rolls))
    session = base_session(
        id="tag-map-quest-session",
        adventure_id="tag-treasure-map-1",
        adventure_type="imported",
        imported_manifest={
            "title": "TAG Treasure Map 1",
            "source": {
                "parameters": {
                    "tag_reference": {
                        "lead_type": "treasure_map",
                        "title": "Underground caves",
                        "room_prompts": {},
                    }
                }
            },
            "rooms": [{"id": "tag-complication", "triggers": []}],
        },
        active_quest=ActiveQuestState(
            tile_id="t",
            key="tag_treasure_map",
            description="Follow the purchased TAG treasure map to the underground caves and resolve its destination procedure.",
        ),
    )
    main.store.save("sessions", session)

    first = client.post(
        "/api/sessions/tag-map-quest-session/tag-branch-action",
        json={"branch_action": "map_cave_room_count", "reference": "Map Leads To 1"},
    )
    assert first.status_code == 200
    assert first.json()["entry"]["total"] == 5

    second = client.post(
        "/api/sessions/tag-map-quest-session/tag-branch-action",
        json={"branch_action": "map_cave_room_count", "reference": "Map Leads To 1"},
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["entry"]["total"] == 5
    assert "already recorded" in second_payload["entry"]["result_text"]
    assert second_payload["session"]["active_quest"]["tag_procedure_state"]["map_cave_room_count"]["total"] == 5


def test_tag_underground_caves_target_spawns_final_boss(monkeypatch) -> None:
    eng = engine()
    session = base_session(
        active_quest=ActiveQuestState(
            tile_id="t",
            key="tag_treasure_map",
            description="Follow the purchased TAG treasure map to the underground caves.",
            tag_procedure_state={
                "map_cave_room_count": {
                    "completed": True,
                    "total": 2,
                }
            },
        )
    )
    target_room = TileState(
        id="target",
        x=1,
        y=0,
        tile_key="22",
        tile_type="room",
        title="Target Room",
        description="The map's scratches match the stone here.",
        exits=[
            ExitState(direction="east", kind="door"),
            ExitState(direction="west", kind="door", destination_tile_id="t"),
        ],
    )
    session.map_state.tiles.append(target_room)
    session.map_state.current_tile_id = target_room.id
    monkeypatch.setattr(
        eng,
        "_roll_enemy",
        lambda *_args, **_kwargs: [
            EnemyState(id="boss", name="Ogre", category="boss", level=4, life=4, max_life=4)
        ],
    )

    started = eng._maybe_trigger_tag_underground_caves_finale(session, target_room, show_rolls=False)

    assert started is True
    assert session.mode == "combat"
    assert target_room.enemies[0].name == "Ogre"
    assert target_room.enemies[0].life == 6
    assert target_room.enemies[0].max_life == 6
    assert "final_boss" in target_room.enemies[0].tags
    assert "tag_treasure_map_finale" in target_room.enemies[0].tags
    assert target_room.final_boss_treasure is True
    assert target_room.exits[0].status == "blocked"
    state = session.active_quest.tag_procedure_state["map_cave_room_count"]
    assert state["final_room_tile_id"] == "target"
    assert state["rooms_seen"] == 2


def test_tag_underground_caves_final_boss_completes_objective() -> None:
    eng = engine()
    boss = EnemyState(
        id="boss",
        name="Ogre",
        category="boss",
        level=4,
        life=0,
        max_life=6,
        tags=["final_boss", "tag_treasure_map_finale"],
    )
    final_room = TileState(
        id="target",
        x=1,
        y=0,
        tile_key="22",
        tile_type="room",
        title="Target Room",
        description="The destination.",
        defeated_enemies=[boss],
    )
    session = base_session(
        mode="exploration",
        active_quest=ActiveQuestState(
            tile_id="t",
            key="tag_treasure_map",
            description="Follow the purchased TAG treasure map to the underground caves.",
            tag_procedure_state={
                "map_cave_room_count": {
                    "completed": True,
                    "total": 2,
                    "rooms_seen": 2,
                    "final_room_tile_id": "target",
                    "finale_spawned": True,
                }
            },
        ),
        map_state=MapState(tiles=[base_session().map_state.tiles[0], final_room], current_tile_id="target"),
    )

    eng._update_quest_on_combat_end(session, [boss], show_rolls=False)

    assert session.active_quest.completed is True
    assert session.active_quest.tag_procedure_signoff is True
    state = session.active_quest.tag_procedure_state["map_cave_room_count"]
    assert state["finale_defeated"] is True
    assert "final Boss defeated" in session.active_quest.tag_procedure_state["next_action"]
    assert any("TAG Treasure Map objective complete" in line for line in session.log)


def test_kerrak_dar_reward_spends_one_clue_for_hoard(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    hero = session.party[0]
    hero.gold = 0
    hero.clues = 1
    session.clues_found = 1
    session.active_quest = ActiveQuestState(tile_id="t", key="peaceful_way", description="Peace", completed=True)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 2)

    eng.advance(session, "claim_quest_reward", show_rolls=False)
    assert "Kerrak Dar Hoard" in hero.statuses

    eng.advance(session, "claim_kerrak_dar_hoard")
    assert hero.clues == 0
    assert session.clues_found == 0
    assert hero.gold == 200
    assert session.map_state.tiles[0].treasure_gold == 300
    assert "Kerrak Dar Hoard" not in hero.statuses
    assert any("Kerrak Dar's hoard found" in entry for entry in session.log)


def test_generated_tag_imports_do_not_claim_core_epic_rewards(monkeypatch) -> None:
    eng = engine()
    session = base_session(
        adventure_type="imported",
        imported_manifest={
            "title": "TAG Guild Job 4: Leprechauns at Blackbird Hill",
            "source": {
                "parameters": {
                    "tag_reference": {
                        "lead_type": "rumor",
                        "title": "Leprechauns at Blackbird Hill",
                        "finale_mode": "vendor",
                    }
                }
            },
        },
    )
    session.active_quest = ActiveQuestState(tile_id="t", key="tag_generated_scene", description="Find the leprechauns.", completed=True)
    hero = session.party[0]
    hero.clues = 1
    session.clues_found = 1
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 2)

    eng.advance(session, "claim_quest_reward", show_rolls=False)

    assert session.active_quest is not None
    assert session.active_quest.reward_claimed is False
    assert "Kerrak Dar Hoard" not in hero.statuses
    assert any("generated Adventures Guild scenes" in entry for entry in session.log)
    assert not any("Quest complete! Epic reward" in entry for entry in session.log)


def test_core_gold_quest_from_generated_tag_session_can_be_turned_in(monkeypatch) -> None:
    eng = engine()
    session = base_session(
        adventure_type="imported",
        imported_manifest={
            "title": "TAG Rumor 2: Medusa in the Hunter's Cabin",
            "source": {
                "parameters": {
                    "tag_reference": {
                        "lead_type": "rumor",
                        "rumor_number": 2,
                        "title": "Medusa in the Hunter's Cabin",
                    }
                }
            },
        },
        active_quest=ActiveQuestState(
            tile_id="t",
            key="bring_gold",
            description="Bring 200gp to the Quest-giver's tile.",
            gold_required=200,
        ),
    )
    session.party[0].gold = 209
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)

    eng.advance(session, "claim_quest_reward", show_rolls=False)

    assert session.active_quest is None
    assert session.party[0].gold == 9
    assert any("Quest complete! Epic reward" in entry for entry in session.log)
    assert not any("generated Adventures Guild scenes" in entry for entry in session.log)
    assert session.tag_generated_completion_pending is True
    assert "encounter remains peaceful and does not restart" in (session.tag_generated_completion_body or "")
    assert "combat treasure is not awarded" in (session.tag_generated_completion_body or "")
    assert TAG_GENERATED_CLOSEOUT_ACTION_LABEL in (session.tag_generated_completion_body or "")


def test_resumed_generated_tag_core_quest_reward_repairs_to_clean_closeout(client) -> None:
    manifest, _entry = build_tag_adventure_manifest(
        default_campaign(),
        lead_type="rumor",
        detail="2",
    )
    session = base_session(
        id="completed-tag-core-quest",
        adventure_id=manifest["id"],
        adventure_type="imported",
        imported_manifest=manifest,
        active_quest=None,
        log=[
            "The encounter ends peacefully.",
            "Quest complete! Epic reward: The Book of Skalitos.",
            "Book of Skalitos (6 pages) added to Quest Hero's inventory.",
        ],
    )
    session.party[0].inventory.append("Book of Skalitos (6 pages)")
    main.store.save("sessions", session)

    resumed = client.get("/api/sessions/completed-tag-core-quest")

    assert resumed.status_code == 200
    payload = resumed.json()
    assert payload["tag_generated_completion_pending"] is True
    assert "encounter remains peaceful and does not restart" in payload["tag_generated_completion_body"]
    assert "combat treasure is not awarded" in payload["tag_generated_completion_body"]
    assert TAG_GENERATED_CLOSEOUT_ACTION_LABEL in payload["tag_generated_completion_body"]
    assert payload["active_quest"] is None
    assert sum("Book of Skalitos" in line for line in payload["log"]) == 2
    assert payload["party"][0]["inventory"].count("Book of Skalitos (6 pages)") == 1

    continued = client.post("/api/sessions/completed-tag-core-quest/tag-generated-lead-continue")

    assert continued.status_code == 200
    completed = continued.json()
    assert completed["mode"] == "complete"
    assert completed["tag_generated_completion_pending"] is False


def test_resumed_legacy_generated_tag_closeout_copy_is_normalized(client) -> None:
    manifest, _entry = build_tag_adventure_manifest(
        default_campaign(),
        lead_type="rumor",
        detail="2",
    )
    legacy_body = (
        "The Quest is complete and the Quest-giver accepts the result. "
        "The encounter remains peaceful and does not restart; combat treasure is not awarded. "
        "The Epic Reward shown in Narrative is the Quest reward. "
        "Choose Return to town and finish to close this Adventures Guild lead."
    )
    session = base_session(
        id="legacy-tag-closeout-copy",
        adventure_id=manifest["id"],
        adventure_type="imported",
        imported_manifest=manifest,
        active_quest=None,
        tag_generated_completion_pending=True,
        tag_generated_completion_title="Medusa in the Hunter's Cabin resolved",
        tag_generated_completion_body=legacy_body,
        log=[
            legacy_body,
            "When you are ready, choose Continue to finish the adventure.",
        ],
    )
    main.store.save("sessions", session)

    resumed = client.get("/api/sessions/legacy-tag-closeout-copy")

    assert resumed.status_code == 200
    payload = resumed.json()
    assert payload["mode"] == "exploration"
    assert payload["active_quest"] is None
    assert payload["tag_generated_completion_pending"] is True
    assert TAG_GENERATED_CLOSEOUT_ACTION_LABEL in payload["tag_generated_completion_body"]
    assert "Choose Return to town and finish" not in payload["tag_generated_completion_body"]
    assert TAG_GENERATED_CLOSEOUT_LOG_MESSAGE in payload["log"]
    assert not any("choose Continue to finish the adventure" in line for line in payload["log"])

    stored = main.store.get("sessions", session.id, SessionState.model_validate)
    assert stored is not None
    assert stored.tag_generated_completion_body == payload["tag_generated_completion_body"]
    assert stored.log == payload["log"]


def test_session_tag_branch_action_syncs_live_party_character(client) -> None:
    character = Character(
        id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=250,
        max_life=3,
        current_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=[],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    session = base_session(
        id="tag-live-sync",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=250,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
                inventory=[],
            )
        ],
    )
    main.store.save("characters", character)
    main.store.save("sessions", session)

    response = client.post(
        "/api/sessions/tag-live-sync/tag-branch-action",
        json={
            "character_id": "h",
            "branch_action": "leprechaun_shoes",
            "reference": "Scene 2 Shoes of Fast Walk",
            "clue_cost": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    hero = payload["session"]["party"][0]
    assert hero["gold"] == 50
    assert "Shoes of Fast Walk" in hero["inventory"]
    assert "buys 1 pair" in payload["entry"]["result_text"]


def test_session_tag_purchase_uses_live_party_bank_gold(client) -> None:
    character = Character(
        id="banked",
        name="Banked Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=203,
        max_life=3,
        current_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=[],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    session = base_session(
        id="tag-bank-sync",
        adventure_id="tag",
        adventure_type="imported",
        party=[
            PartyMemberState(
                character_id="banked",
                name="Banked Hero",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=3,
                bank_gold=200,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
                inventory=[],
            )
        ],
    )
    main.store.save("characters", character)
    main.store.save("sessions", session)

    response = client.post(
        "/api/sessions/tag-bank-sync/tag-branch-action",
        json={
            "character_id": "banked",
            "branch_action": "leprechaun_shoes",
            "reference": "Scene 2 Shoes of Fast Walk",
            "clue_cost": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    hero = payload["session"]["party"][0]
    assert hero["gold"] == 3
    assert hero["bank_gold"] == 0
    assert "Shoes of Fast Walk" in hero["inventory"]
    assert payload["character"]["gold"] == 3


def test_medusa_generated_scene_spawns_after_printed_approach_choice(client, monkeypatch) -> None:
    character = Character(
        id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=0,
        max_life=8,
        current_life=8,
        attack_bonus=3,
        defense_bonus=1,
        save_bonus=0,
        inventory=[],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    manifest, _entry = build_tag_adventure_manifest(default_campaign(), lead_type="rumor", detail="2")
    final_tile = TileState(
        id="final",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Xasartha's Cabin",
        description="Xasartha waits.",
        content_key="imported:tag-final-scene",
    )
    session = base_session(
        id="medusa-choice-session",
        adventure_id=manifest["id"],
        adventure_type="imported",
        imported_manifest=manifest,
        map_state=MapState(tiles=[final_tile], current_tile_id="final"),
        active_quest=ActiveQuestState(
            tile_id="final",
            key="tag_lead",
            description="Resolve Xasartha.",
            boss_target_name="Medusa",
        ),
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
                class_id="warrior",
                class_name="Warrior",
                level=3,
                xp=0,
                gold=0,
                current_life=8,
                max_life=8,
                attack_bonus=3,
                defense_bonus=1,
                save_bonus=0,
                inventory=[],
            )
        ],
    )
    main.store.save("characters", character)
    main.store.save("sessions", session)
    monkeypatch.setattr("app.engine.tag_campaign.roll_exploding_d6", lambda: (6, [6]))

    response = client.post(
        "/api/sessions/medusa-choice-session/tag-branch-action",
        json={
            "character_id": "h",
            "branch_action": "medusa_stealth_approach",
            "reference": "Scene 1 medusa stealth approach",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["mode"] == "combat"
    final_room = payload["session"]["map_state"]["tiles"][0]
    assert [enemy["name"] for enemy in final_room["enemies"]] == ["Medusa"]
    assert final_room["enemies"][0]["level"] == 4
    assert final_room["enemies"][0]["life"] == 4
    assert any("printed Scene 1 result" in line for line in payload["session"]["log"])
    assert not any("Final Boss check" in line for line in payload["session"]["log"])


def test_mutant_fish_api_runs_party_saves_and_campaign_rate_reward(client, monkeypatch) -> None:
    character = Character(
        id="fish-hero",
        name="Fish Hero",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=0,
        max_life=8,
        current_life=8,
        attack_bonus=3,
        defense_bonus=1,
        save_bonus=0,
        inventory=[],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    campaign = default_campaign()
    campaign.tag_friendly_chaos_cultists = True
    save_campaign(main.store, campaign)
    manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail="4")
    final_tile = TileState(
        id="bridge-pool",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="The Bridge Pool",
        description="Mutant fish chant beneath the bridge.",
        content_key="imported:tag-final-scene",
    )
    session = base_session(
        id="mutant-fish-api-session",
        adventure_id=manifest["id"],
        adventure_type="imported",
        imported_manifest=manifest,
        map_state=MapState(tiles=[final_tile], current_tile_id=final_tile.id),
        active_quest=ActiveQuestState(
            tile_id=final_tile.id,
            key="tag_generated_scene",
            description="Resolve the Mutant Fish scene.",
        ),
        party=[
            PartyMemberState(
                character_id="fish-hero",
                name="Fish Hero",
                class_id="warrior",
                class_name="Warrior",
                level=3,
                xp=0,
                gold=0,
                current_life=8,
                max_life=8,
                attack_bonus=3,
                defense_bonus=1,
                save_bonus=0,
                inventory=[],
            )
        ],
    )
    main.store.save("characters", character)
    main.store.save("sessions", session)
    monkeypatch.setattr(
        "app.engine.tag_mutant_fish.roll_exploding_for_level",
        lambda _member, session=None: (5, [5]),
    )
    monkeypatch.setattr("app.engine.tag_mutant_fish.roll_d6", lambda: 2)

    started = client.post(
        "/api/sessions/mutant-fish-api-session/tag-branch-action",
        json={"branch_action": "mutant_fish_scene12", "step": "start"},
    )

    assert started.status_code == 200
    started_session = started.json()["session"]
    fish_state = started_session["active_quest"]["tag_procedure_state"]["mutant_fish_scene12"]
    assert fish_state["phase"] == "reward"
    assert fish_state["ration_count"] == 5
    assert started_session["minor_encounters_defeated"] == 2

    sold = client.post(
        "/api/sessions/mutant-fish-api-session/tag-branch-action",
        json={
            "branch_action": "mutant_fish_scene12",
            "step": "sell",
            "character_id": "fish-hero",
        },
    )

    assert sold.status_code == 200
    payload = sold.json()
    assert payload["session"]["party"][0]["gold"] == 25
    assert payload["session"]["tag_generated_completion_pending"] is True
    assert payload["campaign"]["tag_friendly_chaos_cultists"] is True
    assert "5gp each" in payload["entry"]["result_text"]


def test_mutant_fish_shared_rumor_entry_auto_starts_scene_12_once(client, monkeypatch) -> None:
    manifest, _entry = build_tag_adventure_manifest(default_campaign(), lead_type="rumor", detail="4")
    reference = manifest["source"]["parameters"]["tag_reference"]
    reference["room_prompts"]["tag-lead-entry"]["actions"] = [
        {
            "label": "Record lead choice",
            "tooltip": "Legacy generic action.",
            "action_type": "branch",
            "action_value": "social_choice",
            "reference": "legacy lead choice",
            "amount": 0,
        }
    ]
    session = create_session_from_manifest(
        main.random_engine,
        "mutant-fish-entry-route",
        "party",
        [
            PartyMemberState(
                character_id="fish-entry-hero",
                name="Fish Entry Hero",
                class_id="warrior",
                class_name="Warrior",
                level=3,
                xp=0,
                gold=0,
                current_life=8,
                max_life=8,
                attack_bonus=1,
                defense_bonus=1,
                save_bonus=0,
            ),
            PartyMemberState(
                character_id="fish-entry-victim",
                name="Fish Entry Victim",
                class_id="warrior",
                class_name="Warrior",
                level=3,
                xp=0,
                gold=0,
                current_life=8,
                max_life=8,
                attack_bonus=1,
                defense_bonus=1,
                save_bonus=0,
            ),
        ],
        manifest,
        adventure_id=manifest["id"],
    )
    assert session.active_quest is not None
    assert session.active_quest.key == "tag_generated_scene"
    main.store.save(
        "characters",
        Character(
            id="fish-entry-hero",
            name="Fish Entry Hero",
            class_id="warrior",
            class_name="Warrior",
            level=3,
            xp=0,
            gold=0,
            max_life=8,
            current_life=8,
            attack_bonus=1,
            defense_bonus=1,
            save_bonus=0,
            inventory=[],
            active_session_id=session.id,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        ),
    )
    main.store.save("sessions", session)
    save_calls: list[str] = []

    def roll_scene12(member, session=None):
        save_calls.append(member.character_id)
        return (5, [5]) if member.character_id == "fish-entry-hero" else (1, [1])

    monkeypatch.setattr("app.engine.tag_mutant_fish.roll_exploding_for_level", roll_scene12)

    resumed = client.get("/api/sessions/mutant-fish-entry-route")

    assert resumed.status_code == 200
    resumed_payload = resumed.json()
    entry_actions = resumed_payload["imported_manifest"]["source"]["parameters"]["tag_reference"]["room_prompts"]["tag-lead-entry"]["actions"]
    assert [action["label"] for action in entry_actions] == [
        "Investigate",
        "Not now — return to town",
    ]

    investigated = client.post(
        "/api/sessions/mutant-fish-entry-route/tag-route-action",
        json={
            "route_action": "unlock_scene",
            "reference": entry_actions[0]["reference"],
        },
    )

    assert investigated.status_code == 200
    investigated_session = investigated.json()["session"]
    current_id = investigated_session["map_state"]["current_tile_id"]
    current = next(tile for tile in investigated_session["map_state"]["tiles"] if tile["id"] == current_id)
    assert current["content_key"] == "imported:tag-final-scene"
    assert current["title"] == "The Bridge Pool"
    fish_state = investigated_session["active_quest"]["tag_procedure_state"]["mutant_fish_scene12"]
    assert fish_state["phase"] == "rescue"
    assert fish_state["in_water_character_ids"] == ["fish-entry-victim"]
    assert len(fish_state["initial_saves"]) == 2
    assert save_calls == ["fish-entry-hero", "fish-entry-victim"]
    assert investigated_session["active_quest"]["completed"] is False
    assert investigated_session["tag_generated_completion_pending"] is False
    assert not any(
        line == "Quest complete: objective location reached."
        for line in investigated_session["log"]
    )
    assert investigated_session["generated_tag_diagnostics"]["current_actions"] == [
        "Mutant fish rescue and reward"
    ]

    for _ in range(2):
        reloaded = client.get("/api/sessions/mutant-fish-entry-route")
        assert reloaded.status_code == 200
        reloaded_state = reloaded.json()["active_quest"]["tag_procedure_state"]["mutant_fish_scene12"]
        assert reloaded_state["initial_saves"] == fish_state["initial_saves"]
    assert save_calls == ["fish-entry-hero", "fish-entry-victim"]

    monkeypatch.setattr("app.engine.tag_mutant_fish.roll_d6", lambda: 2)
    rescued = client.post(
        "/api/sessions/mutant-fish-entry-route/tag-branch-action",
        json={
            "branch_action": "mutant_fish_scene12",
            "step": "rescue",
            "character_id": "fish-entry-hero",
            "target_character_id": "fish-entry-victim",
        },
    )
    assert rescued.status_code == 200
    rescued_session = rescued.json()["session"]
    rescued_state = rescued_session["active_quest"]["tag_procedure_state"]["mutant_fish_scene12"]
    assert rescued_state["phase"] == "reward"
    assert rescued_state["ration_count"] == 5
    assert rescued_session["minor_encounters_defeated"] == 2

    sold = client.post(
        "/api/sessions/mutant-fish-entry-route/tag-branch-action",
        json={
            "branch_action": "mutant_fish_scene12",
            "step": "sell",
            "character_id": "fish-entry-hero",
        },
    )
    assert sold.status_code == 200
    sold_session = sold.json()["session"]
    assert sold_session["mode"] == "exploration"
    assert sold_session["active_quest"]["completed"] is True
    assert sold_session["tag_generated_completion_pending"] is True

    completed = client.post("/api/sessions/mutant-fish-entry-route/tag-generated-lead-continue")
    assert completed.status_code == 200
    assert completed.json()["mode"] == "complete"
    completed_campaign = load_campaign(main.store)
    assert completed_campaign.adventures_completed == 1
    assert completed_campaign.days_passed == 1

    repeated = client.post(
        "/api/sessions/mutant-fish-entry-route/advance",
        json={"action": "search", "show_rolls": False},
    )
    assert repeated.status_code == 200
    repeated_campaign = load_campaign(main.store)
    assert repeated_campaign.adventures_completed == 1
    assert repeated_campaign.days_passed == 1


def test_mutant_fish_resume_repairs_stale_arrival_completion_and_persists_all_fail(client, monkeypatch) -> None:
    manifest, _entry = build_tag_adventure_manifest(default_campaign(), lead_type="rumor", detail="4")
    manifest["quest"]["complete_when"] = {"type": "room_reached", "room_id": "tag-final-scene"}
    final_action = manifest["source"]["parameters"]["tag_reference"]["room_prompts"]["tag-final-scene"]["actions"][0]
    final_action.pop("auto_start", None)
    final_action.pop("required_for_completion", None)
    session = create_session_from_manifest(
        main.random_engine,
        "mutant-fish-stale-arrival",
        "party",
        [
            PartyMemberState(
                character_id="fish-stale-hero",
                name="Fish Stale Hero",
                class_id="warrior",
                class_name="Warrior",
                level=3,
                xp=0,
                gold=0,
                current_life=8,
                max_life=8,
                attack_bonus=1,
                defense_bonus=1,
                save_bonus=0,
            )
        ],
        manifest,
        adventure_id=manifest["id"],
    )
    final_tile = next(
        tile for tile in session.map_state.tiles if tile.content_key == "imported:tag-final-scene"
    )
    session.map_state.current_tile_id = final_tile.id
    assert session.active_quest is not None
    session.active_quest.completed = True
    session.log.extend(
        [
            "Quest complete: objective location reached.",
            "Quest objective complete. Return to Guild Contact in Mutant Fish Under the Bridge to report.",
        ]
    )
    session.imported_fired_triggers.append("quest:return_hint")
    main.store.save(
        "characters",
        Character(
            id="fish-stale-hero",
            name="Fish Stale Hero",
            class_id="warrior",
            class_name="Warrior",
            level=3,
            xp=0,
            gold=0,
            max_life=8,
            current_life=8,
            attack_bonus=1,
            defense_bonus=1,
            save_bonus=0,
            inventory=[],
            active_session_id=session.id,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        ),
    )
    main.store.save("sessions", session)
    calls = 0

    def fail_scene12(_member, session=None):
        nonlocal calls
        calls += 1
        return 1, [1]

    monkeypatch.setattr("app.engine.tag_mutant_fish.roll_exploding_for_level", fail_scene12)

    resumed = client.get("/api/sessions/mutant-fish-stale-arrival")

    assert resumed.status_code == 200
    payload = resumed.json()
    assert payload["imported_quest_complete_when"] == {
        "type": "tag_scene_resolved",
        "room_id": "tag-final-scene",
    }
    assert payload["active_quest"]["key"] == "tag_generated_scene"
    assert payload["active_quest"]["completed"] is False
    assert payload["active_quest"]["tag_procedure_state"]["mutant_fish_scene12"]["phase"] == "destroyed"
    assert payload["mode"] == "complete"
    assert payload["party"][0]["current_life"] == 0
    assert payload["minor_encounters_defeated"] == 0
    assert "Character roster updated after the adventure ended." in payload["summary"]
    assert "quest:return_hint" not in payload["imported_fired_triggers"]
    assert not any("objective location reached" in line for line in payload["log"])
    assert calls == 1
    campaign = load_campaign(main.store)
    rumor_state = next(state for state in campaign.tag_rumor_states if state.rumor_number == 4)
    assert rumor_state.status == "resolved"
    assert campaign.adventures_completed == 0
    assert campaign.days_passed == 0
    character = main.store.get("characters", "fish-stale-hero", Character.model_validate)
    assert character is not None
    assert character.current_life == 0
    assert character.active_session_id is None

    reloaded = client.get("/api/sessions/mutant-fish-stale-arrival")
    assert reloaded.status_code == 200
    assert calls == 1
    reloaded_campaign = load_campaign(main.store)
    assert reloaded_campaign.adventures_completed == 0
    assert reloaded_campaign.days_passed == 0


def test_mutant_fish_auto_start_all_fail_persists_death_and_finishes(client, monkeypatch) -> None:
    manifest, _entry = build_tag_adventure_manifest(default_campaign(), lead_type="rumor", detail="4")
    members = [
        PartyMemberState(
            character_id=f"fish-doomed-{index}",
            name=f"Fish Doomed {index}",
            class_id="warrior",
            class_name="Warrior",
            level=3,
            xp=0,
            gold=0,
            current_life=8,
            max_life=8,
            attack_bonus=1,
            defense_bonus=1,
            save_bonus=0,
        )
        for index in (1, 2)
    ]
    session = create_session_from_manifest(
        main.random_engine,
        "mutant-fish-auto-destroyed",
        "party",
        members,
        manifest,
        adventure_id=manifest["id"],
    )
    for member in members:
        character = Character(
            id=member.character_id,
            name=member.name,
            class_id=member.class_id,
            class_name=member.class_name,
            level=member.level,
            xp=member.xp,
            gold=member.gold,
            max_life=member.max_life,
            current_life=member.current_life,
            attack_bonus=member.attack_bonus,
            defense_bonus=member.defense_bonus,
            save_bonus=member.save_bonus,
            inventory=[],
            active_session_id=session.id,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        main.store.save("characters", character)
    main.store.save("sessions", session)
    monkeypatch.setattr(
        "app.engine.tag_mutant_fish.roll_exploding_for_level",
        lambda _member, session=None: (1, [1]),
    )
    investigate = manifest["source"]["parameters"]["tag_reference"]["room_prompts"]["tag-lead-entry"]["actions"][0]

    response = client.post(
        "/api/sessions/mutant-fish-auto-destroyed/tag-route-action",
        json={"route_action": "unlock_scene", "reference": investigate["reference"]},
    )

    assert response.status_code == 200
    payload = response.json()
    destroyed = payload["session"]
    assert destroyed["mode"] == "complete"
    assert destroyed["active_quest"]["completed"] is False
    assert destroyed["active_quest"]["tag_procedure_state"]["mutant_fish_scene12"]["phase"] == "destroyed"
    assert destroyed["tag_generated_completion_pending"] is False
    assert destroyed["minor_encounters_defeated"] == 0
    assert all(member["current_life"] == 0 for member in destroyed["party"])
    assert "Character roster updated after the adventure ended." in destroyed["summary"]
    rumor_state = next(
        state for state in payload["campaign"]["tag_rumor_states"] if state["rumor_number"] == 4
    )
    assert rumor_state["status"] == "resolved"
    assert payload["campaign"]["adventures_completed"] == 0
    assert payload["campaign"]["days_passed"] == 0
    assert not any(
        entry["event_type"] == "adventure_completed"
        for entry in payload["campaign"]["campaign_chronicle"]
    )
    for member in members:
        character = main.store.get("characters", member.character_id, Character.model_validate)
        assert character is not None
        assert character.current_life == 0
        assert character.active_session_id is None


def test_mutant_fish_physical_entry_all_fail_uses_terminal_failure_once(client, monkeypatch) -> None:
    manifest, _entry = build_tag_adventure_manifest(default_campaign(), lead_type="rumor", detail="4")
    member = PartyMemberState(
        character_id="fish-physical-doomed",
        name="Fish Physical Doomed",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=0,
        current_life=8,
        max_life=8,
        attack_bonus=1,
        defense_bonus=1,
        save_bonus=0,
    )
    session = create_session_from_manifest(
        main.random_engine,
        "mutant-fish-physical-destroyed",
        "party",
        [member],
        manifest,
        adventure_id=manifest["id"],
    )
    complication = next(
        tile for tile in session.map_state.tiles if tile.content_key == "imported:tag-complication"
    )
    final_tile = next(
        tile for tile in session.map_state.tiles if tile.content_key == "imported:tag-final-scene"
    )
    final_exit = next(
        exit_state
        for exit_state in complication.exits
        if exit_state.destination_tile_id == final_tile.id
    )
    final_exit.status = "open"
    final_exit.door_open = True
    session.map_state.current_tile_id = complication.id
    main.store.save(
        "characters",
        Character(
            id=member.character_id,
            name=member.name,
            class_id=member.class_id,
            class_name=member.class_name,
            level=member.level,
            xp=member.xp,
            gold=member.gold,
            max_life=member.max_life,
            current_life=member.current_life,
            attack_bonus=member.attack_bonus,
            defense_bonus=member.defense_bonus,
            save_bonus=member.save_bonus,
            inventory=[],
            active_session_id=session.id,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        ),
    )
    main.store.save("sessions", session)
    calls = 0

    def fail_scene12(_member, session=None):
        nonlocal calls
        calls += 1
        return 1, [1]

    monkeypatch.setattr("app.engine.tag_mutant_fish.roll_exploding_for_level", fail_scene12)

    entered = client.post(
        f"/api/sessions/{session.id}/advance",
        json={"action": "explore", "exit_id": final_exit.id, "show_rolls": False},
    )

    assert entered.status_code == 200
    payload = entered.json()
    assert payload["mode"] == "complete"
    assert payload["active_quest"]["tag_procedure_state"]["mutant_fish_scene12"]["phase"] == "destroyed"
    assert payload["party"][0]["current_life"] == 0
    assert calls == 1
    campaign = load_campaign(main.store)
    rumor_state = next(state for state in campaign.tag_rumor_states if state.rumor_number == 4)
    assert rumor_state.status == "resolved"
    assert campaign.adventures_completed == 0
    assert campaign.days_passed == 0
    character = main.store.get("characters", member.character_id, Character.model_validate)
    assert character is not None
    assert character.current_life == 0
    assert character.active_session_id is None

    repeated = client.post(
        f"/api/sessions/{session.id}/advance",
        json={"action": "explore", "exit_id": final_exit.id, "show_rolls": False},
    )
    assert repeated.status_code == 200
    assert calls == 1
    repeated_campaign = load_campaign(main.store)
    assert repeated_campaign.adventures_completed == 0
    assert repeated_campaign.days_passed == 0


def test_shared_rumor_entry_return_to_town_keeps_rumor_for_later(client) -> None:
    manifest, _entry = build_tag_adventure_manifest(default_campaign(), lead_type="rumor", detail="4")
    session = create_session_from_manifest(
        main.random_engine,
        "mutant-fish-entry-return",
        "party",
        [
            PartyMemberState(
                character_id="fish-return-hero",
                name="Fish Return Hero",
                class_id="warrior",
                class_name="Warrior",
                level=3,
                xp=0,
                gold=0,
                current_life=8,
                max_life=8,
                attack_bonus=1,
                defense_bonus=1,
                save_bonus=0,
            )
        ],
        manifest,
        adventure_id=manifest["id"],
    )
    main.store.save("sessions", session)
    return_action = manifest["source"]["parameters"]["tag_reference"]["room_prompts"]["tag-lead-entry"]["actions"][1]

    returned = client.post(
        "/api/sessions/mutant-fish-entry-return/tag-route-action",
        json={
            "route_action": "final_route",
            "reference": return_action["reference"],
        },
    )

    assert returned.status_code == 200
    returned_payload = returned.json()
    assert returned_payload["session"]["tag_generated_completion_pending"] is True
    assert "remains recorded" in returned_payload["session"]["tag_generated_completion_body"]
    rumor_state = next(
        state for state in returned_payload["campaign"]["tag_rumor_states"] if state["rumor_number"] == 4
    )
    assert rumor_state["status"] == "heard"

    completed = client.post("/api/sessions/mutant-fish-entry-return/tag-generated-lead-continue")

    assert completed.status_code == 200
    assert completed.json()["mode"] == "complete"


def test_generated_rumor_entry_pending_requires_the_exact_resolved_investigate_marker(client) -> None:
    session_id = "tag-rumor-entry-marker"
    manifest, _characters = _save_repeatable_tag_service_session(
        session_id,
        11,
        [("archer", "warrior", 3, 180)],
    )
    session = main.store.get("sessions", session_id, SessionState.model_validate)
    assert session is not None
    reference = session.imported_manifest["source"]["parameters"]["tag_reference"]
    investigate = next(
        action
        for action in manifest["source"]["parameters"]["tag_reference"]["room_prompts"]["tag-lead-entry"]["actions"]
        if action["label"] == "Investigate"
    )

    assert generated_tag_rumor_entry_choice_pending(session) is True

    reference["route_markers"] = [
        {
            "action": "unlock_scene",
            "reference": "A later and unrelated scene branch",
            "resolved": True,
        }
    ]
    assert generated_tag_rumor_entry_choice_pending(session) is True

    reference["route_markers"][0]["reference"] = investigate["reference"]
    assert generated_tag_rumor_entry_choice_pending(session) is False


def test_investigated_generated_rumor_returns_from_camp_without_reopening_entry(client) -> None:
    session_id = "tag-rumor-investigated-camp-return"
    manifest, _characters = _save_repeatable_tag_service_session(
        session_id,
        11,
        [("archer", "warrior", 3, 180)],
    )
    entered = _enter_repeatable_tag_service(client, session_id, manifest)
    entry_choice = entered["session"]["active_quest"]["tag_generated_lead_state"]["rumor_entry_choice"]
    assert entry_choice["choice"] == "investigate"
    assert entry_choice["resolved"] is True

    session = main.store.get("sessions", session_id, SessionState.model_validate)
    assert session is not None
    assert session.entrance_tile_id
    session.camped_outside = True
    session.map_state.current_tile_id = session.entrance_tile_id
    main.store.save("sessions", session)

    returned = client.post(
        f"/api/sessions/{session_id}/advance",
        json={"action": "return_to_dungeon", "show_rolls": False},
    )

    assert returned.status_code == 200, returned.text
    payload = returned.json()
    assert payload["camped_outside"] is False
    assert payload["map_state"]["current_tile_id"] == payload["entrance_tile_id"]
    assert payload["generated_tag_diagnostics"]["rumor_entry_choice_pending"] is False
    assert payload["active_quest"]["tag_generated_lead_state"]["rumor_entry_choice"] == entry_choice
    assert payload["tag_repeatable_service_state"]["phase"] == "open"
    assert not payload["log"][-1].startswith("Choose Investigate")


def test_fresh_generated_rumor_can_enter_from_camp_before_making_opening_choice(client) -> None:
    session_id = "tag-rumor-fresh-camp-return"
    _manifest, _characters = _save_repeatable_tag_service_session(
        session_id,
        11,
        [("archer", "warrior", 3, 180)],
        start_camped_outside=True,
    )
    session = main.store.get("sessions", session_id, SessionState.model_validate)
    assert session is not None
    assert session.entrance_tile_id
    assert session.camped_outside is True
    assert session.imported_entrance_pending is True

    returned = client.post(
        f"/api/sessions/{session_id}/advance",
        json={"action": "return_to_dungeon", "show_rolls": False},
    )

    assert returned.status_code == 200, returned.text
    payload = returned.json()
    assert payload["camped_outside"] is False
    assert payload["imported_entrance_pending"] is False
    assert payload["map_state"]["current_tile_id"] == payload["entrance_tile_id"]
    assert payload["generated_tag_diagnostics"]["rumor_entry_choice_pending"] is True
    assert "rumor_entry_choice" not in payload["active_quest"]["tag_generated_lead_state"]
    assert "The party enters the dungeon at the entrance." in payload["log"]


def test_resolved_generated_tag_scene_rejects_further_route_mutation(client) -> None:
    session_id = "tag-rumor-route-closeout-guard"
    manifest, _characters = _save_repeatable_tag_service_session(
        session_id,
        6,
        [("visitor", "wizard", 2, 0)],
    )
    _enter_repeatable_tag_service(client, session_id, manifest)
    done = client.post(
        f"/api/sessions/{session_id}/tag-repeatable-service",
        json={"action": "done"},
    )
    assert done.status_code == 200, done.text
    before = load_campaign(main.store)
    before_routes = list(before.tag_adventure_routes)
    before_tile_id = done.json()["session"]["map_state"]["current_tile_id"]

    blocked = client.post(
        f"/api/sessions/{session_id}/tag-route-action",
        json={"route_action": "final_route", "reference": "stale final route"},
    )

    assert blocked.status_code == 400
    assert "Continue" in blocked.json()["detail"]
    stored = main.store.get("sessions", session_id, SessionState.model_validate)
    assert stored is not None
    assert stored.map_state.current_tile_id == before_tile_id
    assert load_campaign(main.store).tag_adventure_routes == before_routes


def test_daroc_search_progress_persists_resolves_once_and_uses_shared_closeout(
    client,
    monkeypatch,
) -> None:
    session_id = "daroc-search-flow"
    manifest, searcher, recipient = _save_daroc_generated_session(session_id)
    entry_actions = manifest["source"]["parameters"]["tag_reference"]["room_prompts"][
        "tag-lead-entry"
    ]["actions"]
    investigate = next(action for action in entry_actions if action["label"] == "Investigate")

    entered = client.post(
        f"/api/sessions/{session_id}/tag-route-action",
        json={"route_action": "unlock_scene", "reference": investigate["reference"]},
    )

    assert entered.status_code == 200, entered.text
    entered_payload = entered.json()
    entered_session = entered_payload["session"]
    current_id = entered_session["map_state"]["current_tile_id"]
    current = next(tile for tile in entered_session["map_state"]["tiles"] if tile["id"] == current_id)
    assert current["content_key"] == "imported:tag-final-scene"
    assert entered_session["active_quest"]["completed"] is False
    assert entered_session["tag_generated_completion_pending"] is False
    assert entered_session["tag_daroc_familiar_state"]["available_clues"] == 0
    assert entered_session["tag_daroc_familiar_state"]["required_clues"] == 2
    assert not any(line == "Quest complete: objective location reached." for line in entered_session["log"])
    entered_rumor = next(
        state for state in entered_payload["campaign"]["tag_rumor_states"] if state["rumor_number"] == 9
    )
    assert entered_rumor["status"] == "investigating"

    bribes: list[int] = []
    bribe_values = iter([2, 4])
    streetwise_checks: list[tuple[int, list[int]]] = []
    check_values = iter([(3, [3]), (3, [3])])

    def roll_d6() -> int:
        value = next(bribe_values)
        bribes.append(value)
        return value

    def roll_streetwise(_level: int) -> tuple[int, list[int]]:
        result = next(check_values)
        streetwise_checks.append(result)
        return result

    monkeypatch.setattr("app.engine.tag_campaign.roll_d6", roll_d6)
    monkeypatch.setattr("app.engine.tag_campaign.roll_exploding_for_level", roll_streetwise)
    search_payload = {
        "action": "search",
        "character_id": searcher.id,
        "reward_recipient_id": recipient.id,
        "natural_one_consequence": "gold",
        "use_luck": False,
    }

    first_search = client.post(
        f"/api/sessions/{session_id}/tag-daroc-action",
        json=search_payload,
    )

    assert first_search.status_code == 200, first_search.text
    first_session = first_search.json()["session"]
    first_searcher = next(member for member in first_session["party"] if member["character_id"] == searcher.id)
    first_recipient = next(member for member in first_session["party"] if member["character_id"] == recipient.id)
    assert bribes == [2]
    assert streetwise_checks == [(3, [3])]
    assert first_searcher["gold"] == 48
    assert first_searcher["clues"] == 1
    assert TAG_TOWN_STREETWISE_CLUE in first_searcher["statuses"]
    assert first_recipient["gold"] == 10
    assert first_session["tag_daroc_familiar_state"]["available_clues"] == 1
    assert first_session["tag_daroc_familiar_state"]["resolved"] is False
    assert first_session["active_quest"]["completed"] is False
    assert first_session["tag_generated_completion_pending"] is False

    for _ in range(2):
        resumed = client.get(f"/api/sessions/{session_id}")
        assert resumed.status_code == 200
        resumed_session = resumed.json()
        assert resumed_session["tag_daroc_familiar_state"]["available_clues"] == 1
        assert resumed_session["active_quest"]["completed"] is False
    assert bribes == [2]
    assert streetwise_checks == [(3, [3])]

    resolved = client.post(
        f"/api/sessions/{session_id}/tag-daroc-action",
        json=search_payload,
    )

    assert resolved.status_code == 200, resolved.text
    resolved_payload = resolved.json()
    resolved_session = resolved_payload["session"]
    resolved_searcher = next(member for member in resolved_session["party"] if member["character_id"] == searcher.id)
    resolved_recipient = next(member for member in resolved_session["party"] if member["character_id"] == recipient.id)
    assert bribes == [2, 4]
    assert streetwise_checks == [(3, [3]), (3, [3])]
    assert resolved_searcher["gold"] == 44
    assert resolved_recipient["gold"] == 10 + DAROC_FAMILIAR_REWARD_GP
    assert resolved_session["xp_rolls_pending"] == 1
    assert resolved_session["active_quest"]["completed"] is True
    assert resolved_session["active_quest"]["tag_procedure_state"]["daroc_familiar"]["resolved"] is True
    assert resolved_session["tag_generated_completion_pending"] is True
    assert resolved_session["mode"] == "exploration"
    assert TAG_GENERATED_CLOSEOUT_ACTION_LABEL in "\n".join(resolved_session["log"])
    resolved_rumor = next(
        state for state in resolved_payload["campaign"]["tag_rumor_states"] if state["rumor_number"] == 9
    )
    assert resolved_rumor["status"] == "resolved"

    duplicate = client.post(
        f"/api/sessions/{session_id}/tag-daroc-action",
        json=search_payload,
    )

    assert duplicate.status_code == 400
    assert "already" in duplicate.json()["detail"].lower()
    assert bribes == [2, 4]
    assert streetwise_checks == [(3, [3]), (3, [3])]
    stored_after_duplicate = main.store.get("sessions", session_id, SessionState.model_validate)
    assert stored_after_duplicate is not None
    assert stored_after_duplicate.xp_rolls_pending == 1
    assert next(member for member in stored_after_duplicate.party if member.character_id == recipient.id).gold == (
        10 + DAROC_FAMILIAR_REWARD_GP
    )

    blocked_continue = client.post(f"/api/sessions/{session_id}/tag-generated-lead-continue")
    assert blocked_continue.status_code == 200
    assert blocked_continue.json()["mode"] == "exploration"
    assert blocked_continue.json()["tag_generated_completion_pending"] is True

    banked = client.post(
        f"/api/sessions/{session_id}/advance",
        json={"action": "bank_xp_roll", "character_id": recipient.id, "show_rolls": False},
    )
    assert banked.status_code == 200, banked.text
    banked_session = banked.json()
    banked_recipient = next(member for member in banked_session["party"] if member["character_id"] == recipient.id)
    assert banked_session["xp_rolls_pending"] == 0
    assert banked_recipient["xp"] == 1
    assert banked_session["tag_generated_completion_pending"] is True

    completed = client.post(f"/api/sessions/{session_id}/tag-generated-lead-continue")
    assert completed.status_code == 200, completed.text
    assert completed.json()["mode"] == "complete"
    assert completed.json()["tag_generated_completion_pending"] is False
    assert completed.json()["active_quest"]["tag_generated_lead_signoff"] is True
    completed_campaign = load_campaign(main.store)
    completed_rumor = next(state for state in completed_campaign.tag_rumor_states if state.rumor_number == 9)
    assert completed_rumor.status == "resolved"
    assert completed_campaign.adventures_completed == 1


def test_daroc_resume_corrects_stale_scene5_reward_log_without_touching_other_100gp_text(client) -> None:
    session_id = "daroc-narrative-resume"
    _manifest, _searcher, _recipient = _save_daroc_generated_session(session_id)
    session = main.store.get("sessions", session_id, SessionState.model_validate)
    assert session is not None
    stale_scene = (
        "To find the lost cat, you must find 2 Clues. "
        "Once you generate enough Clues, you find the cat and receive a reward of 100 gp and 1 XP roll."
    )
    unrelated_text = "An unrelated merchant offers a service for 100 gp."
    session.log.extend([stale_scene, unrelated_text])
    final_tile = next(
        tile
        for tile in session.map_state.tiles
        if str(tile.content_key or "").removeprefix("imported:") == "tag-final-scene"
    )
    final_tile.description = stale_scene
    main.store.save("sessions", session)

    resumed = client.get(f"/api/sessions/{session_id}")

    assert resumed.status_code == 200, resumed.text
    log = resumed.json()["log"]
    assert any("reward of 200 gp and 1 XP roll" in line for line in log)
    assert not any("reward of 100 gp and 1 XP roll" in line for line in log)
    assert unrelated_text in log
    resumed_final_tile = next(
        tile
        for tile in resumed.json()["map_state"]["tiles"]
        if str(tile.get("content_key") or "").removeprefix("imported:") == "tag-final-scene"
    )
    assert "reward of 200 gp and 1 XP roll" in resumed_final_tile["description"]
    assert "reward of 100 gp" not in resumed_final_tile["description"]
    persisted = main.store.get("sessions", session_id, SessionState.model_validate)
    assert persisted is not None
    assert persisted.log == log
    persisted_final_tile = next(
        tile
        for tile in persisted.map_state.tiles
        if str(tile.content_key or "").removeprefix("imported:") == "tag-final-scene"
    )
    assert persisted_final_tile.description == resumed_final_tile["description"]


def test_daroc_give_up_returns_rumor_to_heard_without_losing_found_clues(
    client,
    monkeypatch,
) -> None:
    session_id = "daroc-give-up"
    manifest, searcher, recipient = _save_daroc_generated_session(session_id)
    entry_actions = manifest["source"]["parameters"]["tag_reference"]["room_prompts"][
        "tag-lead-entry"
    ]["actions"]
    investigate = next(action for action in entry_actions if action["label"] == "Investigate")
    entered = client.post(
        f"/api/sessions/{session_id}/tag-route-action",
        json={"route_action": "unlock_scene", "reference": investigate["reference"]},
    )
    assert entered.status_code == 200, entered.text

    bribes = iter([2])
    monkeypatch.setattr("app.engine.tag_campaign.roll_d6", lambda: next(bribes))
    monkeypatch.setattr(
        "app.engine.tag_campaign.roll_exploding_for_level",
        lambda _level: (3, [3]),
    )
    searched = client.post(
        f"/api/sessions/{session_id}/tag-daroc-action",
        json={
            "action": "search",
            "character_id": searcher.id,
            "reward_recipient_id": recipient.id,
            "natural_one_consequence": "gold",
            "use_luck": False,
        },
    )
    assert searched.status_code == 200, searched.text
    assert searched.json()["session"]["tag_daroc_familiar_state"]["available_clues"] == 1

    gave_up = client.post(
        f"/api/sessions/{session_id}/tag-daroc-action",
        json={
            "action": "give_up",
            "character_id": searcher.id,
            "reward_recipient_id": recipient.id,
        },
    )

    assert gave_up.status_code == 200, gave_up.text
    payload = gave_up.json()
    session = payload["session"]
    saved_searcher = next(member for member in session["party"] if member["character_id"] == searcher.id)
    saved_recipient = next(member for member in session["party"] if member["character_id"] == recipient.id)
    assert session["active_quest"]["completed"] is True
    assert session["active_quest"]["tag_procedure_state"]["daroc_familiar"]["phase"] == "deferred"
    assert session["active_quest"]["tag_procedure_state"]["daroc_familiar"]["resolved"] is False
    assert session["tag_generated_completion_pending"] is True
    assert session["xp_rolls_pending"] == 0
    assert session["tag_daroc_familiar_state"]["available_clues"] == 1
    assert saved_searcher["gold"] == 48
    assert saved_searcher["clues"] == 1
    assert TAG_TOWN_STREETWISE_CLUE in saved_searcher["statuses"]
    assert saved_recipient["gold"] == 10
    assert TAG_GENERATED_CLOSEOUT_ACTION_LABEL in "\n".join(session["log"])
    rumor = next(state for state in payload["campaign"]["tag_rumor_states"] if state["rumor_number"] == 9)
    assert rumor["status"] == "heard"

    resumed = client.get(f"/api/sessions/{session_id}")
    assert resumed.status_code == 200
    resumed_searcher = next(
        member for member in resumed.json()["party"] if member["character_id"] == searcher.id
    )
    assert resumed.json()["tag_daroc_familiar_state"]["available_clues"] == 1
    assert resumed_searcher["clues"] == 1
    assert TAG_TOWN_STREETWISE_CLUE in resumed_searcher["statuses"]

    completed = client.post(f"/api/sessions/{session_id}/tag-generated-lead-continue")
    assert completed.status_code == 200, completed.text
    assert completed.json()["mode"] == "complete"
    roster_searcher = main.store.get("characters", searcher.id, Character.model_validate)
    assert roster_searcher is not None
    assert roster_searcher.clues == 1
    assert TAG_TOWN_STREETWISE_CLUE in roster_searcher.statuses
    assert roster_searcher.active_session_id is None
    completed_campaign = load_campaign(main.store)
    completed_rumor = next(state for state in completed_campaign.tag_rumor_states if state.rumor_number == 9)
    assert completed_rumor.status == "heard"


def test_medusa_quest_reaction_persists_choice_and_accepts_core_quest(client, monkeypatch) -> None:
    character = Character(
        id="quest-hero",
        name="Quest Hero",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=0,
        max_life=8,
        current_life=8,
        attack_bonus=3,
        defense_bonus=1,
        save_bonus=0,
        inventory=[],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    manifest, _entry = build_tag_adventure_manifest(default_campaign(), lead_type="rumor", detail="2")
    final_tile = TileState(
        id="quest-cabin",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Xasartha's Cabin",
        description="Xasartha waits.",
        content_key="imported:tag-final-scene",
    )
    session = base_session(
        id="medusa-quest-session",
        adventure_id=manifest["id"],
        adventure_type="imported",
        imported_manifest=manifest,
        map_state=MapState(tiles=[final_tile], current_tile_id="quest-cabin"),
        active_quest=ActiveQuestState(
            tile_id="quest-cabin",
            key="tag_generated_scene",
            description="Resolve Xasartha.",
            boss_target_name="Medusa",
        ),
        party=[
            PartyMemberState(
                character_id="quest-hero",
                name="Quest Hero",
                class_id="warrior",
                class_name="Warrior",
                level=3,
                xp=0,
                gold=0,
                current_life=8,
                max_life=8,
                attack_bonus=3,
                defense_bonus=1,
                save_bonus=0,
                inventory=[],
            )
        ],
    )
    main.store.save("characters", character)
    main.store.save("sessions", session)
    monkeypatch.setattr("app.engine.tag_campaign.roll_d6", lambda: 2)

    offered = client.post(
        "/api/sessions/medusa-quest-session/tag-branch-action",
        json={
            "branch_action": "medusa_reaction",
            "reference": "TAG p.25, Scene 1 Xasartha reaction",
        },
    )

    assert offered.status_code == 200
    offered_session = offered.json()["session"]
    assert offered_session["mode"] == "exploration"
    assert offered_session["active_quest"]["tag_procedure_state"]["medusa_scene1"]["phase"] == "quest_choice"
    assert any("Accept it and roll on the Quest Table" in line for line in offered_session["log"])
    assert not any(
        line.startswith("Adventures Guild procedure: Medusa reaction roll:")
        for line in offered_session["log"]
    )
    offered_model = main.store.get("sessions", "medusa-quest-session", SessionState.model_validate)
    assert offered_model is not None
    offered_model.log.append(
        "Adventures Guild procedure: Medusa reaction roll: TAG p.25. "
        "Xasartha reaction d6=2: quest branch."
    )
    main.store.save("sessions", offered_model)
    repaired = client.get("/api/sessions/medusa-quest-session")
    assert repaired.status_code == 200
    assert not any(
        line.startswith("Adventures Guild procedure: Medusa reaction roll:")
        for line in repaired.json()["log"]
    )
    offered_model = main.store.get("sessions", "medusa-quest-session", SessionState.model_validate)
    assert offered_model is not None
    refusal_model = offered_model.model_copy(deep=True)
    refusal_model.id = "medusa-quest-refusal-session"
    main.store.save("sessions", refusal_model)

    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)
    accepted = client.post(
        "/api/sessions/medusa-quest-session/tag-branch-action",
        json={
            "branch_action": "medusa_quest_accept",
            "reference": "TAG p.25 Scene 1; EE p.101 Quest reaction",
        },
    )

    assert accepted.status_code == 200
    accepted_session = accepted.json()["session"]
    assert accepted_session["mode"] == "exploration"
    assert accepted_session["active_quest"]["key"] == "bring_head"
    assert any("Complete it to claim the Epic Reward" in line for line in accepted_session["log"])
    assert accepted_session["map_state"]["tiles"][0]["enemies"] == []

    refused = client.post(
        "/api/sessions/medusa-quest-refusal-session/tag-branch-action",
        json={
            "branch_action": "medusa_quest_refuse",
            "reference": "TAG p.25 Scene 1; EE p.101 Quest reaction refused",
        },
    )

    assert refused.status_code == 200
    refused_session = refused.json()["session"]
    assert refused_session["tag_generated_completion_pending"] is True
    assert refused_session["active_quest"]["completed"] is True
    assert any("refuses Xasartha's Quest" in line for line in refused_session["log"])


def test_xasartha_bribe_amount_persists_and_accepts_exact_carried_gold(monkeypatch) -> None:
    from app.engine.tag_medusa import (
        initialize_medusa_reaction_state,
        medusa_scene1_state,
        pay_xasartha_gold_bribe,
    )

    session = base_session(
        active_quest=ActiveQuestState(
            tile_id="t",
            key="tag_generated_scene",
            description="Resolve Xasartha.",
        )
    )
    session.party[0].gold = 30
    rolls = iter([1, 2, 3, 4, 5, 6])
    monkeypatch.setattr("app.engine.tag_medusa.roll_d6", lambda: next(rolls))

    state = initialize_medusa_reaction_state(session, 1)

    assert state["bribe_gold"] == 21
    assert medusa_scene1_state(session)["bribe_gold"] == 21
    assert "21gp bribe" in pay_xasartha_gold_bribe(session)
    assert session.party[0].gold == 9
    assert medusa_scene1_state(session)["resolution"] == "gold_bribe"


def test_xasartha_gold_bribe_endpoint_closes_generated_rumor_and_syncs_roster(client) -> None:
    character = Character(
        id="bribe-hero",
        name="Bribe Hero",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=30,
        max_life=8,
        current_life=8,
        attack_bonus=3,
        defense_bonus=1,
        save_bonus=0,
        inventory=[],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    manifest, _entry = build_tag_adventure_manifest(default_campaign(), lead_type="rumor", detail="2")
    session = base_session(
        id="medusa-bribe-session",
        adventure_id=manifest["id"],
        adventure_type="imported",
        imported_manifest=manifest,
        active_quest=ActiveQuestState(
            tile_id="t",
            key="tag_generated_scene",
            description="Resolve Xasartha.",
            tag_procedure_state={
                "medusa_scene1": {
                    "phase": "bribe_choice",
                    "reaction_roll": 1,
                    "bribe_gold": 21,
                }
            },
        ),
        party=[
            PartyMemberState(
                character_id="bribe-hero",
                name="Bribe Hero",
                class_id="warrior",
                class_name="Warrior",
                level=3,
                xp=0,
                gold=30,
                current_life=8,
                max_life=8,
                attack_bonus=3,
                defense_bonus=1,
                save_bonus=0,
                inventory=[],
            )
        ],
    )
    main.store.save("characters", character)
    main.store.save("sessions", session)

    response = client.post(
        "/api/sessions/medusa-bribe-session/tag-branch-action",
        json={
            "branch_action": "medusa_bribe_gold",
            "reference": "TAG p.25 Scene 1 gold bribe",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["party"][0]["gold"] == 9
    assert payload["session"]["active_quest"]["completed"] is True
    assert payload["session"]["tag_generated_completion_pending"] is True
    roster = main.store.get("characters", "bribe-hero", Character.model_validate)
    assert roster is not None and roster.gold == 9


def test_xasartha_accepts_only_a_carried_gem_worth_at_least_fifteen_gp() -> None:
    from app.engine.tag_medusa import (
        initialize_medusa_reaction_state,
        pay_xasartha_gem_bribe,
    )

    session = base_session(
        active_quest=ActiveQuestState(
            tile_id="t",
            key="tag_generated_scene",
            description="Resolve Xasartha.",
        )
    )
    session.party[0].inventory = ["Gem (10gp)", "Small gemstone (25gp)"]
    initialize_medusa_reaction_state(session, 1)

    try:
        pay_xasartha_gem_bribe(
            session,
            character_id="h",
            item_name="Gem (10gp)",
        )
    except ValueError as exc:
        assert "at least 15gp" in str(exc)
    else:
        raise AssertionError("Xasartha accepted an ineligible gem.")

    result = pay_xasartha_gem_bribe(
        session,
        character_id="h",
        item_name="Small gemstone (25gp)",
    )

    assert "Small gemstone (25gp)" in result
    assert session.party[0].inventory == ["Gem (10gp)"]


def test_xasartha_defeat_stages_reward_once_and_pendant_recharges_luck(monkeypatch) -> None:
    from app.engine.class_abilities import luck_points_remaining, spend_luck_point
    from app.engine.rest import reset_between_foray_resources
    from app.engine.tag_medusa import (
        XASARTHA_PENDANT_ITEM,
        initialize_medusa_reaction_state,
        medusa_scene1_state,
        resolve_xasartha_reward,
        stage_xasartha_defeat_reward,
    )

    session = base_session(
        active_quest=ActiveQuestState(
            tile_id="t",
            key="tag_generated_scene",
            description="Resolve Xasartha.",
        )
    )
    initialize_medusa_reaction_state(session, 3)
    rolls = iter([4, 3])
    monkeypatch.setattr("app.engine.tag_medusa.roll_d6", lambda: next(rolls))
    defeated = [
        EnemyState(
            id="medusa",
            name="Medusa",
            category="boss",
            level=4,
            life=0,
            max_life=4,
            attacks=1,
        )
    ]

    narrative = stage_xasartha_defeat_reward(session, defeated)

    assert narrative is not None and "7 necros" in narrative
    assert stage_xasartha_defeat_reward(session, defeated) is None
    assert medusa_scene1_state(session)["phase"] == "reward_choice"
    result = resolve_xasartha_reward(session, character_id="h", wear_pendant=True)
    assert "1 rechargeable Luck point" in result
    assert XASARTHA_PENDANT_ITEM in session.party[0].inventory
    assert "Crate of necros (7)" in session.party[0].inventory
    assert luck_points_remaining(session, session.party[0]) == 1
    assert spend_luck_point(session, session.party[0]) is True
    assert luck_points_remaining(session, session.party[0]) == 0
    assert XASARTHA_PENDANT_ITEM in session.party[0].inventory
    reset_between_foray_resources(session)
    assert luck_points_remaining(session, session.party[0]) == 0
    next_adventure = base_session(
        party=[session.party[0].model_copy(deep=True)],
    )
    assert luck_points_remaining(next_adventure, next_adventure.party[0]) == 1


def test_xasartha_combat_completion_stages_persisted_reward_choice(monkeypatch) -> None:
    from app.engine.adventure_runtime import update_imported_quest_on_combat_end
    from app.engine.tag_medusa import initialize_medusa_reaction_state, medusa_scene1_state

    session = base_session(
        active_quest=ActiveQuestState(
            tile_id="t",
            key="tag_generated_scene",
            description="Resolve Xasartha.",
        )
    )
    initialize_medusa_reaction_state(session, 4)
    monkeypatch.setattr("app.engine.tag_medusa.roll_d6", lambda: 3)
    defeated = [
        EnemyState(
            id="medusa",
            name="Xasartha",
            category="boss",
            level=4,
            life=0,
            max_life=4,
            attacks=1,
        )
    ]

    update_imported_quest_on_combat_end(session, defeated, session.map_state.tiles[0])
    update_imported_quest_on_combat_end(session, defeated, session.map_state.tiles[0])

    assert medusa_scene1_state(session)["phase"] == "reward_choice"
    assert medusa_scene1_state(session)["necros"] == 6
    assert sum("Xasartha is defeated" in line for line in session.log) == 1


def test_xasartha_pendant_grants_two_extra_luck_points_to_halfling() -> None:
    from app.engine.class_abilities import luck_points_remaining
    from app.engine.tag_medusa import XASARTHA_PENDANT_ITEM

    session = base_session()
    member = session.party[0]
    member.class_id = "halfling"
    member.class_name = "Halfling"
    base_luck = luck_points_remaining(session, member)
    member.inventory.append(XASARTHA_PENDANT_ITEM)

    assert luck_points_remaining(session, member) == base_luck + 2


def test_xasartha_pendant_can_be_sold_untried_for_260gp(monkeypatch) -> None:
    from app.engine.tag_medusa import (
        initialize_medusa_reaction_state,
        resolve_xasartha_reward,
        stage_xasartha_defeat_reward,
    )

    session = base_session(
        active_quest=ActiveQuestState(
            tile_id="t",
            key="tag_generated_scene",
            description="Resolve Xasartha.",
        )
    )
    session.party[0].gold = 0
    initialize_medusa_reaction_state(session, 6)
    monkeypatch.setattr("app.engine.tag_medusa.roll_d6", lambda: 2)
    stage_xasartha_defeat_reward(
        session,
        [
            EnemyState(
                id="medusa",
                name="Medusa",
                category="boss",
                level=4,
                life=0,
                max_life=4,
                attacks=1,
            )
        ],
    )

    result = resolve_xasartha_reward(session, character_id="h", wear_pendant=False)

    assert "sells Xasartha's emerald pendant" in result
    assert session.party[0].gold == 260
    assert "Crate of necros (4)" in session.party[0].inventory


def test_xasartha_pendant_respects_barbarian_magic_item_restriction(monkeypatch) -> None:
    from app.engine.tag_medusa import (
        initialize_medusa_reaction_state,
        resolve_xasartha_reward,
        stage_xasartha_defeat_reward,
    )

    session = base_session(
        active_quest=ActiveQuestState(
            tile_id="t",
            key="tag_generated_scene",
            description="Resolve Xasartha.",
        )
    )
    session.party[0].class_id = "barbarian"
    session.party[0].class_name = "Barbarian"
    initialize_medusa_reaction_state(session, 3)
    monkeypatch.setattr("app.engine.tag_medusa.roll_d6", lambda: 2)
    stage_xasartha_defeat_reward(
        session,
        [
            EnemyState(
                id="medusa",
                name="Medusa",
                category="boss",
                level=4,
                life=0,
                max_life=4,
                attacks=1,
            )
        ],
    )

    try:
        resolve_xasartha_reward(session, character_id="h", wear_pendant=True)
    except ValueError as exc:
        assert "cannot use magic items" in str(exc)
    else:
        raise AssertionError("A barbarian wore Xasartha's magic pendant.")
    assert session.party[0].inventory == ["Potion of Healing"]


def test_medusa_scene10_group_stealth_persists_choice_and_stages_immediate_fight(client, monkeypatch) -> None:
    manifest, _entry = build_tag_adventure_manifest(default_campaign(), lead_type="rumor", detail="2")
    tag_reference = manifest["source"]["parameters"]["tag_reference"]
    tag_reference["room_prompts"]["tag-final-scene"] = {
        "title": "Scene choices",
        "body": (
            "As you come closer to the hunter's cabin, have all the characters perform a Stealth Save vs. L6. "
            "If at least one character fails, d3+2 agents of the guild of assassins will ambush the party."
        ),
        "actions": [
            {"label": "Once this encounter is over, you may reach the cabin by"},
            {"label": "decide to go back to town"},
        ],
    }
    tile = TileState(
        id="approach",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Approach to the Hunter's Cabin",
        description="The party approaches the cabin.",
        content_key="imported:tag-final-scene",
    )
    party = [
        PartyMemberState(
            character_id="rogue",
            name="Rogue",
            class_id="rogue",
            class_name="Rogue",
            level=3,
            xp=0,
            gold=0,
            current_life=6,
            max_life=6,
            attack_bonus=2,
            defense_bonus=1,
            save_bonus=0,
            inventory=[],
        ),
        PartyMemberState(
            character_id="warrior",
            name="Shielded Warrior",
            class_id="warrior",
            class_name="Warrior",
            level=4,
            xp=0,
            gold=0,
            current_life=9,
            max_life=9,
            attack_bonus=4,
            defense_bonus=2,
            save_bonus=0,
            inventory=["Shield", "Heavy Armor"],
        ),
    ]
    session = base_session(
        id="medusa-scene10-fight",
        adventure_id=manifest["id"],
        adventure_type="imported",
        imported_manifest=manifest,
        map_state=MapState(tiles=[tile], current_tile_id=tile.id),
        active_quest=ActiveQuestState(
            tile_id=tile.id,
            key="tag_lead",
            description="Reach Xasartha's cabin.",
        ),
        party=party,
    )
    main.store.save("sessions", session)
    monkeypatch.setattr("app.engine.tag_campaign.roll_exploding_d6", lambda: (3, [3]))
    monkeypatch.setattr("app.engine.tag_campaign.roll_d3", lambda: 2)

    approach = client.post(
        "/api/sessions/medusa-scene10-fight/tag-branch-action",
        json={"branch_action": "medusa_group_stealth", "reference": "Scene 10"},
    )

    assert approach.status_code == 200
    approach_session = approach.json()["session"]
    scene_state = approach_session["active_quest"]["tag_procedure_state"]["medusa_scene10"]
    assert scene_state["phase"] == "assassin_choice"
    assert scene_state["assassin_count"] == 4
    assert scene_state["modifier"] == -2
    assert scene_state["party_modifiers"] == [
        {"character_id": "rogue", "name": "Rogue", "modifier": 3},
        {"character_id": "warrior", "name": "Shielded Warrior", "modifier": -2},
    ]
    assert "one Stealth Save for the whole party" in scene_state["result"]
    assert "Party modifiers: Rogue +3, Shielded Warrior -2" in scene_state["result"]
    assert approach_session["mode"] == "exploration"

    monkeypatch.setattr("app.main.roll_formula", lambda _formula: 2)
    fight = client.post(
        "/api/sessions/medusa-scene10-fight/tag-branch-action",
        json={"branch_action": "medusa_assassin_fight", "reference": "Scene 10 immediate fight"},
    )

    assert fight.status_code == 200
    fight_session = fight.json()["session"]
    assert fight_session["mode"] == "combat"
    assert fight_session["party_attacked_immediately"] is True
    enemy = fight_session["map_state"]["tiles"][0]["enemies"][0]
    assert enemy["name"] == "Assassin agents"
    assert enemy["level"] == 6
    assert enemy["life"] == 4
    assert fight_session["map_state"]["tiles"][0]["treasure_gold"] == 8


def test_medusa_scene10_return_to_town_repairs_completed_route_and_opens_closeout(client) -> None:
    manifest, _entry = build_tag_adventure_manifest(default_campaign(), lead_type="rumor", detail="2")
    tile = TileState(
        id="approach",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Approach to the Hunter's Cabin",
        description="The party reaches the cabin.",
        content_key="imported:tag-final-scene",
    )
    session = base_session(
        id="medusa-scene10-town-return",
        adventure_id=manifest["id"],
        adventure_type="imported",
        imported_manifest=manifest,
        map_state=MapState(tiles=[tile], current_tile_id=tile.id),
        active_quest=ActiveQuestState(
            tile_id=tile.id,
            key="tag_generated_scene",
            description="Reach Xasartha's cabin.",
            completed=True,
            tag_procedure_state={
                "medusa_scene10": {
                    "completed": True,
                    "phase": "cabin_choice",
                }
            },
        ),
    )
    main.store.save("sessions", session)

    returned = client.post(
        "/api/sessions/medusa-scene10-town-return/tag-route-action",
        json={
            "route_action": "final_route",
            "reference": "Scene 10: return to town",
        },
    )

    assert returned.status_code == 200
    returned_session = returned.json()["session"]
    assert returned_session["mode"] == "exploration"
    assert returned_session["tag_generated_completion_pending"] is True
    assert returned_session["active_quest"]["tag_procedure_state"]["medusa_scene10"]["phase"] == "returned_to_town"
    assert "returns to town" in returned_session["tag_generated_completion_body"]

    completed = client.post(
        "/api/sessions/medusa-scene10-town-return/tag-generated-lead-continue"
    )

    assert completed.status_code == 200
    completed_session = completed.json()
    assert completed_session["mode"] == "complete"
    assert completed_session["tag_generated_completion_pending"] is False
    assert "Quest objective complete." in completed_session["summary"]


def test_medusa_scene10_failed_parley_gives_assassins_first_action(client, monkeypatch) -> None:
    manifest, _entry = build_tag_adventure_manifest(default_campaign(), lead_type="rumor", detail="2")
    tile = TileState(
        id="approach",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Approach",
        description="Approach",
        content_key="imported:tag-complication",
    )
    character = Character(
        id="speaker",
        name="Speaker",
        class_id="warrior",
        class_name="Warrior",
        level=2,
        xp=0,
        gold=0,
        max_life=6,
        current_life=6,
        attack_bonus=1,
        defense_bonus=1,
        save_bonus=0,
        inventory=[],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    session = base_session(
        id="medusa-scene10-parley",
        adventure_id=manifest["id"],
        adventure_type="imported",
        imported_manifest=manifest,
        map_state=MapState(tiles=[tile], current_tile_id=tile.id),
        active_quest=ActiveQuestState(
            tile_id=tile.id,
            key="tag_lead",
            description="Reach Xasartha's cabin.",
            tag_procedure_state={
                "medusa_scene10": {
                    "completed": True,
                    "phase": "assassin_choice",
                    "assassin_count": 3,
                }
            },
        ),
        party=[
            PartyMemberState(
                character_id="speaker",
                name="Speaker",
                class_id="warrior",
                class_name="Warrior",
                level=2,
                xp=0,
                gold=0,
                current_life=6,
                max_life=6,
                attack_bonus=1,
                defense_bonus=1,
                save_bonus=0,
                inventory=[],
            )
        ],
    )
    main.store.save("characters", character)
    main.store.save("sessions", session)
    monkeypatch.setattr("app.engine.tag_campaign.roll_exploding_for_level", lambda _level: (2, [2]))
    monkeypatch.setattr("app.main.roll_formula", lambda _formula: 1)

    response = client.post(
        "/api/sessions/medusa-scene10-parley/tag-branch-action",
        json={
            "character_id": "speaker",
            "branch_action": "medusa_assassin_parley",
            "reference": "Scene 10 parley",
        },
    )

    assert response.status_code == 200
    payload = response.json()["session"]
    assert payload["mode"] == "combat"
    assert payload["party_surprised"] is True
    assert payload["map_state"]["tiles"][0]["enemies"][0]["life"] == 3


def test_enchanted_weapon_reward_marks_adventure_status(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    session.active_quest = ActiveQuestState(tile_id="t", key="peaceful_way", description="Peace", completed=True)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 3)

    eng.advance(session, "claim_quest_reward", show_rolls=False)
    assert session.active_quest is None
    assert "Enchanted weapon" in session.party[0].statuses
    assert any("weapon is enchanted until adventure end" in entry for entry in session.log)


def test_arrow_of_slaying_deals_three_damage_to_major_foe() -> None:
    eng = engine()
    boss = EnemyState(id="b", name="Ogre", category="boss", level=5, life=4, max_life=6)
    session = base_session(
        mode="combat",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
                inventory=["Bow", "Arrow of Slaying (target: Ogre)"],
                default_missile_weapon="Bow",
            )
        ],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R", enemies=[boss])],
            current_tile_id="t",
        ),
    )

    eng.advance(session, "use_arrow_of_slaying", character_id="h", attack_targets={"h": "b"}, show_rolls=False)

    assert boss.life == 1
    assert boss.level == 4
    assert session.party[0].inventory == ["Bow"]
    assert any("3 automatic damage" in entry for entry in session.log)


def test_arrow_of_slaying_requires_major_foe() -> None:
    eng = engine()
    goblin = EnemyState(id="g", name="Goblin", category="minions", level=3, life=1, max_life=1)
    session = base_session(
        mode="combat",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
                inventory=["Bow", "Arrow of Slaying (target: Ogre)"],
                default_missile_weapon="Bow",
            )
        ],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R", enemies=[goblin])],
            current_tile_id="t",
        ),
    )

    eng.advance(session, "use_arrow_of_slaying", character_id="h", attack_targets={"h": "g"}, show_rolls=False)

    assert goblin.life == 1
    assert "Arrow of Slaying (target: Ogre)" in session.party[0].inventory
    assert any("must target a living Major Foe" in entry for entry in session.log)


def test_arrow_of_slaying_requires_bow_and_designed_target() -> None:
    eng = engine()
    boss = EnemyState(id="b", name="Ogre", category="boss", level=5, life=4, max_life=6)
    session = base_session(
        mode="combat",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
                inventory=["Arrow of Slaying (target: Ogre)"],
            )
        ],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R", enemies=[boss])],
            current_tile_id="t",
        ),
    )

    eng.advance(session, "use_arrow_of_slaying", character_id="h", attack_targets={"h": "b"}, show_rolls=False)
    assert boss.life == 4
    assert any("only by a PC with a bow" in entry for entry in session.log)


def test_arrow_of_slaying_rejects_wrong_designed_target() -> None:
    eng = engine()
    boss = EnemyState(id="b", name="Troll", category="boss", level=5, life=4, max_life=6)
    session = base_session(
        mode="combat",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
                inventory=["Bow", "Arrow of Slaying (target: Ogre)"],
                default_missile_weapon="Bow",
            )
        ],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R", enemies=[boss])],
            current_tile_id="t",
        ),
    )

    eng.advance(session, "use_arrow_of_slaying", character_id="h", attack_targets={"h": "b"}, show_rolls=False)
    assert boss.life == 4
    assert "Arrow of Slaying (target: Ogre)" in session.party[0].inventory
    assert any("was made for Ogre" in entry for entry in session.log)


def test_arrow_of_slaying_reward_rolls_target(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    session.active_quest = ActiveQuestState(tile_id="t", key="peaceful_way", description="Peace", completed=True)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 5)
    monkeypatch.setattr(eng, "_roll_epic_major_foe_target_name", lambda _session: "Manticore")

    eng.advance(session, "claim_quest_reward", show_rolls=False)

    assert "Arrow of Slaying (target: Manticore)" in session.party[0].inventory
    assert any("Arrow of Slaying target rolled: Manticore" in entry for entry in session.log)


def test_major_foe_table_keys_include_all_environments_and_fiendish() -> None:
    monsters = engine().rules.monsters()
    keys = major_foe_table_keys(monsters)
    assert set(keys) == {
        "weird",
        "boss",
        "caverns_weird",
        "caverns_boss",
        "fungal_grottoes_weird",
        "fungal_grottoes_boss",
        "fiendish_foes_weird",
        "fiendish_foes_boss",
        "tag_weird",
        "tag_boss",
        "fd_weird",
        "fd_boss",
        "fd_horde",
    }


def test_arrow_of_slaying_picks_table_then_foe_pdf_p163() -> None:
    eng = engine()
    session = base_session()
    fiendish_boss = next(
        row for row in eng.rules.monsters()["fiendish_foes_boss"] if row["name"] == "Young Red Dragon"
    )
    with patch("app.engine.random_dungeon.random.choice", side_effect=["fiendish_foes_boss", fiendish_boss]):
        target = eng._roll_epic_major_foe_target_name(session)
    assert target == "Young Red Dragon"
    assert any("Major Foe table" in line and "fiendish_foes_boss" in line for line in session.log)


def test_use_potion_heals_to_full() -> None:
    eng = engine()
    session = base_session()
    session.party[0].current_life = 1
    eng.advance(session, "use_potion", character_id="h")
    assert session.party[0].current_life == 3
    assert "h" in session.potion_used_character_ids
    assert "Potion of Healing" not in session.party[0].inventory


def test_use_potion_only_consumes_one_of_many() -> None:
    eng = engine()
    session = base_session()
    session.party[0].current_life = 1
    session.party[0].inventory = ["Potion of Healing", "Potion of Healing", "Potion of Healing"]
    eng.advance(session, "use_potion", character_id="h", item_name="Potion of Healing")
    assert session.party[0].current_life == 3
    assert session.party[0].inventory.count("Potion of Healing") == 2
    assert "h" in session.potion_used_character_ids


def test_use_potion_of_sleep_in_combat(monkeypatch) -> None:
    eng = engine()
    foe = EnemyState(id="g1", name="Goblin", category="minions", level=3, life=1, max_life=1)
    session = base_session(
        mode="combat",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
                inventory=["Potion of Sleep"],
            )
        ],
        map_state=MapState(
            tiles=[
                TileState(
                    id="t",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="R",
                    description="R",
                    enemies=[foe],
                )
            ],
            current_tile_id="t",
        ),
    )
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    monkeypatch.setattr("app.engine.spells.roll_d6", lambda: 6)
    eng.advance(session, "use_potion", character_id="h", item_name="Potion of Sleep")
    assert session.mode == "exploration"
    assert "Potion of Sleep" not in session.party[0].inventory
    assert any("quaffs" in entry for entry in session.log)


def test_barbarian_cannot_drink_potion() -> None:
    eng = engine()
    session = base_session()
    session.party[0].class_id = "barbarian"
    session.party[0].class_name = "Barbarian"
    session.party[0].current_life = 1
    eng.advance(session, "use_potion", character_id="h")
    assert session.party[0].current_life == 1
    assert "Potion of Healing" in session.party[0].inventory
    assert "h" not in session.potion_used_character_ids
    assert any("cannot use potions" in entry for entry in session.log)


def test_stale_combat_clears_when_no_foes() -> None:
    eng = engine()
    session = base_session(mode="combat", reaction_pending=True)
    eng.advance(session, "rest")
    assert session.mode == "exploration"
    assert any("No active foes remain" in entry for entry in session.log)


def test_final_boss_grants_extra_xp(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    boss = EnemyState(
        id="b",
        name="Dragon",
        category="boss",
        level=6,
        life=0,
        max_life=8,
        tags=["final_boss"],
    )
    eng._award_encounter_xp(session, [boss], show_rolls=False)
    assert session.xp_rolls_pending == 2
    assert session.final_boss_defeated is True


def test_mark_final_boss_on_high_roll(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    tile = session.map_state.tiles[0]
    tile.enemies = [
        EnemyState(id="b", name="Ogre", category="boss", level=5, life=5, max_life=5),
    ]
    monkeypatch.setattr("app.engine.experience.roll_d6", lambda: 6)
    eng._begin_combat(session, "Fight!", show_rolls=False)
    assert any("Final Boss check" in line for line in session.log)
    assert any("final_boss" in enemy.tags for enemy in tile.enemies)
    assert tile.final_boss_treasure is True
    assert session.final_boss_designated is True


def test_final_boss_no_treasure_foe_gets_minimum_bounty() -> None:
    eng = engine()
    session = base_session(mode="exploration")
    tile = session.map_state.tiles[0]
    tile.resolved = True
    tile.final_boss_treasure = True
    tile.defeated_enemies = [
        EnemyState(
            id="s1",
            name="Green Slime",
            category="weird",
            level=7,
            life=0,
            max_life=8,
            tags=["final_boss", "weird"],
        ),
    ]
    eng._award_treasure(session, tile, show_rolls=True)
    assert tile.treasure_gold == 100
    assert tile.treasure_claimed is False
    assert any("Final Boss bounty" in line for line in session.log)


def test_wandering_major_cannot_become_final_boss(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    tile = session.map_state.tiles[0]
    monkeypatch.setattr("app.engine.experience.roll_d6", lambda: 6)
    monkeypatch.setattr(
        eng,
        "_roll_wandering_enemies",
        lambda _session, _category, _hcl: [
            EnemyState(id="b", name="Ogre", category="boss", level=5, life=5, max_life=5),
        ],
    )
    eng._spawn_wandering_monsters(session, tile, show_rolls=True)
    assert session.major_foes_encountered == 1
    assert not any("final_boss" in enemy.tags for enemy in tile.enemies)
    assert not tile.final_boss_treasure
    assert not session.final_boss_designated
    assert not any("Final Boss check" in line for line in session.log)
    assert tile.enemies[0].life == 5
    assert tile.enemies[0].attacks == 1


def test_second_major_foe_skips_final_boss_check(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    tile = session.map_state.tiles[0]
    tile.enemies = [
        EnemyState(id="b1", name="Dragon", category="boss", level=5, life=5, max_life=5),
    ]
    monkeypatch.setattr("app.engine.experience.roll_d6", lambda: 6)
    eng._begin_combat(session, "First major!", show_rolls=False)
    assert session.final_boss_designated is True

    tile.enemies = [
        EnemyState(id="b2", name="Iron Eater", category="weird", level=4, life=4, max_life=4),
    ]
    log_before = len(session.log)
    eng._begin_combat(session, "Second major!", show_rolls=True)
    new_log = session.log[log_before:]
    assert not any("Final Boss check" in line for line in new_log)
    assert not any("final_boss" in enemy.tags for enemy in tile.enemies)
    assert tile.enemies[0].name == "Iron Eater"


def test_peaceful_quest_progress() -> None:
    eng = engine()
    session = base_session()
    session.active_quest = ActiveQuestState(
        tile_id="t",
        key="peaceful_way",
        description="Peace",
        peaceful_required=3,
    )
    eng._record_peaceful_quest_progress(session)
    assert session.active_quest.peaceful_count == 1


def test_peaceful_quest_completion_logs_summary_milestone() -> None:
    eng = engine()
    session = base_session()
    session.active_quest = ActiveQuestState(
        tile_id="t",
        key="peaceful_way",
        description="Peace",
        peaceful_required=1,
    )
    eng._record_peaceful_quest_progress(session)
    assert session.active_quest.completed is True
    assert any("Quest objective complete: peaceful encounters finished" in entry for entry in session.log)


def test_bring_alive_quest_completes_on_subdued_boss() -> None:
    eng = engine()
    session = base_session()
    session.active_quest = ActiveQuestState(
        tile_id="t",
        key="bring_alive",
        description="Capture",
        boss_capture_pending=True,
    )
    boss = EnemyState(
        id="b",
        name="Ogre",
        category="boss",
        level=5,
        life=0,
        max_life=6,
        subdued=True,
    )
    eng._update_quest_on_combat_end(session, [boss], show_rolls=False)
    assert session.active_quest.completed is True
    assert session.active_quest.captured_boss_name == "Ogre"
    assert session.active_quest.boss_capture_pending is False
    assert any("Quest objective complete: return to the Quest-giver with the living captive." in entry for entry in session.log)


def test_bring_item_quest_logs_completion_once(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    session.active_quest = ActiveQuestState(
        tile_id="t",
        key="bring_item",
        description="Find item",
        item_name="Moon Key",
    )
    rolls = iter([1])
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: next(rolls))
    defeated = [
        EnemyState(id="w1", name="Manticore", category="weird", level=4, life=0, max_life=4),
        EnemyState(id="w2", name="Troll", category="weird", level=4, life=0, max_life=4),
    ]
    eng._update_quest_on_combat_end(session, defeated, show_rolls=True)
    assert session.active_quest.item_collected is True
    assert sum(1 for entry in session.log if "Quest objective complete: return to the Quest-giver with the item." in entry) == 1


def test_bring_alive_quest_logs_when_boss_is_slain_instead() -> None:
    eng = engine()
    session = base_session()
    session.active_quest = ActiveQuestState(
        tile_id="t",
        key="bring_alive",
        description="Capture",
        boss_capture_pending=True,
    )
    boss = EnemyState(
        id="b",
        name="Ogre",
        category="boss",
        level=5,
        life=0,
        max_life=6,
        subdued=False,
    )
    eng._update_quest_on_combat_end(session, [boss], show_rolls=False)
    assert session.active_quest.completed is False
    assert session.active_quest.boss_capture_pending is True
    assert any("was slain, not subdued" in entry for entry in session.log)


def test_bring_head_not_complete_when_boss_subdued() -> None:
    eng = engine()
    session = base_session()
    session.active_quest = ActiveQuestState(
        tile_id="t",
        key="bring_head",
        description="Slay",
        boss_slay_pending=True,
    )
    boss = EnemyState(
        id="b",
        name="Ogre",
        category="boss",
        level=5,
        life=0,
        max_life=6,
        subdued=True,
    )
    eng._update_quest_on_combat_end(session, [boss], show_rolls=False)
    assert session.active_quest.completed is False
    assert session.active_quest.boss_slay_pending is True
    assert any("was subdued, not slain" in entry for entry in session.log)


def test_bring_head_requires_selected_boss_head_and_return_to_giver(monkeypatch) -> None:
    eng = engine()
    giver = TileState(
        id="giver",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Quest Giver",
        description="Quest Giver",
    )
    away = TileState(
        id="away",
        x=1,
        y=0,
        tile_key="12",
        tile_type="room",
        title="Away",
        description="Away",
    )
    session = base_session(
        map_state=MapState(tiles=[giver, away], current_tile_id="away"),
        active_quest=ActiveQuestState(
            tile_id="giver",
            key="bring_head",
            description="Bring me its head!",
            boss_slay_pending=True,
            boss_target_name="Ogre",
        ),
    )

    wrong_boss = EnemyState(id="b1", name="Troll", category="boss", level=5, life=0, max_life=6)
    eng._update_quest_on_combat_end(session, [wrong_boss], show_rolls=False)
    assert session.active_quest.boss_slay_pending is True
    assert session.active_quest.boss_head_acquired is False

    target_boss = EnemyState(id="b2", name="Ogre", category="boss", level=5, life=0, max_life=6)
    eng._update_quest_on_combat_end(session, [target_boss], show_rolls=False)
    assert session.active_quest.boss_slay_pending is False
    assert session.active_quest.boss_head_acquired is True
    assert session.active_quest.completed is False

    eng._claim_quest_reward(session, show_rolls=False)
    assert session.active_quest is not None
    assert any("Return to the Quest-giver's tile with the Boss head." in entry for entry in session.log)

    session.map_state.current_tile_id = "giver"
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 2)
    eng._claim_quest_reward(session, show_rolls=False)
    assert session.active_quest is None
    assert any("Quest complete! Epic reward" in entry for entry in session.log)


def test_bring_alive_reward_requires_return_to_giver() -> None:
    eng = engine()
    giver = TileState(
        id="giver",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Quest Giver",
        description="Quest Giver",
    )
    away = TileState(
        id="away",
        x=1,
        y=0,
        tile_key="12",
        tile_type="room",
        title="Away",
        description="Away",
    )
    session = base_session(
        map_state=MapState(tiles=[giver, away], current_tile_id="away"),
        active_quest=ActiveQuestState(
            tile_id="giver",
            key="bring_alive",
            description="I want it alive!",
            boss_capture_pending=False,
            captured_boss_name="Ogre",
            completed=True,
        ),
    )
    eng._claim_quest_reward(session, show_rolls=False)
    assert session.active_quest is not None
    assert any("Return to the Quest-giver's tile with the living captive." in entry for entry in session.log)
