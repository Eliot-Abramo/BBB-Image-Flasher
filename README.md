# BBB Image Forge

## Start Here

```bash
./scripts/run_dev.sh
```

That is the main command.

Then open:

```text
http://127.0.0.1:8000
```

## What This Does

BBB Image Forge builds a BeagleBone Black image on your Linux machine.

You pick a predefined profile, adjust the settings, build the image, and optionally flash it to an SD card.

Build does not need an SD card.

Flashing an SD card may need administrator permissions, because it writes directly to a block device.

## Requirements

- Linux
- Conda or Miniforge installed and available as `conda`
- System tools:

```bash
sudo apt-get update
sudo apt-get install -y git qemu-user-static xz-utils parted util-linux mount rsync e2fsprogs
```

`e2fsprogs` is important for rootless builds, because it provides `debugfs`.

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

## Normal Use

1. Run `./scripts/run_dev.sh`
2. Open `http://127.0.0.1:8000`
3. Choose a profile
4. Adjust hostname, username, password, networking, and extra packages
5. Click `Build My Image`
6. Wait for the `.img.xz` file to appear
7. If you want, switch to the `Flash SD Card` tab and write it to a card

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

For rootless builds, package installation finishes on the BBB during first boot.

### Flash

- Writes directly to an SD card
- May require administrator/root permissions
- Permanently erases the selected card

## Useful Commands

Start the app:

```bash
./scripts/run_dev.sh
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
