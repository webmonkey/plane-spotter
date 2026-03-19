from __future__ import annotations

import abc
from datetime import datetime

from .models import EventType, TrackingEvent


class Notifier(abc.ABC):
    """Abstract base class for notification output."""

    @abc.abstractmethod
    def notify(self, event: TrackingEvent) -> None: ...


class ConsoleNotifier(Notifier):
    """Prints formatted alerts to stdout."""

    _EVENT_LABELS = {
        EventType.NEW_APPROACH: "✈  APPROACHING",
        EventType.STILL_APPROACHING: "✈  STILL APPROACHING",
        EventType.PASSED: "   PASSED",
        EventType.DEPARTED: "   DEPARTED",
    }

    def notify(self, event: TrackingEvent) -> None:
        ac = event.aircraft
        label = self._EVENT_LABELS.get(event.event_type, str(event.event_type))
        timestamp = datetime.now().isoformat(timespec="seconds")

        header = f"{label}: {ac.callsign}"
        if event.cpa_distance_nm is not None:
            header += f" at {event.cpa_distance_nm:.2f}nm"

        parts = [header]

        if ac.aircraft_type:
            parts.append(ac.aircraft_type)
        if ac.alt_baro is not None:
            parts.append(f"{ac.alt_baro}ft")
        if ac.ground_speed is not None:
            parts.append(f"{ac.ground_speed:.0f}kts")
        if event.time_to_cpa_seconds is not None:
            parts.append(f"ETA: {event.time_to_cpa_seconds:.0f}s")

        print(f"{timestamp} {' | '.join(parts)}")
