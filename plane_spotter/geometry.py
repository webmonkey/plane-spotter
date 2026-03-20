"""Geometry functions for distance, bearing, and closest-point-of-approach calculations.

All distances are in nautical miles. All angles are in degrees.
"""

from __future__ import annotations

import math

EARTH_RADIUS_NM = 3440.065


def _deg_to_rad(deg: float) -> float:
    return deg * math.pi / 180.0


def _rad_to_deg(rad: float) -> float:
    return rad * 180.0 / math.pi


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in nautical miles between two points."""
    lat1_r, lon1_r = _deg_to_rad(lat1), _deg_to_rad(lon1)
    lat2_r, lon2_r = _deg_to_rad(lat2), _deg_to_rad(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_NM * c


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the initial bearing in degrees from point 1 to point 2."""
    lat1_r, lon1_r = _deg_to_rad(lat1), _deg_to_rad(lon1)
    lat2_r, lon2_r = _deg_to_rad(lat2), _deg_to_rad(lon2)

    dlon = lon2_r - lon1_r

    x = math.sin(dlon) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(
        lat2_r
    ) * math.cos(dlon)

    return _rad_to_deg(math.atan2(x, y)) % 360


def closest_point_of_approach(
    aircraft_lat: float,
    aircraft_lon: float,
    track_deg: float,
    user_lat: float,
    user_lon: float,
) -> float:
    """Return the perpendicular distance (nm) from the user to the aircraft's projected track line.

    Projects a line from the aircraft's position along its track heading and computes the
    minimum distance from the user's position to that line using cross-track distance.
    """
    # Distance from aircraft to user
    d_ac_user = haversine(aircraft_lat, aircraft_lon, user_lat, user_lon)
    if d_ac_user < 0.001:
        return 0.0

    # Bearing from aircraft to user
    bearing_to_user = bearing(aircraft_lat, aircraft_lon, user_lat, user_lon)

    # Angular difference between track and bearing to user
    angle_diff = _deg_to_rad(bearing_to_user - track_deg)

    # Cross-track distance (perpendicular distance from user to track line)
    # Using the spherical cross-track distance formula
    d_ac_user_rad = d_ac_user / EARTH_RADIUS_NM
    cross_track_rad = math.asin(math.sin(d_ac_user_rad) * math.sin(angle_diff))

    return abs(cross_track_rad * EARTH_RADIUS_NM)


def time_to_closest_approach(
    aircraft_lat: float,
    aircraft_lon: float,
    track_deg: float,
    ground_speed_knots: float,
    user_lat: float,
    user_lon: float,
) -> float:
    """Return the estimated seconds until closest approach.

    Calculates the along-track distance from the aircraft to the CPA point,
    then divides by ground speed. Returns negative if the CPA is behind the aircraft.
    """
    if ground_speed_knots <= 0:
        return float("inf")

    d_ac_user = haversine(aircraft_lat, aircraft_lon, user_lat, user_lon)
    if d_ac_user < 0.001:
        return 0.0

    bearing_to_user = bearing(aircraft_lat, aircraft_lon, user_lat, user_lon)
    angle_diff = _deg_to_rad(bearing_to_user - track_deg)

    # Along-track distance to the CPA point
    d_ac_user_rad = d_ac_user / EARTH_RADIUS_NM
    cross_track_rad = math.asin(math.sin(d_ac_user_rad) * math.sin(angle_diff))
    along_track_rad = math.acos(math.cos(d_ac_user_rad) / math.cos(cross_track_rad))
    along_track_nm = along_track_rad * EARTH_RADIUS_NM

    # Positive if CPA is ahead (cos of angle_diff > 0), negative if behind
    if abs(angle_diff) > math.pi / 2:
        along_track_nm = -along_track_nm

    # Convert distance to time: nm / knots = hours, * 3600 = seconds
    return (along_track_nm / ground_speed_knots) * 3600


def is_approaching(
    aircraft_lat: float,
    aircraft_lon: float,
    track_deg: float,
    user_lat: float,
    user_lon: float,
) -> bool:
    """Return True if the aircraft is heading towards the user (not receding).

    Checks whether the angular difference between the aircraft's track
    and the bearing to the user is less than 90 degrees.
    """
    bearing_to_user = bearing(aircraft_lat, aircraft_lon, user_lat, user_lon)
    angle_diff = abs(bearing_to_user - track_deg) % 360
    if angle_diff > 180:
        angle_diff = 360 - angle_diff
    return angle_diff < 90
