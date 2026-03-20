from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Application configuration. Loaded from environment variables with CLI overrides."""

    lat: float
    lon: float
    radius_nm: float = 5.0
    altitude_threshold_ft: int = 3000
    close_pass_nm: float = 0.5
    api_base_url: str = "https://re-api.adsb.lol/"
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, **overrides: object) -> Config:
        """Build config from environment variables, with keyword overrides taking precedence.

        Environment variables:
            PLANE_SPOTTER_LAT
            PLANE_SPOTTER_LON
            PLANE_SPOTTER_RADIUS
            PLANE_SPOTTER_ALTITUDE_THRESHOLD
            PLANE_SPOTTER_CLOSE_PASS
            PLANE_SPOTTER_API_URL
            PLANE_SPOTTER_LOG_LEVEL
        """

        def _get(
            key: str, env_var: str, convert: type, default: object = None
        ) -> object:
            if key in overrides and overrides[key] is not None:
                return convert(overrides[key])
            env_val = os.environ.get(env_var)
            if env_val is not None:
                return convert(env_val)
            if default is not None:
                return default
            raise ValueError(
                f"Missing required config: set --{key.replace('_', '-')} or {env_var}"
            )

        return cls(
            lat=_get("lat", "PLANE_SPOTTER_LAT", float),
            lon=_get("lon", "PLANE_SPOTTER_LON", float),
            radius_nm=_get("radius_nm", "PLANE_SPOTTER_RADIUS", float, 5.0),
            altitude_threshold_ft=_get(
                "altitude_threshold_ft", "PLANE_SPOTTER_ALTITUDE_THRESHOLD", int, 3000
            ),
            close_pass_nm=_get("close_pass_nm", "PLANE_SPOTTER_CLOSE_PASS", float, 0.5),
            api_base_url=_get(
                "api_base_url", "PLANE_SPOTTER_API_URL", str, "https://re-api.adsb.lol/"
            ),
            log_level=_get("log_level", "PLANE_SPOTTER_LOG_LEVEL", str, "INFO"),
        )
