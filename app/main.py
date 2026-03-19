from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from app.bundles import BUNDLES, bundle_names, bundles_by_category
from app.catalog import BeagleCatalog, CatalogError
from app.manifests import save_manifest
from app.models import ManifestModel
from app.profiles import available_profiles, instantiate_profile


BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="BBB Image Forge")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

_catalog_executor = ThreadPoolExecutor(max_workers=1)
_CATALOG_TIMEOUT = 6.0   # seconds — give up fast so the page loads


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    catalog_entries = []
    catalog_error = None
    loop = asyncio.get_event_loop()
    try:
        catalog_entries = await asyncio.wait_for(
            loop.run_in_executor(_catalog_executor, lambda: BeagleCatalog().fetch_bbb_images()[:8]),
            timeout=_CATALOG_TIMEOUT,
        )
    except asyncio.TimeoutError:
        catalog_error = "Catalog fetch timed out — beagleboard.org may be slow. The tool still works fine."
    except Exception as exc:
        catalog_error = str(exc)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "profiles": available_profiles(),
            "bundles": [BUNDLES[name] for name in bundle_names()],
            "bundles_by_category": bundles_by_category(),
            "catalog_entries": catalog_entries,
            "catalog_error": catalog_error,
        },
    )


@app.post("/manifest", response_class=PlainTextResponse)
def manifest(
    profile: str = Form(...),
    hostname: str = Form(...),
    username: str = Form(...),
    password: str = Form(""),
    bundle_names_selected: list[str] = Form(default=[]),
    ip_mode: str = Form("dhcp"),
    static_address: str = Form(""),
    static_gateway: str = Form(""),
    static_dns: str = Form("8.8.8.8 1.1.1.1"),
    disable_password_auth: bool = Form(False),
    permit_root_login: bool = Form(False),
    authorized_key: str = Form(""),
):
    # Build the user config
    user_config: dict = {
        "username": username,
        "authorized_keys": [authorized_key.strip()] if authorized_key.strip() else [],
    }
    if password.strip():
        user_config["password"] = password.strip()
        user_config["password_locked"] = False
    else:
        user_config["password_locked"] = True

    # Build the network config
    network_config: dict = {}
    if ip_mode == "static" and static_address.strip():
        dns_list = [s.strip() for s in static_dns.replace(",", " ").split() if s.strip()]
        network_config["ethernet"] = {
            "mode": "static",
            "static": {
                "address": static_address.strip(),
                "gateway": static_gateway.strip() or None,
                "dns_servers": dns_list or ["8.8.8.8", "1.1.1.1"],
            },
        }
    else:
        network_config["ethernet"] = {"mode": "dhcp"}

    manifest_model = instantiate_profile(
        profile,
        system={"hostname": hostname},
        user=user_config,
        bundles=bundle_names_selected,
        network=network_config,
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
