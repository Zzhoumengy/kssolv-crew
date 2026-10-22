import json
import pytest
from kssolv_crew.engine import validate_outputs


def test_matlab_transcript_is_stringio_and_flushes(tmp_path):
    import io
    from kssolv_crew.engine import MatlabTranscript
    log = tmp_path / "engine.log"
    with MatlabTranscript(log) as transcript:
        assert isinstance(transcript, io.StringIO)
        transcript.write("SCF converged\n")
        assert "SCF converged" in log.read_text()


def test_engine_closes_on_matlab_failure(tmp_path, monkeypatch):
    import sys
    from types import ModuleType
    import kssolv_crew.engine as runner
    root = tmp_path / "kssolv-3o-dev"
    root.mkdir()
    closed = []
    class Engine:
        def addpath(self, *a, **kw): pass
        def run_kssolv_job(self, *a, **kw): raise RuntimeError("MATLAB failed")
        def quit(self): closed.append(True)
    module = ModuleType("matlab")
    module.engine = ModuleType("matlab.engine")
    module.engine.start_matlab = lambda *args: Engine()
    monkeypatch.setitem(sys.modules, "matlab", module)
    monkeypatch.setitem(sys.modules, "matlab.engine", module.engine)
    with pytest.raises(RuntimeError, match="MATLAB failed"):
        runner.calculate(root, tmp_path)
    assert closed == [True]


def test_reject_missing_segment(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"segments": [{}, {}]}))
    (tmp_path / "engine_result.json").write_text(json.dumps({"scf_returned": True, "density_finite": True, "segments": 1}))
    with pytest.raises(ValueError, match="Incomplete"):
        validate_outputs(tmp_path)


def test_reject_non_png(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"segments": [{}]}))
    (tmp_path / "engine_result.json").write_text(json.dumps({"scf_returned": True, "density_finite": True, "segments": 1}))
    (tmp_path / "band_001_01.png").write_text("not an image")
    with pytest.raises(ValueError, match="PNG"):
        validate_outputs(tmp_path)


@pytest.mark.integration
def test_real_matlab_kssolv(silicon, tmp_path):
    import os
    if os.environ.get("RUN_KSSOLV_INTEGRATION") != "1":
        pytest.skip("Set RUN_KSSOLV_INTEGRATION=1 and KSSOLV_ROOT for actual SCF/NSCF")
    from kssolv_crew.convert import prepare
    from kssolv_crew.models import Parameters
    from kssolv_crew.engine import calculate
    prepare(silicon, Parameters(), tmp_path)
    result = calculate(os.environ["KSSOLV_ROOT"], tmp_path)
    assert result["density_finite"] is True
    assert list(tmp_path.glob("band_*.png"))
