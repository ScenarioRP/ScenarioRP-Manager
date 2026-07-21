. "$PSScriptRoot\common\bootstrap.ps1"

Write-ManagerLine "INFO" "DiscordBot" "Restarting Discord Bot"
& "$PSScriptRoot\stop-discord-bot.ps1"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Start-Sleep -Seconds 1
& "$PSScriptRoot\start-discord-bot.ps1"
exit $LASTEXITCODE
