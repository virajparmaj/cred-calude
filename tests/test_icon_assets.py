"""Tests for runtime icon resolution."""

from __future__ import annotations

from pathlib import Path

from credclaude import icon_assets


def test_menu_bar_icon_path_uses_dedicated_repo_asset():
    icon_path = icon_assets.menu_bar_icon_path()

    assert icon_path == Path("assets/credclaude_menubar.png").resolve()


def test_runtime_icon_path_falls_back_to_tracked_repo_asset(monkeypatch):
    monkeypatch.setattr(icon_assets, "NSBundle", None)

    icon_path = icon_assets.runtime_icon_path()

    assert icon_path == Path("assets/icons/macos/claude_monitor_icon_512.png").resolve()
