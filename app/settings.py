from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from shlex import split as shell_split


APP_NAME = "bbb-image-forge"
_GITHUB_REMOTE_RE = re.compile(
    r"(?:git@github\.com:|https://github\.com/)(?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$"
)


@dataclass(frozen=True, slots=True)
class AppPaths:
    root: Path
    cache_dir: Path
    workspace_dir: Path
    support_dir: Path
    temp_dir: Path

    def ensure(self) -> "AppPaths":
        for path in (
            self.root,
            self.cache_dir,
            self.workspace_dir,
            self.support_dir,
            self.temp_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
        return self


@dataclass(frozen=True, slots=True)
class ServiceSettings:
    catalog_url: str | None
    build_service_url: str | None
    helper_command: tuple[str, ...]
    allow_local_build_service: bool
    allow_maintainer_routes: bool
    github_actions_enabled: bool
    github_api_url: str
    github_owner: str | None
    github_repo: str | None
    github_workflow_file: str
    github_ref: str
    github_token: str | None


def infer_github_repository() -> tuple[str | None, str | None]:
    remote = os.environ.get("BBB_IMAGE_FORGE_GITHUB_REMOTE")
    if not remote:
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            remote = result.stdout.strip() or result.stderr.strip()
        except Exception:
            remote = None
    if not remote:
        return None, None
    match = _GITHUB_REMOTE_RE.search(remote.strip())
    if not match:
        return None, None
    return match.group("owner"), match.group("repo")


def infer_git_ref() -> str:
    if os.environ.get("BBB_IMAGE_FORGE_GITHUB_REF"):
        return os.environ["BBB_IMAGE_FORGE_GITHUB_REF"]
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        branch = result.stdout.strip()
        if branch:
            return branch
    except Exception:
        pass
    return "main"


def app_paths() -> AppPaths:
    roots: list[Path] = []
    if os.environ.get("BBB_IMAGE_FORGE_HOME"):
        roots.append(Path(os.environ["BBB_IMAGE_FORGE_HOME"]).expanduser())
    roots.extend(
        [
            Path.home() / ".local" / "share" / APP_NAME,
            Path.cwd() / ".bbb-image-forge",
            Path("/tmp") / APP_NAME,
        ]
    )
    last_error: OSError | None = None
    for root in roots:
        try:
            return AppPaths(
                root=root,
                cache_dir=root / "cache",
                workspace_dir=root / "workspace",
                support_dir=root / "support",
                temp_dir=root / "tmp",
            ).ensure()
        except OSError as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    raise RuntimeError("Could not determine an application data directory.")


def service_settings() -> ServiceSettings:
    helper_override = os.environ.get("BBB_IMAGE_FORGE_HELPER_COMMAND")
    if helper_override:
        helper_command = tuple(shell_split(helper_override))
    else:
        helper_command = ("python", "-m", "app.helper")
    github_owner, github_repo = infer_github_repository()
    return ServiceSettings(
        catalog_url=os.environ.get("BBB_IMAGE_FORGE_CATALOG_URL"),
        build_service_url=os.environ.get("BBB_IMAGE_FORGE_BUILD_SERVICE_URL"),
        helper_command=helper_command,
        allow_local_build_service=os.environ.get(
            "BBB_IMAGE_FORGE_ALLOW_LOCAL_BUILD_SERVICE",
            "1",
        )
        == "1",
        allow_maintainer_routes=os.environ.get(
            "BBB_IMAGE_FORGE_ALLOW_MAINTAINER_ROUTES",
            "0",
        )
        == "1",
        github_actions_enabled=os.environ.get("BBB_IMAGE_FORGE_GITHUB_ACTIONS_ENABLED", "0")
        == "1",
        github_api_url=os.environ.get("BBB_IMAGE_FORGE_GITHUB_API_URL", "https://api.github.com"),
        github_owner=os.environ.get("BBB_IMAGE_FORGE_GITHUB_OWNER") or github_owner,
        github_repo=os.environ.get("BBB_IMAGE_FORGE_GITHUB_REPO") or github_repo,
        github_workflow_file=os.environ.get(
            "BBB_IMAGE_FORGE_GITHUB_WORKFLOW_FILE",
            "build-certified-image.yml",
        ),
        github_ref=infer_git_ref(),
        github_token=os.environ.get("BBB_IMAGE_FORGE_GITHUB_TOKEN"),
    )
