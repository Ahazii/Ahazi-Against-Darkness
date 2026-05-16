from __future__ import annotations

import os
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
    assets_dir: Path
    static_dir: Path
    host: str
    port: int


def load_settings() -> Settings:
    root_dir = Path(__file__).resolve().parents[2]
    data_dir = Path(os.getenv("DATA_DIR", ".data"))
    if not data_dir.is_absolute():
        data_dir = (root_dir / data_dir).resolve()

    rules_dir = data_dir / "rules"
    settings = Settings(
        root_dir=root_dir,
        data_dir=data_dir,
        db_path=data_dir / "game.db",
        rules_dir=rules_dir,
        packaged_rules_dir=root_dir / "data" / "rules",
        adventures_dir=root_dir / "Adventures",
        assets_dir=root_dir / "assets",
        static_dir=Path(__file__).resolve().parent / "static",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
    )
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.rules_dir.mkdir(parents=True, exist_ok=True)
    return settings
