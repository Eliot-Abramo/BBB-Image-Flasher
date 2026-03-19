from __future__ import annotations

from app.models import Bundle


BUNDLES: dict[str, Bundle] = {
    "core-dev": Bundle(
        name="core-dev",
        description="Basic shell and developer tools",
        apt_packages=["git", "curl", "wget", "vim", "htop", "tmux", "tree", "ca-certificates"],
    ),
    "python": Bundle(
        name="python",
        description="Python 3, pip and virtual environments",
        apt_packages=["python3", "python3-pip", "python3-venv", "python3-dev"],
    ),
    "cpp": Bundle(
        name="cpp",
        description="C/C++ toolchain and debugger",
        apt_packages=["build-essential", "cmake", "gdb", "pkg-config"],
    ),
    "opencv": Bundle(
        name="opencv",
        description="OpenCV development packages",
        apt_packages=["python3-opencv", "libopencv-dev", "v4l-utils", "ffmpeg"],
    ),
    "gpio": Bundle(
        name="gpio",
        description="GPIO userspace tooling",
        apt_packages=["gpiod", "libgpiod-dev", "python3-libgpiod"],
    ),
    "i2c-spi": Bundle(
        name="i2c-spi",
        description="I2C and SPI tooling",
        apt_packages=["i2c-tools", "python3-smbus", "python3-spidev"],
    ),
    "robotics-lite": Bundle(
        name="robotics-lite",
        description="Common robotics extras",
        apt_packages=["screen", "minicom", "usbutils", "pciutils", "net-tools"],
    ),
}


def bundle_names() -> list[str]:
    return sorted(BUNDLES)


def resolve_packages(bundle_list: list[str], extra_packages: list[str] | None = None) -> list[str]:
    packages: set[str] = set()
    for bundle_name in bundle_list:
        bundle = BUNDLES.get(bundle_name)
        if bundle is None:
            raise KeyError(f"Unknown bundle: {bundle_name}")
        packages.update(bundle.apt_packages)
    if extra_packages:
        packages.update(extra_packages)
    return sorted(packages)
