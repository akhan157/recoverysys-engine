"""Tests for ISA atmosphere model."""

import pytest
from engine.atmosphere import air_density, speed_of_sound, mach_number


class TestAirDensity:
    def test_sea_level(self):
        assert air_density(0) == pytest.approx(1.225, abs=0.001)

    def test_1000m(self):
        # ISA table: 1.112 kg/m³ at 1000m
        assert air_density(1000) == pytest.approx(1.112, abs=0.01)

    def test_5000m(self):
        # ISA table: 0.7364 kg/m³ at 5000m
        assert air_density(5000) == pytest.approx(0.7364, abs=0.01)

    def test_10000m(self):
        # ISA table: 0.4135 kg/m³ at 10000m
        assert air_density(10000) == pytest.approx(0.4135, abs=0.01)

    def test_clamp_above_11km(self):
        """Stratosphere clamp — density shouldn't go negative."""
        rho = air_density(15000)
        assert rho > 0
        assert rho == air_density(11000)

    def test_negative_altitude(self):
        """Below sea level clamps to 0."""
        assert air_density(-100) == air_density(0)


class TestSpeedOfSound:
    def test_sea_level(self):
        # ISA: 340.3 m/s at sea level
        assert speed_of_sound(0) == pytest.approx(340.3, abs=1.0)

    def test_decreases_with_altitude(self):
        assert speed_of_sound(5000) < speed_of_sound(0)


class TestMachNumber:
    def test_subsonic(self):
        assert mach_number(170, 0) == pytest.approx(0.5, abs=0.02)

    def test_zero_velocity(self):
        assert mach_number(0, 0) == 0.0
