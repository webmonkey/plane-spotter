from __future__ import annotations

import logging

from .tracker import PlaneTracker

logger = logging.getLogger(__name__)

# Imminent CPA threshold in seconds — switch to high-frequency polling
_IMMINENT_CPA_SECONDS = 120.0


class PollScheduler:
    """Determines the polling interval based on current tracking state.

    Three tiers:
        base_interval     (120s) — no planes of interest
        elevated_interval  (60s) — plane in radius on potential close track
        high_interval      (30s) — plane actively approaching, CPA imminent
    """

    def __init__(
        self,
        base_interval: float = 120.0,
        elevated_interval: float = 60.0,
        high_interval: float = 30.0,
    ) -> None:
        self._base = base_interval
        self._elevated = elevated_interval
        self._high = high_interval
        self._current: float = base_interval

    @property
    def current_interval(self) -> float:
        return self._current

    def get_interval(self, tracker: PlaneTracker) -> float:
        """Return the appropriate polling interval based on tracker state."""
        previous = self._current

        if tracker.has_approaching():
            min_time = tracker.min_time_to_cpa()
            if min_time is not None and min_time < _IMMINENT_CPA_SECONDS:
                self._current = self._high
                reason = f"imminent CPA in {min_time:.0f}s"
            else:
                self._current = self._elevated
                reason = "aircraft on approaching track"
        elif tracker.has_nearby():
            self._current = self._elevated
            reason = "low-altitude aircraft nearby"
        else:
            self._current = self._base
            reason = "no planes of interest"

        if self._current != previous:
            logger.info(
                "Poll interval changed: %.0fs → %.0fs (%s)",
                previous, self._current, reason,
            )
        else:
            logger.debug("Poll interval unchanged: %.0fs (%s)", self._current, reason)

        return self._current
