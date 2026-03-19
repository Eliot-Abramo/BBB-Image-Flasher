from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class BaseImageModel(BaseModel):
    url: HttpUrl
    sha256: str = Field(min_length=32)
    label: str


class FreezeModel(BaseModel):
    debian_snapshot: str | None = None


class SystemModel(BaseModel):
    hostname: str = Field(min_length=1, max_length=63)
    timezone: str = "UTC"


class UserModel(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password_locked: bool = True
    authorized_keys: list[str] = Field(default_factory=list)


class AptModel(BaseModel):
    extra_packages: list[str] = Field(default_factory=list)


class WifiModel(BaseModel):
    ssid: str
    psk: str


class NetworkModel(BaseModel):
    wifi: WifiModel | None = None


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
    apt_packages: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)
