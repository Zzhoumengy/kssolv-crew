"""Source release bundler: does not execute or inspect KSSOLV code."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def bundle(project, destination, kssolv=None):
    project, destination = Path(project).resolve(), Path(destination).resolve()
    vendor = Path(kssolv).resolve() if kssolv else None
    if destination.exists():
        raise ValueError("Destination already exists; choose a new ZIP filename")
    if vendor is not None:
        if not vendor.is_dir() or vendor.name != "kssolv-3o-dev":
            raise ValueError("Choose a directory named kssolv-3o-dev")
        if destination.is_relative_to(vendor):
            raise ValueError("Output ZIP must be outside the KSSOLV directory")
    entries = []
    # Only source/explicit docs; never include credentials, runs or virtualenv.
    for name in ["src", "tests", "scripts", "docs"]:
        entries += [(p, Path(name) / p.relative_to(project / name))
                    for p in (project / name).rglob("*") if p.is_file()
                    and "__pycache__" not in p.parts and p.suffix != ".pyc"
                    and not any(part.endswith(".egg-info") for part in p.parts)]
    for name in ["pyproject.toml", "README.md", "requirements.txt", "requirements-lock.txt", "MANIFEST.in", ".gitignore"]:
        if (project / name).is_file():
            entries.append((project / name, Path(name)))
    if vendor:
        entries += [(p, Path("kssolv-3o-dev") / p.relative_to(vendor)) for p in vendor.rglob("*") if p.is_file()]
    entries.extend((p, Path(p.name)) for p in project.glob("*.cmd") if p.is_file())
    for path, relative in entries:
        # Do not follow linked files outside the chosen package roots.
        if path.is_symlink() or any(parent.is_symlink() or getattr(parent, "is_junction", lambda: False)() for parent in path.parents
                                    if parent != project and parent != vendor):
            raise ValueError("Symlinks are unsupported in release bundles")
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = []
    # ZIP64 supports large KSSOLV trees. Stream files instead of loading them into memory.
    try:
        with ZipFile(destination, "x", compression=ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
            for path, relative in sorted(entries, key=lambda item: str(item[1])):
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    while block := stream.read(1024 * 1024):
                        digest.update(block)
                arcname = (Path("kssolv-crew") / relative).as_posix()
                archive.write(path, arcname)
                manifest.append({"path": relative.as_posix(), "bytes": path.stat().st_size, "sha256": digest.hexdigest()})
            # Preserve empty directories too, including a completely empty named folder.
            if vendor:
                archive.mkdir("kssolv-crew/kssolv-3o-dev/")
                for folder in sorted(vendor.rglob("*")):
                    if folder.is_dir() and not any(folder.iterdir()):
                        archive.mkdir("kssolv-crew/kssolv-3o-dev/" + folder.relative_to(vendor).as_posix() + "/")
            archive.writestr("kssolv-crew/BUNDLE-MANIFEST.json", json.dumps(manifest, indent=2))
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination
