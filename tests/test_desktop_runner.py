import json
from pathlib import Path
import subprocess
import threading
import pytest
from kssolv_crew.desktop_runner import DesktopRunner, history, read_json
from kssolv_crew.models import JobRequest
from kssolv_crew.storage import stage


def request():
    return JobRequest(task="计算硅能带", mp_api_key="desktop-private-mp", llm_api_key="desktop-private-llm", mode="prepare")


def test_desktop_executes_directly_without_web_and_keeps_keys_off_disk(tmp_path, monkeypatch):
    import kssolv_crew.desktop_runner as module
    captured = []
    gate = threading.Event()
    class Worker:
        def __init__(self, command, **options):
            assert command[-1] == "kssolv_crew.worker"
            assert options["stdin"] == subprocess.PIPE
        def communicate(self, content, timeout):
            payload = json.loads(content)
            captured.append(payload)
            gate.wait(5)
            output = Path(payload["output"])
            (output / "report.md").write_text("测试报告", encoding="utf-8")
            stage(output, "prepared")
    monkeypatch.setattr(module.subprocess, "Popen", Worker)
    runner = DesktopRunner(tmp_path)
    output = runner.submit(request())
    try:
        with pytest.raises(RuntimeError, match="已有任务"):
            runner.submit(request())
    finally:
        gate.set()
        runner.thread.join(5)
    assert read_json(output / "status.json")["status"] == "prepared"
    assert captured[0]["request"]["mp_api_key"] == "desktop-private-mp"
    assert captured[0]["request"]["llm_api_key"] == "desktop-private-llm"
    assert not (output / "access.json").exists()  # No Web token or server involved.
    text = "".join(p.read_text(encoding="utf-8") for p in output.rglob("*") if p.is_file())
    assert "desktop-private-" not in text
    assert history(tmp_path)[0]["id"] == output.name


def test_desktop_marks_timeout(tmp_path, monkeypatch):
    import kssolv_crew.desktop_runner as module
    killed = []
    class Worker:
        def __init__(self, *a, **kw): pass
        def communicate(self, *a, **kw): raise subprocess.TimeoutExpired("worker", 1)
    monkeypatch.setattr(module.subprocess, "Popen", Worker)
    monkeypatch.setattr(module, "kill_worker", lambda proc: killed.append(proc))
    runner = DesktopRunner(tmp_path, timeout=1)
    output = runner.submit(request())
    runner.thread.join(5)
    assert read_json(output / "status.json")["status"] == "timed_out"
    assert len(killed) == 1


def test_desktop_cancel(tmp_path, monkeypatch):
    import kssolv_crew.desktop_runner as module
    started, stopped = threading.Event(), threading.Event()
    class Worker:
        def __init__(self, *a, **kw): pass
        def communicate(self, *a, **kw):
            started.set()
            stopped.wait(5)
    monkeypatch.setattr(module.subprocess, "Popen", Worker)
    monkeypatch.setattr(module, "kill_worker", lambda proc: stopped.set())
    runner = DesktopRunner(tmp_path)
    output = runner.submit(request())
    assert started.wait(2)
    runner.cancel()
    runner.thread.join(5)
    assert read_json(output / "status.json")["status"] == "cancelled"


def test_run_requires_software_folder(tmp_path):
    runner = DesktopRunner(tmp_path, root=tmp_path / "missing")
    req = request().model_copy(update={"mode": "run"})
    with pytest.raises(ValueError, match="kssolv-3o-dev"):
        runner.submit(req)


def test_web_startup_does_not_mark_desktop_job_interrupted(tmp_path):
    from fastapi.testclient import TestClient
    from kssolv_crew.server import create_app
    output = tmp_path / "job"
    output.mkdir()
    (output / "desktop_job.json").write_text("{}")
    stage(output, "calculating")
    with TestClient(create_app(runs=tmp_path)):
        assert read_json(output / "status.json")["status"] == "calculating"
