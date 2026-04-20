import pytest

from app.flasher import new_devices_since, validate_candidate_device
from app.models import DeviceRecordModel


def _device(**overrides):
    payload = {
        "device_id": "linux:sdb",
        "device_path": "/dev/sdb",
        "label": "USB SD Reader",
        "vendor": "Test",
        "model": "Reader",
        "serial": "1234",
        "transport": "USB",
        "size_bytes": 16 * 1024**3,
        "removable": True,
        "system_disk": False,
        "mounted_partitions": [],
    }
    payload.update(overrides)
    return DeviceRecordModel.model_validate(payload)


def test_new_devices_since_returns_only_inserted_devices():
    baseline = [_device(device_id="linux:sda", device_path="/dev/sda", serial="a")]
    current = [
        baseline[0],
        _device(device_id="linux:sdb", device_path="/dev/sdb", serial="b"),
    ]

    inserted = new_devices_since(baseline, current)

    assert [device.device_id for device in inserted] == ["linux:sdb"]


def test_validate_candidate_device_rejects_mounted_or_too_small_media():
    with pytest.raises(ValueError):
        validate_candidate_device(
            _device(mounted_partitions=["/media/card"]),
            required_bytes=8 * 1024**3,
        )

    with pytest.raises(ValueError):
        validate_candidate_device(
            _device(size_bytes=4 * 1024**3),
            required_bytes=8 * 1024**3,
        )
