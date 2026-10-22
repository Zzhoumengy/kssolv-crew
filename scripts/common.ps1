$ProjectDir = Split-Path -Parent $PSScriptRoot

function Find-Kssolv([string]$Requested = "") {
    if ($Requested) { return [IO.Path]::GetFullPath($Requested) }
    if ($env:KSSOLV_ROOT) { return [IO.Path]::GetFullPath($env:KSSOLV_ROOT) }
    foreach ($Candidate in @((Join-Path $ProjectDir "kssolv-3o-dev"), (Join-Path (Split-Path -Parent $ProjectDir) "kssolv-3o-dev"))) {
        if (Test-Path -LiteralPath $Candidate -PathType Container) { return $Candidate }
    }
    throw "Cannot find kssolv-3o-dev. Place it beside kssolv-crew, inside it, or pass -KssolvDir."
}

function Find-Python([string]$Requested = "") {
    $Candidates = @()
    if ($Requested) { $Candidates += $Requested }
    else {
        $Candidates += (Join-Path $ProjectDir ".venv\Scripts\python.exe")
        if (Get-Command py -ErrorAction SilentlyContinue) {
            foreach ($Version in @("3.12", "3.11", "3.13")) {
                try {
                    $Found = & py "-$Version" -c "import sys; print(sys.executable)" 2>$null
                    if ($LASTEXITCODE -eq 0) { $Candidates += $Found; break }
                } catch { continue }
            }
        }
        if (Get-Command python -ErrorAction SilentlyContinue) { $Candidates += "python" }
    }
    foreach ($Candidate in $Candidates) {
        if (-not (Get-Command $Candidate -ErrorAction SilentlyContinue)) { continue }
        & $Candidate -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,14) else 1)" 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { return $Candidate }
    }
    throw "Python 3.11-3.13 is required (recommend 3.12). Run scripts/setup.ps1 -Python 'C:\path\python.exe'. Python 3.14 is not supported."
}

function Find-Matlab([string]$Requested = "") {
    if ($Requested) { return [IO.Path]::GetFullPath($Requested) }
    $MatlabCommand = Get-Command matlab -ErrorAction SilentlyContinue
    if ($MatlabCommand) {
        $Candidate = Split-Path -Parent (Split-Path -Parent $MatlabCommand.Source)
        if (Test-Path -LiteralPath (Join-Path $Candidate "extern\engines\python")) { return $Candidate }
    }
    $Parent = "$env:ProgramFiles\MATLAB"
    if (Test-Path -LiteralPath $Parent) {
        foreach ($Candidate in (Get-ChildItem -LiteralPath $Parent -Directory | Sort-Object Name -Descending)) {
            if (Test-Path -LiteralPath (Join-Path $Candidate.FullName "extern\engines\python")) { return $Candidate.FullName }
        }
    }
    throw "MATLAB was not found. Install MATLAB or pass -MatlabRoot 'C:\Program Files\MATLAB\R2025b'."
}
