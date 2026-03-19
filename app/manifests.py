from __future__ import annotations

from pathlib import Path

import yaml

from app.bundles import resolve_packages
from app.models import ManifestModel


def load_manifest(path: str | Path) -> ManifestModel:
    content = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    return ManifestModel.model_validate(data)


def save_manifest(manifest: ManifestModel, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        yaml.safe_dump(manifest.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )


def resolved_package_list(manifest: ManifestModel) -> list[str]:
    return resolve_packages(manifest.bundles, manifest.apt.extra_packages)
