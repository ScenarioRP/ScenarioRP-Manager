. "$PSScriptRoot\common.ps1"

if (-not (Test-TcpPort -HostName $TxAdminHost -Port $TxAdminPort)) {
    Write-ManagerLine "ERROR" "txAdmin" "txAdmin is not available: not listening on ${TxAdminHost}:$TxAdminPort"
    exit 1
}

Start-Process $TxAdminUrl
Write-ManagerLine "INFO" "txAdmin" "Opened $TxAdminUrl"
