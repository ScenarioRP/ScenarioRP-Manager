. "$PSScriptRoot\common\bootstrap.ps1"

$environment = Test-EnvironmentChecks -Checks @(Get-DiscordBotEnvironmentChecks)
if (-not $environment.Ok) {
    exit 1
}

New-Item -ItemType Directory -Force -Path $StateDir | Out-Null

$botPid = Get-PidFromFile $BotPidFile
if ($botPid -and (Get-ManagedProcess -ProcessId $botPid -ExpectedName "python.exe" -ExpectedPath $BotPython -CommandContains $BotFile)) {
    Write-ManagerLine "INFO" "DiscordBot" "Already running with PID $botPid"
    exit 0
}

Remove-StalePid $BotPidFile
Stop-ManagedProcessesBySignature -ExpectedName "python.exe" -CommandContains $BotFile -Source "DiscordBot" | Out-Null

Write-ManagerLine "INFO" "DiscordBot" "Starting Discord Bot"
$bot = Start-Process -FilePath $BotPython -ArgumentList "`"$BotFile`"" -WorkingDirectory $BotDir -WindowStyle Hidden -PassThru
$bot.Id | Set-Content -LiteralPath $BotPidFile
Write-ManagerLine "INFO" "DiscordBot" "Started with PID $($bot.Id)"

if (-not (Get-ManagedProcess -ProcessId $bot.Id -ExpectedName "python.exe" -ExpectedPath $BotPython -CommandContains $BotFile)) {
    Remove-StalePid $BotPidFile
    Write-ManagerLine "ERROR" "DiscordBot" "Discord Bot exited during startup"
    exit 1
}

exit 0
