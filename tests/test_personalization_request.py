import pytest
from pydantic import ValidationError

from app.models import PersonalizationRequestModel


def test_personalization_requires_login_method():
    with pytest.raises(ValidationError):
        PersonalizationRequestModel.model_validate(
            {
                "profile_id": "beginner_starter",
                "system": {"hostname": "bbb-robot"},
                "user": {
                    "username": "student",
                    "password": None,
                    "password_locked": True,
                    "authorized_keys": [],
                },
                "network": {"ethernet": {"mode": "dhcp"}},
                "ssh": {"disable_password_auth": False, "permit_root_login": False},
            }
        )


def test_personalization_accepts_ssh_key_only():
    request = PersonalizationRequestModel.model_validate(
        {
            "profile_id": "beginner_starter",
            "system": {"hostname": "bbb-robot"},
            "user": {
                "username": "student",
                "password": None,
                "password_locked": True,
                "authorized_keys": ["ssh-ed25519 AAAA example@test"],
            },
            "network": {"ethernet": {"mode": "dhcp"}},
            "ssh": {"disable_password_auth": True, "permit_root_login": False},
        }
    )

    assert request.ssh.disable_password_auth is True
    assert request.user.authorized_keys
