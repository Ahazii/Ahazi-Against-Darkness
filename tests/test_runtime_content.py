from __future__ import annotations

from fastapi.testclient import TestClient


def test_runtime_content_endpoint_exposes_read_only_abyss_content_and_modules(client: TestClient) -> None:
    response = client.get("/api/supplements/runtime/four-against-the-abyss")
    assert response.status_code == 200
    payload = response.json()
    assert payload["read_only"] is True
    assert payload["manifest"]["title"] == "Four Against the Abyss"
    assert any(item["id"] == "abyss_room_content_table" for item in payload["content"]["tables"])
    assert any(item["id"] == "abyss_vermin_table" for item in payload["content"]["foe_groups"])
    assert any(item["id"] == "dark-plague" for item in payload["content"]["states"])
    assert any(item["path"].endswith("abyss_campaign.py") for item in payload["runtime_modules"])


def test_runtime_content_endpoint_exposes_structured_core_classes_items_and_tiles(client: TestClient) -> None:
    response = client.get("/api/supplements/runtime/expanded-edition-core")
    assert response.status_code == 200
    payload = response.json()
    assert any(item["id"] == "warrior" for item in payload["content"]["classes"])
    assert payload["content"]["items"]
    assert payload["content"]["tiles"]


def test_runtime_module_source_is_allowlisted_per_supplement(client: TestClient) -> None:
    payload = client.get("/api/supplements/runtime/four-against-the-abyss").json()
    module_id = next(item["id"] for item in payload["runtime_modules"] if item["path"].endswith("abyss_items.py"))
    source = client.get(f"/api/supplements/runtime/four-against-the-abyss/modules/{module_id}")
    assert source.status_code == 200
    assert "def " in source.json()["source"]
    assert client.get("/api/supplements/runtime/four-against-the-abyss/modules/engine-combat-py").status_code == 404


def test_modern_and_legacy_html_cache_bust_static_assets_with_the_current_build(client: TestClient) -> None:
    version = client.get("/api/app/version").json()["version"]
    modern = client.get("/modern").text
    legacy = client.get("/legacy").text

    assert f"/static/modern-pages.js?v={version}" in modern
    assert f"/static/styles.css?v={version}" in modern
    assert f"/static/styles.css?v={version}" in legacy
