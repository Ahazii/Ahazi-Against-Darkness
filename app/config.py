from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import logging


@dataclass(frozen=True)
class AppConfig:
    data_dir: Path
    tiles_dir: Path
    host: str
    port: int


def load_config() -> AppConfig:
    root_dir = Path(__file__).resolve().parent.parent
    data_dir = Path(os.getenv("DATA_DIR", "data"))
    if not data_dir.is_absolute():
        data_dir = (root_dir / data_dir).resolve()

    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        test_file = data_dir / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
    except (PermissionError, OSError) as exc:
        fallback_dir = Path("/tmp/4ad-data")
        fallback_dir.mkdir(parents=True, exist_ok=True)
        logging.warning(
            "Data dir %s is not writable (%s). Falling back to %s.",
            data_dir,
            exc,
            fallback_dir,
        )
        data_dir = fallback_dir

    tiles_dir = data_dir / "tiles"
    tiles_dir.mkdir(parents=True, exist_ok=True)

    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))

    return AppConfig(
        data_dir=data_dir,
        tiles_dir=tiles_dir,
        host=host,
        port=port,
    )
