from __future__ import annotations

import pytest

from app.engine.content_registry import CONTENT_REGISTRY_VERSION, resolve_content_registry


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
    assert "review-only" in context.diagnostics[0]


def test_resolved_content_registry_rejects_unknown_supplements() -> None:
    with pytest.raises(ValueError, match="Unknown supplement id"):
        resolve_content_registry(None, None, ["missing-supplement"])
