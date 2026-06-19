from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.engine.adventure_prompt import build_adventure_prompt, validate_prompt_parameters
from app.rules.repository import RulesRepository
from app.schemas import AdventurePromptParameters

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data" / "rules"


@pytest.fixture
def repo() -> RulesRepository:
    return RulesRepository(RULES, RULES / "_override")


def test_build_prompt_includes_theme_and_allowlists(repo: RulesRepository) -> None:
    params = AdventurePromptParameters(
        theme="goblin warren",
        boss_type="Young Dragon",
        party_level_min=1,
        party_level_max=3,
    )
    prompt = build_adventure_prompt(params, repo=repo)
    assert "goblin warren" in prompt
    assert "ALLOWLISTS" in prompt
    assert "monster_spawn_names" in prompt
    assert "EXAMPLE MODULE" in prompt
    assert "Return ONLY one valid JSON object" in prompt
    assert "COMMON MISTAKES" in prompt
    assert "AUTHORING CHECKLIST" in prompt
    assert "tile_key" in prompt
    assert "min_rooms" in prompt
    assert 'quest.complete_when.boss_name is exactly "Young Dragon"' in prompt
    assert "Do not wrap individual rooms in code blocks" in prompt


def test_build_prompt_rejects_invented_boss_in_parameters(repo: RulesRepository) -> None:
    params = AdventurePromptParameters(theme="test", boss_type="Chaos Champion")
    with pytest.raises(ValueError, match="boss_type"):
        build_adventure_prompt(params, repo=repo)


def test_rejects_unknown_boss(repo: RulesRepository) -> None:
    params = AdventurePromptParameters(theme="test", boss_type="Not A Boss")
    errors = validate_prompt_parameters(params, repo=repo)
    assert errors


def test_api_defaults(client: TestClient) -> None:
    response = client.get("/api/adventures/ai/defaults")
    assert response.status_code == 200
    payload = response.json()
    assert payload["parameters"]["theme"]
    assert payload["boss_options"]
    assert "Wraith" in payload["boss_options"] or payload["boss_options"]


def test_api_prompt(client: TestClient) -> None:
    defaults = client.get("/api/adventures/ai/defaults").json()
    boss = defaults["boss_options"][0]
    response = client.post(
        "/api/adventures/ai/prompt",
        json={
            "theme": "crypt test",
            "difficulty": "standard",
            "length": "short",
            "style": "grim",
            "environment": "dungeon",
            "boss_type": boss,
            "party_level_min": 2,
            "party_level_max": 4,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "crypt test" in body["prompt"]
    assert body["room_count_hint"] == "6–8 rooms"


def test_list_adventures_includes_ai_mode(client: TestClient) -> None:
    adventures = client.get("/api/adventures").json()
    ai = next(item for item in adventures if item["id"] == "ai-adventure")
    assert ai["playable"] is False
    assert "prompt" in ai["notes"].lower()


def test_create_session_rejects_ai_adventure_mode(client: TestClient) -> None:
    parties = client.get("/api/parties").json()
    if not parties:
        pytest.skip("no parties")
    response = client.post(
        "/api/sessions",
        json={"party_id": parties[0]["id"], "adventure_id": "ai-adventure"},
    )
    assert response.status_code == 400
    assert "prompt" in response.json()["detail"].lower()
