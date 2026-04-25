"""Descent stage — parachute terminal velocity and descent timeline.

Simple fidelity: instant terminal velocity, 1-body.
"""

from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np

from engine.atmosphere import G, air_density, FT_PER_M, M_PER_FT


@dataclass
class DescentResult:
    """Output of descent computation."""
    drogue_fps: float
    main_fps: float
    phase1_time_s: float  # apogee → deploy alt (drogue)
    phase2_time_s: float  # deploy alt → ground (main)
    total_time_s: float
    timeline: list[dict]  # [{t_s, alt_ft}]


def compute_descent_rate(
    diameter_in: float,
    cd: float,
    mass_kg: float,
    altitude_ft: float = 0,
) -> float:
    """Terminal descent rate in ft/s for a parachute.

    Drag equilibrium: mg = ½ρCdAv²  →  v = sqrt(2mg / ρCdA)
    """
    if cd <= 0 or diameter_in <= 0:
        return 0.0
    radius_m = (diameter_in * 0.0254) / 2
    area_m2 = math.pi * radius_m ** 2
    rho = air_density(altitude_ft * M_PER_FT)
    v_mps = math.sqrt((2 * mass_kg * G) / (rho * cd * area_m2))
    return v_mps * FT_PER_M


def compute_descent(
    apogee_ft: float,
    deploy_alt_ft: float,
    drogue_specs: dict | None,
    main_specs: dict | None,
    mass_kg: float,
) -> DescentResult:
    """Compute descent timeline from apogee to ground.

    Args:
        apogee_ft: Apogee altitude in feet
        deploy_alt_ft: Main deployment altitude in feet
        drogue_specs: {diameter_in, cd} or None
        main_specs: {diameter_in, cd} or None
        mass_kg: Total rocket mass (kg)
    """
    if apogee_ft <= 0:
        return DescentResult(0, 0, 0, 0, 0, [])

    # Compute descent rates at representative altitudes
    mid_alt = (apogee_ft + deploy_alt_ft) / 2
    drogue_fps = 0.0
    if drogue_specs and drogue_specs.get("diameter_in") and drogue_specs.get("cd"):
        drogue_fps = compute_descent_rate(
            drogue_specs["diameter_in"], drogue_specs["cd"], mass_kg, mid_alt,
        )

    main_fps = 0.0
    if main_specs and main_specs.get("diameter_in") and main_specs.get("cd"):
        main_fps = compute_descent_rate(
            main_specs["diameter_in"], main_specs["cd"], mass_kg, deploy_alt_ft,
        )

    # Phase timings
    drogue_alt_range = max(0, apogee_ft - deploy_alt_ft)
    phase1_time = drogue_alt_range / drogue_fps if drogue_fps > 0 else 0
    phase2_time = deploy_alt_ft / main_fps if main_fps > 0 else 0

    # If no drogue, main handles entire descent
    if drogue_fps == 0 and main_fps > 0:
        phase1_time = 0
        phase2_time = apogee_ft / main_fps
        deploy_alt_ft = apogee_ft

    total_time = phase1_time + phase2_time

    # Build timeline
    timeline = _build_timeline(
        apogee_ft, deploy_alt_ft, drogue_fps, main_fps,
        phase1_time, phase2_time,
    )

    return DescentResult(
        drogue_fps=round(drogue_fps, 1),
        main_fps=round(main_fps, 1),
        phase1_time_s=round(phase1_time, 1),
        phase2_time_s=round(phase2_time, 1),
        total_time_s=round(total_time, 1),
        timeline=timeline,
    )


def _build_timeline(
    apogee_ft: float,
    deploy_alt_ft: float,
    drogue_fps: float,
    main_fps: float,
    phase1_time: float,
    phase2_time: float,
    n_points_phase1: int = 30,
    n_points_phase2: int = 15,
) -> list[dict]:
    """Generate altitude-time points for the descent."""
    timeline = []
    t_offset = 0.0  # ascent time would be added by the pipeline

    # Phase 1: drogue descent
    if phase1_time > 0 and drogue_fps > 0:
        for i in range(n_points_phase1 + 1):
            frac = i / n_points_phase1
            t = frac * phase1_time
            alt = apogee_ft - drogue_fps * t
            timeline.append({
                "t_s": round(t_offset + t, 2),
                "alt_ft": round(max(0, alt), 1),
            })
        t_offset += phase1_time

    # Phase 2: main descent
    if phase2_time > 0 and main_fps > 0:
        start_alt = deploy_alt_ft if drogue_fps > 0 else apogee_ft
        for i in range(n_points_phase2 + 1):
            frac = i / n_points_phase2
            t = frac * phase2_time
            alt = start_alt - main_fps * t
            timeline.append({
                "t_s": round(t_offset + t, 2),
                "alt_ft": round(max(0, alt), 1),
            })

    return timeline
