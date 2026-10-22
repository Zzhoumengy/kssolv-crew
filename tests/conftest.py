import os
import tempfile
from pathlib import Path
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_TELEMETRY_DISABLED"] = "true"
os.environ["CREWAI_TRACING_ENABLED"] = "false"
_session_temp = Path(tempfile.mkdtemp(prefix="kssolv-crew-tests-"))
os.environ["CREWAI_STORAGE_DIR"] = str(_session_temp / "crew")


def pytest_configure(config):
    # Separate invocation directories also work across Windows user identities.
    if config.option.basetemp is None:
        config.option.basetemp = str(_session_temp / "cases")

import pytest
from pymatgen.core import Lattice, Structure


@pytest.fixture
def silicon():
    return Structure(Lattice.cubic(5.43), ["Si"] * 8,
        [[0,0,0],[0,.5,.5],[.5,0,.5],[.5,.5,0],
         [.25,.25,.25],[.25,.75,.75],[.75,.25,.75],[.75,.75,.25]])
