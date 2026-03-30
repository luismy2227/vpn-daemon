#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$configPath = if ($env:VPN_DAEMON_CONFIG) { $env:VPN_DAEMON_CONFIG } else { Join-Path $RepoRoot "config\config.json" }

Write-Host "VPN_DAEMON_CONFIG: $configPath"
if (-not (Test-Path $configPath)) { Write-Host "Config missing."; exit 0 }

$raw = Get-Content -Raw $configPath | ConvertFrom-Json
Write-Host "openvpn_path: $($raw.openvpn_path)"
$cdir = Split-Path -Parent (Resolve-Path $configPath)
$p = $raw.profile
if ($p -and -not [System.IO.Path]::IsPathRooted($p)) { $p = Join-Path $cdir $p }
Write-Host "profile:      $p"
