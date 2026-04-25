"""Tests for descent computation."""

import pytest
from engine.stages.descent import compute_descent_rate, compute_descent


class TestDescentRate:
    def test_basic_descent_rate(self):
        """A 60" chute with Cd=1.5 on a 5 kg rocket should give reasonable fps."""
        fps = compute_descent_rate(diameter_in=60, cd=1.5, mass_kg=5.0)
        assert 10 < fps < 30  # typical range for L2

    def test_sea_level_vs_altitude(self):
        """Descent rate should be faster at altitude (thinner air)."""
        sl = compute_descent_rate(60, 1.5, 5.0, altitude_ft=0)
        alt = compute_descent_rate(60, 1.5, 5.0, altitude_ft=5000)
        assert alt > sl

    def test_larger_chute_is_slower(self):
        rate_small = compute_descent_rate(36, 1.5, 5.0)
        rate_large = compute_descent_rate(60, 1.5, 5.0)
        assert rate_large < rate_small

    def test_zero_cd(self):
        assert compute_descent_rate(60, 0, 5.0) == 0.0

    def test_zero_diameter(self):
        assert compute_descent_rate(0, 1.5, 5.0) == 0.0


class TestDescentCompute:
    def test_dual_deploy(self):
        """Standard dual-deploy: drogue to 700ft, then main."""
        result = compute_descent(
            apogee_ft=7000,
            deploy_alt_ft=700,
            drogue_specs={"diameter_in": 18, "cd": 1.55},
            main_specs={"diameter_in": 60, "cd": 1.5},
            mass_kg=5.0,
        )
        assert result.drogue_fps > 30  # drogue is fast
        assert result.main_fps < 25    # main is slow
        assert result.total_time_s > 30
        assert len(result.timeline) > 0

    def test_no_drogue(self):
        """Single deploy: main only from apogee."""
        result = compute_descent(
            apogee_ft=3000,
            deploy_alt_ft=3000,
            drogue_specs=None,
            main_specs={"diameter_in": 60, "cd": 1.5},
            mass_kg=5.0,
        )
        assert result.drogue_fps == 0
        assert result.main_fps > 0
        assert result.phase1_time_s == 0

    def test_zero_apogee(self):
        result = compute_descent(0, 700, None, None, 5.0)
        assert result.total_time_s == 0
