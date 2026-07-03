from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MEDIA_EXTENSIONS = {
    ".avif",
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".svg",
    ".webp",
}

ALLOWED_LEGACY_RULES_ART = {
    Path("assets/rules_art/local/expanded_dungeon_tables.png"),
    Path("assets/rules_art/local/tag_guild_workflow.png"),
    Path("assets/rules_art/local/tag_settlement_services.png"),
}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_assets_route_prefers_data_dir_and_does_not_use_static_mount() -> None:
    main_py = read("src/app/main.py")
    config_py = read("src/app/config.py")
    entrypoint = read("entrypoint.sh")
    requirements = read("requirements.txt")

    assert 'app.mount("/assets"' not in main_py
    assert "def _resolve_asset_file" in main_py
    assert "(settings.user_assets_dir, \"user\")," in main_py
    assert "(settings.packaged_assets_dir, \"bundled\")," in main_py
    assert '@app.get("/assets/{asset_path:path}")' in main_py
    assert "FileResponse(resolved)" in main_py

    assert 'user_assets_dir = data_dir / "assets"' in config_py
    assert 'packaged_assets_dir = root_dir / "assets"' in config_py
    assert "_seed_user_asset_folders(settings)" in config_py
    assert "_seed_user_narrative_override_template(settings)" in config_py
    assert '"tag_scene_narrative_overrides.json"' in config_py
    assert '@app.post("/api/rules/upload-pdf")' in main_py
    assert '@app.post("/api/rules/extract-tag-narrative")' in main_py
    assert '@app.post("/api/sessions/{session_id}/tag-route-action")' in main_py
    assert "settings.rules_dir" in main_py
    assert "cryptography" in requirements

    assert 'ASSETS_DIR="${DATA_DIR}/assets"' in entrypoint
    assert 'mkdir -p "${ASSETS_DIR}/artwork/user"' in entrypoint
    assert 'mkdir -p "${ASSETS_DIR}/Application Artwork"' in entrypoint
    assert 'mkdir -p "${ASSETS_DIR}/icons/user"' in entrypoint
    assert 'mkdir -p "${ASSETS_DIR}/tiles/user"' in entrypoint
    assert 'mkdir -p "${ASSETS_DIR}/rules_art/local"' in entrypoint


def test_user_facing_asset_guidance_points_to_data_dir_assets() -> None:
    checked_files = [
        "README.md",
        "docs/ARCHITECTURE.md",
        "docs/CONTENT_PIPELINE.md",
        "docs/ROADMAP.md",
        "docs/STATUS.md",
        "data/rules/rulebook_reference.json",
        "src/app/static/icon-editor.html",
        "src/app/static/icon-editor.js",
        "src/app/static/modern-pages.js",
        "tools/extract_rules_artwork.py",
    ]
    combined = "\n".join(read(path) for path in checked_files)

    for required in [
        "DATA_DIR/assets",
        "DATA_DIR/assets/icons/user",
        "DATA_DIR/assets/artwork/user",
        "DATA_DIR/assets/Application Artwork",
        "DATA_DIR/assets/rules_art/local",
    ]:
        assert required in combined

    forbidden_guidance = [
        "Put downloaded files in assets/icons/user",
        "populate assets/rules_art/local",
        "generated image goes to assets/rules_art/local",
        "Manual artwork placeholders live under `assets/artwork/user/`",
        "User-downloaded files should go under\n`assets/icons/user/`",
    ]
    for phrase in forbidden_guidance:
        assert phrase not in combined


def test_user_artwork_templates_do_not_gain_committed_media() -> None:
    user_art_root = ROOT / "assets" / "artwork" / "user"
    committed_media = [
        path.relative_to(ROOT)
        for path in user_art_root.rglob("*")
        if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS
    ]
    assert committed_media == []


def test_application_artwork_templates_do_not_gain_committed_media() -> None:
    app_art_root = ROOT / "assets" / "Application Artwork"
    assert app_art_root.exists()
    committed_media = [
        path.relative_to(ROOT)
        for path in app_art_root.rglob("*")
        if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS
    ]
    assert committed_media == []
    assert (app_art_root / "troupe_management_1600x900_REPLACE_WITH_GIF.txt").exists()
    assert (app_art_root / "camp_screen_2400x1000_REPLACE_WITH_GIF.txt").exists()


def test_local_rules_art_committed_media_is_explicitly_allowlisted() -> None:
    rules_art_root = ROOT / "assets" / "rules_art" / "local"
    committed_media = {
        path.relative_to(ROOT)
        for path in rules_art_root.rglob("*")
        if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS
    }
    assert committed_media == ALLOWED_LEGACY_RULES_ART


def test_artwork_extractor_writes_to_data_dir_assets_only() -> None:
    extractor = read("tools/extract_rules_artwork.py")
    assert 'data_dir() / "assets" / asset_path' in extractor
    assert 'ROOT / "assets" / asset_path' not in extractor
    assert "DATA_DIR/assets/rules_art/local" in extractor
