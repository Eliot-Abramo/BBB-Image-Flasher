from __future__ import annotations

import hashlib
import json
import threading
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

import requests

from app.builder import BuildError, ImageBuilder
from app.catalog_service import CatalogService
from app.models import (
    ArtifactCatalogModel,
    ArtifactManifestModel,
    BuildJobModel,
    BuildRequestModel,
    CatalogModel,
    CatalogProfileModel,
    ManifestModel,
)
from app.profiles import load_profile
from app.settings import app_paths, service_settings


class UnknownBuildJobError(KeyError):
    pass


class BuildService(Protocol):
    def submit_build(self, request: BuildRequestModel) -> BuildJobModel: ...

    def get_job(self, job_id: str) -> BuildJobModel: ...

    def get_artifact_manifest(self, artifact_id: str) -> ArtifactManifestModel: ...


def _catalog_maps(
    catalog: CatalogModel,
) -> tuple[dict[str, CatalogProfileModel], dict[str, ArtifactCatalogModel]]:
    profiles = {profile.id: profile for profile in catalog.profiles}
    artifacts = {artifact.id: artifact for artifact in catalog.artifacts}
    return profiles, artifacts


def resolve_catalog_selection(
    catalog: CatalogModel,
    request: BuildRequestModel,
) -> tuple[CatalogProfileModel, ArtifactCatalogModel, list[str]]:
    profiles, artifacts = _catalog_maps(catalog)
    profile = profiles.get(request.profile_id)
    if profile is None:
        raise BuildError(f"Unknown certified profile: {request.profile_id}")

    allowed = set(profile.optional_bundle_ids)
    invalid = sorted(set(request.addon_bundle_ids) - allowed)
    if invalid:
        raise BuildError(
            "Unsupported add-on bundle(s) for this profile: " + ", ".join(invalid)
        )
    bundle_ids = list(dict.fromkeys([*profile.default_bundle_ids, *request.addon_bundle_ids]))
    artifact_id = profile.artifact_id
    if artifact_id is None or artifact_id not in artifacts:
        raise BuildError(f"No certified artifact template is defined for {profile.label}.")
    return profile, artifacts[artifact_id], bundle_ids


def generic_manifest_from_request(
    catalog: CatalogModel,
    request: BuildRequestModel,
    artifact_name: str,
) -> ManifestModel:
    profile, _, bundle_ids = resolve_catalog_selection(catalog, request)
    data = load_profile(profile.profile_name)
    data["bundles"] = bundle_ids
    data["system"] = {
        **data.get("system", {}),
        "hostname": "bbb-template",
    }
    data["user"] = {
        "username": "student",
        "password": None,
        "password_locked": True,
        "authorized_keys": [],
    }
    data["network"] = {
        "wifi": None,
        "ethernet": {
            "mode": "dhcp",
        },
    }
    data["ssh"] = {
        "disable_password_auth": False,
        "permit_root_login": False,
    }
    data["output"] = {
        "artifact_name": artifact_name,
    }
    return ManifestModel.model_validate(data)


class LocalBuildService:
    def __init__(self, catalog_service: CatalogService | None = None) -> None:
        self.catalog_service = catalog_service or CatalogService()
        self.catalog = self.catalog_service.load()
        self.paths = app_paths()
        self.artifact_dir = self.paths.cache_dir / "generic-artifacts"
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="certified-builds")
        self._jobs: dict[str, BuildJobModel] = {}
        self._lock = threading.Lock()

    def submit_build(self, request: BuildRequestModel) -> BuildJobModel:
        job_id = uuid.uuid4().hex
        artifact_name = self._artifact_filename(request)
        artifact_path = self.artifact_dir / artifact_name
        profile, artifact, _bundle_ids = resolve_catalog_selection(self.catalog, request)

        if artifact_path.exists():
            job = BuildJobModel(
                id=job_id,
                request=request,
                status="done",
                message="Using cached certified artifact.",
                artifact_id=artifact.id,
                artifact_path=str(artifact_path),
            )
            with self._lock:
                self._jobs[job_id] = job
            return job

        job = BuildJobModel(
            id=job_id,
            request=request,
            status="queued",
            message=f"Queued certified artifact build for {profile.label}.",
            artifact_id=artifact.id,
        )
        with self._lock:
            self._jobs[job_id] = job
        self._executor.submit(self._run_build, job_id, artifact_name, artifact.id)
        return job

    def _run_build(
        self,
        job_id: str,
        artifact_name: str,
        artifact_id: str,
    ) -> None:
        self._update_job(job_id, status="running", message="Building the generic certified artifact.")
        try:
            request = self.get_job(job_id).request
            manifest = generic_manifest_from_request(self.catalog, request, artifact_name)
            builder = ImageBuilder(
                manifest,
                workspace=self.paths.workspace_dir / "generic-builds",
            )
            output = builder.build()
            if not output.exists():
                raise BuildError(f"Expected artifact was not produced: {output}")
            self._update_job(
                job_id,
                status="done",
                message=f"Certified artifact ready: {output.name}",
                artifact_id=artifact_id,
                artifact_path=str(output),
            )
        except Exception as exc:
            self._update_job(
                job_id,
                status="error",
                message="Certified artifact build failed.",
                error=str(exc),
            )

    def _artifact_filename(self, request: BuildRequestModel) -> str:
        digest = hashlib.sha256(
            json.dumps(request.model_dump(mode="json"), sort_keys=True).encode("utf-8")
        ).hexdigest()[:12]
        safe_profile = request.profile_id.replace("_", "-")
        return f"{safe_profile}-{digest}.img.xz"

    def _update_job(self, job_id: str, **updates: object) -> None:
        with self._lock:
            current = self._jobs[job_id]
            self._jobs[job_id] = current.model_copy(update=updates)

    def get_job(self, job_id: str) -> BuildJobModel:
        with self._lock:
            try:
                return self._jobs[job_id]
            except KeyError as exc:
                raise UnknownBuildJobError(job_id) from exc

    def get_artifact_manifest(self, artifact_id: str) -> ArtifactManifestModel:
        profiles, artifacts = _catalog_maps(self.catalog)
        artifact = artifacts.get(artifact_id)
        if artifact is None:
            raise UnknownBuildJobError(f"Unknown artifact id: {artifact_id}")
        profile = profiles[artifact.profile_id]
        local_path = None
        for job in self._jobs.values():
            if job.artifact_id == artifact_id and job.artifact_path:
                local_path = job.artifact_path
        return ArtifactManifestModel(
            artifact=artifact,
            profile=profile,
            generated_from=BuildRequestModel(profile_id=profile.id),
            local_path=local_path,
        )


class GitHubActionsBuildService:
    def __init__(self, catalog_service: CatalogService | None = None) -> None:
        self.catalog_service = catalog_service or CatalogService()
        self.catalog = self.catalog_service.load()
        self.settings = service_settings()
        self.paths = app_paths()
        self.job_dir = self.paths.cache_dir / "github-actions-jobs"
        self.job_dir.mkdir(parents=True, exist_ok=True)
        self.bundle_dir = self.paths.cache_dir / "github-actions-artifacts"
        self.bundle_dir.mkdir(parents=True, exist_ok=True)
        self.owner = self.settings.github_owner
        self.repo = self.settings.github_repo
        self.workflow_file = self.settings.github_workflow_file
        self.ref = self.settings.github_ref
        self.token = self.settings.github_token
        self.api_url = self.settings.github_api_url.rstrip("/")
        if not self.owner or not self.repo:
            raise RuntimeError(
                "GitHub Actions mode needs BBB_IMAGE_FORGE_GITHUB_OWNER and BBB_IMAGE_FORGE_GITHUB_REPO, "
                "or a GitHub origin remote that can be inferred automatically."
            )
        if not self.token:
            raise RuntimeError(
                "GitHub Actions mode needs BBB_IMAGE_FORGE_GITHUB_TOKEN."
            )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2026-03-10",
            }
        )

    def submit_build(self, request: BuildRequestModel) -> BuildJobModel:
        profile, artifact, _bundle_ids = resolve_catalog_selection(self.catalog, request)
        job_id = uuid.uuid4().hex
        artifact_name = self._artifact_filename(request)
        self._dispatch_workflow(job_id=job_id, request=request, artifact_name=artifact_name)
        job = BuildJobModel(
            id=job_id,
            request=request,
            status="queued",
            message=f"Queued GitHub Actions build for {profile.label}.",
            artifact_id=artifact.id,
        )
        self._save_job_record(
            job,
            submitted_at=self._now().isoformat(),
            artifact_filename=artifact_name,
            artifact_bundle_name=self._artifact_bundle_name(job_id),
        )
        return job

    def get_job(self, job_id: str) -> BuildJobModel:
        record = self._load_job_record(job_id)
        job = BuildJobModel.model_validate(record["job"])
        submitted_at = datetime.fromisoformat(record["submitted_at"])
        if not job.remote_run_id:
            run = self._find_run(job_id=job_id, submitted_at=submitted_at)
            if run is None:
                return job.model_copy(
                    update={
                        "status": "queued",
                        "message": "Waiting for the GitHub Actions runner to start the build.",
                    }
                )
            job = job.model_copy(
                update={
                    "remote_run_id": str(run["id"]),
                    "remote_url": run.get("html_url"),
                }
            )
            self._save_job_record(
                job,
                submitted_at=record["submitted_at"],
                artifact_filename=record["artifact_filename"],
                artifact_bundle_name=record["artifact_bundle_name"],
            )

        run = self._get_run(job.remote_run_id)
        status = run.get("status")
        conclusion = run.get("conclusion")
        remote_url = run.get("html_url")
        if status == "completed":
            if conclusion == "success":
                job = job.model_copy(
                    update={
                        "status": "done",
                        "message": "The remote image build completed successfully.",
                        "artifact_id": self._artifact_reference(job.id, job.remote_run_id),
                        "remote_url": remote_url,
                    }
                )
            else:
                message = f"The remote image build failed ({conclusion or 'unknown conclusion'})."
                job = job.model_copy(
                    update={
                        "status": "error",
                        "message": message,
                        "error": message,
                        "remote_url": remote_url,
                    }
                )
        elif status == "in_progress":
            job = job.model_copy(
                update={
                    "status": "running",
                    "message": "GitHub Actions is building the generic image now.",
                    "remote_url": remote_url,
                }
            )
        else:
            job = job.model_copy(
                update={
                    "status": "queued",
                    "message": f"GitHub Actions build is currently {status or 'queued'}.",
                    "remote_url": remote_url,
                }
            )
        self._save_job_record(
            job,
            submitted_at=record["submitted_at"],
            artifact_filename=record["artifact_filename"],
            artifact_bundle_name=record["artifact_bundle_name"],
        )
        return job

    def get_artifact_manifest(self, artifact_id: str) -> ArtifactManifestModel:
        job_id, run_id = self._parse_artifact_reference(artifact_id)
        record = self._load_job_record(job_id)
        bundle_name = record["artifact_bundle_name"]
        target_dir = self.bundle_dir / job_id
        manifest_path = target_dir / "artifact-manifest.json"
        image_path = target_dir / record["artifact_filename"]

        if not manifest_path.exists() or not image_path.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            artifact = self._find_run_artifact(run_id=run_id, artifact_name=bundle_name)
            self._download_and_extract_artifact(
                artifact_url=artifact["archive_download_url"],
                target_dir=target_dir,
            )

        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = ArtifactManifestModel.model_validate(payload["artifact_manifest"])
        return manifest.model_copy(update={"local_path": str(image_path)})

    def _dispatch_workflow(
        self,
        job_id: str,
        request: BuildRequestModel,
        artifact_name: str,
    ) -> None:
        response = self.session.post(
            self._repo_url(f"/actions/workflows/{self.workflow_file}/dispatches"),
            json={
                "ref": self.ref,
                "inputs": {
                    "request_id": job_id,
                    "profile_id": request.profile_id,
                    "addon_bundle_ids": json.dumps(request.addon_bundle_ids),
                    "artifact_name": artifact_name,
                },
            },
            timeout=20,
        )
        response.raise_for_status()

    def _find_run(self, job_id: str, submitted_at: datetime) -> dict[str, Any] | None:
        created_after = (submitted_at - timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        response = self.session.get(
            self._repo_url(f"/actions/workflows/{self.workflow_file}/runs"),
            params={
                "event": "workflow_dispatch",
                "branch": self.ref,
                "per_page": 30,
                "created": f">={created_after}",
            },
            timeout=20,
        )
        response.raise_for_status()
        runs = response.json().get("workflow_runs", [])
        for run in runs:
            display_title = str(run.get("display_title") or run.get("name") or "")
            if job_id in display_title:
                return run
        for run in runs:
            created_at = run.get("created_at")
            if not created_at:
                continue
            created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if created_dt >= submitted_at - timedelta(minutes=1):
                return run
        return None

    def _get_run(self, run_id: str | None) -> dict[str, Any]:
        if not run_id:
            raise UnknownBuildJobError("Missing remote run id.")
        response = self.session.get(
            self._repo_url(f"/actions/runs/{run_id}"),
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def _find_run_artifact(self, run_id: str, artifact_name: str) -> dict[str, Any]:
        response = self.session.get(
            self._repo_url(f"/actions/runs/{run_id}/artifacts"),
            timeout=20,
        )
        response.raise_for_status()
        artifacts = response.json().get("artifacts", [])
        for artifact in artifacts:
            if artifact.get("name") == artifact_name and not artifact.get("expired"):
                return artifact
        if artifacts:
            return artifacts[0]
        raise UnknownBuildJobError(
            f"No workflow artifacts were found for run {run_id}."
        )

    def _download_and_extract_artifact(self, artifact_url: str, target_dir: Path) -> None:
        zip_path = target_dir / "artifact.zip"
        with self.session.get(artifact_url, stream=True, timeout=120, allow_redirects=True) as response:
            response.raise_for_status()
            with zip_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(target_dir)
        zip_path.unlink(missing_ok=True)

    def _artifact_filename(self, request: BuildRequestModel) -> str:
        digest = hashlib.sha256(
            json.dumps(request.model_dump(mode="json"), sort_keys=True).encode("utf-8")
        ).hexdigest()[:12]
        safe_profile = request.profile_id.replace("_", "-")
        return f"{safe_profile}-{digest}.img.xz"

    @staticmethod
    def _artifact_bundle_name(job_id: str) -> str:
        return f"bbb-image-{job_id}"

    @staticmethod
    def _artifact_reference(job_id: str, run_id: str | None) -> str:
        if not run_id:
            raise UnknownBuildJobError("Cannot create artifact reference without a run id.")
        return f"github-run:{job_id}:{run_id}"

    @staticmethod
    def _parse_artifact_reference(reference: str) -> tuple[str, str]:
        prefix, job_id, run_id = reference.split(":", 2)
        if prefix != "github-run":
            raise UnknownBuildJobError(f"Unsupported artifact reference: {reference}")
        return job_id, run_id

    def _repo_url(self, path: str) -> str:
        return f"{self.api_url}/repos/{self.owner}/{self.repo}{path}"

    def _save_job_record(
        self,
        job: BuildJobModel,
        *,
        submitted_at: str,
        artifact_filename: str,
        artifact_bundle_name: str,
    ) -> None:
        payload = {
            "job": job.model_dump(mode="json"),
            "submitted_at": submitted_at,
            "artifact_filename": artifact_filename,
            "artifact_bundle_name": artifact_bundle_name,
        }
        self._job_path(job.id).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_job_record(self, job_id: str) -> dict[str, Any]:
        path = self._job_path(job_id)
        if not path.exists():
            raise UnknownBuildJobError(job_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def _job_path(self, job_id: str) -> Path:
        return self.job_dir / f"{job_id}.json"

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)


class HttpBuildService:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def submit_build(self, request: BuildRequestModel) -> BuildJobModel:
        response = requests.post(
            f"{self.base_url}/v1/build-jobs",
            json=request.model_dump(mode="json"),
            timeout=15,
        )
        response.raise_for_status()
        return BuildJobModel.model_validate(response.json())

    def get_job(self, job_id: str) -> BuildJobModel:
        response = requests.get(f"{self.base_url}/v1/build-jobs/{job_id}", timeout=15)
        response.raise_for_status()
        return BuildJobModel.model_validate(response.json())

    def get_artifact_manifest(self, artifact_id: str) -> ArtifactManifestModel:
        response = requests.get(
            f"{self.base_url}/v1/artifacts/{artifact_id}/manifest",
            timeout=15,
        )
        response.raise_for_status()
        return ArtifactManifestModel.model_validate(response.json())
