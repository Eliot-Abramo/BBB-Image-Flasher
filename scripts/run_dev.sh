#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_DIR="$ROOT_DIR/.bbb-image-forge/conda-env"

"$ROOT_DIR/scripts/ensure_conda_env.sh"

exec conda run --no-capture-output --prefix "$ENV_DIR" python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
