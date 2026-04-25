"""Monte Carlo dispersion simulation.

Perturbs wind, motor, mass, Cd, and deploy altitude to generate a scatter
cloud of landing points. Fits a 95% confidence ellipse via PCA.
"""

from __future__ import annotations
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor
import math
import numpy as np

from engine.stages.drift import WindLayer, compute_drift, project_point
from engine.stages.descent import compute_descent_rate
from engine.atmosphere import M_PER_FT


@dataclass
class EllipseResult:
    """95% confidence ellipse parameters."""
    center_lat: float
    center_lon: float
    semi_major_m: float
    semi_minor_m: float
    angle_deg: float  # rotation from north


@dataclass
class MonteCarloResult:
    """Output of Monte Carlo dispersion."""
    scatter: list[dict]  # [{lat, lon}]
    ellipse: EllipseResult | None
    p95_drift_ft: float
    iterations: int


def _perturb_wind_layers(
    layers: list[WindLayer],
    rng: np.random.Generator,
    speed_sigma: float = 0.30,
    direction_sigma_deg: float = 15.0,
) -> list[WindLayer]:
    """Create a perturbed copy of wind layers."""
    perturbed = []
    for layer in layers:
        speed = max(0, layer.speed_mph * (1 + speed_sigma * rng.standard_normal()))
        direction = (layer.direction_deg + direction_sigma_deg * rng.standard_normal()) % 360
        perturbed.append(WindLayer(layer.altitude_ft, speed, direction))
    return perturbed


def _run_single_iteration(args: tuple) -> dict | None:
    """Run one Monte Carlo iteration. Designed for ProcessPoolExecutor."""
    (
        seed, apogee_ft, deploy_alt_ft, drogue_fps, main_fps,
        wind_layers_data, launch_lat, launch_lon,
        motor_sigma, mass_sigma, cd_sigma, deploy_sigma_ft,
    ) = args

    rng = np.random.default_rng(seed)

    # Reconstruct wind layers from serializable data
    wind_layers = [WindLayer(*w) for w in wind_layers_data]

    # Perturb wind
    perturbed_wind = _perturb_wind_layers(wind_layers, rng)

    # Perturb apogee (proxy for motor + mass + Cd combined effect)
    apogee_factor = 1 + motor_sigma * rng.standard_normal()
    perturbed_apogee = apogee_ft * max(0.5, apogee_factor)

    # Perturb deploy altitude
    perturbed_deploy = max(100, deploy_alt_ft + deploy_sigma_ft * rng.standard_normal())

    if perturbed_apogee <= perturbed_deploy:
        return None

    result = compute_drift(
        apogee_ft=perturbed_apogee,
        deploy_alt_ft=perturbed_deploy,
        drogue_fps=drogue_fps,
        main_fps=main_fps,
        wind_layers=perturbed_wind,
        launch_lat=launch_lat,
        launch_lon=launch_lon,
    )

    if result.landing_lat is not None:
        return {"lat": result.landing_lat, "lon": result.landing_lon, "drift_ft": result.drift_ft}
    return None


def fit_confidence_ellipse(points: list[dict]) -> EllipseResult | None:
    """Fit a 95% confidence ellipse to scatter points via PCA.

    Uses eigendecomposition of the 2x2 covariance matrix.
    Chi-squared critical value for 2 DOF at p=0.05: 5.991
    """
    if len(points) < 3:
        return None

    lats = np.array([p["lat"] for p in points])
    lons = np.array([p["lon"] for p in points])

    cx = np.mean(lats)
    cy = np.mean(lons)

    # Convert to local metres
    m_per_deg_lat = 111_320
    m_per_deg_lon = 111_320 * math.cos(math.radians(cx))

    x = (lons - cy) * m_per_deg_lon  # east
    y = (lats - cx) * m_per_deg_lat  # north

    n = len(points)
    sxx = np.sum(x**2) / (n - 1)
    syy = np.sum(y**2) / (n - 1)
    sxy = np.sum(x * y) / (n - 1)

    # Eigenvalues of covariance matrix
    tr = sxx + syy
    det = sxx * syy - sxy**2
    disc = math.sqrt(max(0, tr**2 / 4 - det))

    lambda1 = tr / 2 + disc  # major
    lambda2 = max(0, tr / 2 - disc)  # minor

    # 95% confidence scaling: sqrt(chi2_2_0.05) = sqrt(5.991)
    scale = math.sqrt(5.991)
    rx = scale * math.sqrt(lambda1)
    ry = scale * math.sqrt(lambda2)

    # Rotation angle
    angle_rad = math.atan2(2 * sxy, sxx - syy) / 2
    angle_deg = (90 - math.degrees(angle_rad) + 360) % 360

    return EllipseResult(
        center_lat=round(cx, 6),
        center_lon=round(cy, 6),
        semi_major_m=round(rx, 1),
        semi_minor_m=round(ry, 1),
        angle_deg=round(angle_deg, 1),
    )


def run_monte_carlo(
    apogee_ft: float,
    deploy_alt_ft: float,
    drogue_fps: float,
    main_fps: float,
    wind_layers: list[WindLayer],
    launch_lat: float,
    launch_lon: float,
    iterations: int = 500,
    seed: int | None = None,
    motor_sigma: float = 0.05,
    mass_sigma: float = 0.03,
    cd_sigma: float = 0.10,
    deploy_sigma_ft: float = 50,
    max_workers: int | None = None,
) -> MonteCarloResult:
    """Run Monte Carlo dispersion with multiprocessing.

    Each iteration perturbs wind layers, apogee, and deploy altitude,
    then computes drift. Results are collected into a scatter cloud
    and a 95% confidence ellipse is fitted.
    """
    base_rng = np.random.default_rng(seed)
    seeds = base_rng.integers(0, 2**31, size=iterations)

    # Serialize wind layers for multiprocessing
    wind_data = [(w.altitude_ft, w.speed_mph, w.direction_deg) for w in wind_layers]

    # Combined sigma for apogee perturbation (motor + mass + Cd)
    combined_sigma = math.sqrt(motor_sigma**2 + mass_sigma**2 + cd_sigma**2)

    args_list = [
        (
            int(s), apogee_ft, deploy_alt_ft, drogue_fps, main_fps,
            wind_data, launch_lat, launch_lon,
            combined_sigma, mass_sigma, cd_sigma, deploy_sigma_ft,
        )
        for s in seeds
    ]

    # Run iterations in parallel
    scatter = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(_run_single_iteration, args_list, chunksize=50)
        for result in results:
            if result is not None:
                scatter.append(result)

    # Fit ellipse
    ellipse = fit_confidence_ellipse(scatter) if len(scatter) >= 3 else None

    # P95 drift
    drifts = sorted([p["drift_ft"] for p in scatter])
    p95_idx = int(len(drifts) * 0.95) if drifts else 0
    p95_drift = drifts[p95_idx] if p95_idx < len(drifts) else 0

    return MonteCarloResult(
        scatter=[{"lat": p["lat"], "lon": p["lon"]} for p in scatter],
        ellipse=ellipse,
        p95_drift_ft=round(p95_drift, 1),
        iterations=len(scatter),
    )
