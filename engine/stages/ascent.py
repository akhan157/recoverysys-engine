"""Ascent stage — powered flight + coast to apogee using scipy RK45.

Replaces the forward Euler integrator from the JS sim with a proper
adaptive-step ODE solver. State vector: [altitude_m, velocity_mps].
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.integrate import solve_ivp

from engine.atmosphere import G, air_density, mach_number, FT_PER_M
from engine.stages.motor import ThrustCurve, interpolate_thrust

APCP_ISP = 195   # s — typical APCP specific impulse
V_MAX = 3400     # m/s — hard cap (Mach ~10) for sanity
MAX_ALT = 100_000  # m — 100 km, well beyond HPR range


@dataclass
class AscentResult:
    """Output of the ascent integration."""
    apogee_m: float
    apogee_ft: float
    burnout_alt_m: float
    burnout_velocity_mps: float
    burnout_time_s: float
    max_mach: float
    max_accel_g: float
    timeline: list[dict]  # [{t_s, alt_m, alt_ft, v_mps, v_fps, mach, accel_g}]


def estimate_propellant_mass(
    total_mass_kg: float,
    total_impulse_ns: float,
    prop_mass_override: float | None = None,
) -> float:
    """Estimate propellant mass from total impulse using Isp relationship.
    Capped at 55% of total mass to avoid unphysical solutions."""
    if prop_mass_override is not None:
        return min(prop_mass_override, 0.55 * total_mass_kg)
    m_prop = total_impulse_ns / (APCP_ISP * G)
    return min(m_prop, 0.55 * total_mass_kg)


def _mass_at_time(t: float, total_mass_kg: float, prop_mass_kg: float, burn_time_s: float) -> float:
    """Linear propellant depletion during burn."""
    if t >= burn_time_s or burn_time_s <= 0:
        return total_mass_kg - prop_mass_kg
    return total_mass_kg - prop_mass_kg * (t / burn_time_s)


def integrate_ascent(
    total_mass_kg: float,
    total_impulse_ns: float,
    burn_time_s: float,
    cross_section_area_m2: float,
    cd: float,
    thrust_curve: list[dict] | None = None,
    prop_mass_kg: float | None = None,
) -> AscentResult:
    """Integrate powered ascent + coast to apogee using RK45.

    Args:
        total_mass_kg: Total rocket mass at liftoff (kg)
        total_impulse_ns: Motor total impulse (N·s)
        burn_time_s: Motor burn time (s)
        cross_section_area_m2: Rocket cross-section area (m²)
        cd: Drag coefficient (constant for Simple fidelity)
        thrust_curve: Optional [{t, thrust_N}] points. If None, uses constant thrust.
        prop_mass_kg: Optional propellant mass override (kg).
    """
    m_prop = estimate_propellant_mass(total_mass_kg, total_impulse_ns, prop_mass_kg)
    m_dry = total_mass_kg - m_prop
    A = cross_section_area_m2

    # Constant thrust fallback if no curve provided
    constant_thrust = total_impulse_ns / burn_time_s if burn_time_s > 0 else 0

    # Track max values
    max_mach = 0.0
    max_accel_g = 0.0
    timeline = []

    def get_thrust(t: float) -> float:
        if thrust_curve:
            return interpolate_thrust(t, thrust_curve)
        return constant_thrust if t <= burn_time_s else 0.0

    def derivatives(t: float, state: np.ndarray) -> np.ndarray:
        """ODE right-hand side: d/dt [alt, vel] = [vel, accel]."""
        nonlocal max_mach, max_accel_g
        alt, vel = state

        # Clamp altitude for ISA validity
        alt_clamped = np.clip(alt, 0, MAX_ALT)
        rho = air_density(alt_clamped)

        # Mass at current time (linear depletion)
        m = _mass_at_time(t, total_mass_kg, m_prop, burn_time_s)

        # Thrust
        F_thrust = get_thrust(t)

        # Drag (opposes motion)
        F_drag = 0.5 * rho * cd * A * vel * abs(vel)

        # Net acceleration
        accel = (F_thrust - F_drag) / m - G

        # Track stats
        mach = mach_number(vel, alt_clamped)
        if mach > max_mach:
            max_mach = mach
        accel_g = abs(accel / G)
        if accel_g > max_accel_g:
            max_accel_g = accel_g

        return np.array([vel, accel])

    def apogee_event(t: float, state: np.ndarray) -> float:
        """Event: velocity = 0 (apogee reached)."""
        return state[1]  # velocity
    apogee_event.terminal = True
    apogee_event.direction = -1  # trigger when velocity goes from + to -

    # Skip if no motor
    if total_impulse_ns <= 0 or burn_time_s <= 0:
        return AscentResult(
            apogee_m=0, apogee_ft=0, burnout_alt_m=0,
            burnout_velocity_mps=0, burnout_time_s=0,
            max_mach=0, max_accel_g=0, timeline=[],
        )

    # Integrate: initial state = [alt=0, vel=0], max time = 600s (10 min)
    sol = solve_ivp(
        derivatives,
        t_span=(0, 600),
        y0=np.array([0.0, 0.0]),
        method="RK45",
        events=apogee_event,
        max_step=0.1,       # 100ms max step for smooth timeline
        rtol=1e-8,
        atol=1e-10,
    )

    if not sol.success and not sol.t_events[0].size:
        # Sim failed to reach apogee — return what we have
        return AscentResult(
            apogee_m=0, apogee_ft=0, burnout_alt_m=0,
            burnout_velocity_mps=0, burnout_time_s=0,
            max_mach=max_mach, max_accel_g=max_accel_g, timeline=[],
        )

    # Build timeline from solution
    burnout_alt_m = 0.0
    burnout_velocity_mps = 0.0
    burnout_time_s_actual = burn_time_s

    for i in range(len(sol.t)):
        t = float(sol.t[i])
        alt_m = float(sol.y[0, i])
        vel_mps = float(sol.y[1, i])

        # Track burnout state
        if t <= burn_time_s:
            burnout_alt_m = alt_m
            burnout_velocity_mps = vel_mps

        mach = mach_number(vel_mps, alt_m)

        timeline.append({
            "t_s": round(t, 3),
            "alt_m": round(alt_m, 2),
            "alt_ft": round(alt_m * FT_PER_M, 1),
            "v_mps": round(vel_mps, 2),
            "v_fps": round(vel_mps * FT_PER_M, 1),
            "mach": round(mach, 3),
            "accel_g": 0,  # would need to recompute; tracked via max
        })

    # Apogee is the last point (terminal event)
    apogee_m = float(sol.y[0, -1])
    apogee_ft = apogee_m * FT_PER_M

    return AscentResult(
        apogee_m=round(apogee_m, 2),
        apogee_ft=round(apogee_ft, 1),
        burnout_alt_m=round(burnout_alt_m, 2),
        burnout_velocity_mps=round(burnout_velocity_mps, 2),
        burnout_time_s=round(burnout_time_s_actual, 3),
        max_mach=round(max_mach, 3),
        max_accel_g=round(max_accel_g, 2),
        timeline=timeline,
    )
