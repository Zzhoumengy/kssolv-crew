from kssolv_crew.config import resolve_kssolv


def test_sibling_and_bundled_layout(tmp_path, monkeypatch):
    monkeypatch.delenv("KSSOLV_ROOT", raising=False)
    project = tmp_path / "kssolv-crew"
    project.mkdir()
    sibling = tmp_path / "kssolv-3o-dev"
    sibling.mkdir()
    assert resolve_kssolv(project=project) == sibling
    bundled = project / "kssolv-3o-dev"
    bundled.mkdir()
    assert resolve_kssolv(project=project) == bundled


def test_explicit_and_environment_override(tmp_path, monkeypatch):
    monkeypatch.setenv("KSSOLV_ROOT", str(tmp_path / "environment"))
    assert resolve_kssolv(project=tmp_path) == tmp_path / "environment"
    assert resolve_kssolv(tmp_path / "explicit", project=tmp_path) == tmp_path / "explicit"


def test_cli_bundle_defaults_and_source_only(tmp_path, monkeypatch):
    import sys
    from zipfile import ZipFile
    from kssolv_crew.cli import main
    monkeypatch.delenv("KSSOLV_ROOT", raising=False)
    project = tmp_path / "kssolv-crew"
    project.mkdir()
    (project / "start.cmd").write_text("@echo off")
    vendor = tmp_path / "kssolv-3o-dev"
    vendor.mkdir()
    (vendor / "example.m").write_text("% content")
    monkeypatch.setattr(sys, "argv", ["kssolv-crew", "bundle", "--project", str(project)])
    main()
    with ZipFile(project / "dist" / "kssolv-crew-with-kssolv.zip") as archive:
        assert archive.read("kssolv-crew/kssolv-3o-dev/example.m") == b"% content"
        assert "kssolv-crew/start.cmd" in archive.namelist()
    monkeypatch.setattr(sys, "argv", ["kssolv-crew", "bundle", "--project", str(project), "--source-only"])
    main()
    with ZipFile(project / "dist" / "kssolv-crew-source.zip") as archive:
        assert not any("kssolv-3o-dev/" in name for name in archive.namelist())
