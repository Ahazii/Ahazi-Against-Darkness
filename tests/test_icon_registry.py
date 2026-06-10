from __future__ import annotations

from pathlib import Path

from app.main import _icons_payload


ASSETS_DIR = Path("assets")


def test_icon_registry_ids_are_unique_and_all_files_exist() -> None:
    icons = [icon.model_dump() for icon in _icons_payload()]
    ids = [icon["id"] for icon in icons]
    assert len(ids) == len(set(ids))

    missing_file_fields = [icon["id"] for icon in icons if not icon.get("file")]
    assert not missing_file_fields, f"Icons missing file assignments: {', '.join(missing_file_fields)}"

    missing_assets = [
        f"{icon['id']} -> {icon['file']}"
        for icon in icons
        if not (ASSETS_DIR / icon["file"]).is_file()
    ]
    assert not missing_assets, f"Icon files missing from assets/: {', '.join(missing_assets)}"


def test_game_icons_assets_have_license_metadata() -> None:
    icons = [icon.model_dump() for icon in _icons_payload()]
    game_icons = [icon for icon in icons if str(icon.get("file", "")).startswith("icons/user/game-icons/")]
    assert game_icons
    missing_metadata = [
        icon["id"]
        for icon in game_icons
        if icon.get("license") != "CC BY 3.0"
        or "game-icons.net" not in icon.get("source_url", "")
        or "game-icons.net" not in icon.get("attribution", "")
    ]
    assert not missing_metadata, f"Game-icons rows missing attribution/license metadata: {', '.join(missing_metadata)}"
