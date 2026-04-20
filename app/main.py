from __future__ import annotations

import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.build_service import LocalBuildService, UnknownBuildJobError
from app.catalog_service import CatalogService
from app.controller import ApplianceController
from app.helper_client import HelperClientError
from app.models import BuildRequestModel, BuildJobModel, PersonalizationRequestModel, SSHModel
from app.settings import service_settings


BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="BBB Image Forge")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

catalog_service = CatalogService()
controller = ApplianceController(catalog_service=catalog_service)
catalog = controller.catalog
build_service = controller.build_service


def _bundle_map() -> dict[str, dict]:
    return {bundle.id: bundle.model_dump(mode="json") for bundle in catalog.bundles}


def _profile_map() -> dict[str, dict]:
    return {profile.id: profile.model_dump(mode="json") for profile in catalog.profiles}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    helper_error = None
    helper_status = None
    try:
        helper_status = controller.helper_health()
    except Exception as exc:
        helper_error = str(exc)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "catalog": catalog,
            "catalog_json": json.dumps(catalog.model_dump(mode="json")),
            "helper_status": helper_status,
            "helper_error": helper_error,
        },
    )


@app.get("/flash")
async def flash_redirect():
    return RedirectResponse(url="/", status_code=302)


@app.get("/api/catalog")
async def api_catalog():
    return catalog.model_dump(mode="json")


@app.get("/api/helper-health")
async def api_helper_health():
    try:
        return controller.helper_health().model_dump(mode="json")
    except Exception as exc:
        return {"ok": False, "message": str(exc)}


@app.get("/api/devices")
async def api_devices():
    try:
        devices = controller.list_devices()
        return {"devices": [device.model_dump(mode="json") for device in devices]}
    except HelperClientError as exc:
        return {"devices": [], "error": str(exc)}


@app.post("/api/run")
async def api_run(request: Request):
    payload = await request.json()
    build_request, personalization_request, device_id = _parse_run_request(payload)

    def generate():
        for event in controller.stream_prepare_and_flash(
            build_request=build_request,
            personalization_request=personalization_request,
            device_id=device_id,
        ):
            yield json.dumps(event) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.get("/api/eject")
async def api_eject(device_id: str):
    try:
        return controller.helper_client.eject_device(device_id)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@app.get("/healthz", response_class=PlainTextResponse)
def healthz():
    return "ok"


@app.get("/v1/catalog")
async def v1_catalog():
    return catalog.model_dump(mode="json")


@app.post("/v1/build-jobs")
async def v1_build_jobs(request: Request):
    payload = await request.json()
    build_request = BuildRequestModel.model_validate(payload)
    job = build_service.submit_build(build_request)
    return job.model_dump(mode="json")


@app.get("/v1/build-jobs/{job_id}")
async def v1_build_job(job_id: str):
    try:
        job = build_service.get_job(job_id)
    except UnknownBuildJobError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return job.model_dump(mode="json")


@app.get("/v1/artifacts/{artifact_id}/manifest")
async def v1_artifact_manifest(request: Request, artifact_id: str):
    try:
        manifest = build_service.get_artifact_manifest(artifact_id)
    except UnknownBuildJobError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if manifest.local_path:
        manifest = manifest.model_copy(
            update={
                "local_path": None,
                "artifact": manifest.artifact.model_copy(
                    update={
                        "download_url": str(
                            request.url_for("v1_artifact_download", artifact_id=artifact_id)
                        )
                    }
                ),
            }
        )
    return manifest.model_dump(mode="json")


@app.get("/v1/artifacts/{artifact_id}/download")
async def v1_artifact_download(artifact_id: str):
    try:
        manifest = build_service.get_artifact_manifest(artifact_id)
    except UnknownBuildJobError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if manifest.local_path:
        return FileResponse(
            manifest.local_path,
            media_type="application/octet-stream",
            filename=Path(manifest.local_path).name,
        )
    if manifest.artifact.download_url:
        return RedirectResponse(str(manifest.artifact.download_url), status_code=302)
    raise HTTPException(status_code=404, detail="Artifact download is not available.")


def _parse_run_request(payload: dict) -> tuple[BuildRequestModel, PersonalizationRequestModel, str]:
    profile_id = str(payload.get("profile_id") or "").strip()
    addon_bundle_ids = [str(item).strip() for item in payload.get("addon_bundle_ids", []) if str(item).strip()]
    device_id = str(payload.get("device_id") or "").strip()
    if not device_id:
        raise HTTPException(status_code=422, detail="A target SD card must be selected.")

    authorized_keys = [
        line.strip()
        for line in str(payload.get("authorized_key") or "").splitlines()
        if line.strip()
    ]
    password = str(payload.get("password") or "").strip() or None
    disable_password_auth = bool(payload.get("disable_password_auth"))

    network = {
        "wifi": None,
        "ethernet": {"mode": "dhcp"},
    }
    if str(payload.get("ip_mode") or "dhcp") == "static":
        dns_list = [
            item.strip()
            for item in str(payload.get("static_dns") or "").replace(",", " ").split()
            if item.strip()
        ]
        network["ethernet"] = {
            "mode": "static",
            "static": {
                "address": str(payload.get("static_address") or "").strip(),
                "gateway": str(payload.get("static_gateway") or "").strip() or None,
                "dns_servers": dns_list or ["8.8.8.8", "1.1.1.1"],
            },
        }
    wifi_ssid = str(payload.get("wifi_ssid") or "").strip()
    wifi_psk = str(payload.get("wifi_psk") or "").strip()
    if wifi_ssid and wifi_psk:
        network["wifi"] = {"ssid": wifi_ssid, "psk": wifi_psk}

    build_request = BuildRequestModel(
        profile_id=profile_id,
        addon_bundle_ids=addon_bundle_ids,
    )
    personalization_request = PersonalizationRequestModel(
        profile_id=profile_id,
        addon_bundle_ids=addon_bundle_ids,
        system={
            "hostname": str(payload.get("hostname") or "").strip(),
        },
        user={
            "username": str(payload.get("username") or "").strip(),
            "password": password,
            "password_locked": not bool(password),
            "authorized_keys": authorized_keys,
        },
        network=network,
        ssh=SSHModel(
            disable_password_auth=disable_password_auth,
            permit_root_login=False,
        ),
    )
    return build_request, personalization_request, device_id


def main() -> None:
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
