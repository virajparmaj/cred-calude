"""Tests for post-reset keepalive scheduling."""

from __future__ import annotations

import datetime
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from credclaude import keepalive as keepalive_mod
from credclaude.keepalive import KeepaliveScheduler
from credclaude.keepalive_state import KeepaliveState, load_state, save_state


class _FrozenDateTime(datetime.datetime):
    current: datetime.datetime = datetime.datetime(2026, 4, 6, 12, 0, tzinfo=datetime.timezone.utc)

    @classmethod
    def now(cls, tz=None):
        if tz is not None:
            return cls.current.astimezone(tz)
        return cls.current


class _DummyTimer:
    def __init__(self, interval, function, args=None, kwargs=None):
        self.interval = interval
        self.function = function
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.daemon = False
        self.started = False
        self.cancelled = False

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True


class _SyncThread:
    """threading.Thread stand-in that runs the target synchronously on start()."""

    def __init__(self, target=None, args=None, kwargs=None, daemon=None):
        self._target = target
        self._args = args or ()
        self._kwargs = kwargs or {}
        self.daemon = daemon

    def start(self):
        if self._target is not None:
            self._target(*self._args, **self._kwargs)


@pytest.fixture
def frozen_now(monkeypatch):
    monkeypatch.setattr(keepalive_mod.datetime, "datetime", _FrozenDateTime)
    return _FrozenDateTime.current


@pytest.fixture
def timer_factory(monkeypatch):
    created: list[_DummyTimer] = []

    def _make_timer(interval, function, args=None, kwargs=None):
        timer = _DummyTimer(interval, function, args=args, kwargs=kwargs)
        created.append(timer)
        return timer

    monkeypatch.setattr(keepalive_mod.threading, "Timer", _make_timer)
    return created


@pytest.fixture
def sync_threads(monkeypatch):
    monkeypatch.setattr(keepalive_mod.threading, "Thread", _SyncThread)


@pytest.fixture
def state_path(tmp_path):
    return tmp_path / "keepalive_state.json"


class TestKeepaliveSchedulerSchedule:
    def test_future_resets_at_starts_timer(self, frozen_now, timer_factory):
        scheduler = KeepaliveScheduler()
        resets_at = frozen_now + datetime.timedelta(minutes=5)

        started = scheduler.schedule(resets_at)

        assert started is True
        assert len(timer_factory) == 1
        assert timer_factory[0].interval == pytest.approx(310.0)
        assert timer_factory[0].started is True
        assert timer_factory[0].daemon is True

    def test_past_resets_at_does_not_start_timer(self, frozen_now, timer_factory):
        scheduler = KeepaliveScheduler()
        resets_at = frozen_now - datetime.timedelta(seconds=1)

        started = scheduler.schedule(resets_at)

        assert started is False
        assert timer_factory == []

    def test_none_does_not_start_timer(self, timer_factory):
        scheduler = KeepaliveScheduler()

        started = scheduler.schedule(None)

        assert started is False
        assert timer_factory == []

    def test_reschedule_cancels_previous_timer(self, frozen_now, timer_factory):
        scheduler = KeepaliveScheduler()

        scheduler.schedule(frozen_now + datetime.timedelta(minutes=5))
        first_timer = timer_factory[0]

        scheduler.schedule(frozen_now + datetime.timedelta(minutes=10))

        assert len(timer_factory) == 2
        assert first_timer.cancelled is True
        assert timer_factory[1].started is True

    def test_cancel_cancels_pending_timer(self, frozen_now, timer_factory):
        scheduler = KeepaliveScheduler()
        scheduler.schedule(frozen_now + datetime.timedelta(minutes=5))

        scheduler.cancel()

        assert timer_factory[0].cancelled is True

    def test_schedule_persists_fire_at(self, frozen_now, timer_factory, state_path):
        scheduler = KeepaliveScheduler(state_path=state_path)
        resets_at = frozen_now + datetime.timedelta(minutes=5)

        scheduler.schedule(resets_at)

        state = load_state(state_path)
        expected_fire_at = resets_at + datetime.timedelta(seconds=10)
        assert state.scheduled_fire_at is not None
        assert state.scheduled_fire_at.isoformat() == expected_fire_at.astimezone().isoformat()

    def test_cancel_clears_persisted_schedule(self, frozen_now, timer_factory, state_path):
        scheduler = KeepaliveScheduler(state_path=state_path)
        scheduler.schedule(frozen_now + datetime.timedelta(minutes=5))
        assert load_state(state_path).scheduled_fire_at is not None

        scheduler.cancel()

        assert load_state(state_path).scheduled_fire_at is None


class TestKeepaliveSchedulerFirePing:
    def test_success(self):
        scheduler = KeepaliveScheduler()
        mock_result = MagicMock(returncode=0, stderr="", stdout="pong")

        with patch("shutil.which", return_value="/usr/local/bin/claude"), patch(
            "subprocess.run", return_value=mock_result
        ) as run_mock:
            assert scheduler._fire_ping() is True

        args, kwargs = run_mock.call_args
        assert args[0] == ["/usr/local/bin/claude", "-p", "ping"]
        assert kwargs["timeout"] == 30

    def test_failure(self):
        scheduler = KeepaliveScheduler()
        mock_result = MagicMock(returncode=1, stderr="boom", stdout="")

        with patch("shutil.which", return_value="/usr/local/bin/claude"), patch(
            "subprocess.run", return_value=mock_result
        ):
            assert scheduler._fire_ping() is False

    def test_timeout(self):
        scheduler = KeepaliveScheduler()

        with patch("shutil.which", return_value="/usr/local/bin/claude"), patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=30),
        ):
            assert scheduler._fire_ping() is False

    def test_claude_not_found(self):
        scheduler = KeepaliveScheduler()

        with patch("shutil.which", return_value=None), patch("subprocess.run") as run_mock:
            assert scheduler._fire_ping() is False

        run_mock.assert_not_called()

    def test_success_persists_ok_status(self, state_path):
        scheduler = KeepaliveScheduler(state_path=state_path)
        mock_result = MagicMock(returncode=0, stderr="", stdout="pong")

        with patch("shutil.which", return_value="/usr/local/bin/claude"), patch(
            "subprocess.run", return_value=mock_result
        ):
            scheduler._fire_ping()

        state = load_state(state_path)
        assert state.last_status == "ok"
        assert state.last_fired_at is not None

    def test_failure_persists_failed_status(self, state_path):
        scheduler = KeepaliveScheduler(state_path=state_path)
        mock_result = MagicMock(returncode=1, stderr="boom", stdout="")

        with patch("shutil.which", return_value="/usr/local/bin/claude"), patch(
            "subprocess.run", return_value=mock_result
        ):
            scheduler._fire_ping()

        state = load_state(state_path)
        assert state.last_status == "failed"
        assert state.last_fired_at is not None


class TestCatchUpIfNeeded:
    def test_no_scheduled_time_is_noop(self, frozen_now, state_path, sync_threads):
        scheduler = KeepaliveScheduler(state_path=state_path)

        with patch.object(scheduler, "_fire_ping", return_value=True) as fire_mock:
            fired = scheduler.catch_up_if_needed(None)

        assert fired is False
        fire_mock.assert_not_called()

    def test_future_scheduled_time_is_noop(self, frozen_now, state_path, sync_threads):
        scheduler = KeepaliveScheduler(state_path=state_path)
        future = frozen_now + datetime.timedelta(minutes=30)
        save_state(state_path, KeepaliveState(scheduled_fire_at=future))

        with patch.object(scheduler, "_fire_ping", return_value=True) as fire_mock:
            fired = scheduler.catch_up_if_needed(None)

        assert fired is False
        fire_mock.assert_not_called()

    def test_past_scheduled_never_fired_fires(self, frozen_now, state_path, sync_threads):
        scheduler = KeepaliveScheduler(state_path=state_path)
        past = frozen_now - datetime.timedelta(minutes=5)
        save_state(state_path, KeepaliveState(scheduled_fire_at=past))

        with patch.object(scheduler, "_fire_ping", return_value=True) as fire_mock:
            fired = scheduler.catch_up_if_needed(None)

        assert fired is True
        fire_mock.assert_called_once()

    def test_already_fired_after_scheduled_is_noop(
        self, frozen_now, state_path, sync_threads
    ):
        scheduler = KeepaliveScheduler(state_path=state_path)
        past = frozen_now - datetime.timedelta(minutes=5)
        later = frozen_now - datetime.timedelta(minutes=4)
        save_state(
            state_path,
            KeepaliveState(
                scheduled_fire_at=past, last_fired_at=later, last_status="ok"
            ),
        )

        with patch.object(scheduler, "_fire_ping", return_value=True) as fire_mock:
            fired = scheduler.catch_up_if_needed(None)

        assert fired is False
        fire_mock.assert_not_called()

    def test_past_catch_up_window_skips_and_clears_schedule(
        self, frozen_now, state_path, sync_threads
    ):
        scheduler = KeepaliveScheduler(state_path=state_path, catch_up_window_sec=600)
        very_stale = frozen_now - datetime.timedelta(minutes=30)
        save_state(state_path, KeepaliveState(scheduled_fire_at=very_stale))

        with patch.object(scheduler, "_fire_ping", return_value=True) as fire_mock:
            fired = scheduler.catch_up_if_needed(None)

        assert fired is False
        fire_mock.assert_not_called()
        state = load_state(state_path)
        assert state.last_status == "skipped"
        assert state.scheduled_fire_at is None


class TestHandleWake:
    def test_fresh_state_reschedules_only(
        self, frozen_now, timer_factory, state_path, sync_threads
    ):
        scheduler = KeepaliveScheduler(state_path=state_path)
        # No persisted scheduled_fire_at — nothing to catch up.
        resets = frozen_now + datetime.timedelta(hours=4)

        with patch.object(scheduler, "_fire_ping", return_value=True) as fire_mock:
            scheduler.handle_wake(resets)

        fire_mock.assert_not_called()
        assert len(timer_factory) == 1
        assert timer_factory[0].started is True

    def test_stale_state_triggers_catch_up_and_reschedules(
        self, frozen_now, timer_factory, state_path, sync_threads
    ):
        scheduler = KeepaliveScheduler(state_path=state_path)
        past = frozen_now - datetime.timedelta(minutes=5)
        save_state(state_path, KeepaliveState(scheduled_fire_at=past))
        resets = frozen_now + datetime.timedelta(hours=4)

        with patch.object(scheduler, "_fire_ping", return_value=True) as fire_mock:
            scheduler.handle_wake(resets)

        fire_mock.assert_called_once()
        assert len(timer_factory) == 1

    def test_debounces_rapid_duplicate_wakes(
        self, frozen_now, timer_factory, state_path, sync_threads
    ):
        scheduler = KeepaliveScheduler(state_path=state_path)
        resets = frozen_now + datetime.timedelta(hours=4)

        scheduler.handle_wake(resets)
        scheduler.handle_wake(resets)  # Same instant — should be debounced.

        # First wake schedules one timer; second wake is debounced so no new timer.
        assert len(timer_factory) == 1

    def test_none_resets_at_still_runs_catch_up(
        self, frozen_now, timer_factory, state_path, sync_threads
    ):
        scheduler = KeepaliveScheduler(state_path=state_path)
        past = frozen_now - datetime.timedelta(minutes=5)
        save_state(state_path, KeepaliveState(scheduled_fire_at=past))

        with patch.object(scheduler, "_fire_ping", return_value=True) as fire_mock:
            scheduler.handle_wake(None)

        fire_mock.assert_called_once()
        # No reschedule because resets_at was None.
        assert timer_factory == []


class TestStatusSnapshot:
    def test_reflects_persisted_state(self, state_path):
        scheduler = KeepaliveScheduler(state_path=state_path)
        fired = datetime.datetime(2026, 4, 22, 9, 0, tzinfo=datetime.timezone.utc)
        save_state(
            state_path,
            KeepaliveState(last_fired_at=fired, last_status="ok"),
        )

        snap = scheduler.status_snapshot()

        assert snap.last_status == "ok"
        assert snap.last_fired_at is not None

    def test_empty_state_when_no_path(self):
        scheduler = KeepaliveScheduler()
        assert scheduler.status_snapshot() == KeepaliveState()


class TestSystemWake:
    def test_disabled_does_not_invoke_pmset(self, frozen_now, timer_factory):
        scheduler = KeepaliveScheduler()
        # Wake-system is off by default.
        with patch("subprocess.run") as run_mock:
            scheduler.schedule(frozen_now + datetime.timedelta(minutes=30))

        # schedule() must not call pmset when the feature is disabled.
        assert run_mock.called is False or all(
            "pmset" not in " ".join(call.args[0]) for call in run_mock.call_args_list
        )

    def test_enabled_invokes_pmset_schedule_wake(self, frozen_now, timer_factory):
        scheduler = KeepaliveScheduler()
        scheduler.set_wake_system_enabled(True)

        completed = MagicMock(returncode=0, stderr="", stdout="")
        with patch("subprocess.run", return_value=completed) as run_mock:
            scheduler.schedule(frozen_now + datetime.timedelta(minutes=30))

        pmset_calls = [
            call
            for call in run_mock.call_args_list
            if "pmset" in " ".join(call.args[0])
        ]
        assert len(pmset_calls) == 1
        args = pmset_calls[0].args[0]
        assert args[:4] == ["/usr/bin/sudo", "-n", "/usr/bin/pmset", "schedule"]
        assert args[4] == "wake"

    def test_enabled_cancel_invokes_pmset_cancel(self, frozen_now, timer_factory):
        scheduler = KeepaliveScheduler()
        scheduler.set_wake_system_enabled(True)
        completed = MagicMock(returncode=0, stderr="", stdout="")

        with patch("subprocess.run", return_value=completed) as run_mock:
            scheduler.schedule(frozen_now + datetime.timedelta(minutes=30))
            scheduler.cancel()

        cancel_calls = [
            call
            for call in run_mock.call_args_list
            if "cancel" in " ".join(call.args[0])
        ]
        assert len(cancel_calls) == 1
