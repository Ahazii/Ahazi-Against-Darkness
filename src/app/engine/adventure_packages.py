from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from .adventure_pdf_sources import adventure_pdf_source_dirs, load_adventure_pdf_assessments


PACKAGE_FILENAME = "package.json"
LEGACY_PACKAGE_DIRNAME = "Adventure Packages"
LEGACY_MAP_ASSET_ROOT = Path("adventures")
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
PACKAGE_CAPABILITIES = {"foes", "classes", "items", "tables", "trackers", "procedures", "maps", "pins"}
NODE_TYPES = {"room", "scene", "location", "hex", "camp", "settlement", "ending"}
NODE_REVIEW_STATUSES = {"draft", "checked", "needs_pdf_check", "ready_for_manifest"}


def _slug(value: str, fallback: str = "adventure-package") -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return clean or fallback


def adventure_package_root(data_dir: Path) -> Path:
    path = data_dir / "Adventures"
    path.mkdir(parents=True, exist_ok=True)
    return path


def adventure_folder(data_dir: Path, package_id: str) -> Path:
    path = adventure_package_root(data_dir) / _slug(package_id)
    path.mkdir(parents=True, exist_ok=True)
    for child in ("maps", "artwork", "tables", "notes"):
        (path / child).mkdir(parents=True, exist_ok=True)
    return path


def adventure_package_path(data_dir: Path, package_id: str) -> Path:
    return adventure_folder(data_dir, package_id) / PACKAGE_FILENAME


def adventure_package_asset_dir(data_dir: Path, package_id: str) -> Path:
    path = adventure_folder(data_dir, package_id) / "maps"
    path.mkdir(parents=True, exist_ok=True)
    return path


def legacy_adventure_package_path(data_dir: Path, package_id: str) -> Path:
    return data_dir / LEGACY_PACKAGE_DIRNAME / _slug(package_id) / PACKAGE_FILENAME


def legacy_adventure_package_asset_dir(data_dir: Path, package_id: str) -> Path:
    return data_dir / "assets" / LEGACY_MAP_ASSET_ROOT / _slug(package_id) / "maps"


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
    used_legacy = False
    if not path.is_file():
        legacy_path = legacy_adventure_package_path(data_dir, package_id)
        if legacy_path.is_file():
            path = legacy_path
            used_legacy = True
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if used_legacy:
        payload["package_id"] = _slug(str(payload.get("package_id") or package_id))
        _migrate_legacy_package_assets(data_dir, payload["package_id"], payload)
        save_adventure_package(data_dir, payload)
    return payload


def save_adventure_package(data_dir: Path, package: dict[str, Any]) -> Path:
    package_id = _slug(str(package.get("package_id") or "adventure-package"))
    package["package_id"] = package_id
    path = adventure_package_path(data_dir, package_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    return path


def _asset_url_path(package_id: str, filename: str) -> str:
    return f"maps/{filename}"


def package_map_asset_path(data_dir: Path, package_id: str, asset_path: str) -> Path:
    clean = str(asset_path or "").replace("\\", "/").lstrip("/")
    filename = Path(clean).name if "/" in clean else clean
    current = adventure_package_asset_dir(data_dir, package_id) / filename
    if current.is_file():
        return current
    legacy = legacy_adventure_package_asset_dir(data_dir, package_id) / filename
    if legacy.is_file():
        return legacy
    return current


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
    _migrate_legacy_package_assets(data_dir, package_id, existing)
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
        "nodes": existing.get("nodes", []),
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
    seen: set[str] = set()
    for path in sorted(root.glob(f"*/{PACKAGE_FILENAME}")):
        package = load_adventure_package(data_dir, path.parent.name)
        if package:
            seen.add(str(package.get("package_id") or path.parent.name))
            packages.append(package_summary(data_dir, package))
    legacy_root = data_dir / LEGACY_PACKAGE_DIRNAME
    for path in sorted(legacy_root.glob(f"*/{PACKAGE_FILENAME}")):
        if path.parent.name in seen:
            continue
        package = load_adventure_package(data_dir, path.parent.name)
        if package:
            packages.append(package_summary(data_dir, package))
    return packages


def package_detail(data_dir: Path, package_id: str) -> dict[str, Any]:
    package = load_adventure_package(data_dir, package_id)
    if not package:
        raise FileNotFoundError(f"Adventure package {package_id} was not found.")
    return _package_with_diagnostics(data_dir, package)


def package_summary(data_dir: Path, package: dict[str, Any]) -> dict[str, Any]:
    maps = [item for item in package.get("maps", []) if isinstance(item, dict)]
    pins = sum(len(item.get("pins", [])) for item in maps)
    enriched_maps = []
    for item in maps:
        copy = dict(item)
        asset_path = str(copy.get("asset_path") or "")
        asset_file = package_map_asset_path(data_dir, str(package.get("package_id") or ""), asset_path)
        copy["asset_exists"] = bool(asset_path and asset_file.is_file())
        copy["asset_url"] = (
            f"/api/adventures/packages/{str(package.get('package_id') or '')}/maps/{Path(asset_path).name}"
            if asset_path
            else ""
        )
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
        "node_count": len(package.get("nodes", []) or []),
        "table_count": len(package.get("tables", []) or []),
        "tracker_count": len(package.get("trackers", []) or []),
        "procedure_count": len(package.get("procedures", []) or []),
        "package_path": str(adventure_package_path(data_dir, str(package.get("package_id") or ""))),
        "adventure_folder": str(adventure_folder(data_dir, str(package.get("package_id") or ""))),
        "diagnostics": validate_adventure_package(package),
    }


def _package_with_diagnostics(data_dir: Path, package: dict[str, Any]) -> dict[str, Any]:
    summary = package_summary(data_dir, package)
    detail = dict(package)
    detail.update(summary)
    detail["diagnostics"] = validate_adventure_package(package)
    return detail


def validate_adventure_package(package: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if package.get("schema_version") != 1:
        errors.append("schema_version must be 1.")
    package_id = str(package.get("package_id") or "")
    if not package_id:
        errors.append("package_id is required.")
    if not str(package.get("title") or "").strip():
        errors.append("title is required.")
    source = package.get("source")
    if not isinstance(source, dict) or source.get("type") != "pdf":
        errors.append("source.type must be pdf.")
    elif not str(source.get("source_pdf") or "").strip():
        errors.append("source.source_pdf is required.")
    capabilities = package.get("capabilities") or []
    if not isinstance(capabilities, list):
        errors.append("capabilities must be an array.")
    else:
        for capability in capabilities:
            if capability not in PACKAGE_CAPABILITIES:
                errors.append(f"Unknown capability {capability!r}.")
    nodes = package.get("nodes") or []
    node_ids: set[str] = set()
    if not isinstance(nodes, list):
        errors.append("nodes must be an array.")
    else:
        for node in nodes:
            if isinstance(node, dict) and str(node.get("id") or "").strip():
                node_ids.add(str(node.get("id") or "").strip())
        seen_node_ids: set[str] = set()
        for index, node in enumerate(nodes):
            prefix = f"nodes[{index}]"
            if not isinstance(node, dict):
                errors.append(f"{prefix} must be an object.")
                continue
            node_id = str(node.get("id") or "").strip()
            if not node_id:
                errors.append(f"{prefix}.id is required.")
            elif node_id in seen_node_ids:
                errors.append(f"Duplicate node id {node_id!r}.")
            else:
                seen_node_ids.add(node_id)
            if node.get("type") not in NODE_TYPES:
                errors.append(f"{prefix}.type must be one of {sorted(NODE_TYPES)}.")
            if not str(node.get("title") or "").strip():
                errors.append(f"{prefix}.title is required.")
            if not isinstance(node.get("source_page"), int) or int(node.get("source_page")) < 0:
                errors.append(f"{prefix}.source_page must be a non-negative integer.")
            if not str(node.get("player_text") or "").strip():
                warnings.append(f"{prefix} has no reviewed player_text.")
            if node.get("review_status") and node.get("review_status") not in NODE_REVIEW_STATUSES:
                errors.append(f"{prefix}.review_status is invalid.")
            for branch_index, branch in enumerate(node.get("branches") or []):
                branch_prefix = f"{prefix}.branches[{branch_index}]"
                if not isinstance(branch, dict):
                    errors.append(f"{branch_prefix} must be an object.")
                    continue
                if not str(branch.get("label") or "").strip():
                    errors.append(f"{branch_prefix}.label is required.")
                target = str(branch.get("to") or "").strip()
                if not target:
                    errors.append(f"{branch_prefix}.to is required.")
                elif nodes and target not in node_ids:
                    warnings.append(f"{branch_prefix} points to {target!r}, which is not yet a reviewed node.")
    maps = package.get("maps") or []
    if isinstance(maps, list):
        for map_index, map_record in enumerate(maps):
            if not isinstance(map_record, dict):
                errors.append(f"maps[{map_index}] must be an object.")
                continue
            for pin_index, pin in enumerate(map_record.get("pins") or []):
                if not isinstance(pin, dict):
                    errors.append(f"maps[{map_index}].pins[{pin_index}] must be an object.")
                    continue
                node_id = str(pin.get("node_id") or "").strip()
                if nodes and node_id and node_id not in node_ids:
                    warnings.append(f"Pin {pin.get('label') or pin.get('id')} points to {node_id!r}, which is not yet a reviewed node.")
    else:
        errors.append("maps must be an array.")
    for field in ("foes", "classes", "items", "tables", "trackers", "procedures"):
        if field in package and not isinstance(package.get(field), list):
            errors.append(f"{field} must be an array.")
    for procedure in package.get("procedures") or []:
        if not isinstance(procedure, dict):
            errors.append("procedures entries must be objects.")
            continue
        for step in procedure.get("steps") or []:
            if isinstance(step, dict) and step.get("op") not in ALLOWED_PROCEDURE_OPS:
                errors.append(f"Procedure {procedure.get('id') or '?'} uses unsupported op {step.get('op')!r}.")
    ready_nodes = [node for node in nodes if isinstance(node, dict) and node.get("review_status") == "ready_for_manifest"]
    if nodes and not ready_nodes:
        warnings.append("No reviewed node is marked ready_for_manifest yet.")
    valid = not errors
    return {"valid": valid, "errors": errors, "warnings": warnings}


def update_adventure_package_review(data_dir: Path, package_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    package = load_adventure_package(data_dir, package_id)
    if not package:
        raise FileNotFoundError(f"Adventure package {package_id} was not found.")
    if "title" in payload:
        title = str(payload.get("title") or "").strip()
        if not title:
            raise ValueError("title cannot be blank.")
        package["title"] = title
    source = dict(package.get("source") or {})
    if "source_pages" in payload:
        source["source_pages"] = _integer_list(payload.get("source_pages"))
    if "license_note" in payload:
        source["license_note"] = str(payload.get("license_note") or "")
    if source:
        source.setdefault("type", "pdf")
        package["source"] = source
    review = dict(package.get("review") or {})
    if "review_status" in payload:
        review["status"] = str(payload.get("review_status") or "draft_review_needed")
    if "review_notes" in payload:
        review["notes"] = str(payload.get("review_notes") or "")
    package["review"] = review
    for field in ("nodes", "foes", "classes", "items", "tables", "trackers"):
        if field in payload:
            value = payload.get(field)
            if not isinstance(value, list):
                raise ValueError(f"{field} must be a JSON array.")
            package[field] = value
    if "procedures" in payload:
        value = payload.get("procedures")
        if not isinstance(value, list):
            raise ValueError("procedures must be a JSON array.")
        package["procedures"] = _sanitize_procedures(value)
    save_adventure_package(data_dir, package)
    return _package_with_diagnostics(data_dir, package)


def _integer_list(value: Any) -> list[int]:
    if isinstance(value, str):
        parts = re.split(r"[,;\s]+", value.strip())
        values = []
        for part in parts:
            if not part:
                continue
            try:
                number = int(part)
            except ValueError:
                continue
            if number >= 0:
                values.append(number)
        return values
    if isinstance(value, list):
        clean = []
        for item in value:
            if isinstance(item, int) and item >= 0:
                clean.append(item)
        return clean
    return []


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


def _migrate_legacy_package_assets(data_dir: Path, package_id: str, package: dict[str, Any]) -> None:
    legacy_dir = legacy_adventure_package_asset_dir(data_dir, package_id)
    if not legacy_dir.is_dir():
        return
    target_dir = adventure_package_asset_dir(data_dir, package_id)
    for item in legacy_dir.iterdir():
        if not item.is_file():
            continue
        target = target_dir / item.name
        if not target.exists():
            shutil.copy2(item, target)
    if not package:
        return
    for map_record in package.get("maps", []):
        if isinstance(map_record, dict) and map_record.get("asset_path"):
            map_record["asset_path"] = f"maps/{Path(str(map_record['asset_path'])).name}"
