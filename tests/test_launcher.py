import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from kssolv_crew import launcher
from fastapi.testclient import TestClient
from kssolv_crew.server import create_app


def test_stop_requires_private_token(tmp_path, monkeypatch):
    monkeypatch.setenv("KSSOLV_SERVICE_TOKEN", "private-control")
    app = create_app(runs=tmp_path)
    called = []
    app.state.stop_callback = lambda: called.append(True)
    with TestClient(app) as client:
        assert client.post("/service/stop").status_code == 404
        assert client.post("/service/stop", headers={"X-Service-Token": "wrong"}).status_code == 404
        assert "private-control" not in client.get("/health").text
        assert client.post("/service/stop", headers={"X-Service-Token": "private-control"}).status_code == 200
        assert called == [True]


def test_repeated_launch_reuses_healthy_instance(tmp_path, monkeypatch):
    runtime = tmp_path / ".runtime"
    runtime.mkdir()
    state = {"url": "http://127.0.0.1:8001", "instance_id": "existing"}
    (runtime / "server.json").write_text(json.dumps(state))
    monkeypatch.setattr(launcher, "health", lambda url: {"service": "kssolv-crew", "instance_id": "existing"})
    monkeypatch.setattr(launcher, "_start", lambda *a: pytest.fail("Should reuse existing instance"))
    assert launcher.launch(tmp_path, open_browser=False) == state


def test_unrelated_web_server_not_reused(monkeypatch):
    monkeypatch.setattr(launcher, "health", lambda url: {"service": "other", "instance_id": "same"})
    assert not launcher.matches({"url": "http://127.0.0.1:8000", "instance_id": "same"})


def test_bind_conflict_selects_next_port(tmp_path, monkeypatch):
    import socket
    occupied = socket.socket()
    occupied.bind(("127.0.0.1", 0))
    port = occupied.getsockname()[1]
    if port > 65525:
        occupied.close()
        pytest.skip("Ephemeral port outside launch range")
    spawned = []
    monkeypatch.setattr(launcher, "matches", lambda state: True)
    def spawn(args, **kwargs):
        spawned.append(args)
        return SimpleNamespace(pid=123, poll=lambda: None)
    monkeypatch.setattr(launcher.subprocess, "Popen", spawn)
    try:
        state = launcher._start(tmp_path, tmp_path, port, tmp_path)
    finally:
        occupied.close()
    assert int(state["url"].rsplit(":", 1)[1]) > port
    assert spawned
