/* ══════════════════════════════════════════════════════════════════════════
   Map — light-theme SVG choropleth, no tile server needed
   ══════════════════════════════════════════════════════════════════════════ */
const SVGNS = "http://www.w3.org/2000/svg";
const el = (n, a) => { const e = document.createElementNS(SVGNS, n); for (const k in a) e.setAttribute(k, a[k]); return e; };
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];

function hex2rgb(h) { const n = parseInt(h.slice(1), 16); return [n >> 16 & 255, n >> 8 & 255, n & 255]; }
function rampColor(stops, t) {
  t = clamp(t, 0, 0.9999) * (stops.length - 1);
  const i = Math.floor(t), f = t - i;
  const a = hex2rgb(stops[i]), b = hex2rgb(stops[Math.min(i + 1, stops.length - 1)]);
  return `rgb(${Math.round(lerp(a[0], b[0], f))},${Math.round(lerp(a[1], b[1], f))},${Math.round(lerp(a[2], b[2], f))})`;
}

/* Emerald-anchored so calm districts read as "safe" in the same language as
   the stat cards (emerald=low, amber=moderate, red=high) before climbing
   into the severe/extreme range the original palette didn't need to name. */
const RAMPS = {
  risk:  ["#e2e8f0", "#6ee7b7", "#f2c94c", "#f2994a", "#dc2626", "#7c1d6f"],
  flood: ["#e2e8f0", "#bae6fd", "#7dd3fc", "#38bdf8", "#2563eb", "#1e3a8a"],
  rain:  ["#e2e8f0", "#a7f3d0", "#5eead4", "#38bdf8", "#6366f1", "#7c3aed"],
  soil:  ["#f1e7c9", "#dcd399", "#a8d5ba", "#67c3b0", "#2e9ca6", "#1c5f8a"],
  snow:  ["#e2e8f0", "#c7d9e8", "#9cc0da", "#6fa3c9", "#3d6f9e", "#1c3f66"],
  ndvi:  ["#e7dcc0", "#d9d190", "#bcd08a", "#8fc06a", "#4f9e4e", "#256b32"],
  insar: ["#bfdbfe", "#93c5fd", "#a7c7a3", "#f2c94c", "#f2994a", "#b91c3c"],
  slope: ["#e2e8f0", "#cfe0c4", "#bcd08a", "#e0b25a", "#dc7f3f", "#b0303f"],
};
const LAYERS = {
  risk:  { t: "Landslide failure probability, next 24 h", v: r => r.s.p,     max: 1,   unit: "%", pct: true, gate: true, gamma: .62, cats: true },
  flood: { t: "River flood likelihood, next 72 h",         v: r => r.s.flood, max: 1,   unit: "%", pct: true, gamma: .7 },
  rain:  { t: "Rainfall, past 24 h (GPM IMERG)",            v: r => r.s.r24,   max: 220, unit: " mm", gamma: .65 },
  soil:  { t: "Root-zone soil saturation (SMAP L4)",        v: r => r.s.store / r.s.cap, max: 1, unit: "%", pct: true },
  snow:  { t: "Snow &amp; ice water equivalent (MODIS)",    v: r => r.s.swe,   max: 1800, unit: " mm" },
  ndvi:  { t: "Vegetation index (Sentinel-2 NDVI)",         v: r => (r.d.ndvi != null ? r.d.ndvi : 0.45) / 0.8, max: 1, unit: "" },
  insar: { t: "Ground displacement (Sentinel-1 InSAR)",     v: r => clamp(r.s.p * .7 + r.s.store / r.s.cap * .3, 0, 1), max: 1, unit: " mm/yr", scale: 48 },
  slope: { t: "Mean terrain slope (Cartosat DEM)",          v: r => r.d.sl / 45, max: 1, unit: "°", scale: 45 },
};

const Map3 = {
  svg: null, gRoot: null, gDist: null, gState: null, gOver: null, paths: [], layer: "risk",
  vb: null, view: null, sel: null, mount: null, tip: null,
  ov: { cells: true, sensors: false, reports: true },
  onSelect: null,

  init(geo) {
    this.geo = geo;
    this.vb = geo.vb.slice(); this.view = geo.vb.slice();
    const svg = el("svg", { id: "map", viewBox: this.view.join(" "), preserveAspectRatio: "xMidYMid meet",
      style: "width:100%;height:100%;display:block" });
    this.svg = svg;
    svg.appendChild(el("rect", { x: this.vb[0], y: this.vb[1], width: this.vb[2], height: this.vb[3], fill: "#eef2f6" }));

    const defs = el("defs");
    const pat = el("pattern", { id: "nodata", width: 5, height: 5, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" });
    pat.appendChild(el("rect", { width: 5, height: 5, fill: "#f1f5f9" }));
    pat.appendChild(el("rect", { width: 2, height: 5, fill: "#cbd5e1" }));
    defs.appendChild(pat);
    const rg = el("radialGradient", { id: "cellg" });
    rg.appendChild(el("stop", { offset: "0%", "stop-color": "#38bdf8", "stop-opacity": ".30" }));
    rg.appendChild(el("stop", { offset: "60%", "stop-color": "#2563eb", "stop-opacity": ".12" }));
    rg.appendChild(el("stop", { offset: "100%", "stop-color": "#2563eb", "stop-opacity": "0" }));
    defs.appendChild(rg);
    svg.appendChild(defs);

    this.gRoot = el("g");
    this.gDist = el("g"); this.gState = el("g"); this.gOver = el("g");
    this.gRoot.append(this.gDist, this.gState, this.gOver);
    svg.appendChild(this.gRoot);

    const frag = document.createDocumentFragment();
    World.D.forEach(r => { const p = el("path", { d: r.d.p, class: "dist" }); p.__r = r; frag.appendChild(p); this.paths.push(p); });
    this.gDist.appendChild(frag);
    const sf = document.createDocumentFragment();
    for (const k in geo.states) sf.appendChild(el("path", { d: geo.states[k].p, class: "state" }));
    this.gState.appendChild(sf);

    this.bindPointer();
    this.reveal();
  },

  /* SVG elements can only live in one place; when a tab switches we move
     the same node rather than rebuild the map. */
  mountInto(containerId) {
    const host = document.getElementById(containerId);
    if (!host || this.mount === host) return;
    host.innerHTML = "";
    host.style.position = "relative";
    host.appendChild(this.svg);
    if (!this.tip) {
      this.tip = document.createElement("div");
      this.tip.className = "maptip";
      document.body.appendChild(this.tip);
    }
    this.mount = host;
    this.zoomCtl(host);
    this.legend(host);
  },

  zoomCtl(host) {
    let z = host.querySelector(".zctl");
    if (z) return;
    z = document.createElement("div");
    z.className = "zctl absolute bottom-3 left-3 flex flex-col gap-1 z-10";
    z.innerHTML = `<button class="w-7 h-7 bg-white border border-slate-200 rounded-lg shadow-xs text-sm font-bold text-slate-600" data-zin>+</button>
      <button class="w-7 h-7 bg-white border border-slate-200 rounded-lg shadow-xs text-sm font-bold text-slate-600" data-zout>−</button>
      <button class="w-7 h-7 bg-white border border-slate-200 rounded-lg shadow-xs text-[11px] font-bold text-slate-600" data-zreset>⌂</button>`;
    z.querySelector("[data-zin]").onclick = () => this.zoom(0.7);
    z.querySelector("[data-zout]").onclick = () => this.zoom(1.42);
    z.querySelector("[data-zreset]").onclick = () => this.setView(this.vb.slice(), true);
    host.appendChild(z);
  },

  legend(host) {
    let lg = host.querySelector(".mlegend");
    if (lg) return;
    lg = document.createElement("div");
    lg.className = "mlegend absolute bottom-3 right-3 bg-white/95 backdrop-blur border border-slate-200 rounded-xl px-3 py-2.5 shadow-sm z-10 max-w-[190px]";
    lg.innerHTML = `<div class="text-[10px] text-slate-500 mb-1.5" id="legTitle">—</div>
      <div class="flex h-1.5 rounded overflow-hidden mb-1" id="legRamp"></div>
      <div class="flex justify-between text-[9.5px] text-slate-400" id="legScale"><span>Low</span><span>High</span><span>Extreme</span></div>
      <div class="mt-1.5 pt-1.5 border-t border-slate-100 flex items-center gap-1.5 text-[9.5px] text-slate-400" id="legNote">
        <i class="w-2.5 h-2.5 rounded-sm flex-shrink-0" style="background:repeating-linear-gradient(45deg,#f1f5f9 0 2px,#cbd5e1 2px 4px)"></i>
        No calibrated prediction — plains
      </div>`;
    host.appendChild(lg);
  },

  proj(lat, lon) {
    const P = this.geo.proj;
    const mlat = -Math.log(Math.tan(Math.PI / 4 + clamp(lat, -84, 84) * Math.PI / 360));
    return [P.ox + (lon * Math.PI / 180 - P.mx0) * P.s, P.oy + (mlat - P.my0) * P.s];
  },

  reveal() {
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    this.paint();
    if (reduce) return;
    this.paths.forEach(p => p.style.fillOpacity = "0");
    const order = this.paths.map(p => ({ p, d: p.__r.d.ll[1] * .35 - p.__r.d.ll[0] * 1.0 + p.__r.d.sl * .06 }));
    const lo = Math.min(...order.map(o => o.d)), hi = Math.max(...order.map(o => o.d));
    const t0 = performance.now(), DUR = 1000;
    const step = now => {
      const t = clamp((now - t0) / DUR, 0, 1);
      const front = lerp(hi, lo, t);
      for (const o of order) if (o.d >= front - (hi - lo) * .18) o.p.style.fillOpacity = "";
      if (t < 1) requestAnimationFrame(step); else this.paths.forEach(p => p.style.fillOpacity = "");
    };
    requestAnimationFrame(step);
  },

  paint() {
    const L = LAYERS[this.layer], ramp = RAMPS[this.layer];
    for (const p of this.paths) {
      const r = p.__r;
      if (L.gate && r.d.tier === 3) { p.style.fill = "url(#nodata)"; continue; }
      let t = L.max === 1 ? L.v(r) : L.v(r) / L.max;
      if (L.gamma) t = Math.pow(clamp(t, 0, 1), L.gamma);
      p.style.fill = rampColor(ramp, t);
    }
    this.overlays();
    const lg = document.getElementById("legTitle"); if (lg) lg.innerHTML = L.t;
    const rr = document.getElementById("legRamp"); if (rr) rr.innerHTML = ramp.map(c => `<i style="flex:1;background:${c}"></i>`).join("");
    const sc = document.getElementById("legScale");
    if (sc) sc.innerHTML = L.cats ? `<span>Low</span><span>High</span><span>Extreme</span>`
      : L.pct ? `<span>0%</span><span>50%</span><span>100%</span>`
      : `<span>0</span><span>${Math.round((L.scale || L.max) / 2)}</span><span>${Math.round(L.scale || L.max)}${L.unit}</span>`;
    const nt = document.getElementById("legNote"); if (nt) nt.style.display = L.gate ? "" : "none";
  },

  overlays() {
    const g = this.gOver; g.textContent = "";
    if (this.ov.cells) for (const c of Met.cells) {
      if (!c.now || c.now < 1.5) continue;
      const [x, y] = this.proj(c.lat, c.lon), rr = c.r * this.geo.proj.s * Math.PI / 180 * .85;
      g.appendChild(el("circle", { class: "cell", cx: x, cy: y, r: rr, fill: "url(#cellg)" }));
    }
    for (const q of Met.quakes) {
      const [x, y] = this.proj(q.lat, q.lon), age = World.h - q.h, rr = 6 + age * 2.2;
      g.appendChild(el("circle", { class: "quake", cx: x, cy: y, r: rr, fill: "none", stroke: "#dc2626",
        "stroke-opacity": Math.max(0, .8 - age / 20), "stroke-width": 1.2, "vector-effect": "non-scaling-stroke" }));
      g.appendChild(el("circle", { class: "quake", cx: x, cy: y, r: 2, fill: "#dc2626" }));
    }
    if (this.ov.sensors) for (const r of World.D) {
      if (!r.s.sensors) continue;
      for (const sn of r.s.sensors) {
        const [x, y] = this.proj(sn.lat, sn.lon);
        g.appendChild(el("rect", { class: "cell", x: x - 1.6, y: y - 1.6, width: 3.2, height: 3.2,
          fill: sn.batt > 55 ? "#059669" : "#d97706", stroke: "#fff", "stroke-width": .5, "vector-effect": "non-scaling-stroke" }));
      }
    }
    if (this.ov.reports) for (const rep of (typeof Store !== "undefined" ? Store.reports : [])) {
      const rec = World.byKey.get(rep.key); if (!rec) continue;
      const [x, y] = this.proj(rec.d.ll[0], rec.d.ll[1]);
      g.appendChild(el("path", { class: "cell", d: `M${x},${y - 4.4}L${x + 3.8},${y + 2.4}L${x - 3.8},${y + 2.4}Z`,
        fill: rep.sev >= 3 ? "#dc2626" : "#d97706", stroke: "#fff", "stroke-width": .6, "vector-effect": "non-scaling-stroke" }));
    }
    if (this.sel) { this.paths.forEach(q => q.classList.remove("sel")); this.paths[this.sel.d.i].classList.add("sel"); this.gDist.appendChild(this.paths[this.sel.d.i]); }
  },

  select(rec) { this.sel = rec; this.overlays(); if (this.onSelect) this.onSelect(rec); },

  fitTo(bboxDeg) {
    const a = this.proj(bboxDeg[1], bboxDeg[0]), b = this.proj(bboxDeg[3], bboxDeg[2]);
    const x0 = Math.min(a[0], b[0]), x1 = Math.max(a[0], b[0]), y0 = Math.min(a[1], b[1]), y1 = Math.max(a[1], b[1]);
    const pad = Math.max(x1 - x0, y1 - y0) * .18 + 6;
    this.setView([x0 - pad, y0 - pad, (x1 - x0) + pad * 2, (y1 - y0) + pad * 2], true);
  },

  setView(v, animate) {
    const from = this.view.slice();
    v[2] = clamp(v[2], this.vb[2] * .025, this.vb[2] * 1.6); v[3] = v[2] * (this.vb[3] / this.vb[2]);
    if (!animate) { this.view = v; this.svg.setAttribute("viewBox", v.join(" ")); return; }
    const t0 = performance.now(), DUR = 360;
    const step = now => {
      const t = clamp((now - t0) / DUR, 0, 1), e = 1 - Math.pow(1 - t, 3);
      this.view = from.map((f, i) => lerp(f, v[i], e));
      this.svg.setAttribute("viewBox", this.view.join(" "));
      if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  },

  zoom(f, cx, cy) {
    const v = this.view.slice(), mx = cx != null ? cx : v[0] + v[2] / 2, my = cy != null ? cy : v[1] + v[3] / 2;
    const nw = clamp(v[2] * f, this.vb[2] * .025, this.vb[2] * 1.6), nh = nw * (v[3] / v[2]);
    this.setView([mx - (mx - v[0]) * (nw / v[2]), my - (my - v[1]) * (nh / v[3]), nw, nh]);
  },

  toSvg(ev) {
    const r = this.svg.getBoundingClientRect();
    const sc = Math.max(this.view[2] / r.width, this.view[3] / r.height);
    const ox = this.view[0] + this.view[2] / 2 - (r.width / 2) * sc, oy = this.view[1] + this.view[3] / 2 - (r.height / 2) * sc;
    return [ox + (ev.clientX - r.left) * sc, oy + (ev.clientY - r.top) * sc];
  },

  bindPointer() {
    const svg = this.svg;
    let drag = null, pts = new Map(), pinch = null;
    svg.addEventListener("pointerdown", e => {
      svg.setPointerCapture(e.pointerId); pts.set(e.pointerId, e);
      if (pts.size === 2) { const [a, b] = [...pts.values()]; pinch = { d: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY), v: this.view.slice() }; }
      else drag = { x: e.clientX, y: e.clientY, v: this.view.slice(), moved: 0 };
    });
    svg.addEventListener("pointermove", e => {
      if (pts.has(e.pointerId)) pts.set(e.pointerId, e);
      if (pinch && pts.size === 2) {
        const [a, b] = [...pts.values()], d = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
        const f = clamp(pinch.d / d, .3, 3), v = pinch.v;
        this.setView([v[0] + v[2] * (1 - f) / 2, v[1] + v[3] * (1 - f) / 2, v[2] * f, v[3] * f]);
        return;
      }
      if (drag) {
        const r = svg.getBoundingClientRect(), sc = Math.max(drag.v[2] / r.width, drag.v[3] / r.height);
        drag.moved += Math.abs(e.movementX) + Math.abs(e.movementY);
        if (drag.moved > 4) svg.classList.add("drag");
        this.setView([drag.v[0] - (e.clientX - drag.x) * sc, drag.v[1] - (e.clientY - drag.y) * sc, drag.v[2], drag.v[3]]);
        return;
      }
      const t = e.target;
      if (t.classList && t.classList.contains("dist") && this.mount) {
        const r = t.__r, w = this.mount.getBoundingClientRect(), L = LAYERS[this.layer];
        const noPred = L.gate && r.d.tier === 3;
        const val = noPred ? "—" : (L.pct ? (L.v(r) * 100).toFixed(0) + "%" : (L.max === 1 ? (L.v(r) * (L.scale || 1)).toFixed(1) : L.v(r).toFixed(0)) + L.unit);
        this.tip.innerHTML = `<b>${r.d.n}</b><div class="s">${r.d.s} · ${ZONE_LABEL[r.d.z]}</div>
          <div class="v"><span>Value</span><b class="num" style="color:#fff">${val}</b></div>
          <div class="v"><span>24h rain</span><b class="num" style="color:#fff">${r.s.r24.toFixed(0)} mm</b></div>`;
        this.tip.classList.add("on");
        this.tip.style.left = clamp(e.clientX + 14, 4, innerWidth - 240) + "px";
        this.tip.style.top = clamp(e.clientY + 14, 4, innerHeight - 100) + "px";
      } else this.tip && this.tip.classList.remove("on");
    });
    const end = e => {
      pts.delete(e.pointerId); if (pts.size < 2) pinch = null;
      if (drag && drag.moved < 5 && e.target.classList && e.target.classList.contains("dist")) this.select(e.target.__r);
      drag = null; svg.classList.remove("drag");
    };
    svg.addEventListener("pointerup", end); svg.addEventListener("pointercancel", end);
    svg.addEventListener("pointerleave", () => this.tip && this.tip.classList.remove("on"));
    svg.addEventListener("wheel", e => { e.preventDefault(); const [mx, my] = this.toSvg(e); this.zoom(e.deltaY > 0 ? 1.18 : .85, mx, my); }, { passive: false });
  },
};
