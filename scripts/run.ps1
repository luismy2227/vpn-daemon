#Requires -Version 5.1
<#
.SYNOPSIS
    Start vpn-daemon from the repo root using uv.
#>
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not $env:VPN_DAEMON_CONFIG) {
    $defaultCfg = Join-Path $RepoRoot "config\config.json"
    if (Test-Path $defaultCfg) {
        $env:VPN_DAEMON_CONFIG = (Resolve-Path $defaultCfg).Path
    }
}

uv run python -m vpn_daemon
