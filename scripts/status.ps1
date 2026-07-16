. "$PSScriptRoot\common.ps1"

$fxPid = Get-PidFromFile $FxPidFile
if ($fxPid) {
    $fx = Get-ManagedProcess -ProcessId $fxPid -ExpectedName "FXServer.exe" -ExpectedPath $FxServerExe
    if ($fx) {
        Write-StatusLine "FXServer" "Running" "PID $fxPid"
    }
    else {
        Remove-StalePid $FxPidFile
        Write-StatusLine "FXServer" "Stopped" "Stale PID file removed"
    }
}
else {
    $fxProcesses = @(Get-ManagedProcessesBySignature -ExpectedName "FXServer.exe" -ExpectedPath $FxServerExe)
    if ($fxProcesses.Count -gt 0) {
        Write-StatusLine "FXServer" "Running" "Untracked PID $($fxProcesses[0].ProcessId)"
    }
    else {
        Write-StatusLine "FXServer" "Stopped" "No PID file"
    }
}

$botPid = Get-PidFromFile $BotPidFile
if ($botPid) {
    $bot = Get-ManagedProcess -ProcessId $botPid -ExpectedName "python.exe" -ExpectedPath $BotPython -CommandContains $BotFile
    if ($bot) {
        Write-StatusLine "Discord Bot" "Running" "PID $botPid"
    }
    else {
        Remove-StalePid $BotPidFile
        Write-StatusLine "Discord Bot" "Stopped" "Stale PID file removed"
    }
}
else {
    $botProcesses = @(Get-ManagedProcessesBySignature -ExpectedName "python.exe" -CommandContains $BotFile)
    if ($botProcesses.Count -gt 0) {
        Write-StatusLine "Discord Bot" "Running" "Untracked PID $($botProcesses[0].ProcessId)"
    }
    else {
        Write-StatusLine "Discord Bot" "Stopped" "No PID file"
    }
}

if (Test-TcpPort -HostName $TxAdminHost -Port $TxAdminPort) {
    Write-StatusLine "txAdmin" "Running" $TxAdminUrl
}
else {
    Write-StatusLine "txAdmin" "Stopped" "Not listening on ${TxAdminHost}:$TxAdminPort"
}

$maria = Get-Service -Name "MariaDB" -ErrorAction SilentlyContinue
if ($maria) {
    Write-StatusLine "Database" $maria.Status "MariaDB service"
}
else {
    Write-StatusLine "Database" "Unknown" "MariaDB service not found"
}
