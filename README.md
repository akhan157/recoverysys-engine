# RecoverySys Engine

[![CI](https://github.com/akhan157/recoverysys-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/akhan157/recoverysys-engine/actions/workflows/ci.yml)

Python simulation backend for [RecoverySys](https://github.com/akhan157/RecoverySys),
a recovery planner for high-power rocketry. Given a rocket, a motor, recovery
hardware and a wind profile, it predicts the ascent, the parachute descent,
where the rocket lands, and how widely landing points scatter under wind and
deployment uncertainty.

## What it does

- **Ascent** — vertical 2-DOF powered flight and coast to apogee, integrated
  with SciPy's adaptive-step RK45 solver. Takes an optional thrust curve or a
  constant-thrust approximation derived from total impulse and burn time.
- **Atmosphere** — International Standard Atmosphere troposphere model for air
  density and speed of sound (0–11 km).
- **Descent** — dual-deploy terminal-velocity descent with separate drogue and
  main parachute specifications, plus a descent timeline.
- **Wind drift** — altitude-binned integration through multi-layer winds with
  linear speed and shortest-path direction interpolation, and optional
  great-circle projection to landing coordinates.
- **Monte Carlo** — perturbs wind, apogee and deployment altitude across
  multiprocessing workers, then returns a landing scatter cloud, a 95%
  confidence ellipse fitted by PCA, and P95 drift.
- **API** — FastAPI service exposing health and simulation endpoints.

The engine also parses RASP `.eng` motor files and interpolates thrust curves
(`engine/stages/motor.py`).

## Install

Python 3.10 or newer.

```bash
git clone https://github.com/akhan157/recoverysys-engine.git
cd recoverysys-engine
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Run tests

```bash
pytest
```

## Run the API

```bash
uvicorn api.main:app --reload
```

Endpoints:

- `GET /api/health` — service status
- `POST /api/simulate` — run the full simulation pipeline
- `GET /docs` — interactive OpenAPI documentation

Example request:

```bash
curl -X POST http://127.0.0.1:8000/api/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "rocket_mass_kg": 5.0,
    "motor_total_impulse_ns": 2560,
    "burn_time_s": 1.8,
    "airframe_od_in": 4.0,
    "main_chute": {"diameter_in": 60, "cd": 1.5},
    "drogue_chute": {"diameter_in": 18, "cd": 1.55},
    "wind_layers": [{"altitude_ft": 0, "speed_mph": 8, "direction_deg": 270}],
    "launch_lat": 35.3456,
    "launch_lon": -117.8083
  }'
```

## Project layout

```
api/                 FastAPI application and request/response models
engine/
  atmosphere.py      ISA troposphere constants and helpers
  pipeline.py        End-to-end simulation orchestration
  stages/
    ascent.py        RK45 ascent integration
    descent.py       Drogue and main terminal-velocity descent
    drift.py         Wind-layer interpolation and drift
    monte_carlo.py   Dispersion sampling and confidence ellipse
    motor.py         RASP .eng parsing and thrust interpolation
tests/               Pytest suite and recorded flight data
```

## Model notes

- The atmosphere model is valid from 0 to 11 km; density and speed of sound
  are clamped to that range.
- Drag uses a constant drag coefficient for the airframe, and parachutes are
  modelled at terminal velocity without inflation dynamics.
- Monte Carlo perturbations apply to wind layers, apogee (as a combined proxy
  for motor, mass and drag variation) and deployment altitude; the ascent is
  not re-integrated per iteration.

## Related projects

- [RecoverySys](https://github.com/akhan157/RecoverySys) — the recovery planner frontend
- [recoverysys-surrogate](https://github.com/akhan157/recoverysys-surrogate) — surrogate models for fast predictions

## License

MIT © 2026 Adnan Khan. See [LICENSE](LICENSE).
