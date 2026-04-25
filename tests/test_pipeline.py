"""Integration tests for the full simulation pipeline."""

import pytest
from engine.pipeline import SimulationInput, run_simulation


class TestPipelineBasic:
    def test_full_dual_deploy_sim(self):
        """Full pipeline: L2 rocket with dual-deploy recovery."""
        inputs = SimulationInput(
            rocket_mass_kg=5.0,
            motor_total_impulse_ns=2560,
            burn_time_s=1.8,
            airframe_od_in=4.0,
            cd=0.5,
            main_chute={"diameter_in": 60, "cd": 1.5},
            drogue_chute={"diameter_in": 18, "cd": 1.55},
            main_deploy_alt_ft=700,
            wind_layers=[
                {"altitude_ft": 0, "speed_mph": 8, "direction_deg": 270},
                {"altitude_ft": 5000, "speed_mph": 15, "direction_deg": 250},
            ],
            launch_lat=35.3456,
            launch_lon=-117.8083,
        )
        result = run_simulation(inputs)

        # Ascent
        assert result.ascent["apogee_ft"] > 3000
        assert result.ascent["max_mach"] > 0
        assert len(result.ascent["timeline"]) > 10

        # Descent
        assert result.descent["drogue_fps"] > 30
        assert result.descent["main_fps"] > 5
        assert result.descent["main_fps"] < 30
        assert result.descent["total_time_s"] > 30

        # Drift
        assert result.drift is not None
        assert result.drift["distance_ft"] > 0
        assert result.drift["landing"]["lat"] is not None

        # Shock load
        assert result.shock_load["peak_force_lbs"] > 0

        # Meta
        assert result.compute_time_ms > 0
        assert len(result.warnings) == 0 or isinstance(result.warnings, list)

    def test_monte_carlo(self):
        """Monte Carlo with small iteration count for speed."""
        inputs = SimulationInput(
            rocket_mass_kg=5.0,
            motor_total_impulse_ns=2560,
            burn_time_s=1.8,
            airframe_od_in=4.0,
            cd=0.5,
            main_chute={"diameter_in": 60, "cd": 1.5},
            drogue_chute={"diameter_in": 18, "cd": 1.55},
            main_deploy_alt_ft=700,
            wind_layers=[
                {"altitude_ft": 0, "speed_mph": 8, "direction_deg": 270},
            ],
            launch_lat=35.3456,
            launch_lon=-117.8083,
            monte_carlo_enabled=True,
            monte_carlo_iterations=50,
            monte_carlo_seed=42,
        )
        result = run_simulation(inputs)

        assert result.monte_carlo is not None
        assert result.monte_carlo["iterations"] > 0
        assert len(result.monte_carlo["scatter"]) > 0
        assert result.monte_carlo["ellipse"] is not None
        assert result.monte_carlo["p95_drift_ft"] > 0

    def test_reproducible_monte_carlo(self):
        """Same seed should produce identical results."""
        inputs = SimulationInput(
            rocket_mass_kg=5.0,
            motor_total_impulse_ns=2560,
            burn_time_s=1.8,
            airframe_od_in=4.0,
            cd=0.5,
            main_chute={"diameter_in": 60, "cd": 1.5},
            drogue_chute={"diameter_in": 18, "cd": 1.55},
            main_deploy_alt_ft=700,
            wind_layers=[{"altitude_ft": 0, "speed_mph": 8, "direction_deg": 270}],
            launch_lat=35.3456,
            launch_lon=-117.8083,
            monte_carlo_enabled=True,
            monte_carlo_iterations=20,
            monte_carlo_seed=12345,
        )
        r1 = run_simulation(inputs)
        r2 = run_simulation(inputs)
        assert r1.monte_carlo["p95_drift_ft"] == r2.monte_carlo["p95_drift_ft"]

    def test_ncsu_flight1_full_pipeline(self):
        """Soft validation: NCSU Jackpot Launch 1 through full pipeline."""
        inputs = SimulationInput(
            rocket_mass_kg=16.848,
            motor_total_impulse_ns=2500,
            burn_time_s=1.5,
            airframe_od_in=6.0,  # ~152mm diameter from metadata
            cd=0.38,
            main_chute={"diameter_in": 60, "cd": 1.5},  # assumed
            main_deploy_alt_ft=700,
            wind_layers=[
                {"altitude_ft": 0, "speed_mph": 3.4, "direction_deg": 22},  # NNE 5.5 km/h
            ],
            launch_lat=35.17583,
            launch_lon=-76.82823,
        )
        result = run_simulation(inputs)

        measured_apogee_m = 762.28
        predicted_m = result.ascent["apogee_m"]
        error_pct = abs(predicted_m - measured_apogee_m) / measured_apogee_m * 100

        print(f"\n  NCSU Flight 1 — Full Pipeline:")
        print(f"    Apogee:  {predicted_m:.1f} m predicted vs {measured_apogee_m:.1f} m measured ({error_pct:.1f}% error)")
        print(f"    Descent: {result.descent['main_fps']:.1f} ft/s main")
        print(f"    Drift:   {result.drift['distance_ft']:.0f} ft" if result.drift else "    Drift:   N/A")
        print(f"    Time:    {result.compute_time_ms:.0f} ms")

        assert predicted_m > 0
        assert error_pct < 50  # sanity gate
