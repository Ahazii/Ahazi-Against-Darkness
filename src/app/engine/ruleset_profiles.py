"""Ruleset profiles — enabled source books and session setup resolution."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

TCOTFD_CLASS_IDS = frozenset(
    {
        "wandering_alchemist",
        "satyr",
        "conservationist",
        "demonologist",
        "cambion",
        "succubus",
    }
)


class RulesetProfile(BaseModel):
    id: str
    label: str
    description: str = ""
    ruleset: str = "ee"
    courtship_enabled: bool = False
    fiendish_foes_default: bool = True
    adventure_modes: list[str] = Field(default_factory=lambda: ["random"])
    source_books: list[str] = Field(default_factory=list)


def _profiles_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "rules" / "ruleset_profiles.json"


@lru_cache(maxsize=1)
def load_ruleset_profiles_raw() -> dict[str, Any]:
    return json.loads(_profiles_path().read_text(encoding="utf-8"))


def ruleset_profiles() -> list[RulesetProfile]:
    raw = load_ruleset_profiles_raw()
    return [RulesetProfile.model_validate(item) for item in raw.get("profiles", [])]


def profile_by_id(profile_id: str) -> RulesetProfile | None:
    token = profile_id.strip().lower()
    return next((profile for profile in ruleset_profiles() if profile.id == token), None)


def class_source_books(class_id: str) -> list[str]:
    mapping = load_ruleset_profiles_raw().get("class_source_books") or {}
    books = mapping.get(class_id.strip().lower())
    if isinstance(books, list):
        return [str(item) for item in books]
    return ["ee"]


def class_allowed_for_profile(class_id: str, profile: RulesetProfile) -> bool:
    allowed_books = set(profile.source_books)
    return bool(set(class_source_books(class_id)) & allowed_books)


def filter_classes_for_profile(classes: list[Any], profile: RulesetProfile) -> list[Any]:
    return [item for item in classes if class_allowed_for_profile(getattr(item, "id", ""), profile)]


def resolve_profile_for_adventure(
    adventure_id: str,
    *,
    profile_id: str | None = None,
    ruleset: str | None = None,
    courtship_enabled: bool | None = None,
) -> RulesetProfile:
    if profile_id:
        profile = profile_by_id(profile_id)
        if profile is None:
            raise ValueError(f"Unknown ruleset profile: {profile_id}")
        if adventure_id not in profile.adventure_modes and adventure_id != "random":
            raise ValueError(f"Profile {profile.id} cannot start adventure {adventure_id}.")
        return profile
    if adventure_id == "courtship-demesne":
        profile = profile_by_id("courtship_demesne")
        if profile is not None:
            return profile
    normalized_ruleset = (ruleset or "ee").strip().lower()
    wants_courtship = courtship_enabled if courtship_enabled is not None else normalized_ruleset == "forsaken_depths"
    if normalized_ruleset == "forsaken_depths":
        key = "forsaken_depths" if wants_courtship else "forsaken_depths_no_courtship"
        profile = profile_by_id(key)
        if profile is not None:
            return profile
    profile = profile_by_id("ee_random")
    if profile is None:
        raise ValueError("Default ruleset profile ee_random is missing.")
    return profile


def profiles_for_adventure(adventure_id: str) -> list[RulesetProfile]:
    if adventure_id == "courtship-demesne":
        profile = profile_by_id("courtship_demesne")
        return [profile] if profile else []
    if adventure_id != "random":
        return []
    return [profile for profile in ruleset_profiles() if "random" in profile.adventure_modes]
