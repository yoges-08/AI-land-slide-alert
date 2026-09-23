# LANDSAFE-NER — Backend Log Analysis & Fix Instructions

> **For AI Agent:** These are the 3 critical errors found in the Render backend logs. Fix each one. Exact file paths, line numbers, and solution code are provided.

---

## Log Analysis Summary

### ✅ Working Fine (No Action Needed)
- Server starts and runs on port 10000 ✅
- `/api/locations`, `/api/hierarchy`, `/api/alerts` — all returning 200 OK ✅
- `/api/satellite/1` and `/api/satellite/50` — returning 200 OK with real Sentinel-2 data ✅
- `/api/predict` (POST) — returning 200 OK ✅
- `/api/sources` — returning 200 OK ✅
- Keep-alive health pings from `74.220.52.132` every 10 min — working ✅
- Scheduler IS running (ingestion cycles are firing every 30 min) ✅

### ❌ Three Repeating Errors

| Error | Frequency | Impact |
|---|---|---|
| **MOSDAC HTTP 404** | Every 30 min, 3 retries each = **144 failed requests/day** | INSAT-3D satellite rainfall never ingested |
| **NASA GPM HTTP 404** | Every 30 min, 3 retries each = **144 failed requests/day** | GPM IMERG rainfall never ingested |
| **Open-Meteo HTTP 429** | Every 60 min (scheduler) + every user request = **hundreds/day** | ALL weather data is NULL, ML predictions fail |

---

## Error 1 (CRITICAL): MOSDAC Ingestion — HTTP 404 (Wrong API URL)

**Log pattern (repeats every 30 minutes, 24/7):**
```
[Ingestion:MOSDAC_INSAT3D_QPE] Fetch attempt 1/3 failed: MOSDAC server returned HTTP 404
[Ingestion:MOSDAC_INSAT3D_QPE] Fetch attempt 2/3 failed: MOSDAC server returned HTTP 404
[Ingestion:MOSDAC_INSAT3D_QPE] Fetch attempt 3/3 failed: MOSDAC server returned HTTP 404
[Ingestion:MOSDAC_INSAT3D_QPE] Cycle failed: Failed after 3 attempts: MOSDAC server returned HTTP 404
```

**File:** `backend/app/ingestion/sources/weather/mosdac_insat3d.py` line 31  
**Root cause:** The API endpoint `https://www.mosdac.gov.in/api/v1/qpe` is a **placeholder URL that does not exist**. MOSDAC does not have a REST API at that path — hence HTTP 404 (Not Found).

### Solution

MOSDAC provides satellite data via their data portal, not a REST API. The correct way to access MOSDAC QPE data is through their OPeNDAP/THREDDS server or direct file download.

**Replace the `api_endpoint` and `fetch()` method** in `backend/app/ingestion/sources/weather/mosdac_insat3d.py`:

```python
# Line 31 — CHANGE THE URL:
# BEFORE:
api_endpoint = os.getenv("MOSDAC_API_ENDPOINT", "https://www.mosdac.gov.in/api/v1/qpe")

# AFTER — Use MOSDAC's actual data catalog endpoint:
api_endpoint = os.getenv("MOSDAC_API_ENDPOINT", "https://mosdac.gov.in/catalog/search")
```

**Then update the `fetch()` method** to use the correct MOSDAC data access pattern. Replace the `params` dict (around lines 57-61):

```python
        params = kwargs.get("params", {
            "satellite": "3DIMG",
            "sensor": "IMAGER",
            "product": "QPE",
            "level": "L2",
            "format": "json",
            "limit": 1,
            "sort": "-datetime",  # Most recent first
        })
```

**If MOSDAC's catalog search also returns 404**, the API may require a different base URL. In that case, **disable the MOSDAC ingestion job temporarily** to stop the error spam. Add this check at the start of `fetch()`:

```python
    async def fetch(self, **kwargs) -> Dict[str, Any]:
        simulated_payload = kwargs.get("simulated_payload")
        if simulated_payload is not None:
            return simulated_payload

        # Guard: skip if no working auth token
        if not self.auth_token:
            raise SourceFetchError(
                "MOSDAC_AUTH_TOKEN is empty. Skipping fetch. "
                "Login to mosdac.gov.in to obtain a bearer token."
            )

        # ... rest of fetch logic ...
```

This stops the 3-retry-every-30-min error spam when the token is missing.

---

## Error 2 (CRITICAL): NASA GPM Ingestion — HTTP 404 (Wrong API URL)

**Log pattern (repeats every 30 minutes, 24/7):**
```
[Ingestion:NASA_GPM_IMERG] Fetch attempt 1/3 failed: NASA GPM server returned HTTP 404
[Ingestion:NASA_GPM_IMERG] Fetch attempt 2/3 failed: NASA GPM server returned HTTP 404
[Ingestion:NASA_GPM_IMERG] Fetch attempt 3/3 failed: NASA GPM server returned HTTP 404
[Ingestion:NASA_GPM_IMERG] Cycle failed: Failed after 3 attempts: NASA GPM server returned HTTP 404
```

**File:** `backend/app/ingestion/sources/weather/nasa_gpm.py` line 31  
**Root cause:** The API endpoint `https://gpm.nasa.gov/api/v1/imerg` is a **placeholder URL that does not exist**. NASA GPM data is accessed via GES DISC (Goddard Earth Sciences Data and Information Services Center), not `gpm.nasa.gov`.

### Solution

The real NASA GPM IMERG data endpoint uses the GES DISC OPeNDAP/HTTP service.

**Replace the `api_endpoint`** in `backend/app/ingestion/sources/weather/nasa_gpm.py`:

```python
# Line 31 — CHANGE THE URL:
# BEFORE:
api_endpoint = os.getenv("NASA_GPM_API_ENDPOINT", "https://gpm.nasa.gov/api/v1/imerg")

# AFTER — Use the real GES DISC CMR (Common Metadata Repository) search endpoint:
api_endpoint = os.getenv("NASA_GPM_API_ENDPOINT", 
    "https://cmr.earthdata.nasa.gov/search/granules.json")
```

**Then update the `fetch()` method params** (around lines 52-56):

```python
        params = kwargs.get("params", {
            "collection_concept_id": "C2723754864-GES_DISC",  # GPM IMERG Half-Hourly Late Run V07
            "temporal[]": f"{(datetime.now(timezone.utc) - timedelta(hours=6)).strftime('%Y-%m-%dT%H:%M:%SZ')},",
            "bounding_box": "68,6,98,38",  # India bounding box
            "sort_key[]": "-start_date",
            "page_size": 1,
        })
```

And update the auth header to use Earthdata token (lines 49-50):

```python
        if self.earthdata_token:
            headers["Authorization"] = f"Bearer {self.earthdata_token}"
        else:
            # Use basic auth with Earthdata username/password
            import base64
            username = os.getenv("EARTHDATA_USERNAME", "")
            password = os.getenv("EARTHDATA_PASSWORD", "")
            if username and password:
                creds = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {creds}"
```

---

## Error 3 (CRITICAL): Open-Meteo HTTP 429 — Rate Limit Exhausted

**Log pattern (on-demand + every 60 min from scheduler):**
```
Open-Meteo unavailable for (27.3389, 88.6065): HTTP 429
Open-Meteo unavailable for (13.0271, 75.4559): HTTP 429   ← repeated 40+ times in 2 min!
[Ingestion:OPEN_METEO] Cycle failed: Failed after 2 attempts: Open-Meteo daily request quota or burst rate limit exceeded
```

**Files:** `backend/app/services/weather_service.py`, `backend/app/ingestion/sources/weather/open_meteo.py`

**Root cause — THREE problems combined:**

### Problem A: Simulation endpoint hammers Open-Meteo
The logs show **40+ consecutive** simulation requests at `18:28:08–18:30:04`, each triggering a fresh Open-Meteo call for the same coordinates `(13.0271, 75.4559)`. The `/api/simulation` endpoint calls weather for every slider step.

### Problem B: Scheduler ingestion also calls Open-Meteo
Every 60 minutes, the `OPEN_METEO` ingestion source fires and makes additional calls. Combined with user requests, this exceeds the free tier limit.

### Problem C: No 429-specific cooldown
When a 429 is received, the code still retries immediately with just `0.5s * 2^attempt` delay, wasting more quota on guaranteed-to-fail requests.

### Solution

**Step 1:** Add 429 cooldown in `backend/app/services/weather_service.py`.

After line 96 (after the existing cache check), add:

```python
    # If we recently got a 429, don't even try for 5 minutes
    _RATE_LIMIT_COOLDOWN_S = 300.0
    if cache_key in _WEATHER_CACHE:
        cached_time, cached_val = _WEATHER_CACHE[cache_key]
        if cached_val is None and (now_ts - cached_time) < _RATE_LIMIT_COOLDOWN_S:
            return unavailable(lat, lon, "Rate-limited cooldown active (HTTP 429)")
```

Inside the retry loop (around line 124-128), add 429-specific handling:

```python
                if response.status_code == 200:
                    parsed = parse_open_meteo_response(response.json(), lat, lon)
                    _LAST_SUCCESS[cache_key] = parsed["data_status"]["observed_at"] or utcnow().isoformat()
                    _WEATHER_CACHE[cache_key] = (time.time(), parsed)
                    return parsed
                elif response.status_code == 429:
                    # Cache a None marker so we don't retry for 5 min
                    _WEATHER_CACHE[cache_key] = (time.time(), None)
                    logger.warning("Open-Meteo 429 for (%s, %s) — cooldown activated", lat, lon)
                    break  # Stop retrying immediately
                last_error = f"HTTP {response.status_code}"
```

**Step 2:** Use geographic bucketing — reduce cache precision from 4 decimals to 1 decimal (~11 km grid, matches Open-Meteo resolution):

```python
# Line 91 — CHANGE:
# BEFORE:
cache_key = (round(lat, 4), round(lon, 4))

# AFTER:
cache_key = (round(lat, 1), round(lon, 1))
```

**Step 3:** In `backend/app/api/routes.py`, find the simulation endpoint and make it reuse cached weather instead of fetching fresh:

Find the simulation handler and ensure it uses the same `fetch_live_weather()` function (which has caching), NOT a direct Open-Meteo call.

**Step 4:** Disable the Open-Meteo ingestion source from the scheduler to prevent double-fetching. Weather is already fetched on-demand per location request — the scheduler ingestion just wastes quota.

In `backend/app/ingestion/sources/weather/open_meteo.py`, add at the top of the `fetch()` method:

```python
    async def fetch(self, **kwargs) -> Dict[str, Any]:
        """
        Open-Meteo weather is fetched on-demand per location request
        via weather_service.py. The scheduler ingestion is disabled to
        conserve the free tier quota (10k calls/day).
        """
        raise SourceFetchError(
            "Open-Meteo ingestion via scheduler is disabled. "
            "Weather is fetched on-demand per location request to conserve quota."
        )
```

Or alternatively, remove `OpenMeteoSource` from `backend/app/ingestion/registry.py` line 85-86:

```python
# COMMENT OUT to stop scheduler from calling Open-Meteo:
# if not source_registry.get("OPEN_METEO"):
#     source_registry.register(OpenMeteoSource())
```

---

## Other Observations from Logs (Non-Critical)

### HEAD Requests Return 405 Method Not Allowed
```
INFO: "HEAD /api/satellite/1 HTTP/1.1" 405 Method Not Allowed
```
This is from the `read_url_content` tool probing the endpoint. HEAD is not enabled on FastAPI GET routes by default. This is harmless — no fix needed.

### Multiple Deploys in Quick Succession
Between `17:20` and `18:33`, there were **6 deploys** (each takes ~40s to start). This caused:
- Old server process shutting down while new one starts
- Brief downtime windows
- Cache being cleared on each restart (in-memory cache lost)

**Recommendation:** Batch your code changes and deploy once, not after every small change.

### Server Was Offline for ~7 Hours
```
07:39:45Z — Shutting down
14:42:53Z — Started server process  (7 hours later)
```
The Render free tier let the server sleep from ~07:40 UTC to ~14:42 UTC (7 hours). The keep-alive ping from `74.220.52.132` stopped during this window — possibly because Render killed the process before the next ping could fire.

**Fix:** The keep-alive task `_keep_alive()` in `main.py` is correct, but use an **external ping service** (like cron-job.org or UptimeRobot) to ping `/health` every 5 minutes — don't rely on self-ping alone.

---

## Error Frequency Count

| Error | Times in logs | Every | Daily waste |
|---|---|---|---|
| MOSDAC 404 | 3 retries × 48 cycles = **~144** | 30 min | 144 wasted HTTP requests |
| NASA GPM 404 | 3 retries × 48 cycles = **~144** | 30 min | 144 wasted HTTP requests |
| Open-Meteo 429 | 2 retries × 24 cycles + user requests = **~100+** | 60 min + on-demand | Blocks ALL weather data |
| Simulation 429 spam | **40+ calls** in 2 min | Per user session | Largest single quota drain |

**Total wasted requests per day: ~430+**

---

## Fix Priority

| # | Fix | Impact | Effort |
|---|---|---|---|
| 🥇 **1** | Add Open-Meteo 429 cooldown + geographic bucketing | Restores weather data | Change 10 lines in weather_service.py |
| 🥇 **2** | Disable Open-Meteo scheduler ingestion | Saves ~48 quota calls/day | Comment out 2 lines in registry.py |
| 🥇 **3** | Fix MOSDAC API URL or disable source | Stops 144 error logs/day | Change URL or add guard in mosdac_insat3d.py |
| 🥇 **4** | Fix NASA GPM API URL or disable source | Stops 144 error logs/day | Change URL or add guard in nasa_gpm.py |
| 🥉 **5** | Add external uptime ping | Prevents 7-hour sleep gaps | Set up cron-job.org (no code change) |

---

*Analysis based on Render logs from 2026-09-22T17:01 to 2026-09-23T14:48 UTC.*
