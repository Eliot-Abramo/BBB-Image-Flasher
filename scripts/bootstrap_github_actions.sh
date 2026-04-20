#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.github-actions"

REMOTE_URL="${BBB_IMAGE_FORGE_GITHUB_REMOTE:-$(git -C "$ROOT_DIR" remote get-url origin 2>/dev/null || true)}"
OWNER=""
REPO=""

if [[ "$REMOTE_URL" =~ git@github\.com:([^/]+)/([^/.]+)(\.git)?$ ]]; then
  OWNER="${BASH_REMATCH[1]}"
  REPO="${BASH_REMATCH[2]}"
elif [[ "$REMOTE_URL" =~ https://github\.com/([^/]+)/([^/.]+)(\.git)?$ ]]; then
  OWNER="${BASH_REMATCH[1]}"
  REPO="${BASH_REMATCH[2]}"
fi

cat > "$ENV_FILE" <<EOF
# BBB Image Forge GitHub Actions integration
# Fill in BBB_IMAGE_FORGE_GITHUB_TOKEN with a fine-grained token or GitHub App installation token.

BBB_IMAGE_FORGE_GITHUB_ACTIONS_ENABLED=1
BBB_IMAGE_FORGE_GITHUB_OWNER=${OWNER}
BBB_IMAGE_FORGE_GITHUB_REPO=${REPO}
BBB_IMAGE_FORGE_GITHUB_WORKFLOW_FILE=build-certified-image.yml
BBB_IMAGE_FORGE_GITHUB_REF=main
BBB_IMAGE_FORGE_GITHUB_TOKEN=

# Trusted internal mode only:
# Leave this unset in production desktop clients.
# BBB_IMAGE_FORGE_BUILD_SERVICE_URL=

# Relay/server mode:
# BBB_IMAGE_FORGE_ALLOW_LOCAL_BUILD_SERVICE=0
EOF

printf 'Wrote %s\n' "$ENV_FILE"
printf 'Detected GitHub repo: %s/%s\n' "${OWNER:-<unknown>}" "${REPO:-<unknown>}"
printf 'Next: set BBB_IMAGE_FORGE_GITHUB_TOKEN in that file or in your deployment environment.\n'
