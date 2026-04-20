#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from app.build_service import generic_manifest_from_request, resolve_catalog_selection
from app.builder import ImageBuilder
from app.catalog_service import CatalogService
from app.models import ArtifactManifestModel, BuildRequestModel


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a certified generic BBB image in CI.")
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--addon-bundle-ids", default="[]")
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--export-dir", required=True)
    args = parser.parse_args()

    addon_bundle_ids = json.loads(args.addon_bundle_ids or "[]")
    request = BuildRequestModel(
        profile_id=args.profile_id,
        addon_bundle_ids=addon_bundle_ids,
    )

    catalog = CatalogService().load_builtin()
    profile, artifact, bundle_ids = resolve_catalog_selection(catalog, request)
    manifest = generic_manifest_from_request(catalog, request, args.artifact_name)

    work_dir = Path(args.work_dir).resolve()
    export_dir = Path(args.export_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    export_dir.mkdir(parents=True, exist_ok=True)

    builder = ImageBuilder(manifest, workspace=work_dir / "builder")
    built_artifact = builder.build()
    build_report = built_artifact.parent / f"{manifest.system.hostname}-build-report.json"

    exported_artifact = export_dir / built_artifact.name
    shutil.copy2(built_artifact, exported_artifact)
    exported_report = export_dir / build_report.name
    if build_report.exists():
        shutil.copy2(build_report, exported_report)

    artifact_model = artifact.model_copy(
        update={
            "sha256": sha256sum(exported_artifact),
            "compressed_size_bytes": exported_artifact.stat().st_size,
            "bundle_ids": bundle_ids,
        }
    )
    artifact_manifest = ArtifactManifestModel(
        artifact=artifact_model,
        profile=profile,
        generated_from=request,
    )
    payload = {
        "artifact_manifest": artifact_manifest.model_dump(mode="json"),
        "artifact_filename": exported_artifact.name,
        "build_report_filename": exported_report.name if exported_report.exists() else None,
        "request_id": args.request_id,
    }
    (export_dir / "artifact-manifest.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
