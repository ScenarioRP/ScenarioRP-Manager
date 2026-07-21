. "$PSScriptRoot\common\bootstrap.ps1"

$result = Test-Environment
if ($result.Ok) {
    Write-StatusLine "Environment" "OK" $result.Message
    exit 0
}

Write-StatusLine "Environment" "Error" $result.Message
if (-not $result.Ok) {
    exit 1
}
