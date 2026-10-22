import json
import time
from pathlib import Path
from fastapi.testclient import TestClient
from kssolv_crew.server import create_app
from kssolv_crew.storage import stage


def test_api_auth_artifacts_and_no_credentials(tmp_path, monkeypatch):
    import kssolv_crew.server as server
    class Worker:
        pid = 123456
        def __init__(self, *args, **kwargs): pass
        def communicate(self, content, timeout):
            data = json.loads(content)
            assert data["request"]["mp_api_key"] == "secret-mp"
            output = Path(data["output"])
            (output / "report.md").write_text("report")
            stage(output, "prepared")
            return None, None
    monkeypatch.setattr(server.subprocess, "Popen", Worker)
    with TestClient(create_app(runs=tmp_path)) as client:
        assert client.get("/health").status_code == 200
        response = client.post("/jobs", json={"task": "硅", "mode": "prepare", "mp_api_key": "secret-mp", "llm_api_key": "secret-llm"})
        assert response.status_code == 202
        job = response.json()
        url = "/jobs/" + job["job_id"]
        assert client.get(url).status_code == 404
        headers = {"Authorization": "Bearer " + job["token"]}
        for _ in range(100):
            response = client.get(url, headers=headers)
            if response.json()["status"] == "prepared": break
            time.sleep(.01)
        assert response.json()["status"] == "prepared"
        assert "access.json" not in response.json()["artifacts"]
        assert client.get(url + "/artifacts/report.md", headers=headers).text == "report"
        assert client.get(url + "/artifacts/access.json", headers=headers).status_code == 404
    files = "".join(p.read_text() for p in tmp_path.rglob("*") if p.is_file())
    assert "secret-mp" not in files and "secret-llm" not in files


def test_validation_does_not_echo_secrets(tmp_path):
    with TestClient(create_app(runs=tmp_path, root=tmp_path / "missing-kssolv")) as client:
        response = client.post("/jobs", json={"task": "Si", "mp_api_key": {"secret": "do-not-echo"}, "llm_api_key": "a"})
        assert response.status_code == 422
        assert "do-not-echo" not in response.text
        response = client.post("/jobs", json={"task": "Si", "mp_api_key": "a", "llm_api_key": "b"})
        assert response.status_code == 503


def test_restart_marks_incomplete(tmp_path):
    output = tmp_path / "old"
    output.mkdir()
    stage(output, "calculating")
    with TestClient(create_app(runs=tmp_path)):
        assert json.loads((output / "status.json").read_text())["status"] == "interrupted"


def test_timeout_is_terminal(tmp_path, monkeypatch):
    import kssolv_crew.server as server
    killed = []
    class Worker:
        def __init__(self, *a, **kw): pass
        def communicate(self, *a, **kw):
            raise server.subprocess.TimeoutExpired("worker", 1)
    monkeypatch.setattr(server.subprocess, "Popen", Worker)
    monkeypatch.setattr(server, "kill_worker", lambda proc: killed.append(True))
    with TestClient(create_app(runs=tmp_path, timeout=1)) as client:
        job = client.post("/jobs", json={"task": "Si", "mode": "prepare", "mp_api_key": "a", "llm_api_key": "b"}).json()
        for _ in range(100):
            result = client.get("/jobs/" + job["job_id"], headers={"Authorization": "Bearer " + job["token"]}).json()
            if result["status"] == "timed_out": break
            time.sleep(.01)
        assert result["status"] == "timed_out"
        assert killed == [True]
