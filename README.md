# RecoverySys Engine

High-power rocketry recovery simulation engine. Given motor specs and recovery hardware, it predicts apogee, descent rates, drift, and landing scatter.

**Physics pipeline:** Motor → Ascent (RK45) → Descent → Drift → Monte Carlo

---

## What it does

- **Ascent** — integrates powered flight + coast to apogee using scipy's RK45 ODE solver with ISA atmosphere and altitude-dependent air density. Supports thrust curves or constant-thrust fallback.
- **Descent** — two-phase: drogue (apogee → main deploy altitude) and main (deploy altitude → landing). Computes terminal velocity for each chute from drag area.
- **Drift** — altitude-banded wind layers, each with speed/direction. Tracks drift through drogue and main phases separately.
- **Monte Carlo** — scatter analysis over N runs with randomized wind and Cd perturbations. Returns p95 drift radius and a 1-σ ellipse.
- **Shock load** — static ejection shock estimate (20g for mid-power, 30g for L3-class rockets).

---

## Requirements

- Python 3.10+
- numpy, scipy, fastapi, uvicorn, pydantic

---

## Install

```bash
pip install -e ".[dev]"
```

---

## Run the API

```bash
uvicorn api.main:app --reload
```

API available at `http://localhost:8000`. Interactive docs at `/docs`.

---

## Endpoints

### `GET /api/health`

```json
{"status": "ok", "engine": "recoverysys", "version": "0.1.0"}
```

### `POST /api/simulate`

Minimal request (no chutes, no wind):

```bash
curl -X POST http://localhost:8000/api/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "rocket_mass_kg": 4.5,
    "motor_total_impulse_ns": 1280,
    "burn_time_s": 2.1,
    "airframe_od_in": 3.0
  }'
```

Full request with dual-deploy and wind:

```json
{
  "rocket_mass_kg": 4.5,
  "motor_total_impulse_ns": 1280,
  "burn_time_s": 2.1,
  "airframe_od_in": 3.0,
  "cd": 0.5,
  "main_chute": {"diameter_in": 72, "cd": 2.2},
  "drogue_chute": {"diameter_in": 18, "cd": 1.5},
  "main_deploy_alt_ft": 700,
  "wind_layers": [
    {"altitude_ft": 0,    "speed_mph": 5,  "direction_deg": 270},
    {"altitude_ft": 3000, "speed_mph": 12, "direction_deg": 285},
    {"altitude_ft": 8000, "speed_mph": 20, "direction_deg": 300}
  ],
  "launch_lat": 41.35,
  "launch_lon": -74.65,
  "monte_carlo": {"enabled": true, "iterations": 500}
}
```

Response shape:

```json
{
  "ascent": {
    "apogee_ft": 4821.3,
    "apogee_m": 1469.5,
    "max_mach": 0.412,
    "max_acceleration_g": 8.3,
    "timeline": [...]
  },
  "descent": {
    "drogue_fps": 68.1,
    "main_fps": 14.2,
    "total_time_s": 112.4
  },
  "drift": {
    "distance_ft": 1340,
    "bearing_deg": 87.2,
    "landing": {"lat": 41.351, "lon": -74.643}
  },
  "monte_carlo": {
    "p95_drift_ft": 1820,
    "ellipse": {"semi_major_ft": 910, "semi_minor_ft": 430, "bearing_deg": 85}
  },
  "shock_load": {"g_factor": 20, "peak_force_n": 882, "peak_force_lbs": 198},
  "warnings": [],
  "compute_time_ms": 34.1
}
```

---

## Tests

```bash
pytest
```

---

## Project structure

```
engine/
  atmosphere.py        ISA atmosphere model (air density, speed of sound)
  pipeline.py          Orchestrates all stages into a single run
  stages/
    motor.py           Thrust curve interpolation
    ascent.py          RK45 powered flight + coast integration
    descent.py         Terminal velocity for drogue and main
    drift.py           Altitude-banded wind drift
    monte_carlo.py     Scatter analysis + confidence ellipse
api/
  main.py              FastAPI app — POST /api/simulate, GET /api/health
tests/                 pytest + validation CSVs
docs/
  DESIGN.md            UI design spec (engineering instrument aesthetic)
  TODOS.md             v2 roadmap (altitude-dependent wind, thrust curve DB)
```

---

## Fidelity modes

| Mode       | Description |
|------------|-------------|
| `simple`   | Constant-thrust ascent, fixed Cd, single wind speed |
| `advanced` | Thrust curve integration, altitude-banded wind |
| `research` | Monte Carlo enabled by default |

---

## License

MIT
