# Plane Spotter

A CLI tool that monitors ADS-B aircraft data and alerts you when a low-altitude plane is likely to pass overhead.

Uses data from [adsb.lol](https://adsb.lol) with adaptive polling — the app backs off when skies are quiet and polls more frequently when an aircraft is on an approaching track.

## Quick start (Docker)

The simplest way to run Plane Spotter — no Python or dependencies needed:

```bash
docker build -t plane-spotter .
docker run --rm plane-spotter --lat 51.501 --lon -0.142
```

Or with environment variables:

```bash
docker run --rm -e PLANE_SPOTTER_LAT=51.501 -e PLANE_SPOTTER_LON=-0.142 plane-spotter
```

## How it works

1. Polls the adsb.lol API for aircraft within a configurable radius of your location
2. Filters by altitude threshold (default: 3,000 ft)
3. Projects each aircraft's track to calculate the **Closest Point of Approach (CPA)** to your position
4. If a plane's projected track will bring it within 0.5 nm and it's heading towards you, an alert is printed
5. Polling frequency adapts: 120s (idle) → 60s (aircraft nearby) → 30s (imminent pass)

### Options

| Option | Env var | Default | Description |
|---|---|---|---|
| `--lat` | `PLANE_SPOTTER_LAT` | *required* | Your latitude |
| `--lon` | `PLANE_SPOTTER_LON` | *required* | Your longitude |
| `--radius` | `PLANE_SPOTTER_RADIUS` | 5 | Search radius in nautical miles |
| `--altitude-threshold` | `PLANE_SPOTTER_ALTITUDE_THRESHOLD` | 3000 | Max altitude in feet |
| `--close-pass-distance` | `PLANE_SPOTTER_CLOSE_PASS` | 0.5 | Close pass threshold in nm |
| `--confirmation-count` | `PLANE_SPOTTER_CONFIRMATION_COUNT` | 3 | Consecutive approaching polls before alerting |
| `--ignore-type` | `PLANE_SPOTTER_IGNORED_TYPE_CODES` | | Comma-separated aircraft type codes to ignore (e.g. `BALL,ULAC`) |
| `--log-level` | `PLANE_SPOTTER_LOG_LEVEL` | INFO | Log level (DEBUG, INFO, WARNING, ERROR) |

## Running without Docker

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone <repo-url>
cd plane-spotter
uv sync
uv run python -m plane_spotter --lat 51.501 --lon -0.142
```

## Running tests

```bash
uv run pytest tests/ -v
```

## Project structure

```
plane_spotter/
├── __main__.py      # CLI entry point (Click)
├── app.py           # Async orchestrator (fetch → track → notify → sleep)
├── client.py        # httpx async client for adsb.lol API
├── config.py        # Configuration from env vars / CLI args
├── geometry.py      # Haversine, CPA, time-to-CPA calculations
├── models/
│   ├── aircraft.py  # Aircraft dataclass
│   └── tracking.py  # TrackingEvent, TrackingStatus, EventType
├── notifier.py      # Abstract notifier + console implementation
├── scheduler.py     # Adaptive 3-tier polling intervals
└── tracker.py       # Aircraft state tracking across poll cycles
```

## Architecture

The app is structured with OO principles and a clean separation between domain logic and CLI concerns. `PlaneSpotterApp` orchestrates the polling loop without any CLI dependency, making it straightforward to add a web interface in the future.
