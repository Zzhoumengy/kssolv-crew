param([string]$KssolvDir = "", [int]$Port = 8000, [switch]$NoBrowser, [switch]$Foreground)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")
Set-Location -LiteralPath $ProjectDir
$KssolvPath = Find-Kssolv $KssolvDir
$PythonPath = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $PythonPath)) { throw "Double-click install.cmd first." }
Write-Host "KSSOLV: $KssolvPath"
if ($Foreground) {
    & $PythonPath -m kssolv_crew.cli serve --kssolv-dir $KssolvPath --port $Port
} else {
    $LaunchArgs = @("-m", "kssolv_crew.cli", "launch", "--project", $ProjectDir, "--kssolv-dir", $KssolvPath, "--port", $Port)
    if ($NoBrowser) { $LaunchArgs += "--no-browser" }
    & $PythonPath @LaunchArgs
}
exit $LASTEXITCODE
