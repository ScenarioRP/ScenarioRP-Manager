. "$PSScriptRoot\common.ps1"

Write-ManagerLine "INFO" "Manager" "Restarting ScenarioRP"
& "$PSScriptRoot\stop-server.ps1"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Start-Sleep -Seconds 1
& "$PSScriptRoot\start-server.ps1"
exit $LASTEXITCODE
