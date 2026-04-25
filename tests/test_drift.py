"""Tests for drift computation and wind interpolation."""

import pytest
import math
from engine.stages.drift import (
    interpolate_wind, project_point, compute_drift, WindLayer,
)


class TestWindInterpolation:
    def test_single_layer(self):
        layers = [WindLayer(0, 10, 270)]
        wind = interpolate_wind(500, layers)
        assert wind["speed_mph"] == 10
        assert wind["direction_deg"] == 270

    def test_linear_interpolation(self):
        layers = [WindLayer(0, 10, 0), WindLayer(1000, 20, 0)]
        wind = interpolate_wind(500, layers)
        assert wind["speed_mph"] == pytest.approx(15, abs=0.1)

    def test_direction_wrapping(self):
        """Wind direction should interpolate via shortest path around 360."""
        layers = [WindLayer(0, 10, 350), WindLayer(1000, 10, 10)]
        wind = interpolate_wind(500, layers)
        # Should go 350 → 360/0 → 10, not 350 → 180 → 10
        assert wind["direction_deg"] == pytest.approx(0, abs=1)

    def test_below_lowest_layer(self):
        layers = [WindLayer(1000, 15, 90)]
        wind = interpolate_wind(0, layers)
        assert wind["speed_mph"] == 15

    def test_above_highest_layer(self):
        layers = [WindLayer(0, 10, 90)]
        wind = interpolate_wind(10000, layers)
        assert wind["speed_mph"] == 10


class TestGeoProjection:
    def test_northward_displacement(self):
        lat, lon = project_point(35.0, -117.0, 0, 1000)  # 1km north
        assert lat > 35.0
        assert lon == pytest.approx(-117.0, abs=0.001)

    def test_eastward_displacement(self):
        lat, lon = project_point(35.0, -117.0, 90, 1000)  # 1km east
        assert lat == pytest.approx(35.0, abs=0.001)
        assert lon > -117.0

    def test_zero_distance(self):
        lat, lon = project_point(35.0, -117.0, 45, 0)
        assert lat == pytest.approx(35.0)
        assert lon == pytest.approx(-117.0)


class TestDriftCompute:
    def test_basic_drift(self):
        result = compute_drift(
            apogee_ft=5000,
            deploy_alt_ft=700,
            drogue_fps=80,
            main_fps=17,
            wind_layers=[WindLayer(0, 10, 270)],
            launch_lat=35.0,
            launch_lon=-117.0,
        )
        assert result.drift_ft > 0
        assert result.landing_lat is not None

    def test_no_wind_no_drift(self):
        result = compute_drift(
            apogee_ft=5000,
            deploy_alt_ft=700,
            drogue_fps=80,
            main_fps=17,
            wind_layers=[WindLayer(0, 0, 0)],
        )
        assert result.drift_ft == pytest.approx(0, abs=0.1)

    def test_stronger_wind_more_drift(self):
        r_light = compute_drift(5000, 700, 80, 17, [WindLayer(0, 5, 270)])
        r_heavy = compute_drift(5000, 700, 80, 17, [WindLayer(0, 20, 270)])
        assert r_heavy.drift_ft > r_light.drift_ft
