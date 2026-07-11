from __future__ import annotations

import pytest

from app.engine.content_registry import CONTENT_REGISTRY_VERSION, resolve_content_registry
from app.engine.states import resolve_state_registry


def test_resolved_content_registry_separates_runtime_and_review_only_supplements() -> None:
    context = resolve_content_registry(
        None,
        None,
        ["forsaken-depths", "imported-adventures"],
    )

    assert context.registry_version == CONTENT_REGISTRY_VERSION
    assert context.active_supplement_ids == (
        "expanded-edition-core",
        "forsaken-depths",
        "imported-adventures",
    )
    assert context.runtime_supplement_ids == ("expanded-edition-core", "forsaken-depths")
    assert context.review_only_supplement_ids == ("imported-adventures",)
    assert context.capability_providers["room_tiles"] == ("expanded-edition-core", "forsaken-depths")
    assert context.provides("terrain_types") is True
    assert context.legacy_mappings["ruleset"] == ("ee", "forsaken_depths")
    assert context.state_provider_ids == ("expanded-edition-core", "forsaken-depths")
    assert "protection" in context.active_state_ids
    assert "fd-psychic-residue-save" in context.active_state_ids
    assert "dark-plague" not in context.active_state_ids
    assert context.payload()["state_registry_version"] == 1
    assert "review-only" in context.diagnostics[0]


def test_resolved_content_registry_rejects_unknown_supplements() -> None:
    with pytest.raises(ValueError, match="Unknown supplement id"):
        resolve_content_registry(None, None, ["missing-supplement"])


def test_state_registry_scopes_definitions_to_the_locked_supplement_snapshot() -> None:
    catalog = resolve_state_registry(["expanded-edition-core", "four-against-the-abyss"])

    assert catalog.provider_ids == ("four-against-the-abyss", "expanded-edition-core")
    assert "dark-plague" in catalog.state_ids
    assert "protection" in catalog.state_ids
    assert "fd-my-fingers-are-worms" in catalog.excluded_state_ids
    assert {definition["id"] for definition in catalog.definitions()} == set(catalog.state_ids)
