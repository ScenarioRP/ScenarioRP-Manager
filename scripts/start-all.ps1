. "$PSScriptRoot\common.ps1"

Write-ManagerLine "INFO" "Manager" "Starting ScenarioRP server environment"
& "$PSScriptRoot\start-server.ps1"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& "$PSScriptRoot\start-discord-bot.ps1"
exit $LASTEXITCODE
