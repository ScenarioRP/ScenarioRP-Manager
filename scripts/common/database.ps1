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
