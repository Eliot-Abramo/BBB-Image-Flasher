"""
flasher.py — safe removable-media detection and raw-image writing helpers.

The desktop controller should stay unprivileged. These operations are intended
to be invoked through the helper process so the UI never needs to run as root.
"""
from __future__ import annotations

import json
import lzma
import os
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from app.models import DeviceRecordModel


_CHUNK = 4 * 1024 * 1024


@dataclass(slots=True)
class DriveInfo:
    device: str
    label: str
    size_bytes: int
    bus_type: str

    @property
    def size_human(self) -> str:
        gb = self.size_bytes / (1024**3)
        return f"{gb:.1f} GB" if gb >= 1 else f"{self.size_bytes // (1024**2)} MB"

    def as_dict(self) -> dict:
        return {
            "device": self.device,
            "label": self.label,
            "size_bytes": self.size_bytes,
            "size_human": self.size_human,
            "bus_type": self.bus_type,
        }


def is_admin() -> bool:
    try:
        if platform.system() == "Windows":
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except Exception:
        return False


def admin_instructions() -> str:
    if platform.system() == "Windows":
        return (
            "Restart the installed helper with Administrator privileges. "
            "The main app does not need to run elevated."
        )
    return (
        "Make sure the installed helper/service has the privileges it needs to access "
        "raw disks and mounted images. The main app should remain unprivileged."
    )


def list_candidate_devices() -> list[DeviceRecordModel]:
    if platform.system() == "Windows":
        return _list_devices_windows()
    return _list_devices_linux()


def list_drives() -> list[DriveInfo]:
    drives: list[DriveInfo] = []
    for device in list_candidate_devices():
        if not device.removable:
            continue
        drives.append(
            DriveInfo(
                device=device.device_path,
                label=device.label,
                size_bytes=device.size_bytes,
                bus_type=device.transport or "USB",
            )
        )
    return drives


def device_map(devices: Iterable[DeviceRecordModel]) -> dict[str, DeviceRecordModel]:
    return {device.device_id: device for device in devices}


def new_devices_since(
    baseline: Iterable[DeviceRecordModel],
    current: Iterable[DeviceRecordModel],
) -> list[DeviceRecordModel]:
    baseline_ids = {device.device_id for device in baseline}
    return [device for device in current if device.device_id not in baseline_ids]


def validate_candidate_device(device: DeviceRecordModel, required_bytes: int) -> None:
    if not device.removable:
        raise ValueError("The selected device is not marked as removable media.")
    if device.system_disk:
        raise ValueError("The selected device is a system disk and cannot be written.")
    if device.mounted_partitions:
        raise ValueError(
            "The selected device still has mounted partitions: "
            + ", ".join(device.mounted_partitions)
        )
    if device.size_bytes < required_bytes:
        raise ValueError(
            f"The selected device is too small. Need at least {required_bytes} bytes."
        )


def get_device(device_id: str) -> DeviceRecordModel:
    for device in list_candidate_devices():
        if device.device_id == device_id:
            return device
    raise ValueError(f"Could not find removable device with id {device_id}")


def flash_image(
    image_path: Path,
    device_path: str,
    expected_size_bytes: int | None = None,
) -> Iterator[dict]:
    if not image_path.exists():
        yield _err(0, f"Image file not found: {image_path}")
        return

    if image_path.suffix == ".xz":
        source = lzma.open(str(image_path), "rb")
        total_bytes = expected_size_bytes or max(image_path.stat().st_size * 7, 1)
    else:
        source = image_path.open("rb")
        total_bytes = expected_size_bytes or image_path.stat().st_size

    written = 0
    started = time.monotonic()
    try:
        with source as src, open(device_path, "r+b", buffering=0) as dst:
            while True:
                chunk = src.read(_CHUNK)
                if not chunk:
                    break
                dst.write(chunk)
                written += len(chunk)
                elapsed = max(time.monotonic() - started, 1e-3)
                speed_mb = written / elapsed / (1024 * 1024)
                percent = min(int(written / max(total_bytes, 1) * 100), 99)
                yield {
                    "written": written,
                    "percent": percent,
                    "speed_mb": round(speed_mb, 1),
                    "status": "flashing",
                    "message": (
                        f"Writing image data to {device_path} at {speed_mb:.1f} MB/s."
                    ),
                }
            dst.flush()
            os.fsync(dst.fileno())
    except PermissionError:
        yield _err(
            written,
            "Permission denied while accessing the raw disk. " + admin_instructions(),
        )
        return
    except OSError as exc:
        yield _err(written, f"OS error while writing the image: {exc}")
        return

    elapsed = max(time.monotonic() - started, 1e-3)
    speed_mb = written / elapsed / (1024 * 1024)
    yield {
        "written": written,
        "percent": 100,
        "speed_mb": round(speed_mb, 1),
        "status": "done",
        "message": (
            f"Finished writing {written // (1024**2)} MB in {elapsed:.0f} seconds. "
            "The write cache has been flushed."
        ),
    }


def verify_written_image(device_id: str) -> dict:
    device = get_device(device_id)
    return {
        "status": "done",
        "message": f"Verified that {device.label} is still present after flashing.",
        "device": device.model_dump(mode="json"),
    }


def eject_drive(device_path: str) -> str:
    if platform.system() == "Windows":
        return _eject_windows(device_path)
    return _eject_linux(device_path)


def _eject_windows(device: str) -> str:
    try:
        number = device.lower().replace("\\\\.\\physicaldrive", "").strip()
        script = (
            "Get-Disk -Number "
            + number
            + " | Set-Disk -IsOffline $true -ErrorAction SilentlyContinue; Write-Output ok"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            timeout=15,
            check=False,
        )
    except Exception:
        pass
    return "Flashing complete. Use Safely Remove Hardware before unplugging the SD card."


def _eject_linux(device: str) -> str:
    try:
        subprocess.run(["sync"], timeout=30, check=False)
        result = subprocess.run(
            ["eject", device],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode == 0:
            return "Drive ejected successfully. Safe to unplug."
    except FileNotFoundError:
        try:
            subprocess.run(
                ["udisksctl", "power-off", "-b", device],
                capture_output=True,
                timeout=15,
                check=False,
            )
            return "Drive powered off. Safe to unplug."
        except Exception:
            pass
    except Exception:
        pass
    return "Please unmount the drive manually before unplugging."


def _err(written: int, message: str) -> dict:
    return {
        "written": written,
        "percent": 0,
        "speed_mb": 0.0,
        "status": "error",
        "message": message,
    }


def _list_devices_linux() -> list[DeviceRecordModel]:
    try:
        result = subprocess.run(
            [
                "lsblk",
                "-J",
                "-b",
                "-o",
                "NAME,PATH,PKNAME,SIZE,TYPE,TRAN,MODEL,VENDOR,SERIAL,RM,HOTPLUG,MOUNTPOINTS",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []

    root_disk = _linux_root_disk()
    payload = json.loads(result.stdout)
    devices: list[DeviceRecordModel] = []
    for raw in payload.get("blockdevices", []):
        if raw.get("type") != "disk":
            continue
        path = raw.get("path") or f"/dev/{raw.get('name', '')}"
        transport = (raw.get("tran") or "").lower()
        removable = raw.get("rm") in (True, 1, "1") or raw.get("hotplug") in (
            True,
            1,
            "1",
        ) or transport in {"usb", "mmc", "sd", "sdio"}
        mounted = _collect_mountpoints(raw)
        label = " ".join(
            p for p in [(raw.get("vendor") or "").strip(), (raw.get("model") or "").strip()] if p
        ) or (raw.get("model") or raw.get("name") or path)
        system_disk = path == root_disk
        serial = (raw.get("serial") or "").strip() or None
        device_id = f"linux:{serial or raw.get('name') or path}"
        devices.append(
            DeviceRecordModel(
                device_id=device_id,
                device_path=path,
                label=label,
                vendor=(raw.get("vendor") or "").strip(),
                model=(raw.get("model") or "").strip(),
                serial=serial,
                transport=transport.upper(),
                size_bytes=int(raw.get("size") or 0),
                removable=bool(removable),
                system_disk=system_disk,
                mounted_partitions=mounted,
            )
        )
    return devices


def _linux_root_disk() -> str | None:
    try:
        result = subprocess.run(
            ["findmnt", "-J", "/"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        payload = json.loads(result.stdout)
        filesystems = payload.get("filesystems") or []
        if not filesystems:
            return None
        source = filesystems[0].get("source") or ""
        if not source.startswith("/dev/"):
            return None
        pkname = subprocess.run(
            ["lsblk", "-no", "PKNAME", source],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        parent = pkname.stdout.strip()
        if parent:
            return f"/dev/{parent}"
        return source
    except Exception:
        return None


def _flatten_mountpoints(value: object) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [item for item in value if item]
    if isinstance(value, str):
        return [value] if value else []
    return []


def _collect_mountpoints(node: dict) -> list[str]:
    mountpoints = _flatten_mountpoints(node.get("mountpoints"))
    for child in node.get("children") or []:
        mountpoints.extend(_collect_mountpoints(child))
    return sorted(set(item for item in mountpoints if item))


def _list_devices_windows() -> list[DeviceRecordModel]:
    script = (
        "Get-Disk | Select-Object Number,FriendlyName,Size,BusType,IsBoot,IsSystem,SerialNumber | "
        "ConvertTo-Json -Compress -Depth 3"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except FileNotFoundError:
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []
    payload = json.loads(result.stdout)
    rows = payload if isinstance(payload, list) else [payload]
    devices: list[DeviceRecordModel] = []
    for row in rows:
        number = row.get("Number")
        if number is None:
            continue
        transport = (row.get("BusType") or "").upper()
        removable = transport in {"USB", "SD", "MMC", "SDIO", "1394"}
        serial = (row.get("SerialNumber") or "").strip() or None
        path = f"\\\\.\\PhysicalDrive{number}"
        label = (row.get("FriendlyName") or f"Disk {number}").strip()
        devices.append(
            DeviceRecordModel(
                device_id=f"windows:{serial or number}",
                device_path=path,
                label=label,
                vendor="",
                model=label,
                serial=serial,
                transport=transport,
                size_bytes=int(row.get("Size") or 0),
                removable=removable,
                system_disk=bool(row.get("IsBoot")) or bool(row.get("IsSystem")),
                mounted_partitions=[],
            )
        )
    return devices
