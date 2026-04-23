"""Time formatting utilities used by UI layers."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from credclaude.keepalive_state import KeepaliveState

MAX_DISPLAY_COUNTDOWN_SEC = 12 * 3600


def fmt_relative(dt: datetime.datetime | None) -> str:
    """Format a future datetime as 'Xh Ym' countdown."""
    if dt is None:
        return "--"
    now = datetime.datetime.now().astimezone()
    if dt.tzinfo is None:
        dt = dt.astimezone()
    delta = dt - now
    total_sec = max(0, int(delta.total_seconds()))
    if total_sec > MAX_DISPLAY_COUNTDOWN_SEC:
        return "--"
    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    if h == 0:
        return f"{m}m"
    return f"{h}h {m}m"


def fmt_datetime(dt: datetime.datetime | None) -> str:
    """Format a datetime as 'Apr 7 at 12:00 AM' for reset date+time display."""
    if dt is None:
        return "--"
    if dt.tzinfo is None:
        dt = dt.astimezone()
    else:
        dt = dt.astimezone()
    return dt.strftime("%b %-d at %-I:%M %p")


def _fmt_ago(dt: datetime.datetime) -> str:
    """Format a past datetime as 'Xh Ym ago' / 'Xm ago' / 'just now'."""
    now = datetime.datetime.now().astimezone()
    if dt.tzinfo is None:
        dt = dt.astimezone()
    total_sec = int((now - dt).total_seconds())
    if total_sec < 45:
        return "just now"
    if total_sec < 3600:
        return f"{total_sec // 60}m ago"
    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    if h >= 24:
        d = h // 24
        return f"{d}d ago"
    return f"{h}h {m}m ago" if m else f"{h}h ago"


def fmt_keepalive_status(snap: "KeepaliveState") -> str:
    """Format keepalive state for the menu-bar dropdown.

    Examples: 'Keepalive: 2h 15m ago ✓', 'Keepalive: 5m ago ✗ failed',
    'Keepalive: armed', 'Keepalive: idle'.
    """
    if snap.last_fired_at is None:
        if snap.scheduled_fire_at is not None:
            return "Keepalive: armed"
        return "Keepalive: idle"
    ago = _fmt_ago(snap.last_fired_at)
    status = snap.last_status or ""
    if status == "ok":
        return f"Keepalive: {ago} ✓"
    if status == "skipped":
        return f"Keepalive: {ago} — skipped"
    return f"Keepalive: {ago} ✗ {status or 'failed'}"
