# Task Scheduler

## Default: tray at every logon (Option A)

The scheduled task runs [`scripts/run.ps1`](../scripts/run.ps1), which starts the daemon and tray even outside work hours. Outside work hours the daemon stays idle (no auto-reconnect) unless you enabled `reconnect_outside_hours`.

Register (from the repo):

```powershell
.\scripts\register-logon-task.ps1
```

The task is named `VpnDaemonLogon`. Remove it with:

```powershell
Unregister-ScheduledTask -TaskName 'VpnDaemonLogon' -Confirm:$false
```

If registration fails, try running PowerShell as administrator, or create the task manually in `taskschd.msc` pointing to:

```text
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\path\to\vpn-daemon\scripts\run.ps1"
```

## Optional: start only during work hours (Option B)

1. Set `timezone_windows` in `config.json` to a Windows timezone ID (see [configuration.md](configuration.md)).
2. Point the scheduled task at [`scripts/check-work-hours.ps1`](../scripts/check-work-hours.ps1) instead of `run.ps1`.

If `timezone_windows` is missing, `check-work-hours.ps1` warns and starts the daemon anyway (same as Option A).

## Environment

`run.ps1` sets `VPN_DAEMON_CONFIG` to `config\config.json` under the repo when that file exists. Override in the task’s environment if you keep config elsewhere.
