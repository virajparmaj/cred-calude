# 05 Database Schema

## Status: Not Applicable

No database exists. All persistence uses local files and in-memory state.

### Why this is intentionally empty

- [Confirmed from code] No SQLite, PostgreSQL, Supabase, or any database driver is imported or referenced.
- [Confirmed from code] The only external dependency is `rumps>=0.4.0` (`requirements.txt:1`).

### Actual persistence model

| Store | Path | Format | Purpose |
|---|---|---|---|
| Config | `~/.credclaude/config.json` | JSON | User settings: `billing_day`, `daily_budget_usd`, `warn_at_pct`, `notifications_enabled`, `plan_tier` (`credclaude/config.py`) |
| Pricing table | `~/.credclaude/pricing.json` | JSON | Per-model token rates with `updated_at` field; shipped from `default_pricing.json` on first run (`credclaude/config.py`) |
| Usage snapshot | `~/.credclaude/snapshot.json` | JSON | Last successful OAuth API response; persists utilization across app restarts (`credclaude/limit_providers.py`) |
| Reset notification lock | `~/.credclaude/.last_reset_notif` | Plain text (ISO date) | Prevents duplicate billing-reset notifications per day (`credclaude/notifications.py`) |
| Budget warning locks | `~/.credclaude/.warn_{YYYY-MM-DD}` | Plain text (ISO date) | One file per day; auto-cleaned on startup if >7 days old (`credclaude/notifications.py`) |
| PID lock | `~/.credclaude/monitor.pid` | Plain text (PID) | Atomic single-instance guard via `fcntl.flock` (`credclaude/__main__.py`) |
| App log | `~/.credclaude/monitor.log` | Rotating plain text | Written by Python `RotatingFileHandler`; max 1MB × 3 files (`credclaude/config.py`) |
| File cache | In-memory dict | `{filepath: (file_size, CostData)}` | Avoids re-parsing unchanged JSONL files (`credclaude/ingestion.py`) |

### Data source (read-only)

- Claude session logs at `~/.claude/projects/*/*.jsonl` and subagent logs (`credclaude/ingestion.py`).
- These files are written by Claude Code, not by this app. The monitor only reads them.
- OAuth API at `https://api.anthropic.com/api/oauth/usage` (read-only, authenticated via Keychain token).

### When this would change

A database would only become relevant if the project adds historical trend storage, export, or multi-device sync. None of these are currently implemented.
