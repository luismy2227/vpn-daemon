# Build vpn-daemon.exe with PyInstaller
# Usage: .\scripts\build.ps1
#
# Prerequisites: uv (PyInstaller is installed via dependency group "build").

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent

Push-Location $Root
try {
    Write-Host "Syncing build dependencies..." -ForegroundColor Cyan
    uv sync --group build
    Write-Host "Building vpn-daemon.exe..." -ForegroundColor Cyan
    uv run pyinstaller vpn_daemon.spec --clean
    if (-not $?) {
        Write-Host ""
        Write-Host "PyInstaller failed." -ForegroundColor Red
        Write-Host "If you saw PermissionError on dist\vpn-daemon.exe: the file is in use." -ForegroundColor Yellow
        Write-Host "Quit vpn-daemon.exe (tray), close Explorer windows on dist\, then rebuild." -ForegroundColor Yellow
        if (Test-Path variable:global:LASTEXITCODE) { exit $global:LASTEXITCODE }
        exit 1
    }
    $exe = Join-Path $Root "dist\vpn-daemon.exe"
    if (Test-Path $exe) {
        $size = [math]::Round((Get-Item $exe).Length / 1MB, 1)
        Write-Host "Done: $exe  ($size MB)" -ForegroundColor Green
    } else {
        Write-Error "Build failed: dist\vpn-daemon.exe not found."
    }
} finally {
    Pop-Location
}
