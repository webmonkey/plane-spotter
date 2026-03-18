from __future__ import annotations

import logging

import httpx

from .models import Aircraft

logger = logging.getLogger(__name__)


class ADSBClient:
    """Async client for the adsb.lol API."""

    def __init__(self, base_url: str = "https://re-api.adsb.lol/") -> None:
        self._base_url = base_url.rstrip("/")
        self._http: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
        return self._http

    async def fetch_nearby(self, lat: float, lon: float, radius_nm: float) -> list[Aircraft]:
        """Fetch aircraft within the given radius of a position.

        Returns only aircraft that have valid position data.
        """
        url = f"{self._base_url}/?circle={lat:.6f},{lon:.6f},{radius_nm:.0f}"
        logger.debug("Requesting %s", url)

        client = await self._get_client()
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                logger.warning("Rate limited by API (429), backing off")
            else:
                logger.error("HTTP error %d from API", exc.response.status_code)
            raise
        except httpx.RequestError as exc:
            logger.error("Request failed: %s", exc)
            raise

        data = response.json()
        logger.debug("Response status %d, %d aircraft in payload", response.status_code, data.get("resultCount", 0))

        raw_aircraft = data.get("aircraft", [])
        aircraft = [Aircraft.from_api_response(ac) for ac in raw_aircraft]
        aircraft = [ac for ac in aircraft if ac.has_position]

        logger.info("Fetched %d aircraft (%d with position)", len(raw_aircraft), len(aircraft))
        return aircraft

    async def close(self) -> None:
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()
