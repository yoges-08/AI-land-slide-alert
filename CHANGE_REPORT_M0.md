# M0 — Baseline + cleanup. Change report

**Status:** complete. 62 tests passing, 0 failing.
**Scope:** defects 1–8 from the brief, plus the extra fabrication surfaces found
in `INSPECTION_REPORT.md`. No ingestion, no database — those are M1–M4.

---

## 1. Tests

```
$ python -m pytest
62 passed in 20.8s
```

| File | Tests | Covers |
|---|---|---|
| `tests/test_contract_api.py` | 23 | Every route: 15 `/api` operations + `/` + `/health`. Pins path, status and identity keys. Must stay green to M12. |
| `tests/test_weather_service.py` | 9 | Defects 2 and 3, fixture-driven |
| `tests/test_m0_no_fabrication.py` | 30 | Every fabrication path is closed |

**No test touches the network.** `conftest.no_network` monkeypatches `httpx` to
raise, so the NO DATA path is exercised deterministically rather than relying on
a machine happening to be offline.

**Route count verified from the OpenAPI spec:** 14 paths, 15 operations
(`/api/alerts` carries GET and POST). Identical to baseline. Nothing was lost.

---

## 2. Defects closed

### Defect 3 — rainfall window (fixed first, as instructed)

`weather_service.parse_open_meteo_response()` now slices `hourly` by
`hourly["time"]` against the response's own `current.time`, instead of taking
`hourly_precip[-24:]`. Position-based slicing cannot tell past from future;
timestamp comparison can.

Proof, from `test_rainfall_24h_uses_the_window_ending_now_not_the_forecast_tail`
— the fixture puts 100 mm in the 24 h ending now and 500 mm in the final
forecast day:

| | baseline | now |
|---|---|---|
| reported `rainfall_24h` | **500.0 mm** | **100.0 mm** |

A second test changes only the forecast tail (0 mm vs 900 mm) and asserts the
observed total does not move. The 5-day forecast now starts at the real current
date; baseline labelled day +2 as "Today".

`rainfall_trend_7d` was already correct and is unchanged.

### Defect 2 — fallback values

`get_fallback_weather()` is **deleted**. A test asserts the function no longer
exists. Unreachable source now returns `status: OFFLINE` with every observed
field `null`, a `reason`, and `last_success_at` when we have ever had one.
Timeout raised 4 s → 15 s with 2 retries and exponential backoff, because a slow
response silently becoming fabricated data was half the problem.

Your addition was right and I had missed it: the same fabrication sat in the
**schema**. `WeatherRecord.temperature=22.0 / humidity=75.0` and
`SatelliteFeature.bare_soil_pct=15.0 / vegetation_index=0.65` are now nullable
with no default. So is `LocationResponse.rainfall_24h`, which was defaulting to
`12.0` and thereby serving an invented rainfall observation for all 304 sites.

### Defect 1 — invented satellite indices

`compute_satellite_indices()` moved verbatim to `backend/demo/fake_satellite.py`,
which calls `require_demo_mode()` at import and **raises** under
`LANDSAFE_MODE=production`. A test asserts the import fails; a second test walks
every file in `backend/app/` and fails the build on any module-scope
`import backend.demo`.

Production `get_satellite_observation()` returns `NO_DATA` naming the pending
source and milestone. The false `"NASA MODIS / Sentinel-2 & Sentinel-1"` label
and the `"Near-real-time … automated batch pipeline"` disclaimer are gone, and a
test greps the response to keep them gone. The dead `"Assam" in str(lat)` branch
was dropped.

### Defect 4 — hardcoded alerts

Six literal alerts and the `"2 hours ago"` strings are gone. The store starts
**empty**, `created_at` is a timezone-aware ISO-8601 timestamp, and each alert
carries its inputs plus the advisory notice.

`evaluate_threshold_breach()` now **refuses to evaluate** without an observed
rainfall value. This was the worst path in the codebase: it consumed the
hardcoded 142 mm and emitted *"Critical … 98% due to 142.0mm rainfall"*. Two
tests pin it — one that no alert fires with weather OFFLINE, one that a real
130 mm observation does fire and records `observed_at`.

### Defect 5 — random seed data

The loader strips 17 `random`-derived fields before any record reaches a
response or a model. Each record is classified `CURATED_SEED` (~120 hand-entered
sites with real coordinates and lithology) or `SYNTHETIC_SEED` (the
coordinate-jittered `Sector-N` copies), and carries `data_status: NO_DATA`. A
test confirms the raw file still holds the random values and the loader removes
them. The `/api/locations` `risk` filter returns empty rather than filtering on
a value that does not exist. README's "field-validated" claim is corrected in
place, with the correction recorded rather than quietly deleted.

### Defect 6 — synthetic-label model

Per your note, the SHAP wiring in `ml_service.py` and the `main.py` startup hook
are real infrastructure and are **kept untouched**. Only the claims changed:

- `risk_probability` → `hazard_index`, `flood_risk_probability` → `flood_index`,
  `delta_risk` → `delta_index`. No "probability", "confidence" or "%" anywhere.
- Every response carries `calibration: UNCALIBRATED`,
  `training_data: SYNTHETIC`, `validated_against_observed_events: false`.
- A failed flood inference returns `None` instead of substituting `0.15`.
- Key-factor bars return `None` where the driving input is absent, instead of
  computing a bar from a default.
- `PredictRequest` rainfall fields are now **required**. Baseline defaulted
  `rainfall_24h` to 45.0 mm, so a coordinate-only call got a hazard score from
  rainfall observed nowhere.

Also fixed in `train_models.py`: selection was hardcoded to XGBoost, which its
own metrics showed worst of three (ROC-AUC 0.8327 vs 0.8456). Selection is now
driven by the measured metric, and the metadata records
`split_strategy: RANDOM — not time-based`, so nobody mistakes it for a
temporally honest evaluation. The script is not re-run; existing artifacts are
untouched.

### Defect 7 — CORS, auth, tests

`allow_origins=["*"]` with `allow_credentials=True` replaced by an env-driven
origin list, methods narrowed to GET/POST/OPTIONS, headers to
Authorization/Content-Type. `POST /api/alerts` returns **503** with a reason —
the route is preserved (a test asserts it is not 404) but the unauthenticated
write is closed until M11. Test suite created; there was none.

### Defect 8 — missing boundary input

`build_geo.py` now fails immediately with an explanatory message naming the
candidate sources, instead of a bare `FileNotFoundError` deep in the script. Its
docstring records that `geo_data.json` is shipped but not reproducible, and that
the random seed values propagated into it. Moved to `demo/dashboard/` with the
rest of the demo.

---

## 3. Additional fixes from the inspection report

- **`/api/risk/{id}` fed the model no weather** and defaulted rainfall to 0 mm,
  systematically under-stating risk (it returned 0.0517/Low for Gangtok). It now
  joins observed weather or returns NO DATA.
- **Three-way contradiction resolved.** `/api/locations`, `/api/risk/1` and
  `/api/location/1` returned 0.75, 0.0517 and 0.98 for the same site. All three
  now return `null` with a stated reason, from one code path.
- **ESRI World Imagery basemap removed** — commercial Esri service, outside the
  budget rule.
- **Bhuvan `TileLayer` removed** — its `{bbox-epsg-3857}` is a Mapbox GL
  placeholder Leaflet cannot substitute, so it never rendered. Kept in the layer
  registry as `PENDING_VERIFICATION`, `enabled: false`.
- **Footer attribution corrected** — it credited GIBS, MODIS, Sentinel-1/2 and
  Bhuvan, none of which the map loaded.
- `datetime.utcnow()` → timezone-aware `utcnow()` on all touched paths.
- Duplicate 11k-line dataset and the byte-identical
  `original-react-components/` directory deleted.
- `__init__.py` added throughout plus `pyproject.toml`; imports no longer need
  `PYTHONPATH`.
- `requirements.txt` pinned exactly; `.env.example` committed.
- Advisory notice naming **IMD, NDMA and NCS** replaces the academic-hedge
  disclaimer, and is attached to every hazard-bearing response plus an
  `X-LANDSAFE-Advisory` header on every response.

---

## 4. New scaffolding for later milestones

- `core/mode.py` — `LANDSAFE_MODE` guard, default production.
- `core/freshness.py` — FRESH/RECENT/AGING/STALE/OFFLINE, `Provenance`,
  `DataStatus`, `no_data()`. **Pass-based semantics implemented** per your note:
  NISAR's 12-day repeat means a 3-day-old scene reads FRESH, where clock-based
  staleness would have wrongly aged it out.
- `config.SOURCE_CADENCE` — documented cadence, liveness class and licence per
  source, with `verified` flags. `nisar_ssar` and `resourcesat_liss` are
  `verified: false` and cannot be scheduled.
- Liveness vocabulary enforced: nothing is labelled `LIVE`, because no planned
  source documents real-time delivery.
- `demo/dashboard/` — the HTML dashboard and its simulator, out of the
  production tree entirely.

---

## 5. Intentional contract changes

Not breakage — flag these before M1 if you disagree.

| Route | Change | Why |
|---|---|---|
| `POST /api/alerts` | 200 → **503** | Unauthenticated write (defect 7). Route preserved; re-opens in M11. |
| `POST /api/predict` | rainfall now required | Defaulted to 45.0 mm otherwise. |
| `PredictResponse` | `risk_probability` → `hazard_index` | Not a probability. |
| `SimulationResponse` | `*_probability` → `*_index`, `delta_risk` → `delta_index` | Same. |
| `LocationResponse` | hazard fields now nullable, all currently `null`; `+provenance`, `+data_status` | Values were `random.uniform`. |
| `/api/locations?risk=` | returns empty | Cannot filter on a value that does not exist. |
| `hazard_monitoring_active` | always `false` | No ingestion exists yet. |

The frontend will show empty panels until M9 adds the NO DATA states. That is
the expected shape of the regression I flagged.

---

## 6. Real vs pending

**Real and working:** the API surface; Open-Meteo fetch with correct time
windows, retry and backoff; freshness tiering; mode isolation; the alert store
and threshold evaluation logic; SHAP attribution wiring; the test suite.

**Not real, explicitly marked:** all satellite observations; all rainfall except
Open-Meteo; fire, earthquake and every other hazard; the hazard index itself
(uncalibrated, synthetic training data); the database; auth; the seed site
attributes.

**Verified by running:** everything in §2, via the 62 tests plus a manual probe
of all 15 operations in both modes.

**Not verified — sandbox has no external network.** The container's egress
allowlist excludes `api.open-meteo.com` (Open-Meteo returned HTTP 403 through
the proxy during my run), so the live-response parsing path is exercised only
against fixtures. To verify locally:

```bash
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --port 8000
curl -s 'localhost:8000/api/weather/27.3389/88.6065' | python -m json.tool
```

Expect `status: FRESH|RECENT`, a real `observed.rainfall_24h`,
`rainfall_24h_hours_counted: 24`, and `forecast_5d[0].day == "Today"` on today's
date. Then sanity-check `observed.rainfall_24h` against the last 24
`hourly.precipitation` entries **at or before** `current.time` — that is the D3
fix in the wild. Also confirm `npm install && npm run build` still succeeds; I
did not run the frontend build.

---

## 7. What I need next

**Blocking M1:**

1. **District boundary source and licence.** Now NER-scoped, which narrows it.
   Recommendation unchanged: **GADM v4.1 level-2**, free, non-commercial,
   attribution required — fits the fixed academic status. Alternative: Survey of
   India / data.gov.in if you want an authoritative Indian source and are willing
   to read the licence terms. Without this, `districts.boundary_source` and
   `boundary_licence` cannot be populated, which M1 requires.
2. **PostGIS deployment** — container in the compose file, or an existing
   instance?
3. **Confirm the NER scope call.** M0 left all 304 seed records in place to avoid
   breaking `/api/locations`. M1 seeds NER districts only. If you want the
   records narrowed sooner, say so and it happens in M1 rather than M9.

**Start now regardless — lead time:**

4. **Bhoonidhi** (`bhoonidhi@nrsc.gov.in`). Manual approval, gates NISAR,
   Resourcesat and Cartosat DEM, and therefore most of M4.
5. **NASA Earthdata**, **FIRMS MAP_KEY**, **CDSE**, **MOSDAC** — all free and
   self-service, all needed before M4.

**Needed before M6:**

6. **Labelled landslide events** (NRSC Landslide Atlas, state SDMA logs). Decides
   whether M6 retrains or builds the susceptibility × trigger index.

**One architecture amendment to fold in when you're ready:** `ARCHITECTURE.md`
was written against the all-India brief and proposes a table set that partly
supersedes the existing ORM. Your decision to keep and extend
`Location`/`SatelliteFeature`/`WeatherRecord` shapes, plus the NER scope, changes
§4. Say the word and I will revise it — it is a doc edit, not a code change.

**Not started, as instructed:** M1. Waiting on your explicit "go".
