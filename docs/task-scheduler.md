# Task Scheduler

```powershell
.\scripts\register-logon-task.ps1
```

Task name: `VpnDaemonLogon`. Remove:

```powershell
Unregister-ScheduledTask -TaskName 'VpnDaemonLogon' -Confirm:$false
```
