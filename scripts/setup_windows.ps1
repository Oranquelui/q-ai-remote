$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
Set-Location $RootDir

$VenvPython = Join-Path $RootDir ".venv\\Scripts\\python.exe"

function Invoke-Setup {
    param([string]$PythonCommand)
    & $PythonCommand (Join-Path $RootDir "scripts\\setup_wizard.py")
    return $LASTEXITCODE
}

if (Test-Path $VenvPython) {
    $rc = Invoke-Setup -PythonCommand $VenvPython
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 (Join-Path $RootDir "scripts\\setup_wizard.py")
    $rc = $LASTEXITCODE
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python (Join-Path $RootDir "scripts\\setup_wizard.py")
    $rc = $LASTEXITCODE
} else {
    Write-Host "[ERROR] Python not found. Install Python 3 first."
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host ""
if ($rc -eq 0) {
    Write-Host "[OK] setup completed"
} else {
    Write-Host "[ERROR] setup failed (code=$rc)"
}
Read-Host "Press Enter to close"
exit $rc

