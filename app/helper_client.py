from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Iterator

from app.models import DeviceRecordModel, HelperHealthModel, PersonalizationRequestModel, PreparedImageModel
from app.settings import app_paths, service_settings


class HelperClientError(RuntimeError):
    pass


class HelperClient:
    def __init__(self) -> None:
        self.settings = service_settings()
        self.paths = app_paths()

    def healthcheck(self) -> HelperHealthModel:
        payload = self._run_json(["healthcheck"])
        return HelperHealthModel.model_validate(payload)

    def list_devices(self) -> list[DeviceRecordModel]:
        payload = self._run_json(["list-devices"])
        return [DeviceRecordModel.model_validate(item) for item in payload]

    def prepare_image(
        self,
        artifact_path: str | Path,
        request: PersonalizationRequestModel,
    ) -> PreparedImageModel:
        with tempfile.NamedTemporaryFile(
            suffix=".json",
            prefix="bbb-image-forge-request-",
            dir=self.paths.temp_dir,
            delete=False,
        ) as handle:
            request_path = Path(handle.name)
            handle.write(request.model_dump_json(indent=2).encode("utf-8"))
        try:
            payload = self._run_json(
                ["prepare-image", str(Path(artifact_path)), str(request_path)]
            )
            return PreparedImageModel.model_validate(payload)
        finally:
            request_path.unlink(missing_ok=True)

    def stream_flash_image(
        self,
        image_path: str | Path,
        device_id: str,
        expected_size_bytes: int,
    ) -> Iterator[dict]:
        process = subprocess.Popen(
            [
                *self.settings.helper_command,
                "flash-image",
                str(Path(image_path)),
                device_id,
                "--expected-size-bytes",
                str(expected_size_bytes),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert process.stdout is not None
        for line in process.stdout:
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = {"status": "error", "message": text}
            yield payload
            if payload.get("status") in {"done", "error"}:
                break
        process.wait()
        if process.returncode != 0:
            raise HelperClientError(
                f"Helper flash-image failed with exit code {process.returncode}."
            )

    def verify_image(self, device_id: str) -> dict:
        return self._run_json(["verify-image", device_id])

    def eject_device(self, device_id: str) -> dict:
        return self._run_json(["eject-device", device_id])

    def cleanup_workspace(self, workspace_dir: str | Path) -> dict:
        return self._run_json(["cleanup-workspace", str(Path(workspace_dir))])

    def _run_json(self, args: list[str]) -> dict | list[dict]:
        process = subprocess.run(
            [*self.settings.helper_command, *args],
            capture_output=True,
            text=True,
        )
        if process.returncode != 0:
            raise HelperClientError(process.stdout.strip() or process.stderr.strip())
        text = process.stdout.strip()
        if not text:
            return {}
        return json.loads(text)
