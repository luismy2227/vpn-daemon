#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Install uv: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
}

uv sync

$cfgExample = Join-Path $RepoRoot "config\config.example.json"
$cfgLocal = Join-Path $RepoRoot "config\config.json"
if (-not (Test-Path $cfgLocal)) {
    Write-Host "Copy config and add profile.ovpn:"
    Write-Host "  Copy-Item '$cfgExample' '$cfgLocal'"
}

Write-Host "Optional QR helper: uv sync --extra helper"
Write-Host "Run: .\scripts\run.ps1"
