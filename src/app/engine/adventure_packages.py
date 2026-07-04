from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .adventure_pdf_sources import adventure_pdf_source_dirs, load_adventure_pdf_assessments


PACKAGE_DIRNAME = "Adventure Packages"
PACKAGE_FILENAME = "package.json"
MAP_ASSET_ROOT = Path("adventures")
ALLOWED_PROCEDURE_OPS = {
    "roll_table",
    "spawn_foes",
    "test_save",
    "grant_gold",
    "grant_item",
    "set_tracker",
    "advance_tracker",
    "branch_if",
    "transition_to_node",
    "complete_objective",
    "pin_location",
    "show_choice",
}


def _slug(value: str, fallback: str = "adventure-package") -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return clean or fallback


def adventure_package_root(data_dir: Path) -> Path:
    path = data_dir / PACKAGE_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def adventure_package_path(data_dir: Path, package_id: str) -> Path:
    safe_id = _slug(package_id)
    return adventure_package_root(data_dir) / safe_id / PACKAGE_FILENAME


def adventure_package_asset_dir(data_dir: Path, package_id: str) -> Path:
    path = data_dir / "assets" / MAP_ASSET_ROOT / _slug(package_id) / "maps"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _relative_source_path(root_dir: Path, data_dir: Path, path: Path) -> str:
    for base in (data_dir, root_dir):
        try:
            return str(path.relative_to(base)).replace("\\", "/")
        except ValueError:
            continue
    return str(path)


def _package_source_pdf(root_dir: Path, data_dir: Path, pdf_path: Path, assessment: dict[str, Any]) -> str:
    cached = str(assessment.get("source_path") or "")
    if cached:
        cached_path = Path(cached)
        if cached_path.is_absolute():
            return _relative_source_path(root_dir, data_dir, cached_path)
        return cached.replace("\\", "/")
    return _relative_source_path(root_dir, data_dir, pdf_path)


def _find_pdf_source(root_dir: Path, data_dir: Path, pdf_id: str) -> tuple[Path, dict[str, Any]]:
    assessments = load_adventure_pdf_assessments(data_dir)
    candidates: list[tuple[Path, dict[str, Any]]] = []
    for source_kind, directory in adventure_pdf_source_dirs(root_dir, data_dir):
        if not directory.exists():
            continue
        for pdf in sorted(directory.glob("*.pdf")):
            key = f"{source_kind}:{pdf.name}"
            assessment = dict(assessments.get(key, {}))
            source_id = str(assessment.get("id") or _slug(pdf.stem if source_kind == "legacy" else f"{pdf.stem}-pdf"))
            assessment.setdefault("id", source_id)
            assessment.setdefault("title", pdf.stem.replace("-", " ").replace("_", " ").title())
            assessment.setdefault("source_kind", source_kind)
            assessment.setdefault("source_path", _relative_source_path(root_dir, data_dir, pdf))
            candidates.append((pdf, assessment))
    for pdf, assessment in candidates:
        if str(assessment.get("id")) == pdf_id:
            return pdf, assessment
    raise FileNotFoundError(f"PDF source {pdf_id} was not found. Scan new PDFs first.")


def load_adventure_package(data_dir: Path, package_id: str) -> dict[str, Any] | None:
    path = adventure_package_path(data_dir, package_id)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def save_adventure_package(data_dir: Path, package: dict[str, Any]) -> Path:
    package_id = _slug(str(package.get("package_id") or "adventure-package"))
    package["package_id"] = package_id
    path = adventure_package_path(data_dir, package_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    return path


def _asset_url_path(package_id: str, filename: str) -> str:
    return str(MAP_ASSET_ROOT / _slug(package_id) / "maps" / filename).replace("\\", "/")


def _extract_pdf_map_images(pdf_path: Path, data_dir: Path, package_id: str, *, max_pages: int = 12) -> list[dict[str, Any]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency is present in app image/tests
        raise RuntimeError("pypdf is required to extract PDF map images.") from exc

    asset_dir = adventure_package_asset_dir(data_dir, package_id)
    reader = PdfReader(str(pdf_path))
    maps: list[dict[str, Any]] = []
    for page_index, page in enumerate(reader.pages[: min(max_pages, len(reader.pages))], start=1):
        page_text = (page.extract_text() or "").lower()
        likely_map_page = "map" in page_text or "numbered locations" in page_text or "numbered hexes" in page_text
        try:
            images = list(page.images)
        except Exception:  # noqa: BLE001 - image extraction support varies by PDF
            images = []
        if not images:
            continue
        for image_index, image in enumerate(images, start=1):
            image_name = Path(str(getattr(image, "name", "") or f"image-{image_index}.bin")).name
            extension = Path(image_name).suffix.lower() or ".bin"
            filename = f"page-{page_index:03d}-image-{image_index:02d}{extension}"
            output = asset_dir / filename
            data = getattr(image, "data", b"")
            if not isinstance(data, bytes) or not data:
                continue
            output.write_bytes(data)
            maps.append(
                {
                    "id": f"map-page-{page_index:03d}-image-{image_index:02d}",
                    "title": f"Page {page_index} image {image_index}{' - likely map' if likely_map_page else ''}",
                    "source_pdf": str(pdf_path.name),
                    "source_page": page_index,
                    "asset_path": _asset_url_path(package_id, filename),
                    "coordinate_system": "percent",
                    "pins": [],
                    "extraction_note": "Extracted embedded PDF image. Review against the source PDF before pinning rooms.",
                }
            )
    return maps


def _manual_map_slot(package_id: str, pdf_path: Path, source_page: int = 0) -> dict[str, Any]:
    filename = "manual-map-review-slot_1600x900.png"
    return {
        "id": "manual-map-review-slot",
        "title": "Manual map review slot",
        "source_pdf": pdf_path.name,
        "source_page": source_page,
        "asset_path": _asset_url_path(package_id, filename),
        "coordinate_system": "percent",
        "pins": [],
        "extraction_note": "No embedded map image was extracted. Put a map image at this DATA_DIR/assets path, then add pins.",
    }


def _write_manual_map_readme(data_dir: Path, package_id: str, pdf_path: Path) -> None:
    asset_dir = adventure_package_asset_dir(data_dir, package_id)
    readme = asset_dir / "manual-map-review-slot_1600x900.README.txt"
    if readme.exists():
        return
    readme.write_text(
        "\n".join(
            [
                "Manual map review slot",
                "",
                f"Source PDF: {pdf_path.name}",
                "Expected image filename: manual-map-review-slot_1600x900.png",
                "Recommended size: 1600x900 pixels, or another stable 16:9 crop.",
                "Use Adventure Management -> Modules -> Adventure Package Review to pin rooms, scenes, hexes, or locations.",
                "Keep private-use PDF-derived images local unless publishing rights are secured.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def create_or_refresh_package_from_pdf(
    root_dir: Path,
    data_dir: Path,
    pdf_id: str,
    *,
    extract_maps: bool = True,
) -> dict[str, Any]:
    pdf_path, assessment = _find_pdf_source(root_dir, data_dir, pdf_id)
    package_id = _slug(str(assessment.get("id") or pdf_path.stem))
    existing = load_adventure_package(data_dir, package_id) or {}
    existing_maps = {str(item.get("id")): item for item in existing.get("maps", []) if isinstance(item, dict)}
    maps: list[dict[str, Any]] = []
    extraction_warnings: list[str] = []
    if extract_maps:
        try:
            maps = _extract_pdf_map_images(pdf_path, data_dir, package_id)
        except Exception as exc:  # noqa: BLE001 - extraction failure should still leave a package to edit
            extraction_warnings.append(f"Map image extraction failed: {type(exc).__name__}: {exc}")
    if not maps:
        _write_manual_map_readme(data_dir, package_id, pdf_path)
        maps = [_manual_map_slot(package_id, pdf_path)]
    for item in maps:
        old = existing_maps.get(str(item.get("id")))
        if old and old.get("pins"):
            item["pins"] = old["pins"]
    package = {
        "schema_version": 1,
        "package_id": package_id,
        "title": str(assessment.get("title") or pdf_path.stem.replace("-", " ").replace("_", " ").title()),
        "source": {
            "type": "pdf",
            "source_pdf": _package_source_pdf(root_dir, data_dir, pdf_path, assessment),
            "source_pages": [],
            "license_note": "Local/private-use package derived from a user-owned PDF. Check publishing rights before sharing.",
        },
        "adventure_manifest_id": str(existing.get("adventure_manifest_id") or ""),
        "capabilities": _package_capabilities(assessment, maps),
        "foes": existing.get("foes", []),
        "classes": existing.get("classes", []),
        "items": existing.get("items", []),
        "tables": existing.get("tables", []),
        "trackers": existing.get("trackers", []),
        "procedures": _sanitize_procedures(existing.get("procedures", [])),
        "maps": maps,
        "review": {
            "status": "draft_review_needed",
            "pdf_assessment_id": package_id,
            "package_recommendation": str(assessment.get("package_recommendation") or ""),
            "warnings": [str(item) for item in assessment.get("warnings", []) if item] + extraction_warnings,
        },
    }
    save_adventure_package(data_dir, package)
    return package_summary(data_dir, package)


def _package_capabilities(assessment: dict[str, Any], maps: list[dict[str, Any]]) -> list[str]:
    capabilities = set()
    if maps:
        capabilities.update({"maps", "pins"})
    if int(assessment.get("table_signals") or 0):
        capabilities.add("tables")
    if int(assessment.get("foe_signals") or 0):
        capabilities.add("foes")
    if int(assessment.get("class_signals") or 0):
        capabilities.add("classes")
    return sorted(capabilities)


def _sanitize_procedures(procedures: Any) -> list[dict[str, Any]]:
    clean: list[dict[str, Any]] = []
    if not isinstance(procedures, list):
        return clean
    for procedure in procedures:
        if not isinstance(procedure, dict):
            continue
        steps = []
        for step in procedure.get("steps", []):
            if isinstance(step, dict) and step.get("op") in ALLOWED_PROCEDURE_OPS:
                steps.append(step)
        copy = dict(procedure)
        copy["steps"] = steps
        clean.append(copy)
    return clean


def list_adventure_packages(data_dir: Path) -> list[dict[str, Any]]:
    packages: list[dict[str, Any]] = []
    root = adventure_package_root(data_dir)
    for path in sorted(root.glob(f"*/{PACKAGE_FILENAME}")):
        package = load_adventure_package(data_dir, path.parent.name)
        if package:
            packages.append(package_summary(data_dir, package))
    return packages


def package_summary(data_dir: Path, package: dict[str, Any]) -> dict[str, Any]:
    maps = [item for item in package.get("maps", []) if isinstance(item, dict)]
    pins = sum(len(item.get("pins", [])) for item in maps)
    enriched_maps = []
    for item in maps:
        copy = dict(item)
        asset_path = str(copy.get("asset_path") or "")
        copy["asset_exists"] = bool(asset_path and (data_dir / "assets" / asset_path).is_file())
        enriched_maps.append(copy)
    return {
        "package_id": str(package.get("package_id") or ""),
        "title": str(package.get("title") or ""),
        "source": package.get("source") or {},
        "capabilities": package.get("capabilities") or [],
        "review": package.get("review") or {},
        "map_count": len(maps),
        "pin_count": pins,
        "maps": enriched_maps,
        "foe_count": len(package.get("foes", []) or []),
        "class_count": len(package.get("classes", []) or []),
        "item_count": len(package.get("items", []) or []),
        "table_count": len(package.get("tables", []) or []),
        "tracker_count": len(package.get("trackers", []) or []),
        "procedure_count": len(package.get("procedures", []) or []),
        "package_path": str(adventure_package_path(data_dir, str(package.get("package_id") or ""))),
    }


def upsert_map_pin(data_dir: Path, package_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    package = load_adventure_package(data_dir, package_id)
    if not package:
        raise FileNotFoundError(f"Adventure package {package_id} was not found.")
    map_id = str(payload.get("map_id") or "")
    if not map_id:
        raise ValueError("map_id is required.")
    maps = package.get("maps", [])
    target = next((item for item in maps if isinstance(item, dict) and item.get("id") == map_id), None)
    if target is None:
        raise ValueError(f"Map {map_id} was not found in package {package_id}.")
    label = str(payload.get("label") or "").strip()
    node_id = str(payload.get("node_id") or label or "").strip()
    if not label or not node_id:
        raise ValueError("Pin label and node id are required.")
    pin_id = _slug(str(payload.get("id") or node_id or label), "pin")
    pin = {
        "id": pin_id,
        "label": label[:40],
        "node_id": node_id[:80],
        "x": _bounded_float(payload.get("x"), 0.0, 100.0),
        "y": _bounded_float(payload.get("y"), 0.0, 100.0),
        "width": _bounded_float(payload.get("width", 0), 0.0, 100.0),
        "height": _bounded_float(payload.get("height", 0), 0.0, 100.0),
        "shape": str(payload.get("shape") or "point") if str(payload.get("shape") or "point") in {"point", "rect", "circle", "polygon"} else "point",
    }
    pins = [item for item in target.get("pins", []) if isinstance(item, dict) and item.get("id") != pin_id]
    pins.append(pin)
    target["pins"] = pins
    save_adventure_package(data_dir, package)
    return package_summary(data_dir, package)


def delete_map_pin(data_dir: Path, package_id: str, map_id: str, pin_id: str) -> dict[str, Any]:
    package = load_adventure_package(data_dir, package_id)
    if not package:
        raise FileNotFoundError(f"Adventure package {package_id} was not found.")
    target = next((item for item in package.get("maps", []) if isinstance(item, dict) and item.get("id") == map_id), None)
    if target is None:
        raise ValueError(f"Map {map_id} was not found in package {package_id}.")
    target["pins"] = [item for item in target.get("pins", []) if isinstance(item, dict) and item.get("id") != pin_id]
    save_adventure_package(data_dir, package)
    return package_summary(data_dir, package)


def _bounded_float(value: Any, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = minimum
    return round(max(minimum, min(maximum, number)), 2)
