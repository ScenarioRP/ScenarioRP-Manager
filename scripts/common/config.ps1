$ErrorActionPreference = "Stop" # משתנה ברירת מחדל של shell, אומר מה לעשות במיקרה של שגיאה

$CommonDir = $PSScriptRoot
$ScriptsDir = Split-Path -Parent $CommonDir
$ManagerDir = Split-Path -Parent $ScriptsDir
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
