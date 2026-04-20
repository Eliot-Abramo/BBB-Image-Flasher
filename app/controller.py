from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Iterator

from app.artifact_manager import ArtifactDownloadError, ArtifactManager
from app.build_service import (
    BuildService,
    GitHubActionsBuildService,
    HttpBuildService,
    LocalBuildService,
)
from app.catalog_service import CatalogService
from app.helper_client import HelperClient, HelperClientError
from app.models import BuildRequestModel, PersonalizationRequestModel
from app.settings import app_paths, service_settings


class ApplianceController:
    def __init__(
        self,
        catalog_service: CatalogService | None = None,
        build_service: BuildService | None = None,
        helper_client: HelperClient | None = None,
        artifact_manager: ArtifactManager | None = None,
    ) -> None:
        self.catalog_service = catalog_service or CatalogService()
        self.catalog = self.catalog_service.load()
        self.build_service = build_service or self._default_build_service()
        self.helper_client = helper_client or HelperClient()
        self.artifact_manager = artifact_manager or ArtifactManager()
        self.paths = app_paths()

    def _default_build_service(self) -> BuildService:
        settings = service_settings()
        if settings.build_service_url:
            return HttpBuildService(settings.build_service_url)
        if settings.github_actions_enabled:
            return GitHubActionsBuildService(self.catalog_service)
        if settings.allow_local_build_service:
            return LocalBuildService(self.catalog_service)
        raise RuntimeError(
            "No remote build service is configured and local build fallback is disabled."
        )

    def list_devices(self):
        return self.helper_client.list_devices()

    def helper_health(self):
        return self.helper_client.healthcheck()

    def stream_prepare_and_flash(
        self,
        build_request: BuildRequestModel,
        personalization_request: PersonalizationRequestModel,
        device_id: str,
    ) -> Iterator[dict]:
        prepared_workspace = None
        try:
            yield self._event("preparing", "running", "Validating your certified selection.")
            job = self.build_service.submit_build(build_request)
            yield self._event(
                "building",
                job.status,
                job.message or "Queued the certified artifact build.",
                remote_url=job.remote_url,
            )

            while job.status in {"queued", "running"}:
                time.sleep(1)
                job = self.build_service.get_job(job.id)
                yield self._event(
                    "building",
                    job.status,
                    job.message or "Building the certified artifact.",
                    remote_url=job.remote_url,
                )

            if job.status == "error":
                raise RuntimeError(job.error or job.message or "Certified artifact build failed.")

            if not job.artifact_id:
                raise RuntimeError("Build finished without an artifact id.")
            manifest = self.build_service.get_artifact_manifest(job.artifact_id)
            if job.artifact_path and not manifest.local_path:
                manifest = manifest.model_copy(update={"local_path": job.artifact_path})

            artifact_path = self.artifact_manager.ensure_local_artifact(
                manifest,
                progress=lambda message: None,
            )
            yield self._event(
                "downloading",
                "done",
                f"Certified artifact ready: {artifact_path.name}",
                remote_url=job.remote_url,
            )

            yield self._event("preparing", "running", "Applying your local settings to the image.")
            prepared = self.helper_client.prepare_image(artifact_path, personalization_request)
            prepared_workspace = prepared.workspace_dir
            yield self._event(
                "preparing",
                "done",
                "Your hostname, account, SSH, and network settings have been applied locally.",
                image_size_bytes=prepared.image_size_bytes,
            )

            yield self._event("validating", "running", "Re-checking the selected SD card.")
            for event in self.helper_client.stream_flash_image(
                prepared.image_path,
                device_id,
                expected_size_bytes=prepared.image_size_bytes,
            ):
                message = event.get("message", "")
                if event.get("status") == "flashing":
                    yield self._event(
                        "flashing",
                        "running",
                        message,
                        percent=event.get("percent", 0),
                        speed_mb=event.get("speed_mb", 0.0),
                        written=event.get("written", 0),
                    )
                elif event.get("status") == "done":
                    yield self._event(
                        "flashing",
                        "done",
                        message,
                        percent=100,
                        speed_mb=event.get("speed_mb", 0.0),
                        written=event.get("written", 0),
                    )
                else:
                    raise RuntimeError(message or "Flashing failed.")

            yield self._event("verifying", "running", "Checking that the SD card is still present.")
            verify = self.helper_client.verify_image(device_id)
            yield self._event(
                "safe_to_remove",
                "done",
                verify.get("message", "Flashing complete. Safe to remove the SD card."),
            )
        except Exception as exc:
            support_bundle = self._write_support_bundle(
                build_request=build_request,
                personalization_request=personalization_request,
                device_id=device_id,
                error=str(exc),
            )
            yield self._event(
                "error",
                "error",
                str(exc),
                support_bundle=str(support_bundle),
            )
        finally:
            if prepared_workspace:
                try:
                    self.helper_client.cleanup_workspace(prepared_workspace)
                except HelperClientError:
                    pass

    def _write_support_bundle(self, **payload: object) -> Path:
        path = self.paths.support_dir / f"support-{uuid.uuid4().hex}.json"
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return path

    @staticmethod
    def _event(phase: str, status: str, message: str, **extra: object) -> dict:
        payload = {
            "phase": phase,
            "status": status,
            "message": message,
        }
        payload.update(extra)
        return payload
