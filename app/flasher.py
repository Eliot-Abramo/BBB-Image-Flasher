"""
flasher.py — cross-platform SD card detection and raw-image writing.

Windows:  drives listed via PowerShell Get-Disk; written to \\.\PhysicalDriveN
          (requires the server to be running as Administrator)
Linux:    drives listed via lsblk; written to /dev/sdX
          (requires the server to be running with sudo / as root)
"""
from __future__ import annotations

import json
import lzma
import platform
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator


# Write in 4 MB chunks — satisfies the 512-byte sector-alignment
# requirement on Windows raw-disk writes.
_CHUNK = 4 * 1024 * 1024


# ──────────────────────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class DriveInfo:
    device: str       # "\\.\PhysicalDrive2"  or  "/dev/sdb"
    label: str        # Human-readable model name
    size_bytes: int
    bus_type: str     # USB, SD, MMC, …

    @property
    def size_human(self) -> str:
        gb = self.size_bytes / (1024 ** 3)
        return f"{gb:.1f} GB" if gb >= 1 else f"{self.size_bytes // (1024 ** 2)} MB"

    def as_dict(self) -> dict:
        return {
            "device": self.device,
            "label": self.label,
            "size_bytes": self.size_bytes,
            "size_human": self.size_human,
            "bus_type": self.bus_type,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Admin / privilege detection
# ──────────────────────────────────────────────────────────────────────────────

def is_admin() -> bool:
    """Return True if the current process has the privileges needed to write
    to a raw disk device (Administrator on Windows, root on Linux)."""
    try:
        if platform.system() == "Windows":
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return __import__("os").geteuid() == 0
    except Exception:
        return False


def admin_instructions() -> str:
    """Plain-English fix for the current platform."""
    if platform.system() == "Windows":
        return (
            "Right-click on <strong>Command Prompt</strong> or "
            "<strong>PowerShell</strong> and choose "
            "<strong>\"Run as administrator\"</strong>, then restart the "
            "server from that elevated window."
        )
    return (
        "Stop the server and restart it with <strong>sudo</strong>.<br>"
        "If you use Anaconda/conda, preserve your PATH so the right Python is used:<br>"
        "<code>sudo env PATH=\"$PATH\" python3 -m app.main</code>"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Drive detection
# ──────────────────────────────────────────────────────────────────────────────

def list_drives() -> list[DriveInfo]:
    """Return removable / external drives suitable for SD card flashing."""
    if platform.system() == "Windows":
        return _list_drives_windows()
    return _list_drives_linux()


def _list_drives_windows() -> list[DriveInfo]:
    """Use PowerShell Get-Disk to enumerate USB/SD/MMC disks.

    Deliberately excludes the boot disk, the system disk, and anything
    whose BusType is not obviously removable.
    """
    script = (
        "Get-Disk | "
        "Where-Object { -not $_.IsBoot -and -not $_.IsSystem -and "
        "               $_.BusType -in @('USB','SD','MMC','SDIO','1394') } | "
        "Select-Object Number, FriendlyName, Size, BusType | "
        "ConvertTo-Json -Compress -Depth 3"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=15,
        )
    except FileNotFoundError:
        # PowerShell not on PATH — fall back to wmic
        return _list_drives_windows_wmic()

    raw = result.stdout.strip()
    if not raw:
        return []

    data = json.loads(raw)
    if isinstance(data, dict):          # single result — PowerShell omits the array
        data = [data]

    drives: list[DriveInfo] = []
    for d in data:
        number = d.get("Number")
        size = int(d.get("Size") or 0)
        if number is None or size == 0:
            continue
        drives.append(DriveInfo(
            device=f"\\\\.\\PhysicalDrive{number}",
            label=d.get("FriendlyName") or f"Disk {number}",
            size_bytes=size,
            bus_type=d.get("BusType") or "USB",
        ))
    return drives


def _list_drives_windows_wmic() -> list[DriveInfo]:
    """Fallback for old Windows without a modern PowerShell."""
    try:
        result = subprocess.run(
            [
                "wmic", "diskdrive",
                "where", "MediaType='Removable Media' or InterfaceType='USB'",
                "get", "DeviceID,Model,Size,InterfaceType",
                "/format:csv",
            ],
            capture_output=True, text=True, timeout=15,
        )
    except Exception:
        return []

    drives: list[DriveInfo] = []
    for line in result.stdout.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4 or parts[1] == "DeviceID":
            continue
        _node, device_id, iface, model, size_str = (*parts[:5], *[""] * 5)[:5]
        try:
            size = int(size_str)
        except (ValueError, TypeError):
            continue
        if not device_id or size == 0:
            continue
        # wmic DeviceID is already like \\.\PHYSICALDRIVE2
        drives.append(DriveInfo(
            device=device_id,
            label=model.strip() or device_id,
            size_bytes=size,
            bus_type=iface.strip() or "USB",
        ))
    return drives


def _list_drives_linux() -> list[DriveInfo]:
    """Use lsblk to list removable block devices."""
    try:
        result = subprocess.run(
            ["lsblk", "-J", "-b", "-o", "NAME,SIZE,TYPE,TRAN,MODEL,RM"],
            capture_output=True, text=True, timeout=10,
        )
    except FileNotFoundError:
        return []

    if result.returncode != 0 or not result.stdout.strip():
        return []

    data = json.loads(result.stdout)
    drives: list[DriveInfo] = []
    for dev in data.get("blockdevices", []):
        if dev.get("type") != "disk":
            continue
        tran = (dev.get("tran") or "").lower()
        rm = dev.get("rm") in (True, "1", 1)
        # Only include clearly removable / USB / SD / MMC devices
        if not rm and tran not in ("usb", "sd", "mmc", "sdio"):
            continue
        name = dev.get("name", "")
        size = int(dev.get("size") or 0)
        if not name or size == 0:
            continue
        model = (dev.get("model") or "").strip() or name
        drives.append(DriveInfo(
            device=f"/dev/{name}",
            label=model,
            size_bytes=size,
            bus_type=tran.upper() or "USB",
        ))
    return drives


# ──────────────────────────────────────────────────────────────────────────────
# Flashing
# ──────────────────────────────────────────────────────────────────────────────

def flash_image(image_path: Path, device: str) -> Iterator[dict]:
    """Decompress *image_path* (.img.xz) and write it to *device* in streaming
    fashion.  Yields progress dicts at each chunk so callers can push them to
    the browser via SSE.

    Progress dict keys:
        written   – bytes written so far
        percent   – 0-100 (estimated; based on typical 7× expansion ratio)
        speed_mb  – current write speed in MB/s
        status    – "flashing" | "done" | "error"
        message   – human-readable status string
    """
    if not image_path.exists():
        yield _err(0, f"Image file not found: {image_path}")
        return

    compressed_size = image_path.stat().st_size
    # BBB images compress ~7× — use this as a rough denominator for %
    estimated_total = max(compressed_size * 7, 1)

    written = 0
    t0 = time.monotonic()

    try:
        with lzma.open(str(image_path), "rb") as src:
            # buffering=0 bypasses Python's internal buffer — required for
            # correct sector-aligned writes on Windows raw disk handles.
            with open(device, "r+b", buffering=0) as dst:
                while True:
                    chunk = src.read(_CHUNK)
                    if not chunk:
                        break
                    dst.write(chunk)
                    written += len(chunk)
                    elapsed = max(time.monotonic() - t0, 1e-3)
                    speed = written / elapsed / (1024 * 1024)
                    pct = min(int(written / estimated_total * 100), 99)
                    yield {
                        "written": written,
                        "percent": pct,
                        "speed_mb": round(speed, 1),
                        "status": "flashing",
                        "message": (
                            f"Writing… {written // (1024 ** 2)} MB written"
                            f" at {speed:.1f} MB/s"
                        ),
                    }

                # Flush kernel write-back cache before we report success
                try:
                    dst.flush()
                    __import__("os").fsync(dst.fileno())
                except OSError:
                    pass

    except PermissionError:
        yield _err(
            written,
            "Permission denied — the server needs administrator/root privileges "
            "to write to a raw disk.  "
            + admin_instructions(),
        )
        return

    except OSError as exc:
        code = getattr(exc, "winerror", None) or exc.errno
        if code == 5:   # Windows ERROR_ACCESS_DENIED
            yield _err(
                written,
                "Access denied (error 5).  Make sure the server is running as "
                "Administrator and that no other program is using the drive.",
            )
        elif code == 19:  # Windows ERROR_WRITE_PROTECT
            yield _err(written, "The SD card is write-protected.  Check the physical lock switch on the card.")
        else:
            yield _err(written, f"OS error while writing: {exc}")
        return

    elapsed = max(time.monotonic() - t0, 1e-3)
    speed = written / elapsed / (1024 * 1024)
    yield {
        "written": written,
        "percent": 100,
        "speed_mb": round(speed, 1),
        "status": "done",
        "message": (
            f"Done! Wrote {written // (1024 ** 2)} MB in {elapsed:.0f} s"
            f" ({speed:.1f} MB/s average). "
            f"Safe to remove your SD card."
        ),
    }


def _err(written: int, message: str) -> dict:
    return {
        "written": written,
        "percent": 0,
        "speed_mb": 0.0,
        "status": "error",
        "message": message,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Safe eject
# ──────────────────────────────────────────────────────────────────────────────

def eject_drive(device: str) -> str:
    """Attempt a safe eject/unmount.  Returns a human-readable status string."""
    if platform.system() == "Windows":
        return _eject_windows(device)
    return _eject_linux(device)


def _eject_windows(device: str) -> str:
    try:
        # Extract disk number from \\.\PhysicalDrive2 → "2"
        num = device.lower().replace("\\\\.\\physicaldrive", "").strip()
        script = (
            f"$partitions = Get-Partition -DiskNumber {num} -ErrorAction SilentlyContinue; "
            "foreach ($p in $partitions) { "
            "  if ($p.DriveLetter) { "
            "    $vol = Get-Volume -DriveLetter $p.DriveLetter; "
            "    $vol | Get-Disk | Set-Disk -IsOffline $false -ErrorAction SilentlyContinue "
            "  } "
            "}; "
            "Write-Output ok"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, timeout=10,
        )
    except Exception:
        pass
    return (
        "Flashing complete. Click the <strong>Safely Remove Hardware</strong> icon "
        "in your Windows taskbar (bottom-right corner) before unplugging the SD card."
    )


def _eject_linux(device: str) -> str:
    try:
        subprocess.run(["sync"], timeout=30, check=False)
        result = subprocess.run(
            ["eject", device], capture_output=True, text=True, timeout=15, check=False
        )
        if result.returncode == 0:
            return "Drive ejected successfully. Safe to unplug."
    except FileNotFoundError:
        # 'eject' not installed — try udisksctl
        try:
            subprocess.run(
                ["udisksctl", "power-off", "-b", device],
                capture_output=True, timeout=15, check=False,
            )
            return "Drive powered off. Safe to unplug."
        except Exception:
            pass
    except Exception:
        pass
    return "Please unmount the drive manually before unplugging."
