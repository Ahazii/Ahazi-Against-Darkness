from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    data_dir: Path
    db_path: Path
    rules_dir: Path
    packaged_rules_dir: Path
    adventures_dir: Path
    installed_adventures_dir: Path
    assets_dir: Path
    packaged_assets_dir: Path
    user_assets_dir: Path
    static_dir: Path
    host: str
    port: int


def load_settings() -> Settings:
    root_dir = Path(__file__).resolve().parents[2]
    data_dir = Path(os.getenv("DATA_DIR", ".data"))
    if not data_dir.is_absolute():
        data_dir = (root_dir / data_dir).resolve()

    rules_dir = data_dir / "rules"
    packaged_assets_dir = root_dir / "assets"
    user_assets_dir = data_dir / "assets"
    settings = Settings(
        root_dir=root_dir,
        data_dir=data_dir,
        db_path=data_dir / "game.db",
        rules_dir=rules_dir,
        packaged_rules_dir=root_dir / "data" / "rules",
        adventures_dir=root_dir / "Adventures",
        installed_adventures_dir=data_dir / "Adventures",
        assets_dir=user_assets_dir,
        packaged_assets_dir=packaged_assets_dir,
        user_assets_dir=user_assets_dir,
        static_dir=Path(__file__).resolve().parent / "static",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
    )
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.rules_dir.mkdir(parents=True, exist_ok=True)
    settings.installed_adventures_dir.mkdir(parents=True, exist_ok=True)
    settings.user_assets_dir.mkdir(parents=True, exist_ok=True)
    _seed_user_asset_folders(settings)
    return settings


def _copy_tree_without_overwrite(source: Path, target: Path) -> None:
    if not source.exists():
        return
    for item in source.rglob("*"):
        relative = item.relative_to(source)
        destination = target / relative
        if item.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(item, destination)


def _seed_user_asset_folders(settings: Settings) -> None:
    """Create user-facing asset folders beside game.db without overwriting edits."""
    for relative in [
        "artwork/user",
        "icons/user",
        "tiles/user",
        "adventures",
        "rules_art/local",
    ]:
        (settings.user_assets_dir / relative).mkdir(parents=True, exist_ok=True)
    _copy_tree_without_overwrite(
        settings.packaged_assets_dir / "artwork" / "user",
        settings.user_assets_dir / "artwork" / "user",
    )
    icon_readme = settings.packaged_assets_dir / "icons" / "user" / "README.md"
    target_icon_readme = settings.user_assets_dir / "icons" / "user" / "README.md"
    if icon_readme.exists() and not target_icon_readme.exists():
        shutil.copy2(icon_readme, target_icon_readme)
