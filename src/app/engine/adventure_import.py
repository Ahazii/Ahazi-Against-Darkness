from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ..schemas import AdventureDescriptor
from .adventure_manifest import ManifestValidationResult, validate_adventure_manifest

ADVENTURE_MANIFEST_FILENAME = "adventure.json"
ADVENTURE_META_FILENAME = "adventure.meta.json"


def packaged_adventures_dir(root_dir: Path) -> Path:
    return root_dir / "data" / "adventures"


def installed_adventure_dir(root_dir: Path, adventure_id: str) -> Path:
    return packaged_adventures_dir(root_dir) / adventure_id


def installed_manifest_path(root_dir: Path, adventure_id: str) -> Path:
    return installed_adventure_dir(root_dir, adventure_id) / ADVENTURE_MANIFEST_FILENAME


def load_installed_manifest(root_dir: Path, adventure_id: str) -> dict[str, Any]:
    path = installed_manifest_path(root_dir, adventure_id)
    if not path.exists():
        raise FileNotFoundError(f"Adventure manifest not found: {adventure_id}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Adventure manifest must be a JSON object.")
    return payload


def list_installed_adventure_ids(root_dir: Path) -> list[str]:
    base = packaged_adventures_dir(root_dir)
    if not base.exists():
        return []
    ids: list[str] = []
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        if child.name in {"examples", "schema"}:
            continue
        if (child / ADVENTURE_MANIFEST_FILENAME).exists():
            ids.append(child.name)
    return ids


def list_installed_adventures(root_dir: Path) -> list[AdventureDescriptor]:
    adventures: list[AdventureDescriptor] = []
    for adventure_id in list_installed_adventure_ids(root_dir):
        try:
            manifest = load_installed_manifest(root_dir, adventure_id)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        adventures.append(
            AdventureDescriptor(
                id=adventure_id,
                name=str(manifest.get("title") or adventure_id),
                source=str(manifest.get("source", {}).get("type", "imported")),
                playable=True,
                notes=str(manifest.get("synopsis") or "Imported adventure module."),
            )
        )
    return adventures


def import_adventure_manifest(
    root_dir: Path,
    data: dict[str, Any],
    *,
    rules_repo,
    overwrite: bool = False,
) -> tuple[Path | None, ManifestValidationResult]:
    result = validate_adventure_manifest(data, rules_repo=rules_repo)
    if not result.valid:
        return None, result

    adventure_id = str(data["id"])
    target_dir = installed_adventure_dir(root_dir, adventure_id)
    target_path = target_dir / ADVENTURE_MANIFEST_FILENAME
    if target_dir.exists() and not overwrite and target_path.exists():
        result = ManifestValidationResult(
            valid=False,
            errors=[f"Adventure {adventure_id!r} is already installed. Import again with overwrite enabled."],
            warnings=result.warnings,
        )
        return None, result

    if target_dir.exists() and overwrite:
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    meta_path = target_dir / ADVENTURE_META_FILENAME
    meta_path.write_text(
        json.dumps({"imported": True, "schema_version": data.get("schema_version", 1)}, indent=2) + "\n",
        encoding="utf-8",
    )
    return target_path, result
