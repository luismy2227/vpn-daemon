from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class RuntimeState:
    """Persisted user intent across restarts."""

    daemon_paused: bool = False
    user_disconnected: bool = False

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, raw: str) -> RuntimeState:
        d = json.loads(raw)
        return cls(
            daemon_paused=bool(d.get("daemon_paused", False)),
            user_disconnected=bool(d.get("user_disconnected", False)),
        )


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> RuntimeState:
        if not self.path.is_file():
            return RuntimeState()
        try:
            return RuntimeState.from_json(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return RuntimeState()

    def save(self, state: RuntimeState) -> None:
        self.path.write_text(state.to_json(), encoding="utf-8")
