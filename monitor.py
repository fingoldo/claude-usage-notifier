"""Checks whether the claude.ai weekly usage limit reset early (before the week ended).

Each run:
  1. Fetches the current `seven_day` usage snapshot (utilization %, resets_at).
  2. Compares it against the last saved snapshot.
  3. If utilization dropped by more than DROP_THRESHOLD points AND resets_at did
     NOT move forward to a new future date (i.e. it stayed the same or went
     backwards), that's a mid-week reset anomaly -> fire an alert on every channel.
  4. Saves the new snapshot as the baseline for next time.

Run once (e.g. from Windows Task Scheduler every few minutes):
    python monitor.py

Run in a self-looping process instead:
    python monitor.py --loop
"""

import argparse
import sys
import time
from datetime import datetime, timezone

import config
import state_store
from fetch_usage import fetch_usage
from notify import fire_alert, fire_info_notification, logger


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _format_timedelta(delta) -> str:
    total_seconds = delta.total_seconds()
    if total_seconds <= 0:
        return "0 часов"
    days, rem = divmod(total_seconds, 86400)
    hours, _ = divmod(rem, 3600)
    parts = []
    if days >= 1:
        parts.append(f"{int(days)} дн.")
    parts.append(f"{int(hours)} ч.")
    return " ".join(parts)


def check_once() -> None:
    usage = fetch_usage()
    seven_day = usage["seven_day"]
    new_utilization = float(seven_day["utilization"])
    new_resets_at = seven_day["resets_at"]

    previous = state_store.load()

    if previous is not None:
        old_utilization = float(previous["utilization"])
        old_resets_at = previous["resets_at"]

        dropped = (old_utilization - new_utilization) > config.DROP_THRESHOLD
        reset_date_advanced = _parse_dt(new_resets_at) > _parse_dt(old_resets_at)

        if dropped and not reset_date_advanced:
            now = datetime.now(timezone.utc)
            remaining = _parse_dt(new_resets_at) - now
            message = (
                f"Лимит использования ИИ-моделей сбросился с {old_utilization}% "
                f"до {new_utilization}% за {_format_timedelta(remaining)} "
                f"до окончания учетной недели!"
            )
            fire_alert("Claude: подозрительный сброс лимита", message)
        elif dropped and reset_date_advanced:
            # A legitimate weekly reset (resets_at moved forward to next week) --
            # worth a quiet heads-up, not the full Telegram/email alert treatment.
            message = f"Лимит использования ИИ-моделей сбросился штатно: {old_utilization}% -> {new_utilization}%, следующий сброс {new_resets_at}."
            fire_info_notification("Claude: штатный сброс лимита", message)
        else:
            logger.info(
                "OK: utilization %s%% -> %s%%, resets_at %s -> %s",
                old_utilization,
                new_utilization,
                old_resets_at,
                new_resets_at,
            )
    else:
        logger.info("First run, no baseline yet. utilization=%s%% resets_at=%s", new_utilization, new_resets_at)

    state_store.save(new_utilization, new_resets_at)


def test_alert() -> None:
    """Fires a fake alert through every channel, to verify delivery end-to-end."""
    fire_alert(
        "Claude: подозрительный сброс лимита (ТЕСТ)",
        "Это тестовое сообщение от claude_notifier: Telegram, email, системное " "уведомление, звук и лог-файл должны были сработать все четыре.",
    )


def run_check() -> None:
    """Runs one check, guaranteeing the outcome is always logged (and alerted on
    repeated failure) even under a one-shot invocation with no surrounding loop -
    e.g. Windows Task Scheduler, whose pythonw.exe wrapper swallows stdout/stderr,
    so an unhandled exception here would otherwise vanish silently and freeze
    state.json at its last good value with zero visibility.
    """
    try:
        check_once()
    except Exception:
        logger.exception("Check failed")
        count = state_store.load_failure_count() + 1
        state_store.save_failure_count(count)
        if count == config.FAILURE_ALERT_THRESHOLD or (
            count > config.FAILURE_ALERT_THRESHOLD and (count - config.FAILURE_ALERT_THRESHOLD) % config.FAILURE_ALERT_REPEAT_EVERY == 0
        ):
            fire_alert(
                "Claude: мониторинг лимита не работает",
                f"claude_notifier не смог получить данные использования {count} проверок подряд "
                f"(~{count * config.CHECK_INTERVAL_MINUTES:.0f} мин). Возможно истекла сессия - "
                "запусти `python fetch_usage.py --login`. Подробности в monitor.log.",
            )
    else:
        if state_store.load_failure_count() > 0:
            logger.info("Recovered after failures")
            state_store.save_failure_count(0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loop", action="store_true", help="Keep running, checking every CHECK_INTERVAL_MINUTES")
    parser.add_argument("--test-alert", action="store_true", help="Fire a fake alert on every channel and exit")
    args = parser.parse_args()

    if args.test_alert:
        test_alert()
        return

    if not args.loop:
        run_check()
        return

    while True:
        run_check()
        time.sleep(config.CHECK_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
