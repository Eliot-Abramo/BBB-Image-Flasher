from app import runtime


def test_runtime_label_linux(monkeypatch):
    monkeypatch.setattr(runtime.platform, "system", lambda: "Linux")
    monkeypatch.setattr(runtime.platform, "release", lambda: "6.8.0-generic")
    monkeypatch.setattr(runtime.platform, "version", lambda: "#1 SMP")
    monkeypatch.delenv("WSL_INTEROP", raising=False)

    assert runtime.is_linux() is True
    assert runtime.is_wsl() is False
    assert runtime.runtime_label() == "Linux"
    assert runtime.supports_build() is True


def test_runtime_label_wsl(monkeypatch):
    monkeypatch.setattr(
        runtime.platform,
        "release",
        lambda: "5.15.153.1-microsoft-standard-WSL2",
    )
    monkeypatch.setattr(runtime.platform, "system", lambda: "Linux")
    monkeypatch.setattr(runtime.platform, "version", lambda: "#1 SMP")
    monkeypatch.delenv("WSL_INTEROP", raising=False)

    assert runtime.is_linux() is True
    assert runtime.is_wsl() is True
    assert runtime.runtime_label() == "WSL"
    assert runtime.supports_build() is True


def test_runtime_label_windows(monkeypatch):
    monkeypatch.setattr(runtime.platform, "system", lambda: "Windows")
    monkeypatch.delenv("WSL_INTEROP", raising=False)

    assert runtime.is_windows() is True
    assert runtime.is_wsl() is False
    assert runtime.runtime_label() == "Windows"
    assert runtime.supports_build() is False
    assert runtime.supports_windows_raw_flash() is True
