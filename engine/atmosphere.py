"""International Standard Atmosphere (ISA) — troposphere model."""

import numpy as np

# Constants
G = 9.81          # m/s²
FT_PER_M = 3.28084
M_PER_FT = 1 / FT_PER_M
N_PER_LBF = 4.44822
LBF_PER_N = 1 / N_PER_LBF
MPH_TO_MPS = 0.44704
MPH_TO_FPS = 5280 / 3600
RHO_SL = 1.225    # kg/m³ sea-level density
T_SL = 288.15     # K sea-level temperature
LAPSE_RATE = 0.0065  # K/m tropospheric lapse rate
R_EARTH = 6_371_000  # m mean Earth radius


def air_density(alt_m: float) -> float:
    """ISA troposphere density in kg/m³. Valid 0-11,000 m."""
    alt_clamped = np.clip(alt_m, 0, 11_000)
    T = T_SL - LAPSE_RATE * alt_clamped
    return RHO_SL * (T / T_SL) ** 4.256


def speed_of_sound(alt_m: float) -> float:
    """Speed of sound in m/s at altitude (ISA troposphere)."""
    alt_clamped = np.clip(alt_m, 0, 11_000)
    T = T_SL - LAPSE_RATE * alt_clamped
    return 20.05 * np.sqrt(T)  # sqrt(gamma * R * T) simplified


def mach_number(velocity_mps: float, alt_m: float) -> float:
    """Mach number at given velocity and altitude."""
    a = speed_of_sound(alt_m)
    return abs(velocity_mps) / a if a > 0 else 0.0
