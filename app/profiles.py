from __future__ import annotations

from pathlib import Path

import yaml

from app.models import ManifestModel


PROFILE_DIR = Path(__file__).resolve().parent / "profiles"


def available_profiles() -> list[str]:
    return sorted(path.stem for path in PROFILE_DIR.glob("*.yml"))


def load_profile(name: str) -> dict:
    path = PROFILE_DIR / f"{name}.yml"
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {name}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def instantiate_profile(name: str, **overrides) -> ManifestModel:
    data = load_profile(name)
    deep_update(data, overrides)
    return ManifestModel.model_validate(data)


def deep_update(base: dict, updates: dict) -> None:
    for key, value in updates.items():
        if value is None:
            continue
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value
