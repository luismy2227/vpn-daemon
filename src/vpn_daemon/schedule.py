from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from vpn_daemon.config import Config


def _parse_hhmm(s: str) -> time:
    parts = s.strip().split(":")
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    return time(h, m)


def within_work_hours(config: Config, now: datetime | None = None) -> bool:
    """True if `now` (or current time in config timezone) is inside work_days and work_hours."""
    tz = ZoneInfo(config.timezone)
    if now is None:
        now = datetime.now(tz)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    else:
        now = now.astimezone(tz)

    if now.weekday() not in config.work_weekdays:
        return False

    start = _parse_hhmm(config.work_hours_start)
    end = _parse_hhmm(config.work_hours_end)
    current = now.time()

    if start <= end:
        return start <= current < end
    # spans midnight
    return current >= start or current < end


def should_auto_reconnect(config: Config, now: datetime | None = None) -> bool:
    if config.reconnect_outside_hours:
        return True
    return within_work_hours(config, now)
