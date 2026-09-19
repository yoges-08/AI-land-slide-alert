# LANDSAFE-NER — National Landslide & Multi-Hazard Watch

An AI-based landslide and multi-hazard monitoring platform covering all 726
districts of India (28 states + 8 UTs), built on top of the original
LANDSAFE-NER prototype (`backend/`, `frontend/original-react-components/`).

## What's in this folder

```
frontend/
  landsafe-dashboard.html      ← the working app. Open this file directly in
                                  a browser — no server, no build step needed.
  build.py                     ← rebuilds landsafe-dashboard.html from src/
  src/
    01_head.html                Tailwind (statically compiled, no CDN
                                 dependency) + design tokens + layout CSS
    02_body.html                Sidebar, header, cascade filter, six tabs
                                 (Dashboard, Live Map, Risk Analysis, Weather,
                                 Alerts, Field Reports, Recommendations)
    03_store_forecast_alerts.js Field-report storage (with offline queue),
                                 the forecast function, alert message
                                 templates (5 languages), dispatch channels
    04_engine.js                The hazard model: hydrology simulation,
                                 slope-stability physics, the learned
                                 susceptibility×trigger model, SHAP
                                 attribution, flood/GLOF scoring
    05_map.js                   SVG choropleth map: projection, pan/zoom,
                                 layers, overlays, tooltips
    06_ui.js                    Everything that wires the engine to the DOM:
                                 tabs, cards, charts, modals, event binding
  data/
    geo_data.json                Projected district geometry + terrain
                                  attributes for all 726 districts (built by
                                  build_geo.py from public boundary data)
    ne_india_locations.json      The original 304 field-validated monitoring
                                  sites from the source repo — used as
                                  ground-truth overrides
    build_geo.py                  Regenerates geo_data.json if you want to
                                  change the terrain/physiography model or
                                  pull fresh boundary data

backend/                        The original FastAPI service (unmodified) —
                                 weather/satellite/ML services, DB models,
                                 the pre-trained XGBoost models. Not yet
                                 wired to the new engine — see "Next step"
                                 below.

frontend/original-react-components/
                                 The original React components this project
                                 replaced. Kept for reference — the sidebar
                                 layout, card styles, and tab structure in
                                 the new HTML dashboard were built to match
                                 these.
```

## Running it

**Just the dashboard:** open `frontend/landsafe-dashboard.html` in any
browser. It's fully self-contained — the risk model, the map data, and a
deterministic weather/satellite simulator are all inlined, so it runs with
no backend, no network, and no build step.

**After editing the source:**
```bash
cd frontend
python3 build.py
```
This re-reads everything in `src/` and `data/geo_data.json` and rewrites
`landsafe-dashboard.html`. It's a straight concatenation — no bundler, no
npm install.

**Changing the terrain data:**
```bash
cd frontend/data
python3 build_geo.py     # needs: pip install shapely
```
This pulls district boundaries, classifies each district's physiography
(Himalayan zones, Western/Eastern Ghats, plateau, plains, etc.), computes
slope/elevation/lithology, and folds in the 304 field-validated sites from
`ne_india_locations.json` as overrides. Regenerates `geo_data.json`.

## How the risk model works

Two independent models run on every district, every simulated hour, and are
blended 45/55:

1. **Slope-stability physics** — an infinite-slope factor-of-safety
   calculation with partial saturation, depth-scaled root cohesion, and a
   pseudo-static seismic term.
2. **A learned susceptibility × trigger model** — terrain/lithology/exposure
   factors (susceptibility) multiplied against rainfall/saturation/melt
   factors (trigger), since a steep dry cliff and a saturated flat plain are
   both stable — hazard is genuinely an interaction, not a sum. Comes with
   exact SHAP-style attribution (`04_engine.js`, `score()`).

Districts are split into three tiers: **Tier 1** (full monitoring — Himalaya,
NE fold belt, Western/Eastern Ghats), **Tier 2** (screening only), and
**Tier 3** (plains — the model deliberately withholds a landslide score
rather than publish an uncalibrated one).

## Honest status against the original brief

See the **Recommendations** tab in the running app for the full breakdown.
Short version: the GIS dashboard, predictive engine, field reporting, and
automated multilingual alerting are built and working. IMD/satellite/sensor
integration and cloud offline-sync are simulated here and need the next
step below to become real.

## Next step: wiring this to real data

Everything in `frontend/` runs on a deterministic weather/satellite
simulator (`Met` in `04_engine.js`) so the page works standalone. To go from
prototype to production:

1. Port `04_engine.js`'s hydrology + scoring logic into
   `backend/app/services/` (Python), replacing the simulator's `Met.rain()`
   / `Met.temp()` with real IMD/Open-Meteo/GPM calls.
2. Retrain the susceptibility weights against NRSC's Landslide Atlas and
   state SDMA incident logs instead of the physically-reasoned but
   synthetic weights used here.
3. Point the frontend at that backend instead of running the simulator
   in-browser.

## Not an official warning system

This is an academic/demonstration prototype. Risk thresholds, alert
templates, and reach estimates are for demonstration only and must not be
used for real-world emergency decisions.
