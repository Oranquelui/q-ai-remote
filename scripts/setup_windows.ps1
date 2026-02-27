$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
Set-Location $RootDir

$SetupScript = Join-Path $RootDir "scripts\setup_wizard.py"
$ManagerScript = Join-Path $RootDir "scripts\bot_manager.py"
$VenvPython = Join-Path $RootDir ".venv\Scripts\python.exe"

$SetupPython = $null
$SetupArgs = @()
$BotPython = $null

if (Test-Path $VenvPython) {
    $SetupPython = $VenvPython
    $SetupArgs = @($SetupScript)
    $BotPython = $VenvPython
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $SetupPython = (Get-Command python).Source
    $SetupArgs = @($SetupScript)
    $BotPython = $SetupPython
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $SetupPython = (Get-Command py).Source
    $SetupArgs = @("-3", $SetupScript)
    $BotPython = $SetupPython
} else {
    Write-Host "[ERROR] Python not found. Install Python 3 first."
    Read-Host "Press Enter to close"
    exit 1
}

& $SetupPython @SetupArgs
$rc = $LASTEXITCODE

Write-Host ""
if ($rc -eq 0) {
    Write-Host "[OK] setup completed"

    if ($env:QCA_SETUP_AUTOSTART -match "^(n|N|no|NO|0|false|FALSE)$") {
        Read-Host "Press Enter to close"
        exit 0
    }

    $activeFile = Join-Path $RootDir "config\.active_instance"
    $instanceId = "default"
    if (Test-Path $activeFile) {
        $raw = (Get-Content $activeFile -Raw).Trim()
        if ($raw) { $instanceId = $raw }
    }

    $scope = $env:QCA_SETUP_AUTOSTART_SCOPE
    if (-not $scope) { $scope = "active" }

    Write-Host "[INFO] Starting bot manager..."
    if ($scope -match "^(all|ALL|All)$") {
        & $SetupPython $ManagerScript start --all --restart --python-bin $BotPython
    } else {
        & $SetupPython $ManagerScript restart --instance-id $instanceId --python-bin $BotPython
    }
    $rc2 = $LASTEXITCODE

    if ($rc2 -eq 0) {
        Write-Host "[OK] bot manager started"
        Write-Host "[INFO] status: $SetupPython $ManagerScript status --all"
    } else {
        Write-Host "[ERROR] bot manager start failed (code=$rc2)"
        $rc = $rc2
    }
} else {
    Write-Host "[ERROR] setup failed (code=$rc)"
}

Read-Host "Press Enter to close"
exit $rc
