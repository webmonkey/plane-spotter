from __future__ import annotations

import logging

from .geometry import closest_point_of_approach, is_approaching, time_to_closest_approach
from .models import Aircraft, EventType, TrackingEvent, TrackingStatus

logger = logging.getLogger(__name__)


class TrackedAircraft:
    """Internal state for a tracked aircraft."""

    __slots__ = ("aircraft", "status", "cpa_nm", "time_to_cpa_s")

    def __init__(
        self,
        aircraft: Aircraft,
        status: TrackingStatus,
        cpa_nm: float | None,
        time_to_cpa_s: float | None,
    ) -> None:
        self.aircraft = aircraft
        self.status = status
        self.cpa_nm = cpa_nm
        self.time_to_cpa_s = time_to_cpa_s


class PlaneTracker:
    """Tracks aircraft across polling cycles and generates state-transition events."""

    def __init__(
        self,
        user_lat: float,
        user_lon: float,
        altitude_threshold_ft: int = 3000,
        close_pass_nm: float = 0.5,
    ) -> None:
        self._user_lat = user_lat
        self._user_lon = user_lon
        self._altitude_threshold = altitude_threshold_ft
        self._close_pass_nm = close_pass_nm
        self._tracked: dict[str, TrackedAircraft] = {}

    @property
    def tracked(self) -> dict[str, TrackedAircraft]:
        return self._tracked

    def has_approaching(self) -> bool:
        return any(t.status == TrackingStatus.APPROACHING for t in self._tracked.values())

    def has_nearby(self) -> bool:
        return any(t.status == TrackingStatus.NEARBY for t in self._tracked.values())

    def min_time_to_cpa(self) -> float | None:
        times = [
            t.time_to_cpa_s
            for t in self._tracked.values()
            if t.status == TrackingStatus.APPROACHING and t.time_to_cpa_s is not None
        ]
        return min(times) if times else None

    def update(self, aircraft_list: list[Aircraft]) -> list[TrackingEvent]:
        """Process a new batch of aircraft data and return state-transition events."""
        events: list[TrackingEvent] = []
        seen_hexes: set[str] = set()

        for ac in aircraft_list:
            # Filter by altitude
            if not ac.has_position or ac.alt_baro is None:
                logger.debug("%s skipped: missing position or altitude", ac.callsign)
                continue

            if ac.alt_baro > self._altitude_threshold:
                logger.debug(
                    "%s filtered: alt_baro %d > threshold %d",
                    ac.callsign, ac.alt_baro, self._altitude_threshold,
                )
                continue

            seen_hexes.add(ac.hex)
            status, cpa_nm, time_cpa_s = self._classify(ac)
            if status is None:
                continue
            prev = self._tracked.get(ac.hex)

            if prev is None:
                # New aircraft
                if status == TrackingStatus.APPROACHING:
                    logger.info(
                        "%s NEW_APPROACH — CPA %.2fnm, ETA %.0fs, alt %s ft",
                        ac.callsign, cpa_nm or 0, time_cpa_s or 0, ac.alt_baro,
                    )
                    events.append(TrackingEvent(EventType.NEW_APPROACH, ac, cpa_nm, time_cpa_s))
            else:
                if status == TrackingStatus.APPROACHING:
                    if prev.status == TrackingStatus.APPROACHING:
                        logger.debug(
                            "%s STILL_APPROACHING — CPA %.2fnm, ETA %.0fs",
                            ac.callsign, cpa_nm or 0, time_cpa_s or 0,
                        )
                        events.append(TrackingEvent(EventType.STILL_APPROACHING, ac, cpa_nm, time_cpa_s))
                    else:
                        logger.info(
                            "%s NEW_APPROACH (was %s) — CPA %.2fnm, ETA %.0fs, alt %s ft",
                            ac.callsign, prev.status.name, cpa_nm or 0, time_cpa_s or 0, ac.alt_baro,
                        )
                        events.append(TrackingEvent(EventType.NEW_APPROACH, ac, cpa_nm, time_cpa_s))
                elif prev.status == TrackingStatus.APPROACHING:
                    logger.info("%s PASSED — no longer on approaching track", ac.callsign)
                    events.append(TrackingEvent(EventType.PASSED, ac, cpa_nm, time_cpa_s))

            self._tracked[ac.hex] = TrackedAircraft(ac, status, cpa_nm, time_cpa_s)

        # Handle departed aircraft
        departed = set(self._tracked.keys()) - seen_hexes
        for hex_code in departed:
            prev = self._tracked.pop(hex_code)
            if prev.status == TrackingStatus.APPROACHING:
                logger.info("%s DEPARTED while approaching", prev.aircraft.callsign)
                events.append(TrackingEvent(EventType.DEPARTED, prev.aircraft))
            else:
                logger.debug("%s departed (was %s)", prev.aircraft.callsign, prev.status.name)

        return events

    def _classify(self, ac: Aircraft) -> tuple[TrackingStatus | None, float | None, float | None]:
        """Classify an aircraft's status relative to the user."""
        if not ac.has_track or ac.lat is None or ac.lon is None:
            logger.debug("%s has missing track data, skipping", ac.callsign)
            return None, None, None

        assert ac.track is not None
        assert ac.ground_speed is not None

        cpa_nm = closest_point_of_approach(ac.lat, ac.lon, ac.track, self._user_lat, self._user_lon)
        approaching = is_approaching(ac.lat, ac.lon, ac.track, self._user_lat, self._user_lon)

        time_cpa_s: float | None = None
        if approaching and cpa_nm < self._close_pass_nm:
            time_cpa_s = time_to_closest_approach(
                ac.lat, ac.lon, ac.track, ac.ground_speed, self._user_lat, self._user_lon,
            )

        logger.debug(
            "%s — CPA %.3fnm, approaching=%s, time_to_cpa=%s",
            ac.callsign, cpa_nm, approaching,
            f"{time_cpa_s:.0f}s" if time_cpa_s is not None else "N/A",
        )

        if cpa_nm < self._close_pass_nm and approaching:
            return TrackingStatus.APPROACHING, cpa_nm, time_cpa_s

        return TrackingStatus.NEARBY, cpa_nm, time_cpa_s
