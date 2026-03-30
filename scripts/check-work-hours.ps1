#Requires -Version 5.1
<#
.SYNOPSIS
    Optional Task Scheduler wrapper: start run.ps1 only during work hours.
    Set "timezone_windows" in config.json (e.g. "Eastern Standard Time"). Python still uses IANA "timezone".
#>
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$RunScript = Join-Path $PSScriptRoot "run.ps1"

$configPath = if ($env:VPN_DAEMON_CONFIG) { $env:VPN_DAEMON_CONFIG } else { Join-Path $RepoRoot "config\config.json" }
if (-not (Test-Path $configPath)) {
    & $RunScript
    exit 0
}

$j = Get-Content -Raw $configPath | ConvertFrom-Json
$winTzId = $j.timezone_windows
if (-not $winTzId) {
    Write-Warning "timezone_windows not set in config; starting daemon anyway."
    & $RunScript
    exit 0
}

try {
    $tz = [System.TimeZoneInfo]::FindSystemTimeZoneById($winTzId)
} catch {
    Write-Warning "Invalid timezone_windows '$winTzId'; not starting."
    exit 0
}

$nowLocal = [System.TimeZoneInfo]::ConvertTimeFromUtc([DateTime]::UtcNow, $tz)
$wd = $nowLocal.DayOfWeek.ToString().Substring(0, 3).ToLowerInvariant()
$days = @()
foreach ($d in $j.work_days) {
    $s = $d.ToString().ToLowerInvariant()
    if ($s.Length -ge 3) { $days += $s.Substring(0, 3) }
}
if ($days.Count -eq 0 -or $days -notcontains $wd) {
    exit 0
}

function Parse-HhMm([string]$s) {
    $p = $s.Split(":")
    return [TimeSpan]::FromHours([int]$p[0]) + [TimeSpan]::FromMinutes([int]$p[1])
}

$start = Parse-HhMm $j.work_hours_start
$end = Parse-HhMm $j.work_hours_end
$t = $nowLocal.TimeOfDay

$inside = $false
if ($start -le $end) {
    $inside = ($t -ge $start -and $t -lt $end)
} else {
    $inside = ($t -ge $start -or $t -lt $end)
}

if (-not $inside) {
    exit 0
}

& $RunScript
