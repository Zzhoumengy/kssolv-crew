@echo off
if not exist "%~dp0.venv\Scripts\pythonw.exe" (
  echo Please run install.cmd first.
  pause
  exit /b 1
)
pushd "%~dp0"
start "" "%~dp0.venv\Scripts\pythonw.exe" -m kssolv_crew.cli desktop --project "%~dp0."
popd
