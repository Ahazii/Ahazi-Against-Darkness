from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.engine.adventure_import import import_adventure_manifest, installed_manifest_path  # noqa: E402
from app.engine.tag_campaign import build_tag_adventure_manifest, default_campaign  # noqa: E402
from app.rules.repository import RulesRepository  # noqa: E402


CREATE_LINE = re.compile(
    r"Created TAG adventure '(?P<title>.+)' in the Adventure section with id (?P<id>[^.]+)\."
)
SOURCE_LINE = re.compile(r"Generated from .*?: (?P<detail>.+)\. Source: (?P<source>[^.]+(?:\.[^.]+)*)\.")


def _db_records(data_dir: Path) -> list[tuple[str, str, dict[str, Any]]]:
    db_path = data_dir / "game.db"
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute("select collection,id,data from records").fetchall()
    finally:
        con.close()
    parsed: list[tuple[str, str, dict[str, Any]]] = []
    for collection, record_id, data in rows:
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            parsed.append((str(collection), str(record_id), payload))
    return parsed


def _campaign_payload(records: list[tuple[str, str, dict[str, Any]]]) -> dict[str, Any]:
    for collection, record_id, payload in records:
        if collection == "campaigns" and record_id == "default":
            return payload
    return {}


def _session_payloads(records: list[tuple[str, str, dict[str, Any]]]) -> list[dict[str, Any]]:
    return [payload for collection, _record_id, payload in records if collection == "sessions"]


def _creation_metadata(campaign: dict[str, Any], sessions: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    metadata: dict[str, dict[str, str]] = {}
    for entry in campaign.get("tag_downtime_log", []):
        if not isinstance(entry, dict):
            continue
        text = str(entry.get("result_text") or "")
        match = CREATE_LINE.search(text)
        if match:
            metadata[match.group("id")] = {"title": match.group("title")}
    for session in sessions:
        adventure_id = str(session.get("adventure_id") or "")
        if not adventure_id.startswith("tag-"):
            continue
        meta = metadata.setdefault(adventure_id, {})
        log = session.get("log") or []
        if isinstance(log, list):
            for line in log:
                text = str(line)
                if text.startswith("Imported adventure:"):
                    meta.setdefault("title", text.split(":", 1)[1].strip().rstrip("."))
                source = SOURCE_LINE.search(text)
                if source:
                    meta.setdefault("detail", source.group("detail"))
                    meta.setdefault("source", source.group("source"))
    return metadata


def _generator_request(adventure_id: str, meta: dict[str, str]) -> tuple[str, str]:
    detail = meta.get("detail", "")
    if adventure_id.startswith("tag-rumor-rumor-"):
        match = re.search(r"tag-rumor-rumor-(\d+)-", adventure_id)
        return "rumor", match.group(1) if match else ""
    if adventure_id.startswith("tag-treasure-map-treasure-map-"):
        match = re.search(r"tag-treasure-map-treasure-map-(\d+)-", adventure_id)
        return "treasure_map", match.group(1) if match else ""
    if adventure_id.startswith("tag-thematic-dungeon-"):
        match = re.search(r"tag-thematic-dungeon-(\d+)-", adventure_id)
        return "thematic_dungeon", match.group(1) if match else ""
    if adventure_id.startswith("tag-guild-job-guild-job-"):
        if "Thematic Dungeon 6" in detail or "Bandit Hideout" in detail:
            return "thematic_dungeon", "6"
        rumor = re.search(r"Rumor\s+(\d+)", detail)
        if rumor:
            return "rumor", rumor.group(1)
        theme = re.search(r"Thematic Dungeon\s+(\d+)", detail)
        if theme:
            return "thematic_dungeon", theme.group(1)
        quest = re.search(r"Minor Unique Quest\s+(\d+)", detail)
        if quest:
            return "guild_job", re.search(r"Guild Job\s+(\d+)", detail).group(1) if re.search(r"Guild Job\s+(\d+)", detail) else ""
        match = re.search(r"tag-guild-job-guild-job-(\d+)-", adventure_id)
        return "guild_job", match.group(1) if match else ""
    raise ValueError(f"Cannot infer generator request for {adventure_id}")


def _rewrite_manifest_identity(manifest: dict[str, Any], adventure_id: str, meta: dict[str, str]) -> dict[str, Any]:
    rewritten = deepcopy(manifest)
    rewritten["id"] = adventure_id
    if meta.get("title"):
        rewritten["title"] = meta["title"]
    source = rewritten.setdefault("source", {})
    params = source.setdefault("parameters", {})
    if adventure_id.startswith("tag-guild-job"):
        params["lead_type"] = "guild_job"
        if meta.get("detail"):
            params["lead_detail"] = meta["detail"]
        params.setdefault("original_repaired_generator", "historical TAG module repair")
    source["repaired_from_history"] = True
    return rewritten


def repair_generated_modules(root_dir: Path, data_dir: Path, *, dry_run: bool = False) -> dict[str, Any]:
    records = _db_records(data_dir)
    campaign = _campaign_payload(records)
    sessions = _session_payloads(records)
    ids = [str(item) for item in campaign.get("tag_generated_adventure_ids", []) if item]
    metadata = _creation_metadata(campaign, sessions)
    rules = RulesRepository(root_dir / "data" / "rules", data_dir / "rules")
    repaired: list[str] = []
    existing: list[str] = []
    errors: list[str] = []
    for adventure_id in ids:
        if installed_manifest_path(data_dir, adventure_id).is_file():
            existing.append(adventure_id)
            continue
        meta = metadata.get(adventure_id, {})
        try:
            lead_type, detail = _generator_request(adventure_id, meta)
            campaign_copy = default_campaign()
            manifest, _entry = build_tag_adventure_manifest(campaign_copy, lead_type=lead_type, detail=detail)
            manifest = _rewrite_manifest_identity(manifest, adventure_id, meta)
            if not dry_run:
                path, result = import_adventure_manifest(root_dir, data_dir, manifest, rules_repo=rules, overwrite=True)
                if not result.valid or path is None:
                    errors.append(f"{adventure_id}: {'; '.join(result.errors) or 'import failed'}")
                    continue
            repaired.append(adventure_id)
        except Exception as exc:  # noqa: BLE001 - report all migration failures
            errors.append(f"{adventure_id}: {type(exc).__name__}: {exc}")
    return {"existing": existing, "repaired": repaired, "errors": errors, "dry_run": dry_run}


def main() -> int:
    parser = argparse.ArgumentParser(description="Recreate missing historical generated TAG modules in DATA_DIR/Adventures.")
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--root-dir", default=ROOT, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = repair_generated_modules(args.root_dir.resolve(), args.data_dir.resolve(), dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
