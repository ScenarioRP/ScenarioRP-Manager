. "$PSScriptRoot\common.ps1"

Write-ManagerLine "INFO" "Manager" "Safe Shutdown requested"
& "$PSScriptRoot\stop-server.ps1"
$stopCode = $LASTEXITCODE

Write-ManagerLine "INFO" "Manager" "TODO: MariaDB shutdown is not implemented in this stage"

$fxPid = Get-PidFromFile $FxPidFile
$botPid = Get-PidFromFile $BotPidFile
if ($stopCode -eq 0 -and -not $fxPid -and -not $botPid) {
    Write-ManagerLine "INFO" "Manager" "ScenarioRP is safe to close."
    exit 0
}

Write-ManagerLine "ERROR" "Manager" "Safe Shutdown incomplete"
exit 1
