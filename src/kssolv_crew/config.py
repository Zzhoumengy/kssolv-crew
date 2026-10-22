"""Resolve both the development sibling layout and the bundled layout."""
import os
from pathlib import Path


def resolve_kssolv(explicit=None, project=None):
    configured = explicit or os.environ.get("KSSOLV_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    bases = [Path(project).resolve()] if project else [Path.cwd().resolve()]
    source_project = Path(__file__).resolve().parents[2]
    if project is None and (source_project / "pyproject.toml").is_file():
        bases.append(source_project)
    for base in bases:
        for candidate in [base / "kssolv-3o-dev", base.parent / "kssolv-3o-dev"]:
            if candidate.is_dir():
                return candidate.resolve()
    return bases[0] / "kssolv-3o-dev"
