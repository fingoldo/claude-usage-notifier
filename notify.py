"""Fires an alert across every channel: Telegram, email, OS notification, sound, log."""

import asyncio
import logging
import platform
import smtplib
import subprocess
from email.mime.text import MIMEText

from telegram import Bot
from telegram.error import TelegramError

import config

logging.basicConfig(
    filename=config.LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("claude_notifier")


def send_telegram(message: str) -> None:
    async def _send():
        bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=config.TELEGRAM_CHAT_ID, text=message)

    try:
        asyncio.run(_send())
    except TelegramError as e:
        logger.error("Telegram send failed: %s", e)


def send_email(subject: str, message: str) -> None:
    msg = MIMEText(message, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_FROM
    msg["To"] = config.EMAIL_TO
    try:
        with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.login(config.EMAIL_USER, config.SMTP_SPECIAL_PASS)
            server.sendmail(config.EMAIL_FROM, [config.EMAIL_TO], msg.as_string())
    except Exception as e:
        logger.error("Email send failed: %s", e)


def send_system_notification(title: str, message: str) -> None:
    try:
        from plyer import notification

        notification.notify(title=title, message=message, app_name="Claude Usage Monitor", timeout=20)
    except Exception as e:
        logger.error("System notification failed: %s", e)


def _play_sound(windows_beep: int, mac_sound: str, linux_sound: str, failure: str) -> None:
    system = platform.system()
    try:
        if system == "Windows":
            import winsound

            winsound.MessageBeep(windows_beep)
        elif system == "Darwin":
            subprocess.run(["afplay", mac_sound], check=False)
        else:
            subprocess.run(["paplay", linux_sound], check=False)
    except Exception as e:
        logger.error("%s: %s", failure, e)


def play_alert_sound() -> None:
    # MB_ICONEXCLAMATION; winsound exists only on Windows, so the value is spelled out here.
    _play_sound(48, "/System/Library/Sounds/Sosumi.aiff", "/usr/share/sounds/freedesktop/stereo/dialog-warning.oga", "Sound alert failed")


def play_info_sound() -> None:
    """Quieter, non-alarming sound for a legitimate (expected) weekly reset."""
    # MB_ICONASTERISK; see play_alert_sound.
    _play_sound(64, "/System/Library/Sounds/Glass.aiff", "/usr/share/sounds/freedesktop/stereo/message.oga", "Sound info failed")


def fire_alert(title: str, message: str) -> None:
    """Full alert for something suspicious: every channel (Telegram, email,
    system notification, sound) plus a log entry."""
    logger.warning(message)
    send_telegram(message)
    send_email(title, message)
    send_system_notification(title, message)
    play_alert_sound()


def fire_info_notification(title: str, message: str) -> None:
    """Lighter notice for an expected event (e.g. the weekly limit resetting
    normally): system notification + a distinct, quieter sound, no
    Telegram/email -- and a log entry, same as fire_alert."""
    logger.info(message)
    send_system_notification(title, message)
    play_info_sound()
