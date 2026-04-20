# BBB Image Forge

## Start Here

```bash
./scripts/run_dev.sh
```

That is the main command on Linux and WSL.

On native Windows, use:

```powershell
.\scripts\run_windows.ps1
```

Then open:

```text
http://127.0.0.1:8000
```

## What This Does

BBB Image Forge builds a BeagleBone Black image on your Linux machine or inside WSL, then can flash it to an SD card.

You pick a predefined profile, adjust the settings, build the image, and optionally flash it to an SD card.

Build does not need an SD card.

Flashing an SD card may need administrator permissions, because it writes directly to a block device.

## Supported Runtime Modes

- `Linux native`: build + flash
- `WSL Ubuntu`: build
- `Windows PowerShell`: flash

Image building stays Linux-only because it relies on Linux tooling such as `losetup`, `mount`, `chroot`, `debugfs`, `sfdisk`, `dd`, and `xz`.

For Windows machines, the recommended workflow is:

1. Build the image inside WSL Ubuntu.
2. Flash the image from native Windows using `scripts/run_windows.ps1`.

Windows flashing should be run from native Windows Python, not from WSL, because raw access to `\\.\PhysicalDriveN` is a native Windows capability.

## Linux / WSL Requirements

- Ubuntu/Linux or WSL Ubuntu
- Conda or Miniforge installed and available as `conda`
- System tools:

```bash
sudo apt-get update
sudo apt-get install -y git qemu-user-static xz-utils parted util-linux mount rsync e2fsprogs
```

`e2fsprogs` is important for rootless builds, because it provides `debugfs`.

If you are using WSL, keep this repo inside the WSL filesystem rather than under `/mnt/c/...` for better performance and fewer permission surprises.

## Windows Requirements

- Windows 10/11
- Python 3 installed and available as `py` or `python`
- PowerShell
- Run `scripts/run_windows.ps1` from an elevated PowerShell window when you want to flash a card

## First Run

Clone the repository and enter it:

```bash
git clone https://github.com/Eliot-Abramo/BBB-Image-Flasher.git
cd BBB-Image-Flasher
```

Start the app:

```bash
./scripts/run_dev.sh
```

The script creates or updates the app-owned Conda environment automatically.

## Windows Flashing Setup

Open an elevated PowerShell window, then run:

```powershell
.\scripts\run_windows.ps1
```

The Windows launcher creates a local virtual environment in `.bbb-image-forge/windows-venv`, installs the app, and starts the web UI on `http://127.0.0.1:8000`.

## Normal Use

1. Run `./scripts/run_dev.sh` in Linux or WSL
2. Open `http://127.0.0.1:8000`
3. Choose a profile
4. Adjust hostname, username, password, networking, and extra packages
5. Click `Build My Image`
6. Wait for the `.img.xz` file to appear
7. If you are on Windows, run `.\scripts\run_windows.ps1` in PowerShell
8. Switch to the `Flash SD Card` tab and write it to a card

Built images are stored in:

```text
build/artifacts/
```

## Build vs Flash

### Build

- Runs locally on your machine
- Writes only inside this project folder
- Does not need an SD card inserted
- Does not need `sudo`
- Supported on Linux and WSL

For rootless builds, package installation finishes on the BBB during first boot.

### Flash

- Writes directly to an SD card
- May require administrator/root permissions
- Permanently erases the selected card
- On Windows, use the native Windows launcher rather than WSL

## Useful Commands

Start the app:

```bash
./scripts/run_dev.sh
```

Start the native Windows flashing launcher:

```powershell
.\scripts\run_windows.ps1
```

Refresh the Conda environment only:

```bash
./scripts/ensure_conda_env.sh
```

Run tests:

```bash
conda run --prefix ./.bbb-image-forge/conda-env pytest -q
```

Run a build from the command line:

```bash
conda run --prefix ./.bbb-image-forge/conda-env python ./bbb_image_forge_cli.py build app/profiles/robotics_starter.yml
```

## Notes

- The predefined profiles already include package selections. When you pick one in the UI, Section 4 reflects that automatically.
- If a build is large, first boot on the BBB can take several minutes.
- If flashing fails due to permissions, retry that step with the required administrator access. Building should still stay unprivileged.
- Native Windows is the supported place for `\\.\PhysicalDriveN` flashing; WSL is the supported place for building.
