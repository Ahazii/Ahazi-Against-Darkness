from __future__ import annotations

import io
import json
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..schemas import AdventureDescriptor
from .adventure_manifest import ManifestValidationResult, validate_adventure_manifest
from .tag_compat import upgrade_tag_manifest

ADVENTURE_MANIFEST_FILENAME = "adventure.json"
ADVENTURE_META_FILENAME = "adventure.meta.json"
SKIP_BUNDLED_DIRS = frozenset({"examples", "schema"})
RESERVED_ADVENTURE_IDS = frozenset({"random", "ai-adventure"})


@dataclass(frozen=True)
class RemoveAdventureResult:
    removed: bool
    adventure_id: str
    error: str | None = None
    bundled_still_available: bool = False


def bundled_adventures_dir(root_dir: Path) -> Path:
    """Shipped modules in the application image (read-only defaults)."""
    return root_dir / "data" / "adventures"


def installed_adventures_dir(data_dir: Path) -> Path:
    """User-installed modules live beside game.db (DATA_DIR/Adventures)."""
    return data_dir / "Adventures"


def installed_adventure_dir(data_dir: Path, adventure_id: str) -> Path:
    return installed_adventures_dir(data_dir) / adventure_id


def installed_manifest_path(data_dir: Path, adventure_id: str) -> Path:
    return installed_adventure_dir(data_dir, adventure_id) / ADVENTURE_MANIFEST_FILENAME


def bundled_manifest_path(root_dir: Path, adventure_id: str) -> Path:
    return bundled_adventures_dir(root_dir) / adventure_id / ADVENTURE_MANIFEST_FILENAME


def is_user_installed(data_dir: Path, adventure_id: str) -> bool:
    return installed_manifest_path(data_dir, adventure_id).is_file()


def remove_installed_adventure(root_dir: Path, data_dir: Path, adventure_id: str) -> RemoveAdventureResult:
    """Delete a module from DATA_DIR/Adventures. Shipped bundles under data/adventures/ are untouched."""
    if adventure_id in RESERVED_ADVENTURE_IDS:
        return RemoveAdventureResult(False, adventure_id, error="That adventure cannot be removed.")
    if not is_user_installed(data_dir, adventure_id):
        return RemoveAdventureResult(
            False,
            adventure_id,
            error="Adventure is not installed in your data folder (nothing to remove).",
        )
    shutil.rmtree(installed_adventure_dir(data_dir, adventure_id))
    bundled_still_available = bundled_manifest_path(root_dir, adventure_id).is_file()
    return RemoveAdventureResult(
        True,
        adventure_id,
        bundled_still_available=bundled_still_available,
    )


def resolve_manifest_path(root_dir: Path, data_dir: Path, adventure_id: str) -> Path | None:
    user_path = installed_manifest_path(data_dir, adventure_id)
    if user_path.exists():
        return user_path
    bundled_path = bundled_manifest_path(root_dir, adventure_id)
    if bundled_path.exists():
        return bundled_path
    return None


def seed_bundled_adventures(root_dir: Path, data_dir: Path) -> None:
    """Copy shipped adventures into DATA_DIR/Adventures when not already installed."""
    bundled = bundled_adventures_dir(root_dir)
    if not bundled.exists():
        return
    target_base = installed_adventures_dir(data_dir)
    target_base.mkdir(parents=True, exist_ok=True)
    for child in sorted(bundled.iterdir()):
        if not child.is_dir() or child.name in SKIP_BUNDLED_DIRS:
            continue
        if not (child / ADVENTURE_MANIFEST_FILENAME).exists():
            continue
        dest = target_base / child.name
        if dest.exists():
            continue
        shutil.copytree(child, dest)


def load_installed_manifest(root_dir: Path, data_dir: Path, adventure_id: str) -> dict[str, Any]:
    path = resolve_manifest_path(root_dir, data_dir, adventure_id)
    if path is None:
        raise FileNotFoundError(f"Adventure manifest not found: {adventure_id}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Adventure manifest must be a JSON object.")
    return upgrade_tag_manifest(payload)


def build_adventure_export_zip(root_dir: Path, data_dir: Path, adventure_id: str) -> bytes:
    path = resolve_manifest_path(root_dir, data_dir, adventure_id)
    if path is None:
        raise FileNotFoundError(f"Adventure manifest not found: {adventure_id}")
    adventure_dir = path.parent
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(path, ADVENTURE_MANIFEST_FILENAME)
        meta_path = adventure_dir / ADVENTURE_META_FILENAME
        if meta_path.is_file():
            archive.write(meta_path, ADVENTURE_META_FILENAME)
        assets_dir = adventure_dir / "assets"
        if assets_dir.is_dir():
            for asset in sorted(assets_dir.rglob("*")):
                if asset.is_file():
                    archive.write(asset, str(Path("assets") / asset.relative_to(assets_dir)))
    return buffer.getvalue()


def _iter_adventure_dirs(base: Path) -> list[Path]:
    if not base.exists():
        return []
    return [
        child
        for child in sorted(base.iterdir())
        if child.is_dir() and child.name not in SKIP_BUNDLED_DIRS and (child / ADVENTURE_MANIFEST_FILENAME).exists()
    ]


def list_installed_adventure_ids(root_dir: Path, data_dir: Path) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for base in (installed_adventures_dir(data_dir), bundled_adventures_dir(root_dir)):
        for child in _iter_adventure_dirs(base):
            if child.name in seen:
                continue
            seen.add(child.name)
            ids.append(child.name)
    return ids


def list_installed_adventures(root_dir: Path, data_dir: Path) -> list[AdventureDescriptor]:
    adventures: list[AdventureDescriptor] = []
    for adventure_id in list_installed_adventure_ids(root_dir, data_dir):
        try:
            manifest = load_installed_manifest(root_dir, data_dir, adventure_id)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        adventures.append(
            AdventureDescriptor(
                id=adventure_id,
                name=str(manifest.get("title") or adventure_id),
                source=str(manifest.get("source", {}).get("type", "imported")),
                playable=True,
                notes=str(manifest.get("synopsis") or "Imported adventure module."),
                removable=is_user_installed(data_dir, adventure_id),
                tag_lead_type=str(
                    manifest.get("source", {})
                    .get("parameters", {})
                    .get("lead_type", "")
                ),
                tag_lead_detail=str(
                    manifest.get("source", {})
                    .get("parameters", {})
                    .get("lead_detail", "")
                ),
                tag_scene=str(
                    manifest.get("source", {})
                    .get("parameters", {})
                    .get("tag_reference", {})
                    .get("scene", "")
                ),
                tag_pdf_pages=str(
                    manifest.get("source", {})
                    .get("parameters", {})
                    .get("tag_reference", {})
                    .get("pdf_pages", "")
                ),
                tag_status="generated_tag" if manifest.get("source", {}).get("parameters", {}).get("tag_reference") else "",
                tag_prompt_count=len(
                    manifest.get("source", {})
                    .get("parameters", {})
                    .get("tag_reference", {})
                    .get("room_prompts", {})
                ),
            )
        )
    return adventures


def import_adventure_manifest(
    root_dir: Path,
    data_dir: Path,
    data: dict[str, Any],
    *,
    rules_repo,
    overwrite: bool = False,
) -> tuple[Path | None, ManifestValidationResult]:
    _ = root_dir  # reserved for future bundled merge rules
    result = validate_adventure_manifest(data, rules_repo=rules_repo)
    if not result.valid:
        return None, result

    adventure_id = str(data["id"])
    target_dir = installed_adventure_dir(data_dir, adventure_id)
    target_path = target_dir / ADVENTURE_MANIFEST_FILENAME
    if target_dir.exists() and not overwrite and target_path.exists():
        result = ManifestValidationResult(
            valid=False,
            errors=[f"Adventure {adventure_id!r} is already installed. Import again with overwrite enabled."],
            warnings=result.warnings,
            warning_summary=result.warning_summary,
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
