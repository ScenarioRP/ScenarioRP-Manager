. "$PSScriptRoot\common.ps1"

Write-ManagerLine "INFO" "Manager" "Stopping ScenarioRP"
Write-ManagerLine "INFO" "DiscordBot" "Stopping Discord Bot before FXServer"
$botOk = Stop-ManagedProcess -PidFile $BotPidFile -ExpectedName "python.exe" -ExpectedPath $BotPython -CommandContains $BotFile -Source "DiscordBot"
$extraBotOk = Stop-ManagedProcessesBySignature -ExpectedName "python.exe" -CommandContains $BotFile -Source "DiscordBot"

Write-ManagerLine "INFO" "FXServer" "Stopping FXServer"
$fxOk = Stop-ManagedProcess -PidFile $FxPidFile -ExpectedName "FXServer.exe" -ExpectedPath $FxServerExe -Source "FXServer"
$extraFxOk = Stop-ManagedProcessesBySignature -ExpectedName "FXServer.exe" -ExpectedPath $FxServerExe -Source "FXServer"

if ($botOk -and $extraBotOk -and $fxOk -and $extraFxOk) {
    Write-ManagerLine "INFO" "Manager" "ScenarioRP stopped"
    exit 0
}

Write-ManagerLine "ERROR" "Manager" "ScenarioRP stop failed"
exit 1
