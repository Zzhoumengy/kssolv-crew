param([string]$KssolvDir = "", [string]$Output = "", [string]$Python = "", [switch]$SourceOnly)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")
Set-Location -LiteralPath $ProjectDir
$PythonPath = Find-Python $Python
if (-not $Output) {
    $Label = if ($SourceOnly) { "source" } else { "with-kssolv" }
    $Output = "dist\kssolv-crew-$Label-$(Get-Date -Format 'yyyyMMdd-HHmmss').zip"
}
$PreviousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $ProjectDir "src"
    $BundleArgs = @("-m", "kssolv_crew.cli", "bundle", "--output", $Output)
    if ($SourceOnly) { $BundleArgs += "--source-only" }
    else { $BundleArgs += @("--kssolv-dir", (Find-Kssolv $KssolvDir)) }
    & $PythonPath @BundleArgs
    if ($LASTEXITCODE -ne 0) { throw "Bundle failed" }
} finally { $env:PYTHONPATH = $PreviousPythonPath }
