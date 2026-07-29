# recoverysys-engine — agent contract

## Project and commands

- `engine/` is the Python simulation core; `api/` is the FastAPI service (`POST /api/simulate`, `GET /api/health`); `tests/` contains pytest and validation CSVs; `frontend/RecoverySys/` is the React frontend.
- Install and test: `pip install -e ".[dev]"`; `pytest`.
- Run API: `uvicorn api.main:app --reload`.
- Frontend: from `frontend/RecoverySys/`, run `npm install && npm run dev`. Its separate remote (`akhan157/RecoverySys`) deploys via GitHub Actions to Pages; push from that directory only.

## Brain boundary

Use `C:\Users\adnan\Projects\brain\` only for missing domain context, not general coding or facts already in this project. Read `wiki/hot.md`, then `wiki/index.md`, then pages tagged `recoverysys-engine` as needed. Relevant synthesis pages cover parachute reefing, FAA waivers, wind data, and motor thrust curves.

## graphify

Graphify is on-demand only. For a cross-module relationship or architecture question that ordinary repository search cannot answer, use `graphify query`, `graphify path`, or `graphify explain`. Do not preload reports or run `graphify update` automatically; AST-only updates require an explicit request after meaningful code changes.
