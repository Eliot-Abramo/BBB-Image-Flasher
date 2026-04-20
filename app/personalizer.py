from __future__ import annotations

import json
import lzma
import shutil
import uuid
from pathlib import Path

from app.builder import ImageBuilder, MountedImage
from app.build_service import resolve_catalog_selection
from app.catalog_service import CatalogService
from app.models import PersonalizationRequestModel, PreparedImageModel
from app.profiles import load_profile
from app.settings import app_paths


class ImagePersonalizer:
    def __init__(self, request: PersonalizationRequestModel) -> None:
        self.request = request
        self.paths = app_paths()
        self.catalog = CatalogService().load()

    def prepare(self, artifact_path: str | Path) -> PreparedImageModel:
        profile, _, bundle_ids = resolve_catalog_selection(
            self.catalog,
            self.request_to_build_request(),
        )
        workspace_dir = self.paths.workspace_dir / "prepared" / uuid.uuid4().hex
        workspace_dir.mkdir(parents=True, exist_ok=True)
        raw_image = workspace_dir / f"{profile.id}.img"
        self._materialize_raw_image(Path(artifact_path), raw_image)

        manifest = self._personalized_manifest(bundle_ids)
        builder = ImageBuilder(manifest, workspace=workspace_dir)
        with MountedImage(raw_image) as mount_ctx:
            builder._prepare_rootfs(mount_ctx.rootfs_mount)
            self._reconcile_template_user(builder, mount_ctx.rootfs_mount)
            builder._configure_base_system(mount_ctx.rootfs_mount)
            builder._configure_ssh(mount_ctx.rootfs_mount)
            builder._configure_ethernet(mount_ctx.rootfs_mount)
            builder._configure_wifi(mount_ctx.rootfs_mount)
            builder._write_metadata(mount_ctx.rootfs_mount)
            builder._touch_boot_marker(mount_ctx.boot_mount)
        return PreparedImageModel(
            image_path=str(raw_image),
            image_size_bytes=raw_image.stat().st_size,
            workspace_dir=str(workspace_dir),
        )

    def request_to_build_request(self):
        from app.models import BuildRequestModel

        return BuildRequestModel(
            profile_id=self.request.profile_id,
            addon_bundle_ids=self.request.addon_bundle_ids,
        )

    def cleanup(self, workspace_dir: str | Path) -> None:
        shutil.rmtree(Path(workspace_dir), ignore_errors=True)

    def _materialize_raw_image(self, artifact_path: Path, raw_image: Path) -> None:
        if artifact_path.suffix == ".xz":
            with lzma.open(artifact_path, "rb") as src, raw_image.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=8 * 1024 * 1024)
            return
        shutil.copy2(artifact_path, raw_image)

    def _personalized_manifest(self, bundle_ids: list[str]):
        profile, _, _ = resolve_catalog_selection(
            self.catalog,
            self.request_to_build_request(),
        )
        data = load_profile(profile.profile_name)
        data["bundles"] = bundle_ids
        data["system"] = self.request.system.model_dump(mode="json")
        data["user"] = self.request.user.model_dump(mode="json")
        data["network"] = self.request.network.model_dump(mode="json")
        data["ssh"] = self.request.ssh.model_dump(mode="json")
        data["output"] = {
            "artifact_name": f"{self.request.system.hostname}.img.xz",
        }
        from app.models import ManifestModel

        return ManifestModel.model_validate(data)

    def _reconcile_template_user(self, builder: ImageBuilder, rootfs: Path) -> None:
        metadata_path = rootfs / "opt/bbb-image-forge/manifest-resolved.json"
        desired = self.request.user.username
        template_user = "student"
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                template_user = metadata.get("template_username") or template_user
            except Exception:
                pass
        if template_user == desired:
            return
        builder._run_in_chroot(
            rootfs,
            [
                "bash",
                "-lc",
                (
                    "if id -u "
                    + template_user
                    + " >/dev/null 2>&1 && ! id -u "
                    + desired
                    + " >/dev/null 2>&1; then "
                    + "groupmod -n "
                    + desired
                    + " "
                    + template_user
                    + " >/dev/null 2>&1 || true; "
                    + "usermod -l "
                    + desired
                    + " -m -d /home/"
                    + desired
                    + " "
                    + template_user
                    + "; "
                    + "fi"
                ),
            ],
        )
