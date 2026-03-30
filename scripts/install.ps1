#Requires -Version 5.1
<#
.SYNOPSIS
    Install uv (if missing) and sync Python dependencies for vpn-daemon.
#>
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv not found. Install from https://docs.astral.sh/uv/getting-started/installation/"
    Write-Host "Example (PowerShell): irm https://astral.sh/uv/install.ps1 | iex"
    exit 1
}

Write-Host "Running uv sync in $RepoRoot ..."
uv sync

$cfgExample = Join-Path $RepoRoot "config\config.example.json"
$cfgLocal = Join-Path $RepoRoot "config\config.json"
if (-not (Test-Path $cfgLocal)) {
    Write-Host ""
    Write-Host "Next: copy config and profile:"
    Write-Host "  Copy-Item '$cfgExample' '$cfgLocal'"
    Write-Host "  Copy your Pritunl .ovpn into config\profile.ovpn (or set profile path in config.json)"
}

Write-Host ""
Write-Host "Run: .\scripts\run.ps1"
