import json
from pathlib import Path
from zipfile import ZipFile
import pytest
from kssolv_crew.bundle import bundle


def test_full_folder_and_no_project_secrets(tmp_path):
    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)
    (project / "src" / "main.py").write_text("print('ok')")
    (project / ".env").write_text("secret")
    vendor = tmp_path / "kssolv-3o-dev"
    (vendor / "nested" / "empty").mkdir(parents=True)
    (vendor / "nested" / "data.bin").write_bytes(b"\0\1\2")
    result = bundle(project, tmp_path / "release.zip", vendor)
    with ZipFile(result) as archive:
        assert archive.read("kssolv-crew/kssolv-3o-dev/nested/data.bin") == b"\0\1\2"
        assert "kssolv-crew/kssolv-3o-dev/nested/empty/" in archive.namelist()
        assert not any(".env" in n for n in archive.namelist())
        manifest = json.loads(archive.read("kssolv-crew/BUNDLE-MANIFEST.json"))
        assert any(x["path"].endswith("data.bin") and len(x["sha256"]) == 64 for x in manifest)
    with pytest.raises(ValueError, match="already exists"):
        bundle(project, result, vendor)
    with pytest.raises(ValueError, match="outside"):
        bundle(project, vendor / "bad.zip", vendor)


def test_wrong_folder_name(tmp_path):
    with pytest.raises(ValueError, match="named"):
        bundle(tmp_path, tmp_path / "out.zip", tmp_path)
