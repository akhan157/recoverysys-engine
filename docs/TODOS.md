# TODOS.md — RecoverySys
Last updated: 2026-03-22 by /plan-eng-review

## v2 — Physics & Simulation

### TODO: Altitude-dependent wind model
**What:** Replace the single `wind_speed_mph` input with an altitude-banded wind profile.
**Why:** Current drift formula (`drift_ft = apogee_ft / rate × wind_fps`) uses a constant wind speed (converted from `wind_speed_mph` input) from launch to landing. Real wind varies significantly with altitude — apogee wind can be 3-5x ground wind. This causes drift prediction errors on high-altitude flights.
**Pros:** More accurate drift prediction; matches ARS reference engine's wind model.
**Cons:** Adds a new UI input (wind profile instead of single speed); increases form complexity.
**Context:** ARS reference engine (`Jeffrey Version`) reads altitude-dependent wind from `FAR_Trip_3_Wind.xlsx` with meridional and zonal components. v2 could add a "Wind Profile" input with altitude-banded speeds (e.g., 0-1000ft, 1000-5000ft, 5000ft+). The parts DB schema change is zero — this is purely a `rocket_specs` + physics engine change.
**Depends on / blocked by:** v1 must ship before this work begins. No technical blockers within v2.

---

### TODO: Accurate apogee via thrust-curve integration
**What:** Replace the `(impulse/mass) × 0.5` heuristic with numerical integration of the powered flight phase using motor thrust curves.
**Why:** The v1 heuristic has ±30% error. For an L3 flyer trying to hit a specific field or stay within a flight zone, 30% error on a 5000ft apogee = ±1500ft. That's the difference between a field and a tree line.
**Pros:** Eliminates the ±30% label from the UI; enables meaningful apogee prediction; unlocks Monte Carlo sims; enables RocketPy integration.
**Cons:** Requires a motor parts category (manufacturers, designations, thrust curves — significant data entry); adds powered-phase simulation complexity.
**Context:** v1 uses `motor_total_impulse_ns` as a user-entered scalar. v2 needs a `motors` parts category with thrust curve data (ThrustCurve.org has this in RASP format). The physics engine adds a `simulate_ascent()` function alongside the existing `simulate_descent()`. This also enables RocketPy integration (RocketPy has built-in motor thrust curve support).
**Depends on / blocked by:** Motor parts category (new DB entries + new parts.specs schema for motors).

---

## v2 — Ops & Maintenance

### TODO: Parts DB admin interface
**What:** A lightweight way to update parts.specs JSONB when manufacturers update specs.
**Why:** The v1 parts DB is seeded via SQL/Alembic seed data and changes only on deploy. When Featherweight releases a Raven4 firmware update that changes voltage range, or Fruity Chutes repackages their 36" chute, the DB goes stale. Currently requires a developer to write SQL.
**Pros:** Non-developer (e.g., domain expert) can keep parts up to date without touching code; reduces time-to-accuracy when specs change.
**Cons:** Builds another surface to maintain; requires access control.
**Context:** Supabase Table Editor can already edit JSONB fields directly — this may be sufficient for v2. If not, a simple password-protected FastAPI admin endpoint (POST /admin/parts) with a hardcoded admin token from environment variable is the minimal solution. No separate admin UI framework needed.
**Depends on / blocked by:** v1 ship. Supabase Table Editor may already cover this — evaluate at v1 launch before building.
