import json
import io
from pathlib import Path


class MatlabTranscript(io.StringIO):
    """Engine requires StringIO; mirror writes to a live, flushed log file."""
    def __init__(self, path):
        super().__init__()
        self.log = Path(path).open("w", encoding="utf-8")

    def write(self, text):
        self.log.write(text)
        self.log.flush()
        return len(text)

    def close(self):
        self.log.close()
        super().close()


def calculate(root, output, session=None):
    root, output = Path(root).resolve(), Path(output).resolve()
    if not root.is_dir() or root.name != "kssolv-3o-dev":
        raise ValueError("KSSOLV root must be an existing kssolv-3o-dev directory")
    import matlab.engine
    engine = session
    owns_session = session is None
    try:
        if engine is None:
            engine = matlab.engine.start_matlab("-nodesktop -nosplash")
        engine.addpath(str(Path(__file__).parent / "matlab"), nargout=0)
        with MatlabTranscript(output / "engine_console.log") as transcript:
            engine.run_kssolv_job(str(root), str(output), nargout=0, stdout=transcript, stderr=transcript)
    finally:
        if engine is not None and owns_session:
            engine.quit()
    return validate_outputs(output)


def validate_outputs(output):
    output = Path(output)
    result = json.loads((output / "engine_result.json").read_text(encoding="utf-8"))
    cfg = json.loads((output / "config.json").read_text(encoding="utf-8"))
    if result.get("scf_returned") is not True or result.get("density_finite") is not True:
        raise ValueError("SCF result validation failed")
    count = len(cfg["segments"])
    if result.get("segments") != count:
        raise ValueError("Incomplete band path")
    required = [output / "scf_state.mat"]
    for i in range(1, count + 1):
        plots = list(output.glob(f"band_{i:03d}_*.png"))
        if not plots:
            raise ValueError("Missing band plot")
        for plot in plots:
            if plot.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError("Invalid PNG output")
        required += plots + [output / f"plot_data_{i:03d}.mat"]
        data_path = output / f"band_data_{i:03d}.json"
        if data_path.exists():
            import numpy as np
            data = json.loads(data_path.read_text(encoding="utf-8"))
            energy = np.asarray(data["energy_bands"], dtype=float)
            kpoints = np.asarray(data["k_fractional"], dtype=float)
            if (energy.ndim != 2 or kpoints.ndim != 2 or kpoints.shape[1] != 3
                    or energy.shape != (cfg["parameters"]["nbnd"], len(kpoints))
                    or not np.isfinite(energy).all() or not np.isfinite(kpoints).all()):
                raise ValueError("Band eigenvalue data validation failed")
            required.append(data_path)
    if any(not p.is_file() or p.stat().st_size == 0 for p in required):
        raise ValueError("Missing or empty calculation output")
    return result
