$ErrorActionPreference = "Stop"

$ManagerDir = Split-Path -Parent $PSScriptRoot
$ProjectRoot = Split-Path -Parent $ManagerDir
$ConfigPath = Join-Path $ManagerDir "config.json"
$StateDir = Join-Path $ManagerDir "state"

if (-not (Test-Path $ConfigPath)) {
    throw "Missing config.json: $ConfigPath"
}

$Config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json

function Resolve-ProjectPath {
    param([Parameter(Mandatory)][string]$Path)

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }

    return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path))
}

$FxServerExe = Resolve-ProjectPath $Config.fxserver_exe
$TxDataDir = Resolve-ProjectPath $Config.txdata_dir
$ServerCfg = Resolve-ProjectPath $Config.server_cfg
$BotDir = Resolve-ProjectPath $Config.discord_bot_dir
$BotPython = Resolve-ProjectPath $Config.discord_bot_python
$BotFile = Resolve-ProjectPath $Config.discord_bot_file
$BotStateFile = Join-Path $BotDir "bot_state.json"
$FxServerDir = Split-Path -Parent $FxServerExe
$TxDataRoot = Split-Path -Parent $TxDataDir
$TxAdminProfile = [string]$Config.txadmin_profile
if ([string]::IsNullOrWhiteSpace($TxAdminProfile)) {
    $TxAdminProfile = "default"
}
$TxAdminProfileDir = Join-Path $TxDataRoot $TxAdminProfile
$TxAdminConfig = Join-Path $TxAdminProfileDir "config.json"
$TxAdminUrl = [string]$Config.txadmin_url
$TxAdminUri = [Uri]$TxAdminUrl
$TxAdminHost = if ($TxAdminUri.Host) { $TxAdminUri.Host } else { "127.0.0.1" }
$TxAdminPort = if ($TxAdminUri.Port -gt 0) { $TxAdminUri.Port } else { 80 }
$FxPidFile = Join-Path $StateDir "fxserver.pid"
$BotPidFile = Join-Path $StateDir "discord-bot.pid"
$DatabaseServiceNames = @("MariaDB", "MariaDB11", "MariaDB11.4", "MySQL", "MySQL80")

function Write-ManagerLine {
    param(
        [Parameter(Mandatory)][string]$Level,
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Message
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "$timestamp | $Level | $Source | $Message"
}

function Write-StatusLine {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$State,
        [Parameter(Mandatory)][string]$Message
    )

    Write-Output "STATUS|$Name|$State|$Message"
}

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

function Get-PidFromFile {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    $raw = (Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue | Select-Object -First 1)
    $pidValue = 0
    if ([int]::TryParse($raw, [ref]$pidValue)) {
        return $pidValue
    }

    return $null
}

function Get-ManagedProcess {
    param(
        [Parameter(Mandatory)][int]$ProcessId,
        [Parameter(Mandatory)][string]$ExpectedName,
        [string]$ExpectedPath,
        [string]$CommandContains
    )

    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if (-not $process) {
        return $null
    }

    if ($process.Name -ine $ExpectedName) {
        return $null
    }

    if ($ExpectedPath) {
        $actual = [System.IO.Path]::GetFullPath([string]$process.ExecutablePath)
        $expected = [System.IO.Path]::GetFullPath($ExpectedPath)
        if ($actual -ine $expected) {
            return $null
        }
    }

    if ($CommandContains -and ([string]$process.CommandLine).ToLowerInvariant().Contains($CommandContains.ToLowerInvariant()) -eq $false) {
        return $null
    }

    return $process
}

function Get-ManagedProcessesBySignature {
    param(
        [Parameter(Mandatory)][string]$ExpectedName,
        [string]$ExpectedPath,
        [string]$CommandContains
    )

    $processes = Get-CimInstance Win32_Process -Filter "Name = '$ExpectedName'" -ErrorAction SilentlyContinue
    foreach ($process in $processes) {
        if ($ExpectedPath) {
            $actual = [System.IO.Path]::GetFullPath([string]$process.ExecutablePath)
            $expected = [System.IO.Path]::GetFullPath($ExpectedPath)
            if ($actual -ine $expected) {
                continue
            }
        }

        if ($CommandContains -and ([string]$process.CommandLine).ToLowerInvariant().Contains($CommandContains.ToLowerInvariant()) -eq $false) {
            continue
        }

        $process
    }
}

function Wait-TcpPort {
    param(
        [Parameter(Mandatory)][string]$HostName,
        [Parameter(Mandatory)][int]$Port,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-TcpPort -HostName $HostName -Port $Port) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }

    return $false
}

function Stop-VerifiedProcessTree {
    param(
        [Parameter(Mandatory)][int]$ProcessId,
        [Parameter(Mandatory)][string]$Source,
        [string]$Context = "PID"
    )

    Write-ManagerLine "INFO" $Source "Stopping $Context $ProcessId"
    # Helper processes are detached, so taskkill without /F is tried first and verified below.
    Invoke-TaskKill -Arguments @("/PID", "$ProcessId", "/T")
    Start-Sleep -Milliseconds 700

    if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) {
        Write-ManagerLine "INFO" $Source "$Context $ProcessId exited"
        return $true
    }

    Write-ManagerLine "WARN" $Source "Graceful stop timed out; forcing $Context $ProcessId"
    Invoke-TaskKill -Arguments @("/PID", "$ProcessId", "/T", "/F")
    Start-Sleep -Milliseconds 500

    if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) {
        Write-ManagerLine "INFO" $Source "$Context $ProcessId exited after force"
        return $true
    }

    Write-ManagerLine "ERROR" $Source "$Context $ProcessId is still running"
    return $false
}

function Invoke-TaskKill {
    param([Parameter(Mandatory)][string[]]$Arguments)

    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & taskkill.exe @Arguments 2>&1 | Out-Null
    }
    finally {
        $ErrorActionPreference = $previousErrorAction
    }
}

function Stop-ManagedProcessesBySignature {
    param(
        [Parameter(Mandatory)][string]$ExpectedName,
        [string]$ExpectedPath,
        [string]$CommandContains,
        [Parameter(Mandatory)][string]$Source
    )

    $ok = $true
    $processes = @(Get-ManagedProcessesBySignature -ExpectedName $ExpectedName -ExpectedPath $ExpectedPath -CommandContains $CommandContains)
    foreach ($process in $processes) {
        $stopped = Stop-VerifiedProcessTree -ProcessId ([int]$process.ProcessId) -Source $Source -Context "managed extra PID"
        $ok = $ok -and $stopped
    }

    return $ok
}

function Remove-StalePid {
    param([Parameter(Mandatory)][string]$Path)

    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
        Write-ManagerLine "INFO" "State" "Removed stale PID file: $Path"
    }
}

function Stop-ManagedProcess {
    param(
        [Parameter(Mandatory)][string]$PidFile,
        [Parameter(Mandatory)][string]$ExpectedName,
        [string]$ExpectedPath,
        [string]$CommandContains,
        [Parameter(Mandatory)][string]$Source,
        [string]$Context = "PID"
    )

    $pidValue = Get-PidFromFile $PidFile
    if (-not $pidValue) {
        Write-ManagerLine "INFO" $Source "No PID file found"
        return $true
    }

    $process = Get-ManagedProcess -ProcessId $pidValue -ExpectedName $ExpectedName -ExpectedPath $ExpectedPath -CommandContains $CommandContains
    if (-not $process) {
        Write-ManagerLine "WARN" $Source "PID $pidValue is stale or belongs to another process"
        Remove-StalePid $PidFile
        return $true
    }

    $stopped = Stop-VerifiedProcessTree -ProcessId $pidValue -Source $Source -Context $Context
    if ($stopped) {
        Remove-StalePid $PidFile
    }

    return $stopped
}

function Test-FxServerRunning {
    $fxPid = Get-PidFromFile $FxPidFile
    if ($fxPid) {
        $fx = Get-ManagedProcess -ProcessId $fxPid -ExpectedName "FXServer.exe" -ExpectedPath $FxServerExe
        if ($fx) {
            return $true
        }

        Remove-StalePid $FxPidFile
    }

    $fxProcesses = @(Get-ManagedProcessesBySignature -ExpectedName "FXServer.exe" -ExpectedPath $FxServerExe)
    return $fxProcesses.Count -gt 0
}

function Test-DiscordBotRunning {
    $botPid = Get-PidFromFile $BotPidFile
    if ($botPid) {
        $bot = Get-ManagedProcess -ProcessId $botPid -ExpectedName "python.exe" -ExpectedPath $BotPython -CommandContains $BotFile
        if ($bot) {
            return $true
        }

        Remove-StalePid $BotPidFile
    }

    $botProcesses = @(Get-ManagedProcessesBySignature -ExpectedName "python.exe" -CommandContains $BotFile)
    return $botProcesses.Count -gt 0
}

function Test-TcpPort {
    param(
        [Parameter(Mandatory)][string]$HostName,
        [Parameter(Mandatory)][int]$Port
    )

    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(300)) {
            $client.Close()
            return $false
        }
        $client.EndConnect($async)
        $client.Close()
        return $true
    }
    catch {
        return $false
    }
}

function Get-ListeningPid {
    param([Parameter(Mandatory)][int]$Port)

    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($connection) {
        return [int]$connection.OwningProcess
    }

    return $null
}

function Get-DatabaseEndpoint {
    if (-not (Test-Path -LiteralPath $ServerCfg)) {
        return $null
    }

    $line = Get-Content -LiteralPath $ServerCfg -ErrorAction SilentlyContinue |
        Where-Object { $_ -match 'mysql_connection_string' } |
        Select-Object -First 1
    if (-not $line) {
        return $null
    }

    $match = [regex]::Match($line, '"([^"]+)"')
    if (-not $match.Success) {
        return $null
    }

    try {
        $uri = [Uri]$match.Groups[1].Value
        $port = if ($uri.Port -gt 0) { $uri.Port } else { 3306 }
        return @{
            Host = $uri.Host
            Port = $port
            Source = "mysql_connection_string"
        }
    }
    catch {
        return $null
    }
}

function Get-DatabaseStatus {
    $endpoint = Get-DatabaseEndpoint
    if ($endpoint) {
        if (Test-TcpPort -HostName $endpoint.Host -Port $endpoint.Port) {
            return @{
                State = "Running"
                Message = "Listening on $($endpoint.Host):$($endpoint.Port)"
            }
        }

        return @{
            State = "Stopped"
            Message = "Not listening on $($endpoint.Host):$($endpoint.Port)"
        }
    }

    foreach ($name in $DatabaseServiceNames) {
        $service = Get-Service -Name $name -ErrorAction SilentlyContinue
        if ($service) {
            return @{
                State = [string]$service.Status
                Message = "$name service"
            }
        }
    }

    return @{
        State = "Unknown"
        Message = "No database endpoint or known service found"
    }
}
