. "$PSScriptRoot\common\bootstrap.ps1"

Write-ManagerLine "INFO" "DiscordBot" "Stopping Discord Bot"
$botOk = Stop-ManagedProcess -PidFile $BotPidFile -ExpectedName "python.exe" -ExpectedPath $BotPython -CommandContains $BotFile -Source "DiscordBot"
$extraBotOk = Stop-ManagedProcessesBySignature -ExpectedName "python.exe" -CommandContains $BotFile -Source "DiscordBot"

if ($botOk -and $extraBotOk) {
    Write-ManagerLine "INFO" "DiscordBot" "Discord Bot stopped"
    exit 0
}

Write-ManagerLine "ERROR" "DiscordBot" "Discord Bot stop failed"
exit 1
