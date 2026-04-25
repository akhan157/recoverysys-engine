"""Simulation pipeline — orchestrates all stages into a single run."""

from __future__ import annotations
from dataclasses import dataclass, asdict
import math

from engine.atmosphere import FT_PER_M, M_PER_FT, G, N_PER_LBF
from engine.stages.ascent import integrate_ascent, AscentResult
from engine.stages.descent import compute_descent, compute_descent_rate, DescentResult
from engine.stages.drift import compute_drift, WindLayer, DriftResult
from engine.stages.monte_carlo import run_monte_carlo, MonteCarloResult


@dataclass
class SimulationInput:
    """All inputs needed for a full simulation run."""
    # Rocket specs
    rocket_mass_kg: float
    motor_total_impulse_ns: float
    burn_time_s: float
    airframe_od_in: float  # outer diameter for cross-section
    cd: float = 0.5

    # Recovery parts (diameter_in, cd)
    main_chute: dict | None = None
    drogue_chute: dict | None = None

    # Deploy altitude
    main_deploy_alt_ft: float = 700

    # Wind
    wind_layers: list[dict] | None = None  # [{altitude_ft, speed_mph, direction_deg}]

    # Launch site
    launch_lat: float | None = None
    launch_lon: float | None = None

    # Motor thrust curve (optional)
    thrust_curve: list[dict] | None = None
    propellant_mass_kg: float | None = None

    # Monte Carlo
    monte_carlo_enabled: bool = False
    monte_carlo_iterations: int = 500
    monte_carlo_seed: int | None = None

    # Fidelity
    fidelity: str = "simple"  # simple | advanced | research


@dataclass
class SimulationResult:
    """Complete simulation output."""
    ascent: dict
    descent: dict
    drift: dict | None
    monte_carlo: dict | None
    shock_load: dict | None
    warnings: list[str]
    fidelity_used: str
    compute_time_ms: float = 0


def _build_wind_layers(raw: list[dict] | None) -> list[WindLayer]:
    """Convert raw wind layer dicts to WindLayer objects."""
    if not raw:
        return []
    return [
        WindLayer(
            altitude_ft=w.get("altitude_ft", 0),
            speed_mph=w.get("speed_mph", 0),
            direction_deg=w.get("direction_deg", 0),
        )
        for w in raw
    ]


def _compute_shock_load(mass_kg: float, g_factor: float = 20) -> dict:
    """Static ejection shock load estimate."""
    if mass_kg >= 10:
        g_factor = 30  # L3 class
    peak_n = mass_kg * g_factor * G
    peak_lbs = peak_n / N_PER_LBF
    return {
        "g_factor": g_factor,
        "peak_force_n": round(peak_n, 1),
        "peak_force_lbs": round(peak_lbs, 1),
    }


def run_simulation(inputs: SimulationInput) -> SimulationResult:
    """Execute the full simulation pipeline.

    Pipeline: Motor → Ascent → Descent → Drift → Monte Carlo
    """
    import time
    t_start = time.perf_counter()

    warnings = []

    # Cross-section area from airframe OD
    radius_m = (inputs.airframe_od_in * 0.0254) / 2
    area_m2 = math.pi * radius_m**2

    # ── Stage 1: Ascent ──────────────────────────────────────────────
    ascent = integrate_ascent(
        total_mass_kg=inputs.rocket_mass_kg,
        total_impulse_ns=inputs.motor_total_impulse_ns,
        burn_time_s=inputs.burn_time_s,
        cross_section_area_m2=area_m2,
        cd=inputs.cd,
        thrust_curve=inputs.thrust_curve,
        prop_mass_kg=inputs.propellant_mass_kg,
    )

    if ascent.apogee_ft <= inputs.main_deploy_alt_ft:
        warnings.append(
            f"Apogee ({ascent.apogee_ft:.0f} ft) is at or below main deploy altitude "
            f"({inputs.main_deploy_alt_ft:.0f} ft). Simulation may be invalid."
        )

    # ── Stage 2: Descent ─────────────────────────────────────────────
    descent = compute_descent(
        apogee_ft=ascent.apogee_ft,
        deploy_alt_ft=inputs.main_deploy_alt_ft,
        drogue_specs=inputs.drogue_chute,
        main_specs=inputs.main_chute,
        mass_kg=inputs.rocket_mass_kg,
    )

    # Descent rate warnings
    if descent.main_fps > 20:
        warnings.append(f"Main descent rate {descent.main_fps:.1f} ft/s exceeds 20 ft/s — hard landing risk.")
    elif descent.main_fps > 15:
        warnings.append(f"Main descent rate {descent.main_fps:.1f} ft/s exceeds 15 ft/s — above nominal.")

    if descent.main_fps > 0 and descent.main_fps < 5:
        warnings.append(f"Main descent rate {descent.main_fps:.1f} ft/s is very slow — high drift risk.")

    # ── Stage 3: Drift ───────────────────────────────────────────────
    wind_layers = _build_wind_layers(inputs.wind_layers)
    drift_result = None

    if wind_layers and descent.drogue_fps + descent.main_fps > 0:
        drift_result = compute_drift(
            apogee_ft=ascent.apogee_ft,
            deploy_alt_ft=inputs.main_deploy_alt_ft,
            drogue_fps=descent.drogue_fps,
            main_fps=descent.main_fps,
            wind_layers=wind_layers,
            launch_lat=inputs.launch_lat,
            launch_lon=inputs.launch_lon,
        )

    # ── Stage 4: Monte Carlo ─────────────────────────────────────────
    mc_result = None
    if (
        inputs.monte_carlo_enabled
        and wind_layers
        and inputs.launch_lat is not None
        and inputs.launch_lon is not None
        and descent.drogue_fps + descent.main_fps > 0
    ):
        mc_result = run_monte_carlo(
            apogee_ft=ascent.apogee_ft,
            deploy_alt_ft=inputs.main_deploy_alt_ft,
            drogue_fps=descent.drogue_fps,
            main_fps=descent.main_fps,
            wind_layers=wind_layers,
            launch_lat=inputs.launch_lat,
            launch_lon=inputs.launch_lon,
            iterations=inputs.monte_carlo_iterations,
            seed=inputs.monte_carlo_seed,
        )

    # ── Shock load ───────────────────────────────────────────────────
    shock = _compute_shock_load(inputs.rocket_mass_kg)

    t_end = time.perf_counter()

    return SimulationResult(
        ascent={
            "apogee_ft": ascent.apogee_ft,
            "apogee_m": ascent.apogee_m,
            "burnout_alt_ft": round(ascent.burnout_alt_m * FT_PER_M, 1),
            "burnout_velocity_fps": round(ascent.burnout_velocity_mps * FT_PER_M, 1),
            "max_mach": ascent.max_mach,
            "max_acceleration_g": ascent.max_accel_g,
            "timeline": ascent.timeline,
        },
        descent={
            "drogue_fps": descent.drogue_fps,
            "main_fps": descent.main_fps,
            "phase1_time_s": descent.phase1_time_s,
            "phase2_time_s": descent.phase2_time_s,
            "total_time_s": descent.total_time_s,
            "timeline": descent.timeline,
        },
        drift={
            "distance_ft": drift_result.drift_ft,
            "distance_m": drift_result.drift_m,
            "bearing_deg": drift_result.bearing_deg,
            "landing": {
                "lat": drift_result.landing_lat,
                "lon": drift_result.landing_lon,
            } if drift_result.landing_lat else None,
        } if drift_result else None,
        monte_carlo={
            "scatter": mc_result.scatter,
            "ellipse": asdict(mc_result.ellipse) if mc_result.ellipse else None,
            "p95_drift_ft": mc_result.p95_drift_ft,
            "iterations": mc_result.iterations,
        } if mc_result else None,
        shock_load=shock,
        warnings=warnings,
        fidelity_used=inputs.fidelity,
        compute_time_ms=round((t_end - t_start) * 1000, 1),
    )
