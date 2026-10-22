$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")
Set-Location -LiteralPath $ProjectDir
$PythonPath = Join-Path $ProjectDir ".venv\Scripts\python.exe"
& $PythonPath -m kssolv_crew.cli stop --project $ProjectDir
exit $LASTEXITCODE
