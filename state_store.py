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


def load_failure_count() -> int:
    if not config.FAILURE_FILE.exists():
        return 0
    return json.loads(config.FAILURE_FILE.read_text(encoding="utf-8"))["count"]


def save_failure_count(count: int) -> None:
    if count == 0 and config.FAILURE_FILE.exists():
        config.FAILURE_FILE.unlink()
        return
    config.FAILURE_FILE.write_text(json.dumps({"count": count}), encoding="utf-8")
