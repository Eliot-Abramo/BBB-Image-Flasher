from __future__ import annotations

import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from app.bundles import BUNDLES, bundle_names
from app.catalog import BeagleCatalog, CatalogError
from app.manifests import save_manifest
from app.models import ManifestModel
from app.profiles import available_profiles, instantiate_profile


BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="BBB Image Forge")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    catalog_entries = []
    catalog_error = None
    try:
        catalog_entries = BeagleCatalog().fetch_bbb_images()[:8]
    except Exception as exc:
        catalog_error = str(exc)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "profiles": available_profiles(),
            "bundles": [BUNDLES[name] for name in bundle_names()],
            "catalog_entries": catalog_entries,
            "catalog_error": catalog_error,
        },
    )


@app.post("/manifest", response_class=PlainTextResponse)
def manifest(
    profile: str = Form(...),
    hostname: str = Form(...),
    username: str = Form(...),
    bundle_names_selected: list[str] = Form(default=[]),
    disable_password_auth: bool = Form(False),
    permit_root_login: bool = Form(False),
    authorized_key: str = Form(""),
):
    manifest_model = instantiate_profile(
        profile,
        system={"hostname": hostname},
        user={
            "username": username,
            "authorized_keys": [authorized_key.strip()] if authorized_key.strip() else [],
        },
        bundles=bundle_names_selected,
        ssh={
            "disable_password_auth": disable_password_auth,
            "permit_root_login": permit_root_login,
        },
        output={"artifact_name": f"{hostname}.img.xz"},
    )
    return json.dumps(manifest_model.model_dump(mode="json"), indent=2)


@app.get("/healthz", response_class=PlainTextResponse)
def healthz():
    return "ok"


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
