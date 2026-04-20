from __future__ import annotations

import json
import shutil
from pathlib import Path

import typer

from app.catalog_service import CatalogService
from app.helper_client import HelperClient
from app.settings import app_paths, service_settings


cli = typer.Typer(help="Installer and repair utilities for BBB Image Forge")


@cli.command("selfcheck")
def selfcheck() -> None:
    paths = app_paths()
    settings = service_settings()
    catalog = CatalogService().load()
    helper_message = ""
    helper_ok = False
    try:
      helper = HelperClient().healthcheck()
      helper_message = helper.message
      helper_ok = helper.ok
    except Exception as exc:
      helper_message = str(exc)
    payload = {
        "ok": True,
        "catalog_version": catalog.catalog_version,
        "catalog_profiles": len(catalog.profiles),
        "helper_ok": helper_ok,
        "helper_message": helper_message,
        "helper_command": " ".join(settings.helper_command),
        "build_mode": (
            "http-relay"
            if settings.build_service_url
            else "github-actions"
            if settings.github_actions_enabled
            else "local-fallback"
        ),
        "github": {
            "enabled": settings.github_actions_enabled,
            "owner": settings.github_owner,
            "repo": settings.github_repo,
            "workflow_file": settings.github_workflow_file,
            "ref": settings.github_ref,
            "token_configured": bool(settings.github_token),
        },
        "paths": {
            "root": str(paths.root),
            "cache_dir": str(paths.cache_dir),
            "workspace_dir": str(paths.workspace_dir),
            "support_dir": str(paths.support_dir),
            "temp_dir": str(paths.temp_dir),
        },
    }
    typer.echo(json.dumps(payload, indent=2))


@cli.command("repair-dirs")
def repair_dirs(clear_temp: bool = typer.Option(True, "--clear-temp/--keep-temp")) -> None:
    paths = app_paths().ensure()
    if clear_temp:
        shutil.rmtree(paths.temp_dir, ignore_errors=True)
        paths.temp_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "done",
        "root": str(paths.root),
        "cleared_temp": clear_temp,
    }
    typer.echo(json.dumps(payload))


if __name__ == "__main__":
    cli()
