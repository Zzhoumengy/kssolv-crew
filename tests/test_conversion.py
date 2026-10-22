import json
import re
import numpy as np
import pytest
from pymatgen.core import Structure
from kssolv_crew.convert import BOHR_ANGSTROM, prepare, matrix, write_cached
from kssolv_crew.models import Parameters, JobRequest


def test_primitive_path_and_bohr(silicon, tmp_path):
    config = prepare(silicon, Parameters(), tmp_path)
    assert config["natoms"] == 2
    primitive = Structure.from_dict(json.loads((tmp_path / "primitive.json").read_text()))
    text = (tmp_path / (config["structure_function"] + ".m")).read_text()
    def extract(name):
        body = re.search(rf"{name} = \[(.*?)\];", text, re.S)[1]
        return np.array([[float(x) for x in row.split()] for row in body.split(";")])
    np.testing.assert_allclose(extract("C") * BOHR_ANGSTROM, primitive.lattice.matrix)
    np.testing.assert_allclose(extract("xyz") * BOHR_ANGSTROM,
                               np.mod(primitive.frac_coords, 1) @ primitive.lattice.matrix, atol=1e-12)
    assert all(np.shape(seg["points"]) == (2, 3) for seg in config["segments"])
    assert prepare(silicon, Parameters(), tmp_path) == config


def test_disorder_and_nonfinite_rejected(silicon, tmp_path):
    silicon.replace(0, {"Si": .5, "Ge": .5})
    with pytest.raises(ValueError, match="Disordered"):
        prepare(silicon, Parameters(), tmp_path)
    with pytest.raises(ValueError):
        matrix([[float("nan")]])


def test_non_symmetric_lattice_is_not_transposed(tmp_path):
    from pymatgen.core import Lattice
    structure = Structure(Lattice.hexagonal(2.46, 6.70), ["C", "C"], [[0,0,0],[1/3,2/3,.5]])
    config = prepare(structure, Parameters(), tmp_path)
    primitive = Structure.from_dict(json.loads((tmp_path / "primitive.json").read_text()))
    text = (tmp_path / (config["structure_function"] + ".m")).read_text()
    body = re.search(r"C = \[(.*?)\];", text, re.S)[1]
    actual = np.array([[float(x) for x in row.split()] for row in body.split(";")])
    assert not np.allclose(primitive.lattice.matrix, primitive.lattice.matrix.T)
    np.testing.assert_allclose(actual * BOHR_ANGSTROM, primitive.lattice.matrix, atol=1e-12)


def test_cache_never_overwrites(tmp_path):
    f = tmp_path / "existing.m"
    f.write_text("original")
    with pytest.raises(ValueError, match="differs"):
        write_cached(f, "changed")
    assert f.read_text() == "original"


def test_parameter_validation_and_secrets():
    with pytest.raises(ValueError):
        Parameters(mesh=(0, 2, 2))
    with pytest.raises(ValueError):
        Parameters(ecut=-1)
    with pytest.raises(ValueError):
        JobRequest(task="Si", material_id="../bad", mp_api_key="a", llm_api_key="b")
    req = JobRequest(task="Si", mp_api_key="private-mp", llm_api_key="private-llm")
    assert "private-" not in req.model_dump_json()
