from __future__ import annotations

import asyncio
import json
import os
import platform
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.bundles import BUNDLES, bundle_names, bundles_by_category
from app.catalog import BeagleCatalog, CatalogError
from app.flasher import admin_instructions, eject_drive, flash_image, is_admin, list_drives
from app.manifests import save_manifest
from app.models import ManifestModel
from app.profiles import available_profiles, instantiate_profile


BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="BBB Image Forge")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

_catalog_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="catalog")
_flash_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="flash")
_CATALOG_TIMEOUT = 6.0


# ──────────────────────────────────────────────────────────────────────────────
# Main page
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    catalog_entries = []
    catalog_error = None
    loop = asyncio.get_event_loop()
    try:
        catalog_entries = await asyncio.wait_for(
            loop.run_in_executor(
                _catalog_executor,
                lambda: BeagleCatalog().fetch_bbb_images()[:8],
            ),
            timeout=_CATALOG_TIMEOUT,
        )
    except asyncio.TimeoutError:
        catalog_error = (
            "Catalog fetch timed out — beagleboard.org may be slow. "
            "The tool still works fine."
        )
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


# ──────────────────────────────────────────────────────────────────────────────
# Manifest generation
# ──────────────────────────────────────────────────────────────────────────────

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
    user_config: dict = {
        "username": username,
        "authorized_keys": [authorized_key.strip()] if authorized_key.strip() else [],
    }
    if password.strip():
        user_config["password"] = password.strip()
        user_config["password_locked"] = False
    else:
        user_config["password_locked"] = True

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


# ──────────────────────────────────────────────────────────────────────────────
# Build (SSE streaming)
# ──────────────────────────────────────────────────────────────────────────────

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


@app.post("/api/build")
async def api_build(
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
    """Start a build and stream its output line-by-line as SSE.

    Each event is a JSON object:
        {"line": "...", "status": "running" | "done" | "error",
         "artifact": "<path>"}   ← only on status=done
    """
    # ── Privilege check ──────────────────────────────────────────────────────
    if platform.system() != "Linux":
        async def _no_linux():
            yield f"data: {json.dumps({'status': 'error', 'line': 'Image building requires a Linux host (uses losetup / mount / chroot). The server is currently running on ' + platform.system() + '.'})}\n\n"
        return StreamingResponse(_no_linux(), media_type="text/event-stream", headers=_SSE_HEADERS)

    if not is_admin():
        async def _no_root():
            yield f"data: {json.dumps({'status': 'error', 'line': 'The server must be running as root to build images (needs losetup, mount, chroot). Restart with: sudo env PATH=\"$PATH\" python3 -m app.main'})}\n\n"
        return StreamingResponse(_no_root(), media_type="text/event-stream", headers=_SSE_HEADERS)

    # ── Build the manifest model ─────────────────────────────────────────────
    user_config: dict = {
        "username": username,
        "authorized_keys": [authorized_key.strip()] if authorized_key.strip() else [],
    }
    if password.strip():
        user_config["password"] = password.strip()
        user_config["password_locked"] = False
    else:
        user_config["password_locked"] = True

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

    # ── Save manifest to a temp file ─────────────────────────────────────────
    fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="bbb-forge-")
    try:
        os.write(fd, json.dumps(manifest_model.model_dump(mode="json"), indent=2).encode())
    finally:
        os.close(fd)

    artifact_name = manifest_model.output.artifact_name

    # ── Stream subprocess output ─────────────────────────────────────────────
    async def _generate():
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "app.cli", "build", tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            async for raw_line in proc.stdout:
                text = raw_line.decode(errors="replace").rstrip()
                yield f"data: {json.dumps({'line': text, 'status': 'running'})}\n\n"

            await proc.wait()

            if proc.returncode == 0:
                artifact = str(Path("build") / "artifacts" / artifact_name)
                yield f"data: {json.dumps({'status': 'done', 'line': 'Build complete!', 'artifact': artifact})}\n\n"
            else:
                yield f"data: {json.dumps({'status': 'error', 'line': f'Build failed (exit code {proc.returncode}).'})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'status': 'error', 'line': str(exc)})}\n\n"
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            if proc and proc.returncode is None:
                proc.kill()

    return StreamingResponse(_generate(), media_type="text/event-stream", headers=_SSE_HEADERS)


# ──────────────────────────────────────────────────────────────────────────────
# Flash page
# ──────────────────────────────────────────────────────────────────────────────

def _find_artifacts() -> list[Path]:
    """Return .img.xz files from build/artifacts/, newest first."""
    artifacts_dir = Path("build") / "artifacts"
    if not artifacts_dir.exists():
        return []
    return sorted(
        artifacts_dir.glob("*.img.xz"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


@app.get("/flash", response_class=HTMLResponse)
async def flash_page(request: Request):
    admin = is_admin()
    os_name = platform.system()       # "Windows" | "Linux" | "Darwin"
    artifacts = _find_artifacts()
    return templates.TemplateResponse(
        request,
        "flash.html",
        {
            "admin": admin,
            "os_name": os_name,
            "admin_instructions": admin_instructions(),
            "artifacts": [str(a) for a in artifacts],
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# Flash API
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/drives")
async def api_drives():
    """Return a JSON list of removable drives detected on this machine."""
    loop = asyncio.get_event_loop()
    try:
        drives = await asyncio.wait_for(
            loop.run_in_executor(_catalog_executor, list_drives),
            timeout=12.0,
        )
        return {"drives": [d.as_dict() for d in drives]}
    except asyncio.TimeoutError:
        return {"error": "Drive detection timed out.", "drives": []}
    except Exception as exc:
        return {"error": str(exc), "drives": []}


@app.get("/api/flash")
async def api_flash(
    image: str = Query(...),
    device: str = Query(...),
):
    """Server-Sent Events stream: decompresses image and writes to device.

    Each event is a JSON object with keys:
        written, percent, speed_mb, status ("flashing"|"done"|"error"), message
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    def _worker() -> None:
        try:
            for progress in flash_image(Path(image), device):
                asyncio.run_coroutine_threadsafe(queue.put(progress), loop)
        except Exception as exc:
            asyncio.run_coroutine_threadsafe(
                queue.put({
                    "written": 0, "percent": 0, "speed_mb": 0.0,
                    "status": "error", "message": str(exc),
                }),
                loop,
            )
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

    loop.run_in_executor(_flash_executor, _worker)

    async def _generate():
        while True:
            item = await queue.get()
            if item is None:
                break
            yield f"data: {json.dumps(item)}\n\n"
            if item.get("status") in ("done", "error"):
                break

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/eject")
async def api_eject(device: str = Query(...)):
    """Attempt a safe eject of the given device."""
    loop = asyncio.get_event_loop()
    try:
        msg = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: eject_drive(device)),
            timeout=20.0,
        )
        return {"status": "ok", "message": msg}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


# ──────────────────────────────────────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/healthz", response_class=PlainTextResponse)
def healthz():
    return "ok"


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
