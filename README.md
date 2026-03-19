# BBB Image Forge

BBB Image Forge is a beginner-friendly BeagleBone Black image builder.

It is designed for one job: start from an official BeagleBoard Debian image and turn it into a reproducible, pre-configured image with the tools a user actually wants.

Instead of teaching beginners to manually install packages, edit boot files, configure users, inject SSH keys, and debug broken apt states on-device, the tool builds a ready-to-flash image ahead of time.

## What it does

- Fetches the latest official BeagleBone Black Debian base image metadata.
- Lets users choose bundles such as Python, C/C++, OpenCV, Git, GPIO/I2C/SPI, and robotics basics.
- Generates a validated manifest.
- Builds a custom `.img.xz` starting from the official BeagleBoard image.
- Verifies the base image checksum before customization.
- Supports SSH-key-only onboarding.
- Freezes Debian package selection to a snapshot date for more reproducible images.
- Produces a build report for traceability.

## Why this architecture

This project intentionally **does not** replace the BeagleBoard distribution with a home-grown distro.

Instead, it layers customization on top of the official BeagleBoard Debian images. That keeps the kernel, bootloader, and board-specific support aligned with the images maintained by the Beagle ecosystem, while still giving users an Arduino-style profile selector.

## Build modes

### 1. Offline image customization (default)

The build host mounts the Beagle image, chroots into the ARM root filesystem with `qemu-user-static`, installs packages, applies config, and repacks the image.

This gives the most deterministic result because the board boots with the selected tools already installed.

### 2. First-boot provisioning (fallback)

If the build host cannot use loop devices or chroot, the tool can inject a `systemd` first-boot unit that installs packages and applies configuration on the target board.

This is less deterministic than offline customization but still much easier for beginners than manual setup.

## Current state

This repository is an MVP scaffold that includes:

- a FastAPI web UI,
- a manifest format,
- built-in package bundles,
- base-image catalog fetching,
- a Linux builder pipeline,
- example manifests,
- and a local run script.

The code is structured to be directly extendable into a production utility.

## Requirements

### Host OS

A Linux machine is strongly recommended for full image building because loop mounts and chroots are required.

### Host packages

For offline builds you will typically need:

- `xz-utils`
- `parted`
- `losetup` / `util-linux`
- `mount`
- `rsync`
- `qemu-user-static`
- `systemd-container` (optional but useful)
- `kpartx` (optional fallback)
- `sudo`

### Python

- Python 3.11+

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

Then open:

```text
http://127.0.0.1:8000
```

## CLI usage

Generate a manifest from a built-in profile:

```bash
python -m app.cli generate-manifest \
  --profile python_lab \
  --hostname bbb-python-01 \
  --username student \
  --authorized-key-file ~/.ssh/id_ed25519.pub \
  --output build/python_lab.yml
```

Build an image:

```bash
sudo python -m app.cli build build/python_lab.yml
```

## Example workflow

1. Start the web UI.
2. Pick **BeagleBone Black**.
3. Choose a base image from the official Beagle catalog.
4. Select bundles such as `git`, `python`, `cpp`, and `opencv`.
5. Set hostname, username, SSH keys, and whether password login is disabled.
6. Export the manifest.
7. Run the build on a Linux host.
8. Flash the generated `.img.xz` with bb-imager or balenaEtcher.

## Bundle philosophy

The default bundles are conservative. They aim for stable, common Debian packages instead of exotic stacks.

Examples:

- `core-dev`: git, curl, vim, htop, tmux
- `python`: python3, pip, venv
- `cpp`: build-essential, cmake, gdb
- `opencv`: python3-opencv, libopencv-dev
- `gpio`: libgpiod tools and Python bindings
- `i2c-spi`: i2c-tools, spidev helpers

Production rollouts should prefer a small number of tested profiles rather than arbitrary free-form package selection.

## Manifest format

Example:

```yaml
schema_version: 1
board: beaglebone-black
base_image:
  url: https://files.beagle.cc/...
  sha256: "..."
  label: "BeagleBone Black Debian 13.4 IoT 2026-03-17"
freeze:
  debian_snapshot: "2026-03-17T00:00:00Z"
provision_mode: offline
system:
  hostname: bbb-python-01
  timezone: UTC
user:
  username: student
  password_locked: true
  authorized_keys:
    - ssh-ed25519 AAAA...
bundles:
  - core-dev
  - python
  - gpio
apt:
  extra_packages:
    - tree
    - jq
network:
  wifi: null
ssh:
  disable_password_auth: true
  permit_root_login: false
output:
  artifact_name: bbb-python-01.img.xz
```

## Design notes for production hardening

A production version should add:

- signed manifest support,
- a compatibility matrix by board/image/kernel,
- a tested package allowlist,
- CI builds of known-good classroom and lab profiles,
- image signing / attestations,
- post-build smoke tests in QEMU where feasible,
- and a separate desktop flasher app.

## Safety and support boundaries

This tool customizes Linux images, but it intentionally avoids modifying the board kernel, bootloader, or device-tree stack unless a profile explicitly requires that.

That choice reduces the chance of creating fragile images.

## Suggested next steps

1. Add a prebuilt desktop app wrapper around the current web UI.
2. Maintain 5–10 curated profiles instead of letting beginners mix arbitrary packages.
3. Keep a small validation farm of real BBB boards for smoke testing each released profile.
4. Add support for classroom fleet provisioning and per-device SSH key injection.

