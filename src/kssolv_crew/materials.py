import json
from pathlib import Path


def fetch_structure(formula, material_id, key, output):
    from mp_api.client import MPRester
    with MPRester(api_key=key, mute_progress_bars=True) as mpr:
        docs = mpr.materials.summary.search(
            **({"material_ids": [material_id]} if material_id else {"formula": formula}),
            fields=["material_id", "structure", "energy_above_hull", "formula_pretty"])
    if not docs:
        raise ValueError("Materials Project returned no structures")
    # Stable deterministic choice, retain all candidates for user review.
    docs.sort(key=lambda d: (float(d.energy_above_hull) if d.energy_above_hull is not None else float("inf"), str(d.material_id)))
    selected = docs[0]
    from pymatgen.core import Composition
    if Composition(selected.formula_pretty).reduced_composition != Composition(formula).reduced_composition:
        raise ValueError("Selected material_id does not match requested formula")
    metadata = {"material_id": str(selected.material_id), "formula": selected.formula_pretty,
                "selection": "lowest energy_above_hull, then material_id; explicit id takes precedence",
                "candidates": [{"material_id": str(d.material_id), "energy_above_hull": d.energy_above_hull} for d in docs]}
    Path(output, "structure.json").write_text(json.dumps(selected.structure.as_dict(), indent=2), encoding="utf-8")
    Path(output, "selection.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return selected.structure, metadata
