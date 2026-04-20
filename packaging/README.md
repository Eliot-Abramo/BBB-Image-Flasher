# Desktop Packaging Notes

This repository now separates the product into three pieces:

1. `bbb-image-forge`
   The unprivileged desktop controller and UI.
2. `bbb-image-forge-helper`
   The narrowly scoped helper used for device access, local image personalization, flashing, eject, and cleanup.
3. `bbb-image-forge-installer`
   Installer-facing self-check and repair entrypoints.

## Installer expectations

- Bundle the Python runtime directly when possible.
- If a fully bundled runtime is not practical on a target platform, create a private environment from `packaging/environment.yml` during installation.
- The end user should never need to install Python, Conda, or dependencies manually.
- Run `bbb-image-forge-installer selfcheck` after install and after upgrades.
- Use `bbb-image-forge-installer repair-dirs` as the lightweight repair action for app-owned directories.

## Reference packaging targets

- Windows: signed `.msi` or `.exe`
- macOS: signed `.dmg` or `.pkg`
- Linux: `.deb` plus an `.AppImage` fallback

## Recommended packaging flow

1. Build the UI/controller entrypoint with the bundled runtime or private environment.
2. Install the helper as a separate executable or service owned by the installer.
3. Point the controller at the installed helper with `BBB_IMAGE_FORGE_HELPER_COMMAND`.
4. Run the installer self-check.
5. Create a launcher so users start the app from the desktop or applications menu.
