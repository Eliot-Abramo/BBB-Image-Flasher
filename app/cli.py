from __future__ import annotations

from pathlib import Path

import typer

from app.builder import ImageBuilder
from app.catalog import BeagleCatalog
from app.manifests import load_manifest, save_manifest
from app.models import ManifestModel
from app.profiles import available_profiles, instantiate_profile


cli = typer.Typer(help="BBB Image Forge CLI")


@cli.command()
def list_profiles() -> None:
    for profile in available_profiles():
        typer.echo(profile)


@cli.command()
def list_base_images() -> None:
    catalog = BeagleCatalog()
    for entry in catalog.fetch_bbb_images():
        typer.echo(f"{entry.label}\n  {entry.image_url}\n  sha256={entry.checksum}\n")


@cli.command()
def generate_manifest(
    profile: str = typer.Option(..., help="Built-in profile name"),
    hostname: str = typer.Option(..., help="Target hostname"),
    username: str = typer.Option(..., help="Primary non-root user"),
    authorized_key_file: Path | None = typer.Option(None, help="Path to SSH public key"),
    output: Path = typer.Option(..., help="Output YAML manifest"),
) -> None:
    authorized_keys: list[str] = []
    if authorized_key_file:
        authorized_keys = [authorized_key_file.read_text(encoding="utf-8").strip()]

    manifest = instantiate_profile(
        profile,
        system={"hostname": hostname},
        user={"username": username, "authorized_keys": authorized_keys},
        output={"artifact_name": f"{hostname}.img.xz"},
    )
    save_manifest(manifest, output)
    typer.echo(f"Saved {output}")


@cli.command()
def build(manifest_path: Path = typer.Argument(..., help="Manifest YAML file")) -> None:
    manifest = load_manifest(manifest_path)
    builder = ImageBuilder(manifest)
    artifact = builder.build()
    typer.echo(f"Built artifact: {artifact}")


@cli.command()
def validate(manifest_path: Path = typer.Argument(..., help="Manifest YAML file")) -> None:
    manifest = load_manifest(manifest_path)
    ManifestModel.model_validate(manifest.model_dump())
    typer.echo("Manifest is valid.")


if __name__ == "__main__":
    cli()
