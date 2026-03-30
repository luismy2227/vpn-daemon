#Requires -Version 5.1
<#
.SYNOPSIS
    Register a scheduled task to start vpn-daemon at user logon.
    Usually runs without elevation for the current user; if registration fails, try "Run as administrator".
#>
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RunScript = Join-Path $PSScriptRoot "run.ps1"
$TaskName = "VpnDaemonLogon"

if (-not (Test-Path $RunScript)) {
    Write-Error "Missing $RunScript"
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$RunScript`""

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Start vpn-daemon (tray) at logon" `
    -Force | Out-Null

Write-Host "Registered task '$TaskName' for user $env:USERNAME"
Write-Host "To remove: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
