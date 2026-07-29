# RecoverySys — Session Context
_Last updated: 2026-05-06. Time-sensitive items are dated — treat anything marked with a date in the past as historical context, not active priority._

## ⏱ Time-sensitive (expires 2026-05-07)
Polish pass on the current frontend tonight. No major restructuring — tighten what exists, enforce DESIGN.md spec, fix rough edges. Must be shippable for presentation on 2026-05-07.

## Two-Phase Frontend Plan

### Phase 1 — Polish current (TONIGHT)
- Branch: `redesign`
- Keep existing React structure and routing
- Enforce `docs/DESIGN.md` spec (typography, color tokens, spacing scale, component rules)
- Skills to use: `/redesign-skill`, `/impeccable`, `/brutalist-skill`
- Goal: presentation-ready by end of tonight

### Phase 2 — Scratch redesign (after presentation)
- Blank slate, no constraints from current codebase
- Skills: `/ui-ux-pro-max` for design system, `/taste-skill` or `/soft-skill` for build
- Separate branch or repo

## Design North Star
Engineering instrument aesthetic — oscilloscope/MATLAB/terminal, NOT SaaS.
Full spec: `docs/DESIGN.md`

## Installed Design Skills (global)
- `/impeccable` — anti-cookie-cutter, from Anthropic's frontend-design skill
- `/redesign-skill` — upgrades existing apps
- `/brutalist-skill` — raw mechanical interfaces (closest to engineering instrument aesthetic)
- `/taste-skill` — typography/layout/motion/spacing
- `/soft-skill` — high-end agency style
- `/ui-ux-pro-max` — design system generator (Phase 2)
- `/gpt-tasteskill` — advanced GSAP motion

## Project Structure
```
engine/       Python sim core (RK45, atmosphere, stages)
api/          FastAPI — POST /api/simulate, GET /api/health
tests/        pytest + Jackpot launch validation data
docs/         DESIGN.md (UI spec), TODOS.md (v2 roadmap), session-context.md
frontend/     React/JS frontend → akhan157/RecoverySys on GitHub Pages
```

## Deployment Plan
- Frontend: GitHub Pages (stays)
- Backend: Render free tier (not deployed yet)
- CORS already configured in api/main.py for akhan157.github.io
- Health check fallback: frontend hits /api/health, falls back to JS sim if cold

## Simulation Status
- Current JS sim: good for chute sizing + rough shock load, instantaneous opening model
- Python engine: better apogee accuracy (RK45), shock load model is simpler than JS
- Neither has dynamic snatch force — that's the v2 upgrade to decide on after presentation
