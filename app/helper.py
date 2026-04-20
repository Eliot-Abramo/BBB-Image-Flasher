from __future__ import annotations

import json
import shutil
from pathlib import Path

import typer

from app.flasher import (
    admin_instructions,
    eject_drive,
    flash_image,
    get_device,
    is_admin,
    list_candidate_devices,
    validate_candidate_device,
    verify_written_image,
)
from app.models import HelperHealthModel, PersonalizationRequestModel
from app.personalizer import ImagePersonalizer
from app.settings import service_settings


cli = typer.Typer(help="BBB Image Forge privileged helper")


@cli.command("healthcheck")
def healthcheck() -> None:
    settings = service_settings()
    model = HelperHealthModel(
        ok=True,
        message=(
            "Helper is reachable."
            if is_admin()
            else "Helper is reachable but is not currently elevated. "
            + admin_instructions()
        ),
        helper_command=" ".join(settings.helper_command),
    )
    typer.echo(model.model_dump_json())


@cli.command("list-devices")
def list_devices() -> None:
    typer.echo(
        json.dumps([device.model_dump(mode="json") for device in list_candidate_devices()])
    )


@cli.command("prepare-image")
def prepare_image(
    artifact_path: Path = typer.Argument(...),
    request_path: Path = typer.Argument(...),
) -> None:
    request = PersonalizationRequestModel.model_validate_json(
        request_path.read_text(encoding="utf-8")
    )
    result = ImagePersonalizer(request).prepare(artifact_path)
    typer.echo(result.model_dump_json())


@cli.command("flash-image")
def flash_image_command(
    image_path: Path = typer.Argument(...),
    device_id: str = typer.Argument(...),
    expected_size_bytes: int = typer.Option(..., "--expected-size-bytes"),
) -> None:
    device = get_device(device_id)
    validate_candidate_device(device, expected_size_bytes)
    for event in flash_image(image_path, device.device_path, expected_size_bytes=expected_size_bytes):
        typer.echo(json.dumps(event))
        if event.get("status") in {"done", "error"}:
            break


@cli.command("verify-image")
def verify_image(device_id: str = typer.Argument(...)) -> None:
    typer.echo(json.dumps(verify_written_image(device_id)))


@cli.command("eject-device")
def eject_device(device_id: str = typer.Argument(...)) -> None:
    device = get_device(device_id)
    typer.echo(json.dumps({"status": "done", "message": eject_drive(device.device_path)}))


@cli.command("cleanup-workspace")
def cleanup_workspace(workspace_dir: Path = typer.Argument(...)) -> None:
    shutil.rmtree(workspace_dir, ignore_errors=True)
    typer.echo(json.dumps({"status": "done", "message": "Workspace removed."}))


if __name__ == "__main__":
    cli()
