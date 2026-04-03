"""Helpers for locating menu bar and app icon assets."""

from __future__ import annotations

from pathlib import Path

try:
    from AppKit import NSBundle
except ImportError:  # pragma: no cover - AppKit is only available on macOS.
    NSBundle = None


_REPO_ROOT = Path(__file__).resolve().parent.parent
_REPO_MENU_BAR_ICON = _REPO_ROOT / "assets/credclaude_menubar.png"
_REPO_ICON_CANDIDATES = (
    _REPO_ROOT / "assets/icons/macos/claude_monitor_icon_512.png",
    _REPO_ROOT / "assets/icons/macos/claude_monitor_icon_1024.png",
)
_BUNDLE_ICON_CANDIDATES = ("AppIconRuntime.png", "AppIcon.icns")


def menu_bar_icon_path() -> Path | None:
    """Return the dedicated status bar icon path."""

    if _REPO_MENU_BAR_ICON.exists():
        return _REPO_MENU_BAR_ICON

    return None


def runtime_icon_path() -> Path | None:
    """Return the best icon path for runtime UI surfaces."""

    if NSBundle is not None:
        bundle = NSBundle.mainBundle()
        if bundle is not None:
            resource_path = bundle.resourcePath()
            if resource_path:
                resources = Path(str(resource_path))
                for name in _BUNDLE_ICON_CANDIDATES:
                    candidate = resources / name
                    if candidate.exists():
                        return candidate

    for candidate in _REPO_ICON_CANDIDATES:
        if candidate.exists():
            return candidate

    return None
