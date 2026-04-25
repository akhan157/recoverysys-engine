"""Drift stage — wind-driven lateral displacement during descent.

Altitude-binned integration with multi-layer wind interpolation.
Includes geodetic projection for landing coordinates.
"""

from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np

from engine.atmosphere import FT_PER_M, M_PER_FT, MPH_TO_FPS, R_EARTH


@dataclass
class WindLayer:
    """A single wind measurement at an altitude."""
    altitude_ft: float
    speed_mph: float
    direction_deg: float  # 0=N, 90=E, 180=S, 270=W (wind FROM direction)


@dataclass
class DriftResult:
    """Output of drift computation."""
    drift_ft: float
    drift_m: float
    bearing_deg: float
    landing_lat: float | None
    landing_lon: float | None
    dx_ft: float  # east displacement
    dy_ft: float  # north displacement


def interpolate_wind(alt_ft: float, layers: list[WindLayer]) -> dict:
    """Interpolate wind speed and direction at a given altitude.

    Speed: linear interpolation between layers.
    Direction: shortest-path angular interpolation (handles 360° wrapping).
    """
    if not layers:
        return {"speed_mph": 0, "direction_deg": 0}

    # Sort by altitude
    sorted_layers = sorted(layers, key=lambda l: l.altitude_ft)

    # Below lowest layer
    if alt_ft <= sorted_layers[0].altitude_ft:
        return {"speed_mph": sorted_layers[0].speed_mph, "direction_deg": sorted_layers[0].direction_deg}

    # Above highest layer
    if alt_ft >= sorted_layers[-1].altitude_ft:
        return {"speed_mph": sorted_layers[-1].speed_mph, "direction_deg": sorted_layers[-1].direction_deg}

    # Find bracketing layers
    for i in range(1, len(sorted_layers)):
        if alt_ft <= sorted_layers[i].altitude_ft:
            lo = sorted_layers[i - 1]
            hi = sorted_layers[i]
            alt_range = hi.altitude_ft - lo.altitude_ft
            if alt_range <= 0:
                return {"speed_mph": lo.speed_mph, "direction_deg": lo.direction_deg}

            frac = (alt_ft - lo.altitude_ft) / alt_range

            # Linear speed interpolation
            speed = lo.speed_mph + frac * (hi.speed_mph - lo.speed_mph)

            # Angular direction interpolation (shortest path)
            d_dir = hi.direction_deg - lo.direction_deg
            if d_dir > 180:
                d_dir -= 360
            elif d_dir < -180:
                d_dir += 360
            direction = (lo.direction_deg + frac * d_dir) % 360

            return {"speed_mph": speed, "direction_deg": direction}

    return {"speed_mph": sorted_layers[-1].speed_mph, "direction_deg": sorted_layers[-1].direction_deg}


def project_point(lat_deg: float, lon_deg: float, bearing_deg: float, dist_m: float) -> tuple[float, float]:
    """Great-circle forward projection. Returns (lat, lon) in degrees."""
    lat1 = math.radians(lat_deg)
    lon1 = math.radians(lon_deg)
    brng = math.radians(bearing_deg)
    delta = dist_m / R_EARTH

    lat2 = math.asin(
        math.sin(lat1) * math.cos(delta) + math.cos(lat1) * math.sin(delta) * math.cos(brng)
    )
    lon2 = lon1 + math.atan2(
        math.sin(brng) * math.sin(delta) * math.cos(lat1),
        math.cos(delta) - math.sin(lat1) * math.sin(lat2),
    )

    return math.degrees(lat2), math.degrees(lon2)


def compute_drift(
    apogee_ft: float,
    deploy_alt_ft: float,
    drogue_fps: float,
    main_fps: float,
    wind_layers: list[WindLayer],
    launch_lat: float | None = None,
    launch_lon: float | None = None,
    alt_step_ft: float = 100,
) -> DriftResult:
    """Compute lateral drift during descent using altitude-binned wind integration.

    For each altitude step, samples wind at the midpoint altitude and accumulates
    east/north displacement based on descent rate and wind speed.
    """
    dx_ft = 0.0  # east
    dy_ft = 0.0  # north

    # Phase 1: drogue descent (apogee → deploy_alt)
    if drogue_fps > 0:
        alt = apogee_ft
        while alt > deploy_alt_ft:
            step = min(alt_step_ft, alt - deploy_alt_ft)
            mid_alt = alt - step / 2
            wind = interpolate_wind(mid_alt, wind_layers)
            wind_fps = wind["speed_mph"] * MPH_TO_FPS
            dt = step / drogue_fps

            # Wind FROM direction → drift TO (opposite)
            drift_bearing = (wind["direction_deg"] + 180) % 360
            bearing_rad = math.radians(drift_bearing)

            dx_ft += wind_fps * dt * math.sin(bearing_rad)
            dy_ft += wind_fps * dt * math.cos(bearing_rad)
            alt -= step

    # Phase 2: main descent (deploy_alt → ground)
    descent_fps = main_fps if main_fps > 0 else drogue_fps
    if descent_fps > 0:
        alt = deploy_alt_ft if drogue_fps > 0 else apogee_ft
        while alt > 0:
            step = min(alt_step_ft, alt)
            mid_alt = alt - step / 2
            wind = interpolate_wind(mid_alt, wind_layers)
            wind_fps = wind["speed_mph"] * MPH_TO_FPS
            dt = step / descent_fps

            drift_bearing = (wind["direction_deg"] + 180) % 360
            bearing_rad = math.radians(drift_bearing)

            dx_ft += wind_fps * dt * math.sin(bearing_rad)
            dy_ft += wind_fps * dt * math.cos(bearing_rad)
            alt -= step

    # Magnitude and bearing
    drift_ft = math.sqrt(dx_ft**2 + dy_ft**2)
    drift_m = drift_ft * M_PER_FT
    bearing_deg = (math.degrees(math.atan2(dx_ft, dy_ft)) + 360) % 360

    # Landing coordinates
    landing_lat = None
    landing_lon = None
    if launch_lat is not None and launch_lon is not None:
        landing_lat, landing_lon = project_point(launch_lat, launch_lon, bearing_deg, drift_m)

    return DriftResult(
        drift_ft=round(drift_ft, 1),
        drift_m=round(drift_m, 1),
        bearing_deg=round(bearing_deg, 1),
        landing_lat=round(landing_lat, 6) if landing_lat else None,
        landing_lon=round(landing_lon, 6) if landing_lon else None,
        dx_ft=round(dx_ft, 1),
        dy_ft=round(dy_ft, 1),
    )
