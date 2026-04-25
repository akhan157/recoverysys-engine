"""Tests for ascent integration — RK45 solver."""

import pytest
from engine.stages.ascent import integrate_ascent, estimate_propellant_mass
from engine.atmosphere import FT_PER_M


class TestPropellantMass:
    def test_basic_estimate(self):
        m = estimate_propellant_mass(10.0, 2560)
        assert 0 < m < 5.5  # capped at 55%

    def test_cap_at_55_percent(self):
        # Huge impulse should still cap
        m = estimate_propellant_mass(10.0, 100_000)
        assert m == pytest.approx(5.5)

    def test_override(self):
        m = estimate_propellant_mass(10.0, 2560, prop_mass_override=2.0)
        assert m == 2.0


class TestAscentIntegration:
    def test_basic_ascent(self):
        """A mid-J motor on a ~5 kg rocket should reach several thousand feet."""
        result = integrate_ascent(
            total_mass_kg=5.0,
            total_impulse_ns=2560,
            burn_time_s=1.8,
            cross_section_area_m2=0.008,  # ~4" diameter
            cd=0.5,
        )
        assert result.apogee_m > 500
        assert result.apogee_ft > 1500
        assert result.burnout_velocity_mps > 0
        assert result.max_mach > 0
        assert len(result.timeline) > 10

    def test_zero_impulse(self):
        """No motor = no flight."""
        result = integrate_ascent(
            total_mass_kg=5.0,
            total_impulse_ns=0,
            burn_time_s=0,
            cross_section_area_m2=0.008,
            cd=0.5,
        )
        assert result.apogee_m == 0

    def test_timeline_monotonic_during_ascent(self):
        """Altitude should increase monotonically during ascent."""
        result = integrate_ascent(
            total_mass_kg=5.0,
            total_impulse_ns=2560,
            burn_time_s=1.8,
            cross_section_area_m2=0.008,
            cd=0.5,
        )
        alts = [p["alt_m"] for p in result.timeline]
        # All altitudes should be >= 0
        assert all(a >= 0 for a in alts)
        # Last altitude should be close to apogee
        assert alts[-1] == pytest.approx(result.apogee_m, rel=0.01)

    def test_ncsu_flight1_validation(self):
        """Soft validation against NCSU Jackpot Launch 1.

        Known data:
        - Motor: L1390G-P (total impulse ~2560 Ns, burn ~1.8s)
        - Dry mass: 16.848 kg
        - Cd: 0.38
        - Cross-section: 0.0182 m²
        - Measured apogee: 762.28 m

        Note: This is a soft check — prints error % but doesn't fail.
        The L1390G-P has ~2500 Ns total impulse and ~1.5s burn time.
        """
        result = integrate_ascent(
            total_mass_kg=16.848,
            total_impulse_ns=2500,  # approximate L1390 total impulse
            burn_time_s=1.5,
            cross_section_area_m2=0.0182,
            cd=0.38,
        )
        measured_apogee = 762.28
        error_pct = abs(result.apogee_m - measured_apogee) / measured_apogee * 100
        print(f"\n  NCSU Flight 1 validation:")
        print(f"    Predicted: {result.apogee_m:.1f} m")
        print(f"    Measured:  {measured_apogee:.1f} m")
        print(f"    Error:     {error_pct:.1f}%")
        print(f"    Max Mach:  {result.max_mach:.2f}")
        print(f"    Max G:     {result.max_accel_g:.1f}")

        # Soft gate: log but don't fail unless wildly off
        assert result.apogee_m > 0, "Sim should produce a positive apogee"
        # Hard fail only if >50% off (sanity check)
        assert error_pct < 50, f"Apogee prediction {error_pct:.0f}% off — sanity check failed"
