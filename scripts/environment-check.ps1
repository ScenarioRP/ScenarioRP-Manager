. "$PSScriptRoot\common.ps1"

$checks = @(
    @{ Name = "FXServer.exe"; Path = $FxServerExe },
    @{ Name = "txData profile"; Path = $TxDataDir },
    @{ Name = "server.cfg"; Path = $ServerCfg },
    @{ Name = "txAdmin profile config"; Path = $TxAdminConfig },
    @{ Name = "Discord bot directory"; Path = $BotDir },
    @{ Name = "Discord bot Python"; Path = $BotPython },
    @{ Name = "Discord bot file"; Path = $BotFile }
)

$ok = $true
foreach ($check in $checks) {
    if (Test-Path -LiteralPath $check.Path) {
        Write-ManagerLine "INFO" "Environment" "OK | $($check.Name) | $($check.Path)"
    }
    else {
        $ok = $false
        Write-ManagerLine "ERROR" "Environment" "Missing | $($check.Name) | $($check.Path)"
    }
}

if (-not $ok) {
    exit 1
}
