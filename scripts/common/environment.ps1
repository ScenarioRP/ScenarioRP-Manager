function Get-ServerEnvironmentChecks {
    return @(
        @{ Name = "FXServer.exe"; Path = $FxServerExe },
        @{ Name = "txData profile"; Path = $TxDataDir },
        @{ Name = "server.cfg"; Path = $ServerCfg },
        @{ Name = "txAdmin profile config"; Path = $TxAdminConfig }
    )
}

function Get-DiscordBotEnvironmentChecks {
    return @(
        @{ Name = "Discord bot directory"; Path = $BotDir },
        @{ Name = "Discord bot Python"; Path = $BotPython },
        @{ Name = "Discord bot file"; Path = $BotFile }
    )
}

function Get-EnvironmentChecks {
    return @(
        Get-ServerEnvironmentChecks
        Get-DiscordBotEnvironmentChecks
    )
}

function Test-EnvironmentChecks {
    param(
        [Parameter(Mandatory)][array]$Checks,
        [bool]$LogDetails = $true
    )

    $missing = @()
    foreach ($check in $Checks) {
        if (Test-Path -LiteralPath $check.Path) {
            if ($LogDetails) {
                Write-ManagerLine "INFO" "Environment" "OK | $($check.Name) | $($check.Path)"
            }
        }
        else {
            $missing += $check
            if ($LogDetails) {
                Write-ManagerLine "ERROR" "Environment" "Missing | $($check.Name) | $($check.Path)"
            }
        }
    }

    if ($missing.Count -eq 0) {
        return @{
            Ok = $true
            Message = "All required paths exist"
        }
    }

    return @{
        Ok = $false
        Message = "$($missing.Count) required path(s) missing"
    }
}

function Test-Environment {
    param([bool]$LogDetails = $true)

    return Test-EnvironmentChecks -Checks @(Get-EnvironmentChecks) -LogDetails $LogDetails
}
