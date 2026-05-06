# recoverysys-engine

Full RecoverySys project — monorepo layout:

```
engine/          Python simulation core (atmosphere, pipeline, stages)
api/             FastAPI service — POST /api/simulate, GET /api/health
tests/           pytest + validation CSVs (Jackpot launch data)
docs/            DESIGN.md (UI spec), TODOS.md (v2 roadmap)
frontend/        React/JS frontend → deploys to GitHub Pages (akhan157/RecoverySys)
                 frontend has its own git remote — push from inside frontend/
```

Build/test (engine):
- `pip install -e ".[dev]"`
- `pytest`

Run API locally:
- `uvicorn api.main:app --reload`

Frontend (cd into frontend/ first):
- `cd frontend/RecoverySys && npm install && npm run dev`
- Deploy: push to akhan157/RecoverySys — GitHub Actions handles Pages deploy

## Wiki Knowledge Base

Path: `C:\Users\adnan\Projects\brain\`

When you need context not already in this project (recoverysys-engine domain knowledge: parachute reefing, FAA waivers, wind data, motor thrust curves, NY-region launch sites, etc.):

1. Read `wiki/hot.md` first (recent context, ~500 words)
2. If not enough, read `wiki/index.md`
3. For domain specifics, filter wiki pages by tag `recoverysys-engine` (search frontmatter `tag: recoverysys-engine` across `wiki/`)
4. Only then read individual wiki pages

Entry-point synthesis pages for recoverysys-engine:
- `Research- parachute reefing for amateur rocketry recovery systems`
- `Research- FAA waivers and airspace authorizations for amateur high-power rocketry`
- `Research- Wind data and forecasting for amateur high-power rocketry`
- `Research- motor thrust curves for amateur high-power rocketry`

Do NOT read the wiki for general coding questions or things already in this project.

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)
