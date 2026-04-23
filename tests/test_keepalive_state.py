"""Tests for the persistent keepalive state store."""

from __future__ import annotations

import datetime

import pytest

from credclaude.keepalive_state import KeepaliveState, load_state, save_state


@pytest.fixture
def state_path(tmp_path):
    return tmp_path / "keepalive_state.json"


def test_missing_file_returns_empty_state(state_path):
    assert load_state(state_path) == KeepaliveState()


def test_roundtrip_preserves_fields(state_path):
    fired = datetime.datetime(2026, 4, 22, 9, 0, tzinfo=datetime.timezone.utc)
    scheduled = datetime.datetime(2026, 4, 22, 14, 0, tzinfo=datetime.timezone.utc)
    original = KeepaliveState(
        last_fired_at=fired, last_status="ok", scheduled_fire_at=scheduled
    )

    save_state(state_path, original)
    reloaded = load_state(state_path)

    assert reloaded.last_status == "ok"
    assert reloaded.last_fired_at is not None
    assert reloaded.last_fired_at.isoformat() == fired.isoformat()
    assert reloaded.scheduled_fire_at is not None
    assert reloaded.scheduled_fire_at.isoformat() == scheduled.isoformat()


def test_corrupt_json_returns_empty_state(state_path):
    state_path.write_text("{not json")
    assert load_state(state_path) == KeepaliveState()


def test_non_object_returns_empty_state(state_path):
    state_path.write_text("[1, 2, 3]")
    assert load_state(state_path) == KeepaliveState()


def test_invalid_status_is_dropped(state_path):
    state_path.write_text('{"last_status": "bogus"}')
    assert load_state(state_path).last_status is None


def test_invalid_datetime_is_dropped(state_path):
    state_path.write_text('{"last_fired_at": "not-a-date"}')
    assert load_state(state_path).last_fired_at is None


def test_save_creates_parent_directory(tmp_path):
    nested = tmp_path / "a" / "b" / "state.json"
    save_state(nested, KeepaliveState(last_status="ok"))
    assert nested.exists()


def test_save_is_atomic_no_temp_file_left_behind(state_path, tmp_path):
    save_state(state_path, KeepaliveState(last_status="ok"))
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.startswith(".keepalive_state_")]
    assert leftovers == []


def test_with_fired_rejects_invalid_status():
    state = KeepaliveState()
    with pytest.raises(ValueError):
        state.with_fired(datetime.datetime.now(datetime.timezone.utc), "bogus")


def test_with_scheduled_preserves_other_fields():
    fired = datetime.datetime(2026, 4, 22, 9, 0, tzinfo=datetime.timezone.utc)
    state = KeepaliveState(last_fired_at=fired, last_status="ok")
    new_sched = datetime.datetime(2026, 4, 22, 14, 0, tzinfo=datetime.timezone.utc)

    updated = state.with_scheduled(new_sched)

    assert updated.last_fired_at == fired
    assert updated.last_status == "ok"
    assert updated.scheduled_fire_at == new_sched
