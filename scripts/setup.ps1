param([string]$Python = "", [string]$MatlabRoot = "", [string]$EngineVersion = "", [switch]$Dev)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")
Set-Location -LiteralPath $ProjectDir
$KssolvPath = Find-Kssolv
$BootstrapPython = Find-Python $Python
$MatlabPath = Find-Matlab $MatlabRoot
$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
    & $BootstrapPython -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Virtualenv creation failed" }
}
$null = Find-Python $VenvPython
Write-Host "KSSOLV: $KssolvPath"
Write-Host "MATLAB: $MatlabPath"
Write-Host "Python: $VenvPython"
$InstallTarget = "."
if ($Dev) { $InstallTarget = ".[dev]" }
& $VenvPython -m pip install -e $InstallTarget
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed; check the network and retry." }
$EngineDir = Join-Path $MatlabPath "extern\engines\python"
# The official PyPI build avoids writing build metadata under Program Files.
if (-not $EngineVersion -and (Split-Path -Leaf $MatlabPath) -eq "R2025b") { $EngineVersion = "25.2.2" }
if ($EngineVersion) { & $VenvPython -m pip install "matlabengine==$EngineVersion" }
else { & $VenvPython -m pip install $EngineDir }
if ($LASTEXITCODE -ne 0) { throw "MATLAB Engine installation failed. Check MATLAB/Python compatibility." }
& $VenvPython -c "import matlab.engine; import tkinter; import kssolv_crew; print('MATLAB Engine and desktop Tk import: OK')"
if ($LASTEXITCODE -ne 0) { throw "MATLAB Engine import failed. Check the MATLAB installation and Python version." }
& $VenvPython -m kssolv_crew.cli doctor
if ($LASTEXITCODE -ne 0) { throw "Environment check failed" }
Write-Host "Installation completed. Double-click start.cmd to open the desktop app. No browser is required."
