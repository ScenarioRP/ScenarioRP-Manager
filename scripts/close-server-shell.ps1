. "$PSScriptRoot\common.ps1"

Write-ManagerLine "INFO" "FXServer" "Close Shell requested"

$observedOffline = $false
if (Test-Path -LiteralPath $BotStateFile) {
    try {
        $state = Get-Content -LiteralPath $BotStateFile -Raw | ConvertFrom-Json
        if ($null -ne $state.last_known_online -and -not [bool]$state.last_known_online) {
            $observedOffline = $true
        }
    }
    catch {
        Write-ManagerLine "WARN" "DiscordBot" "Could not read bot state: $($_.Exception.Message)"
    }
}

if (-not $observedOffline) {
    Write-ManagerLine "ERROR" "FXServer" "Server shell can be closed only after the Discord bot observes the server offline."
    exit 1
}

$fxOk = Stop-ManagedProcess -PidFile $FxPidFile -ExpectedName "FXServer.exe" -ExpectedPath $FxServerExe -Source "FXServer" -Context "server shell PID"
$extraFxOk = Stop-ManagedProcessesBySignature -ExpectedName "FXServer.exe" -ExpectedPath $FxServerExe -Source "FXServer"

if ($fxOk -and $extraFxOk) {
    Write-ManagerLine "INFO" "FXServer" "Server shell closed"
    & "$PSScriptRoot\stop-discord-bot.ps1"
    $botCode = $LASTEXITCODE

    if ($botCode -eq 0) {
        Write-ManagerLine "INFO" "Manager" "Server shell and Discord Bot closed"
        exit 0
    }

    Write-ManagerLine "ERROR" "DiscordBot" "Server shell closed, but Discord Bot stop failed"
    exit 1
}

Write-ManagerLine "ERROR" "FXServer" "Server shell close failed"
exit 1
