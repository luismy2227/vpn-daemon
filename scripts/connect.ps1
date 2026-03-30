#Requires -Version 5.1
<#
.SYNOPSIS
    Print the same OpenVPN command the tray app would use (pin+TOTP from config).

.DESCRIPTION
    Reads config the same way as run.ps1 (VPN_DAEMON_CONFIG or config\config.json),
    runs the Python helper that builds a fresh auth-user-pass file and prints a
    single cmd.exe-style line you can copy. Use -Run to start OpenVPN in this console.

.EXAMPLE
    .\scripts\connect.ps1
.EXAMPLE
    .\scripts\connect.ps1 -Run
#>
param(
    [switch] $Run
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not $env:VPN_DAEMON_CONFIG) {
    $defaultCfg = Join-Path $RepoRoot "config\config.json"
    if (Test-Path $defaultCfg) {
        $env:VPN_DAEMON_CONFIG = (Resolve-Path $defaultCfg).Path
    }
}

$extra = @()
if ($Run) {
    $extra += "--run"
}

uv run python -m vpn_daemon.connect_manual @extra
