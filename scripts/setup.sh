#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
"${PYTHON:-python3.12}" -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
if [ -n "${MATLAB_ROOT:-}" ]; then
  .venv/bin/python -m pip install "$MATLAB_ROOT/extern/engines/python"
fi
.venv/bin/python -m kssolv_crew.cli doctor
