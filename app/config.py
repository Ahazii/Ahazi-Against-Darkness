from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class AppConfig:
    data_dir: Path
    host: str
    port: int


def load_config() -> AppConfig:
    root_dir = Path(__file__).resolve().parent.parent
    data_dir = Path(os.getenv("DATA_DIR", "data"))
    if not data_dir.is_absolute():
        data_dir = (root_dir / data_dir).resolve()

    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))

    return AppConfig(
        data_dir=data_dir,
        host=host,
        port=port,
    )
