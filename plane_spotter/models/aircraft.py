from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Aircraft:
    """Represents an aircraft observed via ADS-B."""

    hex: str
    flight: str | None
    registration: str | None
    aircraft_type: str | None
    alt_baro: int | None
    alt_geom: int | None
    ground_speed: float | None
    track: float | None
    lat: float | None
    lon: float | None
    distance: float | None
    direction: float | None

    @classmethod
    def from_api_response(cls, data: dict) -> Aircraft:
        return cls(
            hex=data.get("hex", ""),
            flight=(data.get("flight") or "").strip() or None,
            registration=data.get("r"),
            aircraft_type=data.get("t"),
            alt_baro=data.get("alt_baro") if isinstance(data.get("alt_baro"), int) else None,
            alt_geom=data.get("alt_geom") if isinstance(data.get("alt_geom"), int) else None,
            ground_speed=data.get("gs"),
            track=data.get("track"),
            lat=data.get("lat"),
            lon=data.get("lon"),
            distance=data.get("dst"),
            direction=data.get("dir"),
        )

    @property
    def has_position(self) -> bool:
        return self.lat is not None and self.lon is not None

    @property
    def has_track(self) -> bool:
        return self.track is not None and self.ground_speed is not None

    @property
    def callsign(self) -> str:
        return self.flight or self.registration or self.hex
