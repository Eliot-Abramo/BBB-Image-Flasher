from __future__ import annotations

import json
from pathlib import Path

import requests

from app.models import CatalogModel
from app.settings import service_settings


class CatalogServiceError(RuntimeError):
    pass


class CatalogService:
    def __init__(self, builtin_path: Path | None = None) -> None:
        self.builtin_path = builtin_path or Path(__file__).resolve().parent / "data" / "catalog.json"

    def load(self) -> CatalogModel:
        settings = service_settings()
        if settings.catalog_url:
            try:
                response = requests.get(settings.catalog_url, timeout=8)
                response.raise_for_status()
                return CatalogModel.model_validate(response.json())
            except Exception as exc:
                builtin = self.load_builtin()
                builtin.warnings.append(
                    f"Fell back to the built-in catalog because the remote catalog could not be loaded: {exc}"
                )
                return builtin
        return self.load_builtin()

    def load_builtin(self) -> CatalogModel:
        try:
            payload = json.loads(self.builtin_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise CatalogServiceError(f"Missing built-in catalog: {self.builtin_path}") from exc
        return CatalogModel.model_validate(payload)
