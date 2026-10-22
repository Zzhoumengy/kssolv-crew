import hashlib
import json
import re
from pathlib import Path
import numpy as np

BOHR_ANGSTROM = 0.529177210903


def matlab_string(value):
    return "'" + str(value).replace("'", "''") + "'"


def matrix(value):
    a = np.asarray(value, dtype=float)
    if not np.isfinite(a).all():
        raise ValueError("Non-finite matrix")
    return "[" + ";\n".join(" ".join(f"{x:.16g}" for x in row) for row in a) + "]"


def write_cached(path, text):
    path = Path(path)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise ValueError(f"Existing structure file differs: {path.name}")
        return
    path.write_text(text, encoding="utf-8")


def prepare(structure, parameters, output):
    from pymatgen.symmetry.bandstructure import HighSymmKpath
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    if not structure.is_ordered:
        raise ValueError("Disordered/partial-occupancy structures are unsupported")
    if not np.isfinite(structure.volume) or structure.volume <= 0:
        raise ValueError("Invalid unit cell")
    if len(structure) > 200:
        raise ValueError("Structure exceeds 200-site safety limit")
    # Setyawan-Curtarolo k coordinates refer to this very primitive standard cell.
    primitive = SpacegroupAnalyzer(structure).get_primitive_standard_structure(international_monoclinic=False)
    path = HighSymmKpath(primitive, path_type="setyawan_curtarolo")
    lattice = np.asarray(primitive.lattice.matrix)
    frac = np.mod(primitive.frac_coords, 1)
    cart_bohr = frac @ lattice / BOHR_ANGSTROM
    symbols = [s.specie.symbol for s in primitive]
    if any(not re.fullmatch(r"[A-Z][a-z]?", s) for s in symbols):
        raise ValueError("Unsupported species")
    identity = json.dumps(primitive.as_dict(), sort_keys=True)
    name = "mpstruct_" + hashlib.sha256(identity.encode()).hexdigest()[:16]
    atoms = "\n".join(f"atomlist({i}) = Atom('{symbol}');" for i, symbol in enumerate(symbols, 1))
    text = (f"function crystal = {name}()\n% Generated Cartesian coordinates and lattice in Bohr.\n"
            f"{atoms}\nC = {matrix(lattice / BOHR_ANGSTROM)};\nxyz = {matrix(cart_bohr)};\n"
            "crystal = Crystal('supercell', C, 'atomlist', atomlist, 'xyzlist', xyz);\nend\n")
    output = Path(output)
    write_cached(output / (name + ".m"), text)
    segments = []
    for branch in path.kpath["path"]:
        for a, b in zip(branch, branch[1:]):
            segments.append({"labels": [a, b], "points": [path.kpath["kpoints"][a].tolist(), path.kpath["kpoints"][b].tolist()]})
    if not segments:
        raise ValueError("Empty k path")
    config = {"structure_function": name, "parameters": parameters.model_dump(), "segments": segments,
              "coordinate_convention": "SC primitive reciprocal fractional; KSSOLV3 C rows are lattice vectors; xyz rows Cartesian Bohr",
              "natoms": len(primitive), "status": "prepared", "convergence_verified": False}
    (output / "primitive.json").write_text(json.dumps(primitive.as_dict(), indent=2), encoding="utf-8")
    (output / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config
