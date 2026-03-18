from __future__ import annotations

import math

from plane_spotter.geometry import (
    bearing,
    closest_point_of_approach,
    haversine,
    is_approaching,
    time_to_closest_approach,
)


class TestHaversine:
    def test_same_point(self):
        assert haversine(51.501, -0.142, 51.501, -0.142) == 0.0

    def test_known_distance(self):
        # London (51.5074, -0.1278) to Paris (48.8566, 2.3522) ≈ 185-187 nm
        d = haversine(51.5074, -0.1278, 48.8566, 2.3522)
        assert 184 < d < 187

    def test_short_distance(self):
        # ~1 nm apart at the equator (1 minute of latitude ≈ 1 nm)
        d = haversine(0.0, 0.0, 1 / 60, 0.0)
        assert abs(d - 1.0) < 0.01

    def test_symmetry(self):
        d1 = haversine(51.501, -0.142, 51.5, 0.0)
        d2 = haversine(51.5, 0.0, 51.501, -0.142)
        assert abs(d1 - d2) < 1e-10


class TestBearing:
    def test_due_north(self):
        b = bearing(51.0, 0.0, 52.0, 0.0)
        assert abs(b - 0.0) < 0.1

    def test_due_east(self):
        b = bearing(0.0, 0.0, 0.0, 1.0)
        assert abs(b - 90.0) < 0.1

    def test_due_south(self):
        b = bearing(52.0, 0.0, 51.0, 0.0)
        assert abs(b - 180.0) < 0.1

    def test_due_west(self):
        b = bearing(0.0, 1.0, 0.0, 0.0)
        assert abs(b - 270.0) < 0.1


class TestClosestPointOfApproach:
    def test_heading_directly_at_user(self):
        # Aircraft south of user, heading due north → CPA ≈ 0
        cpa = closest_point_of_approach(51.0, 0.0, 0.0, 52.0, 0.0)
        assert cpa < 0.1

    def test_heading_perpendicular(self):
        # Aircraft south of user, heading due east → CPA ≈ distance to user
        d = haversine(51.0, 0.0, 52.0, 0.0)
        cpa = closest_point_of_approach(51.0, 0.0, 90.0, 52.0, 0.0)
        assert abs(cpa - d) < 0.5

    def test_user_at_aircraft_position(self):
        cpa = closest_point_of_approach(51.501, -0.142, 45.0, 51.501, -0.142)
        assert cpa == 0.0

    def test_close_pass(self):
        # Aircraft heading roughly past user at ~0.3nm offset
        # Aircraft south of user, heading north (0°), user slightly offset east
        cpa = closest_point_of_approach(51.47, -0.142, 0.0, 51.501, -0.137)
        assert cpa < 0.5  # Should be a close pass


class TestTimeToCPA:
    def test_heading_at_user(self):
        # Aircraft 10nm south, heading north at 120kts
        t = time_to_closest_approach(50.0, 0.0, 0.0, 120.0, 50.0 + 10 / 60, 0.0)
        # ~10nm at 120kts = 5 min = 300s, but distance calc may differ slightly
        assert 250 < t < 350

    def test_zero_speed(self):
        t = time_to_closest_approach(51.0, 0.0, 0.0, 0.0, 52.0, 0.0)
        assert t == float("inf")

    def test_already_at_user(self):
        t = time_to_closest_approach(51.501, -0.142, 0.0, 100.0, 51.501, -0.142)
        assert t == 0.0

    def test_heading_away_gives_negative(self):
        # Aircraft north of user, heading north (away)
        t = time_to_closest_approach(52.0, 0.0, 0.0, 120.0, 51.0, 0.0)
        assert t < 0


class TestIsApproaching:
    def test_heading_towards(self):
        # Aircraft south, heading north towards user
        assert is_approaching(51.0, 0.0, 0.0, 52.0, 0.0) is True

    def test_heading_away(self):
        # Aircraft south, heading south (away from user who is north)
        assert is_approaching(51.0, 0.0, 180.0, 52.0, 0.0) is False

    def test_heading_perpendicular(self):
        # Aircraft south, heading east (90° off)
        assert is_approaching(51.0, 0.0, 90.0, 52.0, 0.0) is False

    def test_heading_slightly_towards(self):
        # Aircraft south, heading NNE (bearing to user ≈ 0°, track ≈ 30° → diff 30° < 90°)
        assert is_approaching(51.0, 0.0, 30.0, 52.0, 0.0) is True
