from __future__ import annotations

from unittest.mock import MagicMock

from plane_spotter.models import TrackingStatus
from plane_spotter.scheduler import PollScheduler
from plane_spotter.tracker import PlaneTracker, TrackedAircraft


def _mock_tracker(
    has_approaching: bool = False,
    has_nearby: bool = False,
    min_time_to_cpa: float | None = None,
) -> PlaneTracker:
    tracker = MagicMock(spec=PlaneTracker)
    tracker.has_approaching.return_value = has_approaching
    tracker.has_nearby.return_value = has_nearby
    tracker.min_time_to_cpa.return_value = min_time_to_cpa
    return tracker


class TestPollScheduler:
    def test_base_interval_no_planes(self):
        scheduler = PollScheduler()
        tracker = _mock_tracker()
        interval = scheduler.get_interval(tracker)
        assert interval == 120.0

    def test_elevated_interval_nearby(self):
        scheduler = PollScheduler()
        tracker = _mock_tracker(has_nearby=True)
        interval = scheduler.get_interval(tracker)
        assert interval == 60.0

    def test_elevated_interval_approaching_no_imminent(self):
        scheduler = PollScheduler()
        tracker = _mock_tracker(has_approaching=True, min_time_to_cpa=300.0)
        interval = scheduler.get_interval(tracker)
        assert interval == 60.0

    def test_high_interval_imminent_cpa(self):
        scheduler = PollScheduler()
        tracker = _mock_tracker(has_approaching=True, min_time_to_cpa=45.0)
        interval = scheduler.get_interval(tracker)
        assert interval == 30.0

    def test_returns_to_base_when_clear(self):
        scheduler = PollScheduler()
        # First: approaching
        high_tracker = _mock_tracker(has_approaching=True, min_time_to_cpa=30.0)
        scheduler.get_interval(high_tracker)
        assert scheduler.current_interval == 30.0

        # Then: clear
        clear_tracker = _mock_tracker()
        scheduler.get_interval(clear_tracker)
        assert scheduler.current_interval == 120.0

    def test_custom_intervals(self):
        scheduler = PollScheduler(
            base_interval=180, elevated_interval=90, high_interval=45
        )
        tracker = _mock_tracker(has_approaching=True, min_time_to_cpa=10.0)
        interval = scheduler.get_interval(tracker)
        assert interval == 45.0
