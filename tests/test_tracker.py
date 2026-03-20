from __future__ import annotations

from plane_spotter.models import Aircraft, EventType, TrackingStatus
from plane_spotter.tracker import PlaneTracker


def _make_aircraft(**overrides) -> Aircraft:
    defaults = dict(
        hex="abc123",
        flight="TEST1",
        registration="G-TEST",
        aircraft_type="C172",
        alt_baro=2000,
        alt_geom=2100,
        ground_speed=100.0,
        track=0.0,
        lat=51.4,
        lon=-0.142,
        distance=3.0,
        direction=180.0,
    )
    defaults.update(overrides)
    return Aircraft(**defaults)


class TestPlaneTracker:
    def _make_tracker(self, **kwargs) -> PlaneTracker:
        defaults = dict(user_lat=51.501, user_lon=-0.142)
        defaults.update(kwargs)
        return PlaneTracker(**defaults)

    def test_no_aircraft_no_events(self):
        tracker = self._make_tracker()
        events = tracker.update([])
        assert events == []

    def test_above_altitude_threshold_filtered(self):
        tracker = self._make_tracker(altitude_threshold_ft=3000)
        ac = _make_aircraft(alt_baro=5000)
        events = tracker.update([ac])
        assert len(events) == 0
        assert not tracker.has_approaching()
        assert not tracker.has_nearby()

    def test_new_approaching_aircraft(self):
        tracker = self._make_tracker()
        # Aircraft south of user, heading north, on track to pass close
        ac = _make_aircraft(
            hex="a1",
            lat=51.45,
            lon=-0.142,
            track=0.0,  # heading north
            ground_speed=100.0,
            alt_baro=2000,
        )
        # Need 3 consecutive approaching polls (default confirmation_count)
        tracker.update([ac])
        tracker.update([ac])
        events = tracker.update([ac])
        approaching = [e for e in events if e.event_type == EventType.NEW_APPROACH]
        assert len(approaching) == 1
        assert tracker.has_approaching()

    def test_aircraft_departs(self):
        tracker = self._make_tracker()
        ac = _make_aircraft(
            hex="a1",
            lat=51.45,
            lon=-0.142,
            track=0.0,
            ground_speed=100.0,
            alt_baro=2000,
        )
        # Confirm approach first
        tracker.update([ac])
        tracker.update([ac])
        tracker.update([ac])
        # Aircraft disappears
        events = tracker.update([])
        departed = [e for e in events if e.event_type == EventType.DEPARTED]
        assert len(departed) == 1

    def test_nearby_not_approaching(self):
        tracker = self._make_tracker()
        # Aircraft heading east, perpendicular to user — should be NEARBY not APPROACHING
        ac = _make_aircraft(
            hex="a2",
            lat=51.45,
            lon=-0.142,
            track=90.0,  # heading east
            ground_speed=100.0,
            alt_baro=2000,
        )
        events = tracker.update([ac])
        approach_events = [e for e in events if e.event_type == EventType.NEW_APPROACH]
        assert len(approach_events) == 0
        assert tracker.has_nearby()
        assert not tracker.has_approaching()

    def test_aircraft_without_track_not_tracked(self):
        tracker = self._make_tracker()
        ac = _make_aircraft(hex="a3", track=None, ground_speed=None, alt_baro=2000)
        events = tracker.update([ac])
        assert "a3" not in tracker.tracked

    def test_none_altitude_filtered(self):
        tracker = self._make_tracker(altitude_threshold_ft=3000)
        ac = _make_aircraft(hex="a4", alt_baro=None, lat=51.45, lon=-0.142, track=0.0)
        events = tracker.update([ac])
        # Should be filtered out — no valid altitude
        assert "a4" not in tracker.tracked

    def test_has_approaching_and_min_time(self):
        tracker = self._make_tracker()
        ac = _make_aircraft(
            hex="a1",
            lat=51.45,
            lon=-0.142,
            track=0.0,
            ground_speed=100.0,
            alt_baro=2000,
        )
        # Confirm approach first
        tracker.update([ac])
        tracker.update([ac])
        tracker.update([ac])
        assert tracker.has_approaching()
        min_t = tracker.min_time_to_cpa()
        assert min_t is not None
        assert min_t > 0

    # ---- Confirmation / CANDIDATE tests ----

    def test_single_poll_no_alert(self):
        """A single approaching observation should NOT trigger NEW_APPROACH."""
        tracker = self._make_tracker()
        ac = _make_aircraft(
            hex="a1",
            lat=51.45,
            lon=-0.142,
            track=0.0,
            ground_speed=100.0,
            alt_baro=2000,
        )
        events = tracker.update([ac])
        approach_events = [e for e in events if e.event_type == EventType.NEW_APPROACH]
        assert len(approach_events) == 0
        assert not tracker.has_approaching()
        assert tracker.has_candidate()

    def test_candidate_turns_away_no_alert(self):
        """Aircraft approaching for fewer than N polls then turning away should never alert."""
        tracker = self._make_tracker()
        approaching_ac = _make_aircraft(
            hex="a1",
            lat=51.45,
            lon=-0.142,
            track=0.0,  # heading north (toward user)
            ground_speed=100.0,
            alt_baro=2000,
        )
        # Two approaching observations (still CANDIDATE)
        events1 = tracker.update([approaching_ac])
        events2 = tracker.update([approaching_ac])
        assert not tracker.has_approaching()
        assert tracker.has_candidate()

        # Aircraft turns east — no longer approaching
        turned_ac = _make_aircraft(
            hex="a1",
            lat=51.45,
            lon=-0.142,
            track=90.0,  # heading east
            ground_speed=100.0,
            alt_baro=2000,
        )
        events3 = tracker.update([turned_ac])

        # No approach or passed events — user was never alerted
        all_events = events1 + events2 + events3
        assert all(
            e.event_type not in (EventType.NEW_APPROACH, EventType.PASSED)
            for e in all_events
        )
        assert not tracker.has_approaching()
        assert not tracker.has_candidate()
        assert tracker.has_nearby()

    def test_confirmation_count_exact(self):
        """NEW_APPROACH fires on the exact Nth consecutive approaching observation."""
        tracker = self._make_tracker(confirmation_count=3)
        ac = _make_aircraft(
            hex="a1",
            lat=51.45,
            lon=-0.142,
            track=0.0,
            ground_speed=100.0,
            alt_baro=2000,
        )
        events1 = tracker.update([ac])
        events2 = tracker.update([ac])
        assert all(e.event_type != EventType.NEW_APPROACH for e in events1 + events2)

        events3 = tracker.update([ac])
        approach = [e for e in events3 if e.event_type == EventType.NEW_APPROACH]
        assert len(approach) == 1

    def test_confirmation_count_one_immediate(self):
        """With confirmation_count=1, alert fires immediately like old behavior."""
        tracker = self._make_tracker(confirmation_count=1)
        ac = _make_aircraft(
            hex="a1",
            lat=51.45,
            lon=-0.142,
            track=0.0,
            ground_speed=100.0,
            alt_baro=2000,
        )
        events = tracker.update([ac])
        approach = [e for e in events if e.event_type == EventType.NEW_APPROACH]
        assert len(approach) == 1
        assert tracker.has_approaching()

    def test_candidate_counter_resets_on_turn_away(self):
        """If an aircraft turns away mid-candidate, the counter resets."""
        tracker = self._make_tracker(confirmation_count=3)
        approaching_ac = _make_aircraft(
            hex="a1",
            lat=51.45,
            lon=-0.142,
            track=0.0,
            ground_speed=100.0,
            alt_baro=2000,
        )
        turned_ac = _make_aircraft(
            hex="a1",
            lat=51.45,
            lon=-0.142,
            track=90.0,
            ground_speed=100.0,
            alt_baro=2000,
        )
        # 2 approaching, then turn, then 2 more approaching — should NOT trigger
        tracker.update([approaching_ac])
        tracker.update([approaching_ac])
        tracker.update([turned_ac])  # counter resets
        tracker.update([approaching_ac])
        events = tracker.update([approaching_ac])
        approach = [e for e in events if e.event_type == EventType.NEW_APPROACH]
        assert len(approach) == 0
        assert tracker.has_candidate()

    def test_passed_after_confirmed_approach(self):
        """After confirmed APPROACHING, turning away emits PASSED."""
        tracker = self._make_tracker(confirmation_count=2)
        approaching_ac = _make_aircraft(
            hex="a1",
            lat=51.45,
            lon=-0.142,
            track=0.0,
            ground_speed=100.0,
            alt_baro=2000,
        )
        tracker.update([approaching_ac])
        tracker.update([approaching_ac])  # confirmed

        turned_ac = _make_aircraft(
            hex="a1",
            lat=51.45,
            lon=-0.142,
            track=90.0,
            ground_speed=100.0,
            alt_baro=2000,
        )
        events = tracker.update([turned_ac])
        passed = [e for e in events if e.event_type == EventType.PASSED]
        assert len(passed) == 1

    def test_departed_while_candidate_no_event(self):
        """Aircraft disappearing while CANDIDATE should NOT emit DEPARTED."""
        tracker = self._make_tracker()
        ac = _make_aircraft(
            hex="a1",
            lat=51.45,
            lon=-0.142,
            track=0.0,
            ground_speed=100.0,
            alt_baro=2000,
        )
        tracker.update([ac])  # CANDIDATE
        events = tracker.update([])  # disappears
        departed = [e for e in events if e.event_type == EventType.DEPARTED]
        assert len(departed) == 0

    def test_departed_while_approaching_emits_event(self):
        """Aircraft disappearing while confirmed APPROACHING emits DEPARTED."""
        tracker = self._make_tracker(confirmation_count=2)
        ac = _make_aircraft(
            hex="a1",
            lat=51.45,
            lon=-0.142,
            track=0.0,
            ground_speed=100.0,
            alt_baro=2000,
        )
        tracker.update([ac])
        tracker.update([ac])  # confirmed
        events = tracker.update([])  # disappears
        departed = [e for e in events if e.event_type == EventType.DEPARTED]
        assert len(departed) == 1
