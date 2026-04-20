#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_DIR="$ROOT_DIR/.bbb-image-forge/conda-env"
ENV_FILE="$ROOT_DIR/environment.yml"
PKGS_DIR="$ROOT_DIR/.bbb-image-forge/conda-pkgs"
CACHE_DIR="$ROOT_DIR/.bbb-image-forge/cache"

if ! command -v conda >/dev/null 2>&1; then
  echo "Conda was not found on PATH."
  echo "Install Miniforge or Conda first, then re-run this script."
  exit 1
fi

mkdir -p "$ROOT_DIR/.bbb-image-forge"
mkdir -p "$PKGS_DIR"
mkdir -p "$CACHE_DIR"
export CONDA_PKGS_DIRS="$PKGS_DIR"
export XDG_CACHE_HOME="$CACHE_DIR"
conda env update --prefix "$ENV_DIR" --file "$ENV_FILE" --prune
