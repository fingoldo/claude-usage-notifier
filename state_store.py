"""Persists the last-seen seven_day usage snapshot between runs."""

import json

import config


def load() -> dict | None:
    if not config.STATE_FILE.exists():
        return None
    return json.loads(config.STATE_FILE.read_text(encoding="utf-8"))


def save(utilization: float, resets_at: str) -> None:
    config.STATE_FILE.write_text(
        json.dumps({"utilization": utilization, "resets_at": resets_at}, indent=2),
        encoding="utf-8",
    )
