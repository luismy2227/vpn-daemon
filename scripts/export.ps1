#Requires -Version 5.1
<#
.SYNOPSIS
    Print resolved paths for debugging (no secrets).
#>
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

$configPath = if ($env:VPN_DAEMON_CONFIG) { $env:VPN_DAEMON_CONFIG } else { Join-Path $RepoRoot "config\config.json" }

Write-Host "VPN_DAEMON_CONFIG: $configPath"
Write-Host "Repo root:         $RepoRoot"

if (-not (Test-Path $configPath)) {
    Write-Host "Config file not found."
    exit 0
}

$raw = Get-Content -Raw -Path $configPath | ConvertFrom-Json
Write-Host "openvpn_path:      $($raw.openvpn_path)"
Write-Host "profile (as set): $($raw.profile)"

$configDir = Split-Path -Parent (Resolve-Path $configPath)
$prof = $raw.profile
if (-not [System.IO.Path]::IsPathRooted($prof)) {
    $prof = Join-Path $configDir $prof
}
Write-Host "profile resolved:  $prof"

$stateDir = Join-Path $env:LOCALAPPDATA "vpn-daemon"
Write-Host "state directory:   $stateDir"

if ($raw.log_directory) {
    Write-Host "log_directory:     $($raw.log_directory)"
}
