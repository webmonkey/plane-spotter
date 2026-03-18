from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from .aircraft import Aircraft


class TrackingStatus(Enum):
    """Classification of an aircraft relative to the user's position."""

    APPROACHING = auto()
    NEARBY = auto()
    GONE = auto()


class EventType(Enum):
    """Type of state transition event."""

    NEW_APPROACH = auto()
    STILL_APPROACHING = auto()
    PASSED = auto()
    DEPARTED = auto()


@dataclass(frozen=True)
class TrackingEvent:
    """A state-change event for a tracked aircraft."""

    event_type: EventType
    aircraft: Aircraft
    cpa_distance_nm: float | None = None
    time_to_cpa_seconds: float | None = None
