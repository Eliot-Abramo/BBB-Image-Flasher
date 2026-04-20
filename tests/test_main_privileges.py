import pytest

from app import main


def test_cli_command_stays_unprivileged_for_build_flash_and_eject(monkeypatch):
    monkeypatch.setattr(main, "is_admin", lambda: False)
    monkeypatch.setattr(
        main, "_managed_python", lambda: "/opt/conda/envs/bbb/bin/python"
    )
    monkeypatch.setattr(main, "CLI_WRAPPER", main.Path("/repo/bbb_image_forge_cli.py"))

    build_command = main._cli_command("build", "/tmp/example.json", privileged=True)
    flash_command = main._cli_command(
        "flash-json", "/tmp/example.img.xz", "/dev/sdb", privileged=True
    )
    eject_command = main._cli_command("eject", "/dev/sdb", privileged=True)

    assert build_command == [
        "/opt/conda/envs/bbb/bin/python",
        "-u",
        "/repo/bbb_image_forge_cli.py",
        "build",
        "/tmp/example.json",
    ]
    assert flash_command == [
        "/opt/conda/envs/bbb/bin/python",
        "-u",
        "/repo/bbb_image_forge_cli.py",
        "flash-json",
        "/tmp/example.img.xz",
        "/dev/sdb",
    ]
    assert eject_command == [
        "/opt/conda/envs/bbb/bin/python",
        "-u",
        "/repo/bbb_image_forge_cli.py",
        "eject",
        "/dev/sdb",
    ]
