"""FastAPI application — RecoverySys simulation engine API."""

from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from engine.pipeline import SimulationInput, run_simulation

app = FastAPI(
    title="RecoverySys Engine",
    version="0.1.0",
    description="High-fidelity recovery simulation engine for high-power rocketry",
)

# CORS — allow the GitHub Pages frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://akhan157.github.io",
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Request/Response Models ──────────────────────────────────────────


class ChuteSpec(BaseModel):
    diameter_in: float
    cd: float


class WindLayerSpec(BaseModel):
    altitude_ft: float
    speed_mph: float
    direction_deg: float = 0


class ThrustPoint(BaseModel):
    t: float
    thrust_N: float


class MonteCarloConfig(BaseModel):
    enabled: bool = False
    iterations: int = Field(default=500, ge=10, le=5000)
    seed: int | None = None


class SimulateRequest(BaseModel):
    rocket_mass_kg: float = Field(gt=0)
    motor_total_impulse_ns: float = Field(gt=0)
    burn_time_s: float = Field(gt=0)
    airframe_od_in: float = Field(gt=0)
    cd: float = Field(default=0.5, gt=0)

    main_chute: ChuteSpec | None = None
    drogue_chute: ChuteSpec | None = None
    main_deploy_alt_ft: float = Field(default=700, ge=0)

    wind_layers: list[WindLayerSpec] | None = None

    launch_lat: float | None = Field(default=None, ge=-90, le=90)
    launch_lon: float | None = Field(default=None, ge=-180, le=180)

    thrust_curve: list[ThrustPoint] | None = None
    propellant_mass_kg: float | None = None

    monte_carlo: MonteCarloConfig = Field(default_factory=MonteCarloConfig)
    fidelity: str = Field(default="simple", pattern="^(simple|advanced|research)$")


class ErrorResponse(BaseModel):
    error: str
    code: str
    details: dict | None = None


# ── Endpoints ────────────────────────────────────────────────────────


@app.get("/api/health")
def health():
    """Health check for auto-detection by the React frontend."""
    return {"status": "ok", "engine": "recoverysys", "version": "0.1.0"}


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    """Run a full simulation pipeline."""
    try:
        inputs = SimulationInput(
            rocket_mass_kg=req.rocket_mass_kg,
            motor_total_impulse_ns=req.motor_total_impulse_ns,
            burn_time_s=req.burn_time_s,
            airframe_od_in=req.airframe_od_in,
            cd=req.cd,
            main_chute=req.main_chute.model_dump() if req.main_chute else None,
            drogue_chute=req.drogue_chute.model_dump() if req.drogue_chute else None,
            main_deploy_alt_ft=req.main_deploy_alt_ft,
            wind_layers=[w.model_dump() for w in req.wind_layers] if req.wind_layers else None,
            launch_lat=req.launch_lat,
            launch_lon=req.launch_lon,
            thrust_curve=[p.model_dump() for p in req.thrust_curve] if req.thrust_curve else None,
            propellant_mass_kg=req.propellant_mass_kg,
            monte_carlo_enabled=req.monte_carlo.enabled,
            monte_carlo_iterations=req.monte_carlo.iterations,
            monte_carlo_seed=req.monte_carlo.seed,
            fidelity=req.fidelity,
        )
        result = run_simulation(inputs)
        return {
            "ascent": result.ascent,
            "descent": result.descent,
            "drift": result.drift,
            "monte_carlo": result.monte_carlo,
            "shock_load": result.shock_load,
            "warnings": result.warnings,
            "fidelity_used": result.fidelity_used,
            "compute_time_ms": result.compute_time_ms,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "code": "SIM_FAILURE", "details": None},
        )
