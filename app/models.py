from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


_HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")
_USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")


class SupportTier(str, Enum):
    CERTIFIED = "certified"
    PREVIEW = "preview"
    EXPERIMENTAL = "experimental"
    MAINTAINER = "maintainer"


class BaseImageModel(BaseModel):
    url: HttpUrl
    sha256: str = Field(min_length=32)
    label: str


class FreezeModel(BaseModel):
    debian_snapshot: str | None = None


class SystemModel(BaseModel):
    hostname: str = Field(min_length=1, max_length=63)
    timezone: str = "UTC"
    locale: str = "en_US.UTF-8"

    @model_validator(mode="after")
    def validate_hostname(self) -> "SystemModel":
        if not _HOSTNAME_RE.fullmatch(self.hostname):
            raise ValueError(
                "Hostname must contain only letters, numbers, and hyphens."
            )
        return self


class UserModel(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str | None = None  # plaintext — hashed via chpasswd in builder
    password_locked: bool = True
    authorized_keys: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_username(self) -> "UserModel":
        if not _USERNAME_RE.fullmatch(self.username):
            raise ValueError(
                "Username must start with a letter or underscore and use lowercase letters, numbers, hyphens, or underscores."
            )
        return self


class AptModel(BaseModel):
    extra_packages: list[str] = Field(default_factory=list)


class WifiModel(BaseModel):
    ssid: str
    psk: str


class StaticIPConfig(BaseModel):
    """Static IP configuration in CIDR notation, e.g. address='192.168.1.100/24'."""

    address: str  # e.g. "192.168.1.100/24"
    gateway: str | None = None  # e.g. "192.168.1.1"
    dns_servers: list[str] = Field(default_factory=lambda: ["8.8.8.8", "1.1.1.1"])


class EthernetModel(BaseModel):
    mode: Literal["dhcp", "static"] = "dhcp"
    static: StaticIPConfig | None = None


class NetworkModel(BaseModel):
    wifi: WifiModel | None = None
    ethernet: EthernetModel = Field(default_factory=EthernetModel)


class SSHModel(BaseModel):
    disable_password_auth: bool = True
    permit_root_login: bool = False


class OutputModel(BaseModel):
    artifact_name: str = "bbb-custom.img.xz"


class ManifestModel(BaseModel):
    schema_version: int = 1
    board: Literal["beaglebone-black"] = "beaglebone-black"
    base_image: BaseImageModel
    freeze: FreezeModel = Field(default_factory=FreezeModel)
    provision_mode: Literal["offline", "firstboot"] = "offline"
    system: SystemModel
    user: UserModel
    bundles: list[str] = Field(default_factory=list)
    apt: AptModel = Field(default_factory=AptModel)
    network: NetworkModel = Field(default_factory=NetworkModel)
    ssh: SSHModel = Field(default_factory=SSHModel)
    output: OutputModel = Field(default_factory=OutputModel)


@dataclass(slots=True)
class Bundle:
    name: str
    description: str
    category: str = "General"
    apt_packages: list[str] = field(default_factory=list)
    pip_packages: list[str] = field(default_factory=list)
    # Commands injected into the firstboot script BEFORE apt-get install.
    # Useful for adding 3rd-party apt repositories (e.g. ROS).
    # Ignored in offline build mode.
    firstboot_commands: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)


class CatalogSignatureModel(BaseModel):
    algorithm: str
    key_id: str
    value: str


class CatalogBundleModel(BaseModel):
    id: str
    label: str
    description: str
    category: str
    support_tier: SupportTier = SupportTier.CERTIFIED
    warnings: list[str] = Field(default_factory=list)
    requires_network: bool = False


class CatalogProfileModel(BaseModel):
    id: str
    label: str
    description: str
    profile_name: str
    support_tier: SupportTier = SupportTier.CERTIFIED
    minimum_sd_size_bytes: int = 8 * 1024**3
    default_bundle_ids: list[str] = Field(default_factory=list)
    optional_bundle_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    artifact_id: str | None = None


class ArtifactCatalogModel(BaseModel):
    id: str
    label: str
    profile_id: str
    bundle_ids: list[str] = Field(default_factory=list)
    download_url: HttpUrl | None = None
    sha256: str | None = None
    compressed_size_bytes: int = 0
    uncompressed_size_bytes: int = 0
    minimum_sd_size_bytes: int = 8 * 1024**3
    support_tier: SupportTier = SupportTier.CERTIFIED
    signature: CatalogSignatureModel | None = None
    build_required: bool = False


class CatalogModel(BaseModel):
    schema_version: int = 1
    catalog_version: str
    source: str = "builtin"
    signature: CatalogSignatureModel
    warnings: list[str] = Field(default_factory=list)
    bundles: list[CatalogBundleModel] = Field(default_factory=list)
    profiles: list[CatalogProfileModel] = Field(default_factory=list)
    artifacts: list[ArtifactCatalogModel] = Field(default_factory=list)


class BuildRequestModel(BaseModel):
    profile_id: str
    addon_bundle_ids: list[str] = Field(default_factory=list)


class PersonalizationRequestModel(BaseModel):
    profile_id: str
    addon_bundle_ids: list[str] = Field(default_factory=list)
    system: SystemModel
    user: UserModel
    network: NetworkModel = Field(default_factory=NetworkModel)
    ssh: SSHModel

    @model_validator(mode="after")
    def validate_auth(self) -> "PersonalizationRequestModel":
        has_keys = bool(self.user.authorized_keys)
        has_password = bool(self.user.password)
        if self.ssh.disable_password_auth and not has_keys:
            raise ValueError(
                "SSH key(s) are required when password login is disabled."
            )
        if not self.ssh.disable_password_auth and not has_password and not has_keys:
            raise ValueError(
                "Provide either a password or an SSH key so the user can log in."
            )
        return self


class BuildJobModel(BaseModel):
    id: str
    request: BuildRequestModel
    status: Literal["queued", "running", "done", "error"] = "queued"
    message: str = ""
    artifact_id: str | None = None
    artifact_path: str | None = None
    remote_run_id: str | None = None
    remote_url: str | None = None
    error: str | None = None


class ArtifactManifestModel(BaseModel):
    artifact: ArtifactCatalogModel
    profile: CatalogProfileModel
    generated_from: BuildRequestModel
    local_path: str | None = None


class DeviceRecordModel(BaseModel):
    device_id: str
    device_path: str
    label: str
    vendor: str = ""
    model: str = ""
    serial: str | None = None
    transport: str = ""
    size_bytes: int
    removable: bool = False
    system_disk: bool = False
    mounted_partitions: list[str] = Field(default_factory=list)

    @property
    def size_human(self) -> str:
        gb = self.size_bytes / (1024**3)
        return f"{gb:.1f} GB" if gb >= 1 else f"{self.size_bytes // (1024**2)} MB"


class PreparedImageModel(BaseModel):
    image_path: str
    image_size_bytes: int
    workspace_dir: str


class HelperHealthModel(BaseModel):
    ok: bool
    message: str
    helper_command: str
