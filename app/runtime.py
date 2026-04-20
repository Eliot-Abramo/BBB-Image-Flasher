from __future__ import annotations

import os
import platform


def system_name() -> str:
    return platform.system()


def is_windows() -> bool:
    return system_name() == "Windows"


def is_linux() -> bool:
    return system_name() == "Linux"


def is_wsl() -> bool:
    if not is_linux():
        return False

    release = platform.release().lower()
    version = platform.version().lower()
    return "microsoft" in release or "microsoft" in version or "WSL_INTEROP" in os.environ


def runtime_label() -> str:
    if is_windows():
        return "Windows"
    if is_wsl():
        return "WSL"
    if is_linux():
        return "Linux"
    return system_name()


def supports_build() -> bool:
    return is_linux()


def supports_windows_raw_flash() -> bool:
    return is_windows()


def build_guidance() -> str:
    if is_windows():
        return (
            "Building is supported in WSL/Linux. Flashing is supported in native "
            "Windows PowerShell or Command Prompt."
        )
    if is_wsl():
        return (
            "This WSL environment can build images. For the most reliable raw SD-card "
            "flashing, use the Windows launcher from an elevated PowerShell window."
        )
    if is_linux():
        return (
            "This Linux environment can build images and can flash removable media "
            "when the process has raw-disk access."
        )
    return "Building requires Linux or WSL."


def flash_guidance() -> str:
    if is_windows():
        return (
            "Flash from this native Windows session. If drive detection or writing "
            "fails, restart the app from an Administrator PowerShell window."
        )
    if is_wsl():
        return (
            "Use this page to review built images, but do the actual SD-card flashing "
            "from the native Windows launcher for best results."
        )
    if is_linux():
        return (
            "Flash from this Linux environment once the process has permission to "
            "write to the selected raw device."
        )
    return "Flashing support depends on the host operating system."
