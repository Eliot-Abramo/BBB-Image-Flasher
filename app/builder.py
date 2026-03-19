from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import requests

from app.manifests import resolved_package_list
from app.models import ManifestModel


class BuildError(RuntimeError):
    pass


class ImageBuilder:
    def __init__(self, manifest: ManifestModel, workspace: str | Path = "build") -> None:
        self.manifest = manifest
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.download_dir = self.workspace / "downloads"
        self.output_dir = self.workspace / "artifacts"
        self.work_dir = self.workspace / "work"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def build(self) -> Path:
        compressed = self._download_base_image()
        self._verify_sha256(compressed, self.manifest.base_image.sha256)
        raw_image = self._decompress_image(compressed)
        custom_image = self.work_dir / self.manifest.output.artifact_name.replace(".xz", "")
        shutil.copy2(raw_image, custom_image)

        if self.manifest.provision_mode == "offline":
            self._customize_offline(custom_image)
        else:
            self._inject_firstboot_only(custom_image)

        report = self._write_build_report(custom_image)
        output_path = self._compress_output(custom_image)
        print(f"Build report: {report}")
        return output_path

    def _download_base_image(self) -> Path:
        filename = Path(str(self.manifest.base_image.url)).name
        target = self.download_dir / filename
        if target.exists():
            return target
        with requests.get(str(self.manifest.base_image.url), stream=True, timeout=60) as response:
            response.raise_for_status()
            with target.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        return target

    def _verify_sha256(self, path: Path, expected: str) -> None:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        actual = digest.hexdigest()
        if actual.lower() != expected.lower():
            raise BuildError(f"SHA256 mismatch for {path.name}: {actual} != {expected}")

    def _decompress_image(self, compressed: Path) -> Path:
        raw = self.work_dir / compressed.name.replace(".xz", "")
        if raw.exists():
            return raw
        self._run(["xz", "-dk", str(compressed)], cwd=compressed.parent)
        decompressed = compressed.with_suffix("")
        shutil.move(decompressed, raw)
        return raw

    def _customize_offline(self, image_path: Path) -> None:
        with MountedImage(image_path) as mount_ctx:
            rootfs = mount_ctx.rootfs_mount
            bootfs = mount_ctx.boot_mount
            self._prepare_rootfs(rootfs)
            self._configure_base_system(rootfs)
            self._configure_ssh(rootfs)
            self._configure_wifi(rootfs)
            self._install_packages(rootfs)
            self._write_metadata(rootfs)
            self._touch_boot_marker(bootfs)

    def _inject_firstboot_only(self, image_path: Path) -> None:
        with MountedImage(image_path) as mount_ctx:
            rootfs = mount_ctx.rootfs_mount
            self._prepare_rootfs(rootfs)
            self._configure_base_system(rootfs)
            self._configure_ssh(rootfs)
            self._configure_wifi(rootfs)
            self._install_firstboot_service(rootfs)
            self._write_metadata(rootfs)

    def _prepare_rootfs(self, rootfs: Path) -> None:
        qemu_binary = shutil.which("qemu-arm-static")
        if qemu_binary:
            target = rootfs / "usr/bin/qemu-arm-static"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(qemu_binary, target)

        for directory in ["proc", "sys", "dev", "run"]:
            (rootfs / directory).mkdir(parents=True, exist_ok=True)

    def _configure_base_system(self, rootfs: Path) -> None:
        (rootfs / "etc/hostname").write_text(f"{self.manifest.system.hostname}\n", encoding="utf-8")

        user = self.manifest.user.username
        self._run_in_chroot(
            rootfs,
            ["bash", "-lc", f"id -u {user} >/dev/null 2>&1 || useradd -m -s /bin/bash {user}"],
        )
        if self.manifest.user.password_locked:
            self._run_in_chroot(rootfs, ["passwd", "-l", user])

        ssh_dir = rootfs / "home" / user / ".ssh"
        ssh_dir.mkdir(parents=True, exist_ok=True)
        authorized_keys = ssh_dir / "authorized_keys"
        authorized_keys.write_text("\n".join(self.manifest.user.authorized_keys) + "\n", encoding="utf-8")
        os.chmod(ssh_dir, 0o700)
        os.chmod(authorized_keys, 0o600)
        self._run_in_chroot(rootfs, ["chown", "-R", f"{user}:{user}", f"/home/{user}/.ssh"])

        timezone_file = rootfs / "etc/timezone"
        timezone_file.write_text(f"{self.manifest.system.timezone}\n", encoding="utf-8")

    def _configure_ssh(self, rootfs: Path) -> None:
        conf_dir = rootfs / "etc/ssh/sshd_config.d"
        conf_dir.mkdir(parents=True, exist_ok=True)
        contents = [
            f"PasswordAuthentication {'no' if self.manifest.ssh.disable_password_auth else 'yes'}",
            f"PermitRootLogin {'no' if not self.manifest.ssh.permit_root_login else 'yes'}",
            "PubkeyAuthentication yes",
        ]
        (conf_dir / "90-bbb-image-forge.conf").write_text("\n".join(contents) + "\n", encoding="utf-8")

    def _configure_wifi(self, rootfs: Path) -> None:
        wifi = self.manifest.network.wifi
        if wifi is None:
            return
        network_dir = rootfs / "etc/systemd/network"
        network_dir.mkdir(parents=True, exist_ok=True)
        (network_dir / "25-wlan0.network").write_text(
            "[Match]\nName=wlan0\n\n[Network]\nDHCP=yes\n",
            encoding="utf-8",
        )
        wpa_dir = rootfs / "etc/wpa_supplicant"
        wpa_dir.mkdir(parents=True, exist_ok=True)
        (wpa_dir / "wpa_supplicant-wlan0.conf").write_text(
            f'ctrl_interface=DIR=/run/wpa_supplicant GROUP=netdev\nupdate_config=1\ncountry=CH\n\nnetwork={{\n    ssid="{wifi.ssid}"\n    psk="{wifi.psk}"\n}}\n',
            encoding="utf-8",
        )
        self._run_in_chroot(rootfs, ["systemctl", "enable", "wpa_supplicant@wlan0.service"])
        self._run_in_chroot(rootfs, ["systemctl", "enable", "systemd-networkd.service"])

    def _install_packages(self, rootfs: Path) -> None:
        packages = resolved_package_list(self.manifest)
        if not packages:
            return
        if self.manifest.freeze.debian_snapshot:
            self._apply_debian_snapshot(rootfs, self.manifest.freeze.debian_snapshot)
        env = {"DEBIAN_FRONTEND": "noninteractive"}
        self._run_in_chroot(rootfs, ["apt-get", "update"], env=env)
        self._run_in_chroot(rootfs, ["apt-get", "install", "-y", *packages], env=env)
        self._run_in_chroot(rootfs, ["apt-get", "clean"], env=env)

    def _install_firstboot_service(self, rootfs: Path) -> None:
        packages = resolved_package_list(self.manifest)
        pkg_line = " ".join(packages)
        script = rootfs / "usr/local/sbin/bbb-image-forge-firstboot.sh"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "export DEBIAN_FRONTEND=noninteractive\n"
            "apt-get update\n"
            f"apt-get install -y {pkg_line}\n"
            "systemctl disable bbb-image-forge-firstboot.service\n"
            "rm -f /etc/systemd/system/bbb-image-forge-firstboot.service\n"
            "rm -f /usr/local/sbin/bbb-image-forge-firstboot.sh\n",
            encoding="utf-8",
        )
        os.chmod(script, 0o755)
        unit = rootfs / "etc/systemd/system/bbb-image-forge-firstboot.service"
        unit.parent.mkdir(parents=True, exist_ok=True)
        unit.write_text(
            "[Unit]\nDescription=BBB Image Forge first boot provisioning\nAfter=network-online.target\nWants=network-online.target\n\n"
            "[Service]\nType=oneshot\nExecStart=/usr/local/sbin/bbb-image-forge-firstboot.sh\nRemainAfterExit=yes\n\n"
            "[Install]\nWantedBy=multi-user.target\n",
            encoding="utf-8",
        )
        self._run_in_chroot(rootfs, ["systemctl", "enable", "bbb-image-forge-firstboot.service"])

    def _apply_debian_snapshot(self, rootfs: Path, timestamp: str) -> None:
        suite = self._debian_suite()
        snapshot_tag = timestamp.replace(":", "").replace("-", "")
        content = (
            f"deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/{snapshot_tag}/ {suite} main contrib non-free non-free-firmware\n"
            f"deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/{snapshot_tag}/ {suite}-security main contrib non-free non-free-firmware\n"
            f"deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/{snapshot_tag}/ {suite}-updates main contrib non-free non-free-firmware\n"
        )
        (rootfs / "etc/apt/sources.list").write_text(content, encoding="utf-8")
        apt_conf = rootfs / "etc/apt/apt.conf.d/99snapshot"
        apt_conf.write_text('Acquire::Check-Valid-Until "false";\n', encoding="utf-8")

    def _debian_suite(self) -> str:
        label = self.manifest.base_image.label.lower()
        url = str(self.manifest.base_image.url).lower()
        searchable = f"{label} {url}"
        if "debian 13" in searchable or "trixie" in searchable:
            return "trixie"
        if "debian 12" in searchable or "bookworm" in searchable:
            return "bookworm"
        if "debian 11" in searchable or "bullseye" in searchable:
            return "bullseye"
        return "trixie"

    def _write_metadata(self, rootfs: Path) -> None:
        metadata_dir = rootfs / "opt/bbb-image-forge"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "hostname": self.manifest.system.hostname,
            "bundles": self.manifest.bundles,
            "extra_packages": self.manifest.apt.extra_packages,
            "base_image": self.manifest.base_image.label,
            "base_url": str(self.manifest.base_image.url),
            "snapshot": self.manifest.freeze.debian_snapshot,
            "provision_mode": self.manifest.provision_mode,
        }
        (metadata_dir / "manifest-resolved.json").write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

    def _touch_boot_marker(self, bootfs: Path) -> None:
        (bootfs / "bbb-image-forge.txt").write_text(
            f"Built for {self.manifest.system.hostname}\n",
            encoding="utf-8",
        )

    def _compress_output(self, image_path: Path) -> Path:
        output = self.output_dir / self.manifest.output.artifact_name
        if output.exists():
            output.unlink()
        self._run(["xz", "-T0", "-z", "-k", "-f", str(image_path)])
        compressed = Path(f"{image_path}.xz")
        shutil.move(compressed, output)
        return output

    def _write_build_report(self, image_path: Path) -> Path:
        report = {
            "artifact": str(image_path),
            "hostname": self.manifest.system.hostname,
            "bundles": self.manifest.bundles,
            "resolved_packages": resolved_package_list(self.manifest),
            "base_image": self.manifest.base_image.label,
            "base_url": str(self.manifest.base_image.url),
            "snapshot": self.manifest.freeze.debian_snapshot,
            "provision_mode": self.manifest.provision_mode,
        }
        report_path = self.output_dir / f"{self.manifest.system.hostname}-build-report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report_path

    def _run_in_chroot(self, rootfs: Path, command: list[str], env: dict[str, str] | None = None) -> None:
        self._bind_mounts(rootfs)
        try:
            base_cmd = ["chroot", str(rootfs), *command]
            self._run(base_cmd, env=env)
        finally:
            self._unbind_mounts(rootfs)

    def _bind_mounts(self, rootfs: Path) -> None:
        for src, dst in [("/proc", "proc"), ("/sys", "sys"), ("/dev", "dev"), ("/run", "run")]:
            target = rootfs / dst
            target.mkdir(parents=True, exist_ok=True)
            if not self._is_mountpoint(target):
                self._run(["mount", "--bind", src, str(target)])

    def _unbind_mounts(self, rootfs: Path) -> None:
        for dst in ["run", "dev", "sys", "proc"]:
            target = rootfs / dst
            if self._is_mountpoint(target):
                subprocess.run(["umount", str(target)], check=False)

    @staticmethod
    def _is_mountpoint(path: Path) -> bool:
        result = subprocess.run(["mountpoint", "-q", str(path)], check=False)
        return result.returncode == 0

    @staticmethod
    def _run(command: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        subprocess.run(command, cwd=cwd, env=merged_env, check=True)


class MountedImage:
    def __init__(self, image_path: Path) -> None:
        self.image_path = image_path
        self.loop_device: str | None = None
        self.tempdir = Path(tempfile.mkdtemp(prefix="bbbforge-"))
        self.rootfs_mount = self.tempdir / "rootfs"
        self.boot_mount = self.tempdir / "boot"

    def __enter__(self) -> "MountedImage":
        self.rootfs_mount.mkdir(parents=True, exist_ok=True)
        self.boot_mount.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["losetup", "--find", "--partscan", "--show", str(self.image_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        self.loop_device = result.stdout.strip()
        boot_part = f"{self.loop_device}p1"
        root_part = f"{self.loop_device}p2"

        subprocess.run(["mount", root_part, str(self.rootfs_mount)], check=True)
        if Path(boot_part).exists():
            subprocess.run(["mount", boot_part, str(self.boot_mount)], check=True)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        for mountpoint in [self.boot_mount, self.rootfs_mount]:
            subprocess.run(["umount", str(mountpoint)], check=False)
        if self.loop_device:
            subprocess.run(["losetup", "-d", self.loop_device], check=False)
        shutil.rmtree(self.tempdir, ignore_errors=True)
