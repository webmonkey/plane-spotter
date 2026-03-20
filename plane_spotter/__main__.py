from __future__ import annotations

import asyncio
import logging

import click

from .app import PlaneSpotterApp
from .client import ADSBClient
from .config import Config
from .notifier import ConsoleNotifier
from .scheduler import PollScheduler
from .tracker import PlaneTracker


@click.command()
@click.option(
    "--lat", type=float, default=None, help="Your latitude (or set PLANE_SPOTTER_LAT)"
)
@click.option(
    "--lon", type=float, default=None, help="Your longitude (or set PLANE_SPOTTER_LON)"
)
@click.option(
    "--radius",
    "radius_nm",
    type=float,
    default=None,
    help="Search radius in nm (default: 5)",
)
@click.option(
    "--altitude-threshold",
    "altitude_threshold_ft",
    type=int,
    default=None,
    help="Max altitude in ft (default: 3000)",
)
@click.option(
    "--close-pass-distance",
    "close_pass_nm",
    type=float,
    default=None,
    help="Close pass distance in nm (default: 0.5)",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="WARNING",
    help="Log output level (default: INFO, or set PLANE_SPOTTER_LOG_LEVEL)",
)
def main(
    lat: float | None,
    lon: float | None,
    radius_nm: float | None,
    altitude_threshold_ft: int | None,
    close_pass_nm: float | None,
    log_level: str | None,
) -> None:
    """Monitor nearby low-altitude aircraft and alert when one is approaching."""
    try:
        config = Config.from_env(
            lat=lat,
            lon=lon,
            radius_nm=radius_nm,
            altitude_threshold_ft=altitude_threshold_ft,
            close_pass_nm=close_pass_nm,
            log_level=log_level,
        )
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc

    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("httpcore.http11").setLevel(logging.INFO)
    logging.getLogger("httpcore.connection").setLevel(logging.INFO)

    client = ADSBClient(base_url=config.api_base_url)
    tracker = PlaneTracker(
        user_lat=config.lat,
        user_lon=config.lon,
        altitude_threshold_ft=config.altitude_threshold_ft,
        close_pass_nm=config.close_pass_nm,
    )
    scheduler = PollScheduler()
    notifier = ConsoleNotifier()

    app = PlaneSpotterApp(config, client, tracker, scheduler, notifier)
    asyncio.run(app.run())


if __name__ == "__main__":
    main()
