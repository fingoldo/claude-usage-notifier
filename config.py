"""Configuration loaded from .env, shared by every module in this app."""

from pathlib import Path

from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

CLAUDE_ORG_ID = os.environ["CLAUDE_ORG_ID"]
USAGE_URL = f"https://claude.ai/api/organizations/{CLAUDE_ORG_ID}/usage"

SMTP_HOST = os.environ["SMTP_HOST"]
SMTP_PORT = int(os.environ["SMTP_PORT"])
EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO = os.environ["EMAIL_TO"]
EMAIL_USER = os.environ["EMAIL_USER"]
SMTP_SPECIAL_PASS = os.environ["SMTP_SPECIAL_PASS"]

CHECK_INTERVAL_MINUTES = float(os.environ.get("CHECK_INTERVAL_MINUTES", "15"))
DROP_THRESHOLD = float(os.environ.get("DROP_THRESHOLD", "1.0"))

BROWSER_PROFILE_DIR = BASE_DIR / "browser_profile"
STATE_FILE = BASE_DIR / "state.json"
LOG_FILE = BASE_DIR / "monitor.log"
