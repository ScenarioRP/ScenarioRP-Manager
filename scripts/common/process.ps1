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
