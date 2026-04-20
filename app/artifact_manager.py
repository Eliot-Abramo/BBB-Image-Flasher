from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import requests

from app.models import ArtifactManifestModel
from app.settings import app_paths


class ArtifactDownloadError(RuntimeError):
    pass


class ArtifactManager:
    def __init__(self) -> None:
        self.paths = app_paths()
        self.download_dir = self.paths.cache_dir / "downloads"
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def ensure_local_artifact(
        self,
        manifest: ArtifactManifestModel,
        progress: Callable[[str], None] | None = None,
    ) -> Path:
        if manifest.local_path:
            path = Path(manifest.local_path)
            if not path.exists():
                raise ArtifactDownloadError(f"Local artifact is missing: {path}")
            if progress:
                progress(f"Using cached certified artifact: {path.name}")
            return path

        url = manifest.artifact.download_url
        if url is None:
            raise ArtifactDownloadError(
                "No download URL is available for the certified artifact."
            )

        parsed = urlparse(str(url))
        filename = Path(parsed.path).name or f"{manifest.artifact.id}.img.xz"
        target = self.download_dir / filename
        temp_target = target.with_suffix(target.suffix + ".part")

        if target.exists() and self._is_verified(target, manifest.artifact.sha256):
            if progress:
                progress(f"Using verified downloaded artifact: {target.name}")
            return target

        headers: dict[str, str] = {}
        resume_from = temp_target.stat().st_size if temp_target.exists() else 0
        if resume_from:
            headers["Range"] = f"bytes={resume_from}-"
            if progress:
                progress(f"Resuming artifact download at {resume_from // (1024**2)} MB.")
        else:
            if progress:
                progress("Downloading the certified artifact.")

        with requests.get(str(url), headers=headers, stream=True, timeout=60) as response:
            if response.status_code not in {200, 206}:
                raise ArtifactDownloadError(
                    f"Artifact download failed with HTTP {response.status_code}."
                )
            mode = "ab" if response.status_code == 206 else "wb"
            with temp_target.open(mode) as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)

        temp_target.replace(target)
        if not self._is_verified(target, manifest.artifact.sha256):
            raise ArtifactDownloadError(
                f"Artifact checksum verification failed for {target.name}."
            )
        return target

    def copy_into_managed_cache(self, path: str | Path) -> Path:
        source = Path(path)
        target = self.download_dir / source.name
        if source.resolve() == target.resolve():
            return target
        shutil.copy2(source, target)
        return target

    def _is_verified(self, path: Path, expected_sha256: str | None) -> bool:
        if not expected_sha256:
            return path.exists() and path.stat().st_size > 0
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest().lower() == expected_sha256.lower()
