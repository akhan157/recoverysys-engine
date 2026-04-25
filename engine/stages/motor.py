"""Motor stage — .eng file parsing and thrust interpolation."""

from __future__ import annotations
from dataclasses import dataclass, field
import re
import numpy as np


@dataclass
class ThrustCurve:
    """Parsed motor thrust curve from RASP .eng format."""
    designation: str
    diameter_mm: float
    length_mm: float
    delays: str
    propellant_kg: float
    total_kg: float
    manufacturer: str
    curve: list[dict]  # [{t: float, thrust_N: float}, ...]
    total_impulse_ns: float = 0.0
    burn_time_s: float = 0.0
    peak_thrust_n: float = 0.0

    def __post_init__(self):
        if self.curve:
            self.peak_thrust_n = max(p["thrust_N"] for p in self.curve)
            self.burn_time_s = self._compute_burn_time()
            self.total_impulse_ns = self._compute_impulse()

    def _compute_burn_time(self) -> float:
        """Time of last non-zero thrust sample."""
        for p in reversed(self.curve):
            if p["thrust_N"] > 0:
                return p["t"]
        return 0.0

    def _compute_impulse(self) -> float:
        """Trapezoidal integration of thrust curve."""
        impulse = 0.0
        for i in range(1, len(self.curve)):
            dt = self.curve[i]["t"] - self.curve[i - 1]["t"]
            f_avg = (self.curve[i]["thrust_N"] + self.curve[i - 1]["thrust_N"]) / 2
            impulse += f_avg * dt
        return impulse


def interpolate_thrust(t: float, curve: list[dict]) -> float:
    """Linear interpolation of thrust at time t from curve points.
    Returns 0 past the end of the curve (motor burned out)."""
    if not curve:
        return 0.0
    if t <= curve[0]["t"]:
        return curve[0]["thrust_N"]
    if t >= curve[-1]["t"]:
        return 0.0
    for i in range(1, len(curve)):
        if t <= curve[i]["t"]:
            lo, hi = curve[i - 1], curve[i]
            frac = (t - lo["t"]) / (hi["t"] - lo["t"])
            return lo["thrust_N"] + frac * (hi["thrust_N"] - lo["thrust_N"])
    return 0.0


def parse_eng(text: str) -> ThrustCurve:
    """Parse RASP .eng format motor file.

    Format:
        ; comments
        designation diameter_mm length_mm delays propellant_kg total_kg manufacturer
        time_s thrust_N
        ...
    """
    lines = text.strip().splitlines()
    header = None
    curve = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            continue

        parts = stripped.split()
        if header is None:
            # Header line
            if len(parts) < 7:
                raise ValueError(f"Invalid .eng header: {stripped}")
            header = {
                "designation": parts[0],
                "diameter_mm": float(parts[1]),
                "length_mm": float(parts[2]),
                "delays": parts[3],
                "propellant_kg": float(parts[4]),
                "total_kg": float(parts[5]),
                "manufacturer": " ".join(parts[6:]),
            }
        else:
            # Data line: time thrust
            if len(parts) >= 2:
                t = float(parts[0])
                thrust = float(parts[1])
                curve.append({"t": t, "thrust_N": thrust})

    if header is None:
        raise ValueError("No header found in .eng file")
    if not curve:
        raise ValueError("No thrust data found in .eng file")

    # Ensure curve starts at t=0
    if curve[0]["t"] > 0:
        curve.insert(0, {"t": 0.0, "thrust_N": 0.0})

    # Ensure times are strictly increasing
    for i in range(1, len(curve)):
        if curve[i]["t"] <= curve[i - 1]["t"]:
            raise ValueError(f"Non-increasing time at sample {i}: {curve[i]['t']}")

    return ThrustCurve(
        designation=header["designation"],
        diameter_mm=header["diameter_mm"],
        length_mm=header["length_mm"],
        delays=header["delays"],
        propellant_kg=header["propellant_kg"],
        total_kg=header["total_kg"],
        manufacturer=header["manufacturer"],
        curve=curve,
    )
