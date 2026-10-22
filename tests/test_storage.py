import json
from kssolv_crew.storage import atomic_json


def test_windows_sharing_violation_retries(tmp_path, monkeypatch):
    import kssolv_crew.storage as storage
    original = storage.os.replace
    calls = []
    def temporarily_locked(source, target):
        calls.append(source)
        if len(calls) < 3:
            raise PermissionError("reader has file open")
        return original(source, target)
    monkeypatch.setattr(storage.os, "replace", temporarily_locked)
    monkeypatch.setattr(storage.time, "sleep", lambda seconds: None)
    target = tmp_path / "status.json"
    atomic_json(target, {"status": "prepared"})
    assert json.loads(target.read_text())["status"] == "prepared"
    assert len(calls) == 3
    assert not list(tmp_path.glob("*.tmp"))
