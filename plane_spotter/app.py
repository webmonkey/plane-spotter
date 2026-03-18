from __future__ import annotations

import asyncio
import logging
import signal

from .client import ADSBClient
from .config import Config
from .notifier import Notifier
from .scheduler import PollScheduler
from .tracker import PlaneTracker

logger = logging.getLogger(__name__)


class PlaneSpotterApp:
    """Core application orchestrator. No CLI dependency — reusable for web backends."""

    def __init__(
        self,
        config: Config,
        client: ADSBClient,
        tracker: PlaneTracker,
        scheduler: PollScheduler,
        notifier: Notifier,
    ) -> None:
        self._config = config
        self._client = client
        self._tracker = tracker
        self._scheduler = scheduler
        self._notifier = notifier
        self._running = False
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        """Main polling loop. Runs until interrupted."""
        self._running = True
        self._stop_event.clear()
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._shutdown)

        logger.info(
            "Starting plane-spotter at %.3f,%.3f — radius %.0fnm, alt ≤%d ft, close pass ≤%.1fnm",
            self._config.lat,
            self._config.lon,
            self._config.radius_nm,
            self._config.altitude_threshold_ft,
            self._config.close_pass_nm,
        )

        try:
            while self._running:
                await self._poll_cycle()
                interval = self._scheduler.get_interval(self._tracker)
                logger.debug("Sleeping %.0fs until next poll", interval)
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
                except asyncio.TimeoutError:
                    pass
        finally:
            logger.info("Shutting down")
            await self._client.close()

    async def _poll_cycle(self) -> None:
        """Execute one fetch → track → notify cycle."""
        try:
            aircraft = await self._client.fetch_nearby(
                self._config.lat,
                self._config.lon,
                self._config.radius_nm,
            )
            events = self._tracker.update(aircraft)
            for event in events:
                self._notifier.notify(event)
        except Exception:
            logger.exception("Error during poll cycle")

    def _shutdown(self) -> None:
        logger.info("Received shutdown signal")
        self._running = False
        self._stop_event.set()
