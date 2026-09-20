/* ══════════════════════════════════════════════════════════════════════════
   LANDSAFE engine
   ─────────────────────────────────────────────────────────────────────────
   Two models run side by side on every district, every simulated hour:

   1. A physical slope-stability model (infinite-slope factor of safety with
      partial saturation and a pseudo-static seismic term).
   2. A learned additive hazard model standing in for the server-side
      gradient-boosted classifier, with linear-SHAP attributions.

   They are blended; their disagreement is reported as model uncertainty.

   The met/satellite feed here is a deterministic monsoon simulator so the
   page runs standalone. Point CFG.api at the LANDSAFE backend and the same
   engine consumes real IMD / Open-Meteo / GPM / MODIS fields instead.
   ══════════════════════════════════════════════════════════════════════════ */
const CFG = {
  api: null,                 // e.g. "https://landsafe.example.gov.in/api/v1"
  startISO: "2026-09-18T06:00:00+05:30",
  tickMs: 1600,              // real ms per simulated hour at 1×
  spinupHours: 240,          // antecedent conditions built before t0
};

const CAT = [
  { k: "low",      lab: "Low",      min: 0.00, c: "var(--h0)" },
  { k: "moderate", lab: "Moderate", min: 0.10, c: "var(--h1)" },
  { k: "high",     lab: "High",     min: 0.25, c: "var(--h2)" },
  { k: "severe",   lab: "Severe",   min: 0.45, c: "var(--h3)" },
  { k: "extreme",  lab: "Extreme",  min: 0.70, c: "var(--h4)" },
];
const catOf = p => { let r = CAT[0]; for (const c of CAT) if (p >= c.min) r = c; return r; };
const RAMP = ["#4E8C6A", "#7FA13F", "#C8A21C", "#DE6A25", "#C1303C", "#8D2150"];

const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
const lerp = (a, b, t) => a + (b - a) * t;
const sig = z => 1 / (1 + Math.exp(-z));

/* deterministic hash-noise so every run of the page is identical */
function hash(...xs) {
  let h = 2166136261 >>> 0;
  for (const x of xs) {
    let v = Math.imul(Math.round(x * 1000) ^ 0x9e3779b9, 0x85ebca6b) >>> 0;
    h = Math.imul(h ^ v, 16777619) >>> 0;
  }
  return ((h >>> 8) & 0xffffff) / 0xffffff;
}

/* ── geotechnical property tables ───────────────────────────────────────── */
const LITHO = {
  // [susceptibility 0-1, effective cohesion kPa, friction angle deg]
  "greater_himalaya": [0.72, 8, 36], "lesser_himalaya": [0.92, 5, 30],
  "siwalik": [0.95, 3, 28], "ne_hills": [0.90, 4, 29], "shillong": [0.78, 7, 33],
  "western_ghats": [0.80, 9, 32], "wg_south": [0.84, 7, 31],
  "eastern_ghats": [0.55, 10, 33], "plateau": [0.42, 12, 34],
  "alluvium": [0.10, 6, 30], "coastal": [0.15, 5, 30],
  "desert": [0.05, 2, 34], "deccan": [0.28, 14, 35],
};
const SOILCAP = {  // plant-available storage, mm
  "greater_himalaya": 55, "lesser_himalaya": 130, "siwalik": 110, "ne_hills": 145,
  "shillong": 150, "western_ghats": 165, "wg_south": 170, "eastern_ghats": 120,
  "plateau": 125, "alluvium": 190, "coastal": 110, "desert": 60, "deccan": 200,
};
const DENSITY = { // persons / km², for exposure estimates
  "greater_himalaya": 22, "lesser_himalaya": 150, "siwalik": 260, "ne_hills": 130,
  "shillong": 160, "western_ghats": 330, "wg_south": 620, "eastern_ghats": 170,
  "plateau": 230, "alluvium": 900, "coastal": 640, "desert": 75, "deccan": 340,
};
const ZONE_LABEL = {
  "greater_himalaya": "Greater Himalaya", "lesser_himalaya": "Lesser Himalaya",
  "siwalik": "Siwalik foothills", "ne_hills": "Northeast fold belt",
  "shillong": "Shillong plateau", "western_ghats": "Western Ghats (Deccan trap)",
  "wg_south": "Southern Western Ghats", "eastern_ghats": "Eastern Ghats",
  "plateau": "Peninsular plateau", "alluvium": "Indo-Gangetic / Brahmaputra plain",
  "coastal": "Coastal plain", "desert": "Thar arid zone", "deccan": "Deccan plateau",
};

/* IS 1893 seismic zones, coarse */
function seismicZone(lat, lon, state) {
  if (lon > 90.5 && lat > 22) return 5;                 // NE fold belt
  if (["Assam","Nagaland","Manipur","Mizoram","Tripura","Arunachal Pradesh","Meghalaya"].includes(state)) return 5;
  if (state === "Gujarat" && lon < 71.5 && lat > 22.5) return 5;   // Kutch
  if (state === "Andaman and Nicobar Islands") return 5;
  if (lat > 30 && lon < 80) return 4;                   // NW Himalaya
  if (["Sikkim","Uttarakhand","Himachal Pradesh","Jammu and Kashmir","Ladakh"].includes(state)) return 4;
  if (state === "Bihar" && lat > 26) return 4;
  if (state === "Delhi" || state === "Chandigarh") return 4;
  if (lon < 77 && lat < 20) return 3;                   // W coast
  if (["West Bengal","Uttar Pradesh","Odisha","Punjab","Haryana","Kerala","Goa"].includes(state)) return 3;
  return 2;
}
const PGA = { 2: 0.10, 3: 0.16, 4: 0.24, 5: 0.36 };

/* ══════════════════════════════════════════════════════════════════════════
   Meteorological simulator — monsoon-withdrawal regime, mid-September
   ══════════════════════════════════════════════════════════════════════════ */
const Met = {
  cells: [],
  quakes: [],
  pulse: 1,

  /* Mesoscale systems. Bay-of-Bengal lows track WNW across the plains;
     the NE fold belt and the Ghats generate local convection.            */
  seedCells(h) {
    const nWanted = 5;
    while (this.cells.length < nWanted) {
      const i = this.cells.length + h * 7;
      const kind = hash(i, 11) < 0.42 ? "bay" : (hash(i, 12) < 0.55 ? "ne" : "ghat");
      let lat, lon, r, inten, vlat, vlon, life;
      if (kind === "bay") {
        lat = lerp(17, 26, hash(i, 1)); lon = lerp(84, 91, hash(i, 2));
        r = lerp(2.4, 4.2, hash(i, 3)); inten = lerp(4, 14, hash(i, 4));
        vlat = lerp(0.01, 0.06, hash(i, 5)); vlon = -lerp(0.05, 0.13, hash(i, 6));
        life = Math.round(lerp(60, 130, hash(i, 7)));
      } else if (kind === "ne") {
        lat = lerp(23.5, 28.5, hash(i, 1)); lon = lerp(90, 96, hash(i, 2));
        r = lerp(1.1, 2.3, hash(i, 3)); inten = lerp(6, 20, hash(i, 4));
        vlat = lerp(-0.02, 0.03, hash(i, 5)); vlon = -lerp(0.01, 0.05, hash(i, 6));
        life = Math.round(lerp(20, 60, hash(i, 7)));
      } else {
        lat = lerp(9, 20, hash(i, 1)); lon = lerp(73.5, 76.5, hash(i, 2));
        r = lerp(0.9, 2.0, hash(i, 3)); inten = lerp(5, 17, hash(i, 4));
        vlat = lerp(0.01, 0.05, hash(i, 5)); vlon = lerp(-0.01, 0.02, hash(i, 6));
        life = Math.round(lerp(24, 70, hash(i, 7)));
      }
      this.cells.push({ id: i, kind, lat, lon, r, inten, vlat, vlon, age: 0, life });
    }
  },

  step(h) {
    this.seedCells(h);
    for (const c of this.cells) {
      c.lat += c.vlat; c.lon += c.vlon; c.age++;
      // intensity follows a life-cycle envelope
      const f = c.age / c.life;
      c.now = c.inten * Math.sin(Math.PI * clamp(f, 0, 1)) ** 0.7;
    }
    this.cells = this.cells.filter(c => c.age < c.life && c.lon > 66 && c.lon < 99 && c.lat < 38 && c.lat > 5);
    // slow synoptic pulse: active and break phases of the monsoon
    this.pulse = 0.55 + 0.75 * (0.5 + 0.5 * Math.sin(h / 41 + 1.1)) + 0.25 * hash(h, 99);

    // occasional tectonic events — Zone IV/V background seismicity
    this.quakes = this.quakes.filter(q => h - q.h < 18);
    if (hash(h, 777) > 0.988) {
      const ne = hash(h, 778) < 0.55;
      this.quakes.push({
        h, lat: ne ? lerp(24, 28.5, hash(h, 3)) : lerp(29, 35, hash(h, 3)),
        lon: ne ? lerp(90, 96, hash(h, 4)) : lerp(74, 82, hash(h, 4)),
        mag: +(lerp(3.6, 5.4, hash(h, 5))).toFixed(1),
      });
    }
  },

  /* hourly rainfall (mm) at a district */
  rain(d, h) {
    const [lat, lon] = d.ll;
    // diurnal cycle: hill convection peaks late afternoon and pre-dawn
    const hr = ((h % 24) + 24) % 24;
    const diurnal = d.sl > 12
      ? 0.7 + 0.55 * Math.sin((hr - 9) * Math.PI / 12) + 0.35 * Math.sin((hr - 2) * Math.PI / 8)
      : 0.85 + 0.3 * Math.sin((hr - 14) * Math.PI / 12);
    let mm = (d.rn / 24) * Math.max(0.15, diurnal) * this.pulse;

    for (const c of this.cells) {
      const dy = (lat - c.lat), dx = (lon - c.lon) * Math.cos(lat * Math.PI / 180);
      const dist2 = dy * dy + dx * dx;
      const g = Math.exp(-dist2 / (2 * c.r * c.r * 0.25));
      if (g > 0.02) mm += (c.now || 0) * g;
    }
    // orographic enhancement on windward relief
    mm *= 1 + 0.85 * Math.min(1, d.sl / 34) * Math.min(1, d.rf / 1400);
    // stochastic texture, deterministic per district-hour
    mm *= 0.55 + 0.9 * hash(d.i, h);
    return Math.max(0, mm);
  },

  /* screen-level air temperature (°C) */
  temp(d, h) {
    const hr = ((h % 24) + 24) % 24;
    const seaLevel = 32.5 - 0.30 * Math.max(0, d.ll[0] - 12);
    const diurnal = -4.6 * Math.cos((hr - 15) * Math.PI / 12);
    return seaLevel - 0.0062 * d.e + diurnal + 2.2 * (hash(d.i, h, 3) - 0.5);
  },

  freezingLevel(h) { return 4750 + 260 * Math.sin(h / 33) + 180 * (hash(h, 21) - 0.5); },
};

/* ══════════════════════════════════════════════════════════════════════════
   District state
   ══════════════════════════════════════════════════════════════════════════ */
function initState(d) {
  const cap = SOILCAP[d.z];
  return {
    cap,
    store: cap * (0.32 + 0.22 * hash(d.i, 5)),   // antecedent wetness
    swe: d.snowline * 1800 * (0.92 + 0.25 * hash(d.i, 6)),  // snow + ice water equivalent, mm
    rain: new Float32Array(336),                  // 14-day ring buffer
    ptr: 0,
    hist: [], satHist: [], rainHist: [],          // series for the outlook chart
    r24: 0, r72: 0, r168: 0, api: 0, melt: 0, temp: 20,
    p: 0, pPrev: 0, pPhys: 0, pMl: 0, unc: 0, flood: 0, glof: 0,
    shap: [], sensors: null,
  };
}

function accum(s, n) {
  let t = 0;
  for (let k = 1; k <= n; k++) t += s.rain[(s.ptr - k + 336) % 336];
  return t;
}

/* ── hydrology: one hour ────────────────────────────────────────────────── */
function stepHydrology(d, s, h) {
  const rain = Met.rain(d, h);
  const T = Met.temp(d, h);
  s.temp = T;

  // Snow and ice. Seasonal snow melts out entirely; the perennial store —
  // glaciers and permanent snowfields above the equilibrium line — does not,
  // and in September it is the dominant meltwater source in the high Himalaya.
  let melt = 0;
  const perennial = d.snowline * 1800;
  if (perennial > 0 || s.swe > 0) {
    if (T < 0.5) {
      s.swe += rain * 0.85;                       // falling as snow
    } else {
      const ddf = 4.2 + 2.6 * d.snowline;         // debris-covered ice melts faster
      const potential = ddf * Math.max(0, T) / 24;
      const seasonal = Math.max(0, s.swe - perennial);
      melt = Math.min(potential, seasonal + (perennial > 0 ? potential * 0.55 : 0));
      s.swe = Math.max(perennial, s.swe - melt);
    }
    if (d.e > Met.freezingLevel(h) - 400) s.swe += 0.10;   // accumulation above the freezing level
  }
  s.melt = melt;

  const input = (T < 0.5 ? 0 : rain) + melt;

  // runoff rises with slope and with how full the profile already is
  const wet = s.store / s.cap;
  const runoffC = clamp(0.12 + 0.55 * (d.sl / 45) + 0.42 * wet ** 2, 0, 0.93);
  const infil = input * (1 - runoffC);

  // nonlinear drainage + evapotranspiration
  const kDrain = 0.008 + 0.024 * (d.sl / 45);
  s.store += infil - s.cap * kDrain * wet ** 3 - 0.055 * Math.max(0, T - 8) * (1 - wet) * 0.25;
  s.store = clamp(s.store, 0, s.cap * 1.12);

  s.rain[s.ptr] = rain; s.ptr = (s.ptr + 1) % 336;
  s.r24 = accum(s, 24); s.r72 = accum(s, 72); s.r168 = accum(s, 168);
  // antecedent precipitation index, k = 0.92 / day
  s.api = s.api * Math.pow(0.92, 1 / 24) + rain;
  return rain;
}

/* ── model 1: infinite-slope factor of safety ───────────────────────────── */
function factorOfSafety(d, s, kh) {
  const beta = Math.max(2, d.sl) * Math.PI / 180;
  const [, cSoil, phiDeg] = LITHO[d.z];
  const phi = phiDeg * Math.PI / 180;
  const z = clamp(3.2 - 0.05 * d.sl, 0.7, 3.2);      // thinner regolith on steeper ground
  const gamma = 18.5, gammaW = 9.81;
  // root cohesion from canopy; bare ground and recent clearing remove it
  const ndvi = d.ndvi != null ? d.ndvi : (d.z === "desert" ? 0.12 : 0.45);
  const cRoot = 5.5 * clamp(ndvi / 0.6, 0, 1) * Math.min(1, 1.05 / z);  // rooting depth ≈ 1 m
  const c = 0.65 * cSoil + cRoot;                                        // residual, not peak
  const m = clamp(s.store / s.cap, 0, 1);            // saturated depth ratio

  const num = c + (gamma - m * gammaW) * z * Math.cos(beta) ** 2 * Math.tan(phi);
  const den = gamma * z * Math.sin(beta) * Math.cos(beta);
  const fs = num / Math.max(den, 0.001);
  return fs / (1 + 2.4 * kh);                        // pseudo-static seismic term
}

/* ── model 2: susceptibility × trigger hazard model ─────────────────────
   Landslide hazard is not the sum of "steep" and "wet" — it is their
   product. A dry cliff and a saturated plain are both stable. The model
   therefore learns a susceptibility term S from terrain, a trigger term T
   from water, and lets the interaction carry most of the weight.        */
const SUSC = [
  { k: "slope",  lab: "Slope angle",             w:  0.42, base: 0.30 },
  { k: "litho",  lab: "Lithology & weathering",  w:  0.20, base: 0.35 },
  { k: "hist",   lab: "Past failure density",    w:  0.14, base: 0.18 },
  { k: "bare",   lab: "Bare-soil exposure",      w:  0.10, base: 0.28 },
  { k: "cut",    lab: "Road cut & construction", w:  0.10, base: 0.25 },
  { k: "relief", lab: "Local relief",            w:  0.08, base: 0.22 },
  { k: "veg",    lab: "Root reinforcement",      w: -0.18, base: 0.62 },
  { k: "seis",   lab: "Seismic setting",         w:  0.06, base: 0.45 },
];
const TRIG = [
  { k: "sat",    lab: "Soil saturation",          w: 0.34, base: 0.34 },
  { k: "rain24", lab: "24-hour rainfall",         w: 0.26, base: 0.14 },
  { k: "api",    lab: "Antecedent wetness",       w: 0.20, base: 0.20 },
  { k: "idthr",  lab: "Intensity–duration limit", w: 0.14, base: 0.16 },
  { k: "melt",   lab: "Snowmelt input",           w: 0.06, base: 0.03 },
];
const A = { b0: -5.60, s: 1.20, t: 2.00, st: 7.40 };

function features(d, s, kh, quakeBoost) {
  // Caine-type intensity–duration threshold: I = 14.8 · D^-0.39  (mm/h, h)
  const i24 = s.r24 / 24, thr24 = 14.82 * Math.pow(24, -0.39);
  const ndvi = d.ndvi != null ? d.ndvi : 0.45;
  const bare = d.bare != null ? d.bare / 100 : clamp(1 - ndvi * 1.6, 0, 1);
  return {
    slope:  clamp(d.sl / 42, 0, 1.15),
    litho:  LITHO[d.z][0],
    hist:   clamp(d.hist / 16, 0, 1),
    bare,
    cut:    clamp((DENSITY[d.z] / 700) * 0.6 + (d.tier === 1 ? 0.35 : 0.1), 0, 1),
    relief: clamp(d.rf / 1600, 0, 1),
    veg:    clamp(ndvi / 0.65, 0, 1.1),
    seis:   clamp(PGA[d.seis] / 0.36, 0, 1) * (1 + 0.8 * quakeBoost),
    sat:    clamp(s.store / s.cap, 0, 1.1),
    rain24: clamp(s.r24 / 190, 0, 1.25),
    api:    clamp(s.api / 210, 0, 1.25),
    idthr:  clamp(i24 / thr24, 0, 2.2) / 2.2,
    melt:   clamp(s.melt * 24 / 26, 0, 1),
  };
}

/* ── ensemble + attribution ─────────────────────────────────────────────── */
function score(d, s, h) {
  // Pseudo-static seismic loading applies only while the ground is shaking.
  // Long-term rock damage in high-zone terrain is carried by the
  // susceptibility term instead, not by a permanent factor-of-safety penalty.
  let quakeBoost = 0;
  for (const q of Met.quakes) {
    const dy = d.ll[0] - q.lat, dx = (d.ll[1] - q.lon) * Math.cos(d.ll[0] * Math.PI / 180);
    const km = Math.sqrt(dy * dy + dx * dx) * 111;
    const reach = 40 * Math.pow(10, q.mag - 4);
    if (km < reach) quakeBoost += (1 - km / reach) * (q.mag - 3) * 0.6 * Math.exp(-(h - q.h) / 9);
  }
  const kh = PGA[d.seis] * 0.5 * clamp(quakeBoost, 0, 1);

  const fs = factorOfSafety(d, s, kh);
  const pPhys = sig(-7.0 * (fs - 1.06));

  const f = features(d, s, kh, quakeBoost);
  let S = 0; for (const ft of SUSC) S += ft.w * f[ft.k];
  let T = 0; for (const ft of TRIG) T += ft.w * f[ft.k];
  S = clamp(S, 0, 1.05); T = clamp(T, 0, 1.05);
  const z = A.b0 + A.s * S + A.t * T + A.st * S * T;
  const pMl = sig(z);

  // Attribution: exact first-order contribution of each input, carried
  // through the interaction by the chain rule and mapped into probability
  // space by the local logistic slope. This is linear SHAP on the
  // linearised model at the current operating point.
  const slope = pMl * (1 - pMl);
  const dS = (A.s + A.st * T) * slope;
  const dT = (A.t + A.st * S) * slope;
  const shap = SUSC.map(ft => ({ k: ft.k, lab: ft.lab, v: dS * ft.w * (f[ft.k] - ft.base), raw: f[ft.k] }))
    .concat(TRIG.map(ft => ({ k: ft.k, lab: ft.lab, v: dT * ft.w * (f[ft.k] - ft.base), raw: f[ft.k] })))
    .sort((a, b) => Math.abs(b.v) - Math.abs(a.v));

  let p = 0.45 * pPhys + 0.55 * pMl;
  if (d.tier === 3) p = Math.min(p, 0.09);        // plains: uncalibrated, never elevated
  s.pPhys = pPhys; s.pMl = pMl; s.fs = fs; s.susc = S; s.trig = T;
  s.unc = Math.abs(pPhys - pMl) * 0.5 + (d.tier === 2 ? 0.07 : 0) + (d.obs ? 0 : 0.045);
  s.shap = shap;
  s.quakeBoost = quakeBoost;
  s.pPrev = s.p;
  s.p = p;
  return p;
}

/* ── flood & GLOF ───────────────────────────────────────────────────────── */
function floodScore(d, s, D) {
  let upstream = 0;
  for (const j of d.up) upstream += D[j].s.r72 * D[j].d.area;
  upstream = upstream / Math.max(1, d.upArea) / 120;
  const local = clamp(s.r72 / 400, 0, 1.2);
  const flat = clamp(1 - d.sl / 18, 0, 1);
  const soak = clamp(s.store / s.cap, 0, 1);
  // steep ground sheds water rather than ponding it: the 0.45 floor keeps a
  // genuine flash-flood signal without claiming river inundation on a ridge
  const z = -3.9 + 2.4 * local * (0.45 + 0.55 * flat)
          + 2.0 * clamp(upstream, 0, 1.4) * (0.30 + 0.70 * flat)
          + 1.5 * flat * soak + 0.7 * flat;
  s.flood = sig(z);

  // glacial lake outburst watch: rapid melt on a glaciated catchment,
  // amplified by nearby seismicity
  if (d.snowline > 0.32 && d.e > 2400) {
    const meltRate = clamp(s.melt * 24 / 22, 0, 1);
    s.glof = clamp(0.45 * meltRate + 0.35 * clamp(s.temp / 12, 0, 1) + 0.6 * (s.quakeBoost || 0), 0, 1);
  } else s.glof = 0;
}

/* ── ground sensor network ──────────────────────────────────────────────── */
function makeSensors(d) {
  if (d.tier !== 1) return null;
  const n = 1 + Math.floor(hash(d.i, 41) * 3);
  const out = [];
  const kinds = ["Tiltmeter", "Piezometer", "Rain gauge", "Extensometer", "Geophone"];
  for (let k = 0; k < n; k++) {
    out.push({
      id: `${d.n.slice(0, 3).toUpperCase()}-${String(100 + Math.floor(hash(d.i, k, 7) * 899))}`,
      kind: kinds[Math.floor(hash(d.i, k, 8) * kinds.length)],
      lat: d.ll[0] + (hash(d.i, k, 9) - 0.5) * 0.28,
      lon: d.ll[1] + (hash(d.i, k, 10) - 0.5) * 0.28,
      batt: Math.round(lerp(42, 100, hash(d.i, k, 11))),
    });
  }
  return out;
}
function sensorReading(sn, d, s, h) {
  switch (sn.kind) {
    case "Tiltmeter":    return { v: (s.store / s.cap * 34 * (d.sl / 35) + hash(sn.id.length, h) * 3).toFixed(1), u: "arc-sec/day" };
    case "Piezometer":   return { v: (s.store / s.cap * 4.6).toFixed(2), u: "m head" };
    case "Rain gauge":   return { v: s.r24.toFixed(1), u: "mm/24h" };
    case "Extensometer": return { v: (s.store / s.cap * 11 * (d.sl / 32)).toFixed(2), u: "mm/day" };
    default:             return { v: (2 + (s.quakeBoost || 0) * 40 + hash(sn.id.length, h, 2) * 4).toFixed(1), u: "counts/h" };
  }
}

/* ══════════════════════════════════════════════════════════════════════════
   World: builds the district array, upstream graph, and drives the clock
   ══════════════════════════════════════════════════════════════════════════ */
const World = {
  D: [], byKey: new Map(), h: 0, t0: 0, events: [], listeners: [],

  build(geo) {
    geo.districts.forEach((d, i) => {
      d.i = i;
      d.seis = seismicZone(d.ll[0], d.ll[1], d.s);
      d.pop = Math.round(d.area * DENSITY[d.z] * (0.65 + 0.7 * hash(i, 31)));
      d.key = d.s + "|" + d.n;
      const s = initState(d);
      s.sensors = makeSensors(d);
      const rec = { d, s };
      this.D.push(rec);
      this.byKey.set(d.key, rec);
    });

    // upstream graph: nearby districts that sit higher in the same catchment
    const D = this.D;
    for (const { d } of D) {
      const up = [];
      for (const { d: o } of D) {
        if (o.i === d.i) continue;
        const dy = o.ll[0] - d.ll[0], dx = (o.ll[1] - d.ll[1]) * Math.cos(d.ll[0] * Math.PI / 180);
        const deg = Math.sqrt(dy * dy + dx * dx);
        if (deg < 2.2 && o.e > d.e + 120) up.push({ i: o.i, deg });
      }
      up.sort((a, b) => a.deg - b.deg);
      d.up = up.slice(0, 22).map(u => u.i);
      d.upArea = d.up.reduce((t, i) => t + D[i].d.area, 0) || 1;
    }

    this.t0 = new Date(CFG.startISO).getTime();
    this.h = -CFG.spinupHours;
    for (let k = 0; k < CFG.spinupHours; k++) {
      this.tick(k < CFG.spinupHours - 110 ? "cold" : "warm");
    }
  },

  /* mode: "cold" = spin-up only, "warm" = build history quietly,
     undefined = live (history + detection + repaint)                     */
  tick(mode) {
    Met.step(this.h);
    for (const r of this.D) stepHydrology(r.d, r.s, this.h);
    for (const r of this.D) score(r.d, r.s, this.h);
    for (const r of this.D) floodScore(r.d, r.s, this.D);
    if (mode !== "cold") {
      for (const r of this.D) {
        r.s.hist.push(r.s.p);
        r.s.satHist.push(r.s.store / r.s.cap);
        if (r.s.hist.length > 120) { r.s.hist.shift(); r.s.satHist.shift(); }
      }
    }
    if (!mode) this.detect();
    this.h++;
    if (!mode) this.listeners.forEach(f => f());
  },

  now() { return new Date(this.t0 + this.h * 3600e3); },

  /* automatic escalation detection — the part that runs unattended */
  detect() {
    for (const { d, s } of this.D) {
      if (d.tier === 3) continue;
      const c = catOf(s.p), cPrev = catOf(s.pPrev);
      const idx = CAT.indexOf(c), idxPrev = CAT.indexOf(cPrev);
      if (idx >= 3 && idx > idxPrev) {
        this.push({
          kind: "escalation", d, p: s.p, cat: c,
          msg: `${d.n} crossed into ${c.lab.toLowerCase()} risk`,
          detail: `${s.r24.toFixed(0)} mm in 24 h · profile ${(s.store / s.cap * 100).toFixed(0)}% saturated`,
        });
      }
      if (s.glof > 0.62 && hash(d.i, this.h) > 0.6) {
        this.push({ kind: "glof", d, p: s.glof, cat: CAT[3],
          msg: `Glacial lake watch — ${d.n}`,
          detail: `Melt ${(s.melt * 24).toFixed(1)} mm/day at ${d.e} m` });
      }
      if (s.flood > 0.70 && hash(d.i, this.h, 2) > 0.75) {
        this.push({ kind: "flood", d, p: s.flood, cat: CAT[3],
          msg: `River flooding likely — ${d.n}`,
          detail: `${s.r72.toFixed(0)} mm over 72 h with upstream contribution` });
      }
    }
    for (const q of Met.quakes) {
      if (q.h === this.h - 1) {
        this.push({ kind: "quake", p: 0.5, cat: CAT[2],
          msg: `M${q.mag} tremor recorded`,
          detail: `${q.lat.toFixed(2)}°N ${q.lon.toFixed(2)}°E — slope stability re-evaluated within 120 km` });
      }
    }
  },

  push(e) {
    e.t = this.now().getTime();
    e.id = "e" + this.h + "_" + this.events.length;
    this.events.unshift(e);
    if (this.events.length > 260) this.events.pop();
  },

  ranked(filterFn, sortKey) {
    let list = this.D.filter(r => r.d.tier !== 3 && (!filterFn || filterFn(r)));
    const key = {
      risk: r => r.s.p,
      rise: r => r.s.p - (r.s.hist.length > 6 ? r.s.hist[r.s.hist.length - 7] : r.s.p),
      rain: r => r.s.r24,
    }[sortKey] || (r => r.s.p);
    return list.sort((a, b) => key(b) - key(a));
  },

  national() {
    let sev = 0, hi = 0, pop = 0, wettest = null, peak = null;
    for (const r of this.D) {
      if (r.d.tier === 3) continue;
      const i = CAT.indexOf(catOf(r.s.p));
      if (i >= 3) { sev++; pop += r.d.pop; }
      else if (i === 2) hi++;
      if (!wettest || r.s.r24 > wettest.s.r24) wettest = r;
      if (!peak || r.s.p > peak.s.p) peak = r;
    }
    return { sev, hi, pop, wettest, peak };
  },
};
