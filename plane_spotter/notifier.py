from __future__ import annotations

import abc

from .models import EventType, TrackingEvent


class Notifier(abc.ABC):
    """Abstract base class for notification output."""

    @abc.abstractmethod
    def notify(self, event: TrackingEvent) -> None:
        ...


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

        parts = [f"{label}: {ac.callsign}"]

        if ac.aircraft_type:
            parts.append(f"Type: {ac.aircraft_type}")
        if ac.alt_baro is not None:
            parts.append(f"Alt: {ac.alt_baro} ft")
        if event.cpa_distance_nm is not None:
            parts.append(f"CPA: {event.cpa_distance_nm:.2f} nm")
        if event.time_to_cpa_seconds is not None:
            parts.append(f"ETA: {event.time_to_cpa_seconds:.0f}s")
        if ac.ground_speed is not None:
            parts.append(f"Speed: {ac.ground_speed:.0f} kts")
        if ac.distance is not None:
            parts.append(f"Dist: {ac.distance:.1f} nm")

        print(" | ".join(parts))
