. "$PSScriptRoot\common.ps1"

$environment = Test-EnvironmentChecks -Checks @(Get-ServerEnvironmentChecks)
if (-not $environment.Ok) {
    exit 1
}

New-Item -ItemType Directory -Force -Path $StateDir | Out-Null

$fxPid = Get-PidFromFile $FxPidFile
if ($fxPid -and (Get-ManagedProcess -ProcessId $fxPid -ExpectedName "FXServer.exe" -ExpectedPath $FxServerExe)) {
    Write-ManagerLine "INFO" "FXServer" "Already running with PID $fxPid"
}
else {
    Remove-StalePid $FxPidFile

    $existingFxServers = @(Get-ManagedProcessesBySignature -ExpectedName "FXServer.exe" -ExpectedPath $FxServerExe)
    if ($existingFxServers.Count -gt 0) {
        Write-ManagerLine "ERROR" "FXServer" "FXServer is already running outside this Manager session. Use txAdmin to manage the running server."
        exit 1
    }

    $txAdminPortOwner = Get-ListeningPid $TxAdminPort
    if ($txAdminPortOwner) {
        Write-ManagerLine "ERROR" "txAdmin" "Port $TxAdminPort is already in use by PID $txAdminPortOwner"
        exit 1
    }

    $portOwner = Get-ListeningPid 30120
    if ($portOwner) {
        Write-ManagerLine "ERROR" "FXServer" "Port 30120 is already in use by PID $portOwner"
        exit 1
    }

    Write-ManagerLine "INFO" "txAdmin" "Starting txAdmin profile '$TxAdminProfile'"
    $arguments = @("+set", "txAdminPort", "$TxAdminPort", "+set", "txAdminProfile", $TxAdminProfile)
    $fx = Start-Process -FilePath $FxServerExe -ArgumentList $arguments -WorkingDirectory $FxServerDir -WindowStyle Minimized -PassThru
    $fx.Id | Set-Content -LiteralPath $FxPidFile
    Write-ManagerLine "INFO" "FXServer" "Started with PID $($fx.Id)"

    if (-not (Get-ManagedProcess -ProcessId $fx.Id -ExpectedName "FXServer.exe" -ExpectedPath $FxServerExe)) {
        Remove-StalePid $FxPidFile
        Write-ManagerLine "ERROR" "FXServer" "FXServer exited during startup"
        exit 1
    }

    Write-ManagerLine "INFO" "txAdmin" "Waiting for $TxAdminUrl"
    if (Wait-TcpPort -HostName $TxAdminHost -Port $TxAdminPort -TimeoutSeconds 30) {
        Write-ManagerLine "INFO" "txAdmin" "Listening on $TxAdminUrl"
    }
    else {
        Write-ManagerLine "ERROR" "txAdmin" "txAdmin did not start listening on ${TxAdminHost}:$TxAdminPort"
        exit 1
    }
}

exit 0
