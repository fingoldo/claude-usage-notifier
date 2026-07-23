# Claude Usage Notifier

[![CI](https://github.com/fingoldo/claude-usage-notifier/actions/workflows/ci.yml/badge.svg)](https://github.com/fingoldo/claude-usage-notifier/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

Watches your claude.ai **weekly** usage limit (`seven_day.utilization` /
`seven_day.resets_at`) and alerts you the moment it resets early, i.e. before
the week is actually over. Fires on four channels at once: Telegram, email, an
OS notification, and a system sound, plus a log entry.

## Why this scrapes a browser instead of calling an API

`https://claude.ai/api/organizations/{org}/usage` is an internal endpoint of
the claude.ai **web session** (cookie-authenticated), not part of the public
Anthropic API. An Anthropic console API key has an entirely different
(token-based) billing model and no concept of the Pro/Max "5-hour" / "weekly"
limits at all — those only exist on the claude.ai subscription side. So this
tool drives a real, persistent Chrome profile instead.

Two separate bot defenses had to be worked around along the way:

- **Cloudflare's managed JS challenge** on the usage endpoint detects genuine
  headless rendering (even on the real Chrome channel) and loops forever. The
  fix: launch **headed**, but with the window positioned off-screen
  (`--window-position=-32000,-32000`) — same rendering pipeline as a normal
  tab, so the challenge clears, and nothing is ever visible to the user.
- **Google's OAuth login** ("Sign in with Google") is far more aggressive and
  blocks automation-driven browsers outright, no matter what stealth flags are
  passed. So the one-time login step launches a **plain, non-automated Chrome
  subprocess** (no CDP, no Playwright) against the same profile directory —
  Playwright only takes over afterward, headless-but-offscreen, to read the
  already-authenticated session.

## Install

```bash
pip install -r requirements.txt
python -m playwright install chrome
```

## One-time login

```bash
python fetch_usage.py --login
```

A normal Chrome window opens — log in to claude.ai as usual (Google login
included), close that window completely, then press Enter in the console.
The session is saved under `browser_profile/` and reused headlessly from then on.

## Usage

```bash
python fetch_usage.py          # print the current raw usage JSON, no comparison
python monitor.py               # one check: compare against the last saved snapshot, alert if needed
python monitor.py --loop         # keep running, checking every CHECK_INTERVAL_MINUTES
python monitor.py --test-alert   # fire a fake alert through every channel, to verify delivery
```

### Alert condition

If `seven_day.utilization` drops by more than `DROP_THRESHOLD` percentage
points compared to the last saved snapshot, **and** `resets_at` did *not*
advance to a new future date (i.e. it stayed the same or moved backwards),
that's a mid-week reset anomaly — fire the alert on every channel.

Sitting at 100% for hours near the end of the week (right up to `resets_at`)
is expected, not a bug — the limit simply hasn't rolled over yet.

### If the check itself fails

Every run's outcome is always logged — including under a one-shot Task
Scheduler invocation, where `pythonw.exe` swallows stdout/stderr and an
unhandled exception would otherwise vanish silently. After
`FAILURE_ALERT_THRESHOLD` consecutive failed checks (default 3), an alert
fires on every channel saying monitoring itself is down (most commonly
because the browser session expired — re-run `fetch_usage.py --login`), and
repeats every `FAILURE_ALERT_REPEAT_EVERY` checks (default 18) while it stays
broken. `fetch_usage()` also retries a failed attempt a couple of times on
its own first, to ride out transient issues like a locked desktop session.

Two further mitigations against a locked/sleeping Windows session specifically:

- Chrome launches with `--disable-gpu` (software rendering) — Windows can tear
  down a process's GPU device context on screen lock or display power-off,
  which otherwise surfaces as an unpredictable render/launch failure.
- The Task Scheduler task has `WakeToRun` enabled, so it fires even if the
  machine was asleep, rather than silently missing the trigger entirely.

### Scheduling

Instead of `--loop`, you can register a periodic Windows Task Scheduler job,
e.g. every 10 minutes:

```powershell
$action = New-ScheduledTaskAction -Execute "pythonw.exe" -Argument "monitor.py" -WorkingDirectory "<repo path>"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 10) -RepetitionDuration (New-TimeSpan -Days 3650)
Register-ScheduledTask -TaskName "ClaudeUsageMonitor" -Action $action -Trigger $trigger
```

Or import the included [`ClaudeUsageMonitor.xml`](ClaudeUsageMonitor.xml) directly
(Task Scheduler → Action → Import Task...). It hardcodes this machine's own
`pythonw.exe` and repo path — edit `<Exec><Command>`/`<WorkingDirectory>` first
if importing on a different machine.

## Configuration

Copy [`.env.example`](.env.example) to `.env` and fill in your own values.
All settings live in `.env` (never committed — see `.gitignore`):

| Variable | Purpose |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your chat id (resolve via the bot's `getUpdates` after you `/start` it) |
| `CLAUDE_ORG_ID` | Your claude.ai organization UUID |
| `SMTP_HOST` / `SMTP_PORT` / `EMAIL_FROM` / `EMAIL_TO` / `EMAIL_USER` | SMTP settings for the email alert |
| `SMTP_SPECIAL_PASS` | App-specific SMTP password (not your regular account password) |
| `CHECK_INTERVAL_MINUTES` | Interval for `--loop` mode |
| `DROP_THRESHOLD` | Percentage-point drop that counts as suspicious |

## Files

- `.env` — tokens, chat id, SMTP credentials, org id (gitignored)
- `state.json` — last saved `seven_day` snapshot, created automatically (gitignored)
- `monitor.log` — every check + alert (gitignored)
- `browser_profile/` — the persisted Chrome session (gitignored, contains cookies)

## If the session expires

`monitor.py` will report a 401/403 or a redirect to the login page — just log
in again:

```bash
python fetch_usage.py --login
```

## License

MIT — see [LICENSE](LICENSE).
