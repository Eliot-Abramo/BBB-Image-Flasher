# GitHub Actions CI/CD Setup

This repository now supports the workflow:

1. User opens the app.
2. User picks a certified profile and add-ons.
3. User clicks **Build**.
4. The app dispatches a GitHub Actions workflow.
5. GitHub builds a generic BBB image artifact.
6. The app downloads that artifact.
7. The app applies user-specific settings locally.
8. The app flashes the SD card locally.

## Recommended topology

For production desktop clients, do **not** embed a GitHub token inside the shipped app.

Use this split instead:

- Desktop app:
  - local helper
  - personalization
  - SD flashing
  - `BBB_IMAGE_FORGE_BUILD_SERVICE_URL=https://your-build-relay.example.com`
- Build relay:
  - runs this FastAPI app in server mode
  - has `BBB_IMAGE_FORGE_GITHUB_TOKEN`
  - dispatches and polls GitHub Actions on behalf of desktop clients
- GitHub Actions:
  - builds the generic image artifact
  - uploads the artifact bundle

For internal or trusted-only testing, you can skip the relay and let the app talk to GitHub Actions directly by setting the GitHub environment variables locally.

## Files added for this flow

- `.github/workflows/build-certified-image.yml`
  The remote image build workflow.
- `.github/workflows/ci.yml`
  The normal test pipeline.
- `scripts/ci_build_certified_image.py`
  The script the workflow runs under `sudo`.
- `scripts/bootstrap_github_actions.sh`
  Generates a starter `.env.github-actions` file.
- `app/build_service.py`
  Contains the GitHub Actions-backed build service.

## One-time setup

### 1. Push the workflow files to GitHub

Push the branch containing the new `.github/workflows/` files so GitHub can see them.

### 2. Create a GitHub token for the build relay

Use either:

- a fine-grained PAT, or
- a GitHub App installation token

Minimum repository permissions for the token used by the build relay:

- `Actions: write`
  Needed to create the workflow dispatch event.
- `Actions: read`
  Needed to read workflow runs and download workflow artifacts.
- `Contents: read`
  Recommended so the workflow file and repo metadata can be read safely.

### 3. Generate the local environment template

From the repo root:

```bash
bash scripts/bootstrap_github_actions.sh
```

This writes `.env.github-actions` and auto-fills the GitHub owner/repo when `origin` points at GitHub.

### 4. Fill in the token

Edit `.env.github-actions` and set:

```bash
BBB_IMAGE_FORGE_GITHUB_TOKEN=your_token_here
```

### 5. Choose the mode

#### Safe production mode

Run a hosted build relay with:

```bash
BBB_IMAGE_FORGE_GITHUB_ACTIONS_ENABLED=1
BBB_IMAGE_FORGE_GITHUB_OWNER=Eliot-Abramo
BBB_IMAGE_FORGE_GITHUB_REPO=BBB-Image-Flasher
BBB_IMAGE_FORGE_GITHUB_WORKFLOW_FILE=build-certified-image.yml
BBB_IMAGE_FORGE_GITHUB_REF=main
BBB_IMAGE_FORGE_GITHUB_TOKEN=...
BBB_IMAGE_FORGE_ALLOW_LOCAL_BUILD_SERVICE=0
```

Then point desktop clients at it:

```bash
BBB_IMAGE_FORGE_BUILD_SERVICE_URL=https://your-build-relay.example.com
```

#### Trusted local testing mode

Source the GitHub Actions env file locally and run the app directly:

```bash
set -a
source .env.github-actions
set +a
python -m app.main
```

## What the GitHub workflow does

`build-certified-image.yml`:

1. Checks out the repo.
2. Installs Python dependencies.
3. Installs Linux image-build dependencies on the runner.
4. Runs `scripts/ci_build_certified_image.py` under `sudo`.
5. Uploads a single artifact bundle named `bbb-image-<request_id>`.

That uploaded bundle contains:

- the built `.img.xz`
- `artifact-manifest.json`
- the build report JSON

## What the app does when the user clicks Build

1. Creates a `BuildRequestModel` from the selected certified profile and add-ons.
2. Dispatches `build-certified-image.yml` with:
   - `request_id`
   - `profile_id`
   - `addon_bundle_ids`
   - `artifact_name`
3. Polls the workflow runs for that workflow.
4. Waits for the run to complete.
5. Downloads the uploaded artifact bundle.
6. Extracts `artifact-manifest.json` plus the built image into the local cache.
7. Continues with local personalization and flashing.

## Relay deployment checklist

Use these steps for the hosted relay:

1. Deploy this FastAPI app on a Linux host or service.
2. Set the GitHub Actions environment variables there.
3. Disable local build fallback there:
   - `BBB_IMAGE_FORGE_ALLOW_LOCAL_BUILD_SERVICE=0`
4. Keep the helper local-only on desktop clients. The relay does not need SD-card access.
5. Configure your packaged desktop client with:
   - `BBB_IMAGE_FORGE_BUILD_SERVICE_URL`

## Verification steps

### Verify GitHub can see the workflow

Open the repository’s **Actions** tab and confirm:

- `CI`
- `Build Certified Image`

### Verify the workflow dispatches correctly

From a machine that has the relay env configured:

```bash
python -m app.installer selfcheck
python -m app.main
```

Then in the UI:

1. Pick a certified profile
2. Click Build
3. Confirm a new workflow run appears in GitHub Actions

### Verify the full user flow

1. Start the app with GitHub Actions mode or relay mode enabled.
2. Choose profile and add-ons.
3. Click Build.
4. Wait for the GitHub workflow to finish.
5. Confirm the app reports the certified artifact is ready.
6. Insert SD card.
7. Let the app personalize and flash locally.

## Important operational notes

- GitHub-hosted artifact retention is finite. The workflow currently keeps image artifacts for 14 days.
- If you expect many users, the build relay is the right place to add:
  - rate limiting
  - queueing
  - job deduplication
  - build caching
  - prebuilt warm caches for popular profiles
- If build demand grows, move the actual image build workflow from GitHub-hosted runners to self-hosted Linux runners while keeping the same dispatch/poll/download contract.

## Official GitHub references

- Manually running a workflow:
  https://docs.github.com/en/actions/managing-workflow-runs/manually-running-a-workflow
- REST API for workflow dispatch:
  https://docs.github.com/en/rest/actions/workflows
- REST API for workflow runs:
  https://docs.github.com/en/rest/actions/workflow-runs
- REST API for workflow artifacts:
  https://docs.github.com/en/rest/actions/artifacts
