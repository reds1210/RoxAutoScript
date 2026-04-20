param(
    [string]$VenvPath = ".venv",
    [switch]$InstallFullStack
)

$ErrorActionPreference = "Stop"

python -m venv $VenvPath

$pythonExe = Join-Path $VenvPath "Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Virtual environment python executable not found at $pythonExe"
}

& $pythonExe -m pip install --upgrade pip

$extras = if ($InstallFullStack) { ".[all]" } else { ".[dev]" }
& $pythonExe -m pip install -e $extras

Write-Host "Bootstrap complete using $pythonExe"

