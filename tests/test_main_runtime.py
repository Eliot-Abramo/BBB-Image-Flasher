import asyncio

from app import main


async def _read_streaming_response(response) -> str:
    chunks: list[str] = []
    async for part in response.body_iterator:
        chunks.append(part.decode() if isinstance(part, bytes) else part)
    return "".join(chunks)


def test_managed_python_prefers_managed_linux_env(tmp_path, monkeypatch):
    candidate = tmp_path / "bin" / "python"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text("", encoding="utf-8")

    monkeypatch.setattr(main, "supports_build", lambda: True)
    monkeypatch.setattr(main, "MANAGED_CONDA_ENV", tmp_path)

    assert main._managed_python() == str(candidate)


def test_managed_python_uses_current_python_when_no_managed_env(monkeypatch):
    monkeypatch.setattr(main, "supports_build", lambda: False)

    assert main._managed_python() == main.sys.executable


def test_build_api_returns_windows_guidance(monkeypatch):
    monkeypatch.setattr(main, "supports_build", lambda: False)
    monkeypatch.setattr(main, "runtime_label", lambda: "Windows")

    response = asyncio.run(
        main.api_build(
            profile="beginner_starter",
            hostname="bbb-test",
            username="student",
            password="",
            bundle_names_selected=[],
            ip_mode="dhcp",
            static_address="",
            static_gateway="",
            static_dns="8.8.8.8 1.1.1.1",
            disable_password_auth=False,
            permit_root_login=False,
            authorized_key="",
        )
    )
    text = asyncio.run(_read_streaming_response(response))

    assert "Building is supported in WSL/Linux; flashing is supported in native Windows." in text


def test_build_api_runs_on_linux(monkeypatch):
    monkeypatch.setattr(main, "supports_build", lambda: True)

    class DummyProc:
        def __init__(self):
            self.stdout = self._stdout()
            self.returncode = 0

        async def _stdout(self):
            for line in [b"step 1\n", b"step 2\n"]:
                yield line

        async def wait(self):
            self.returncode = 0

        def kill(self):
            self.returncode = -9

    async def fake_exec(*args, **kwargs):
        return DummyProc()

    monkeypatch.setattr(main.asyncio, "create_subprocess_exec", fake_exec)

    response = asyncio.run(
        main.api_build(
            profile="beginner_starter",
            hostname="bbb-test",
            username="student",
            password="",
            bundle_names_selected=[],
            ip_mode="dhcp",
            static_address="",
            static_gateway="",
            static_dns="8.8.8.8 1.1.1.1",
            disable_password_auth=False,
            permit_root_login=False,
            authorized_key="",
        )
    )
    text = asyncio.run(_read_streaming_response(response))

    assert '"status": "running"' in text
    assert '"status": "done"' in text
