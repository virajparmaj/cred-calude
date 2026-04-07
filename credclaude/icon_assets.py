"""Helpers for locating menu bar and app icon assets."""

from __future__ import annotations

from pathlib import Path

try:
    from AppKit import NSBitmapImageRep, NSBundle, NSImage
    from Foundation import NSSize
except ImportError:  # pragma: no cover - AppKit is only available on macOS.
    NSBitmapImageRep = None
    NSBundle = None
    NSImage = None
    NSSize = None


_REPO_ROOT = Path(__file__).resolve().parent.parent
_REPO_MENU_BAR_ICON = _REPO_ROOT / "assets/credclaude_menubar.png"
_REPO_MENU_BAR_ICON_2X = _REPO_ROOT / "assets/credclaude_menubar@2x.png"
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


def load_status_icon() -> "NSImage | None":
    """Return an NSImage with 1x and 2x reps for the menu bar status icon.

    On Retina displays macOS will automatically select the 44-px rep; on
    non-Retina it uses the 22-px rep.  Falls back to a system symbol when
    the asset files are missing.
    """
    if NSImage is None or NSBitmapImageRep is None or NSSize is None:
        return None  # pragma: no cover - not on macOS

    path_1x = _REPO_MENU_BAR_ICON
    path_2x = _REPO_MENU_BAR_ICON_2X

    if not path_1x.exists() or not path_2x.exists():
        return NSImage.imageNamed_("NSStatusAvailable")

    data_1x = path_1x.read_bytes()
    data_2x = path_2x.read_bytes()

    rep_1x = NSBitmapImageRep.imageRepWithData_(data_1x)
    rep_2x = NSBitmapImageRep.imageRepWithData_(data_2x)

    if rep_1x is None or rep_2x is None:
        return NSImage.imageNamed_("NSStatusAvailable")

    target_size = NSSize(22, 22)
    rep_1x.setSize_(target_size)
    rep_2x.setSize_(target_size)

    image = NSImage.alloc().initWithSize_(target_size)
    image.setTemplate_(False)
    image.addRepresentation_(rep_2x)
    image.addRepresentation_(rep_1x)
    return image


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
