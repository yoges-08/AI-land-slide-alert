/* ══════════════════════════════════════════════════════════════════════════
   Icons (inline, lucide-style — no external icon font needed)
   ══════════════════════════════════════════════════════════════════════════ */
const ICO = {
  dashboard: '<path d="M3 3h8v8H3zM13 3h8v5h-8zM13 12h8v9h-8zM3 15h8v6H3z"/>',
  map: '<path d="M9 20 3 17V4l6 3m0 13 6-3m-6 3V7m6 10 6 3V7l-6-3m0 16V4m0 3L9 4"/>',
  chart: '<path d="M3 3v18h18M7 16l4-6 3 3 5-8"/>',
  cloud: '<path d="M17.5 19a4.5 4.5 0 0 0 0-9 6 6 0 0 0-11.6 1.7A4 4 0 0 0 6 19z"/><path d="M12 22v-3M8 22v-1M16 22v-1"/>',
  bell: '<path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
  field: '<path d="M12 2 2 7l10 5 10-5-10-5Z"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>',
  lightbulb: '<path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.2 1 2.3h6c0-1.1.4-1.8 1-2.3A7 7 0 0 0 12 2Z"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  check: '<path d="m20 6-11 11-5-5"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/>',
  alert: '<path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/>',
  shield: '<path d="M12 2 4 5v6c0 5 3.5 8.5 8 11 4.5-2.5 8-6 8-11V5l-8-3Z"/>',
  trend: '<path d="M23 6l-9.5 9.5-5-5L1 18"/><path d="M17 6h6v6"/>',
  sat: '<rect x="8" y="8" width="8" height="8" rx="1"/><path d="m5 5 3 3M19 5l-3 3M5 19l3-3M19 19l-3-3"/>',
};
const ico = (k, cls) => `<svg viewBox="0 0 24 24" class="${cls || "w-4 h-4"}" fill="none" stroke="currentColor" stroke-width="2">${ICO[k]}</svg>`;

const NAV = [
  { id: "dashboard", label: "Dashboard", icon: "dashboard" },
  { id: "live-map", label: "Live Map", icon: "map" },
  { id: "risk-analysis", label: "Risk Analysis", icon: "chart" },
  { id: "weather", label: "Weather & Satellite", icon: "cloud" },
  { id: "alerts", label: "Alerts", icon: "bell", badge: true },
  { id: "field", label: "Field Reports", icon: "field", badge2: true },
  { id: "recs", label: "Recommendations", icon: "lightbulb" },
];

const UI = {
  tab: "dashboard", filterState: "", filterDist: "", filterTier: "", query: "",

  boot() {
    this.buildNav();
    this.buildFilters();
    this.buildLayerChips();
    Map3.onSelect = rec => this.onSelect(rec);
    const top = World.ranked(null, "risk")[0];
    Map3.select(top);
    this.bind();
    this.setTab("dashboard");
    this.tickUI();
    setInterval(() => World.tick(), CFG.tickMs);
    this.renderRecs();
  },

  buildNav() {
    const row = (item, mobile) => `<button data-tab="${item.id}" class="navbtn w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all duration-150 text-slate-400 hover:text-slate-100 hover:bg-slate-800/60">
      <span class="flex items-center gap-3">${ico(item.icon, "w-4 h-4")}<span>${item.label}</span></span>
      ${item.badge ? `<span class="navbadge-a bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center hidden"></span>` : ""}
      ${item.badge2 ? `<span class="navbadge-b bg-amber-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center hidden"></span>` : ""}
    </button>`;
    $("#navList").innerHTML = NAV.map(n => row(n)).join("");
    $("#navListMobile").innerHTML = NAV.map(n => row(n, true)).join("");
    $("#mobNav").innerHTML = NAV.slice(0, 4).map(n => `<button data-tab="${n.id}" class="mobbtn py-2.5 flex flex-col items-center gap-0.5 text-slate-400 border-t-2 border-transparent">
      ${ico(n.icon, "w-4 h-4")}<span class="text-[9px] font-medium">${n.label.split(" ")[0]}</span></button>`).join("");
  },

  setTab(id) {
    this.tab = id;
    $$(".tab-panel").forEach(p => p.classList.toggle("active", p.id === "tab-" + id));
    $$(".navbtn").forEach(b => {
      const on = b.dataset.tab === id;
      b.classList.toggle("bg-emerald-700/80", on); b.classList.toggle("text-white", on); b.classList.toggle("shadow-sm", on);
      b.classList.toggle("text-slate-400", !on);
    });
    $$(".mobbtn").forEach(b => {
      const on = b.dataset.tab === id;
      b.classList.toggle("text-emerald-700", on); b.classList.toggle("border-emerald-600", on); b.classList.toggle("text-slate-400", !on);
    });
    if (id === "dashboard") { Map3.mountInto("mapWrapDash"); this.donut(); this.rainChart(); this.highRiskTable(); }
    if (id === "live-map") Map3.mountInto("mapWrapFull");
    if (id === "risk-analysis") this.risingTable();
    if (id === "weather") { this.feedGrid(); this.weatherGrid(); }
    if (id === "alerts") { this.alertPreview(); this.alertLog(); }
    if (id === "field") { this.syncBar(); this.reportList(); }
    this.closeMobNav();
    if (Map3.sel) this.locationCard();
    Map3.paint();
  },

  closeMobNav() {
    $("#mobSidebar").classList.add("-translate-x-full");
    $("#navScrim").classList.remove("on");
  },

  /* ── cascade filters ─────────────────────────────────────────────────── */
  buildFilters() {
    const states = [...new Set(World.D.map(r => r.d.s))].sort();
    const ss = $("#selState"); states.forEach(s => ss.add(new Option(s, s)));
    this.buildDistPicker("#frDist");
    this.buildDistPicker("#alDist");
    $("#covLine").textContent = `${states.length} states & UTs · ${World.D.length} districts monitored`;
  },
  /* Every district, grouped by state so all 726 are reachable — not just the
     top-400-by-risk slice this used to show. Narrows to the state chosen in
     the cascade filter above, same as the "District" dropdown does. */
  buildDistPicker(sel) {
    const el = $(sel);
    const prev = el.value;
    el.innerHTML = "";
    const states = this.filterState ? [this.filterState] : [...new Set(World.D.map(r => r.d.s))].sort();
    for (const st of states) {
      const grp = document.createElement("optgroup"); grp.label = st;
      World.D.filter(r => r.d.s === st).sort((a, b) => a.d.n.localeCompare(b.d.n))
        .forEach(r => grp.appendChild(new Option(r.d.n, r.d.key)));
      el.appendChild(grp);
    }
    if ([...el.options].some(o => o.value === prev)) el.value = prev;
  },
  refreshDistricts() {
    const sel = $("#selDist"); sel.innerHTML = "";
    if (!this.filterState) { sel.disabled = true; sel.add(new Option("Select state first", "")); return; }
    sel.disabled = false; sel.add(new Option("All districts in state", ""));
    World.D.filter(r => r.d.s === this.filterState).sort((a, b) => a.d.n.localeCompare(b.d.n))
      .forEach(r => sel.add(new Option(r.d.n, r.d.key)));
  },
  filterFn() {
    const q = this.query.trim().toLowerCase();
    return r => (!this.filterState || r.d.s === this.filterState)
      && (!this.filterDist || r.d.key === this.filterDist)
      && (!this.filterTier || (this.filterTier === "high" ? r.s.p >= .25 : this.filterTier === "moderate" ? (r.s.p >= .10 && r.s.p < .25) : r.s.p < .10))
      && (!q || r.d.n.toLowerCase().includes(q) || r.d.s.toLowerCase().includes(q));
  },

  /* ── map layer chips (duplicated on dashboard + live-map tab) ───────── */
  buildLayerChips() {
    const defs = [["risk", "Landslide risk"], ["flood", "Flood"], ["rain", "Rainfall"], ["soil", "Soil moisture"],
      ["snow", "Snow & melt"], ["ndvi", "Vegetation"], ["insar", "Ground motion"], ["slope", "Slope"]];
    const html = defs.map(([k, l], i) => `<button class="chip lchip" data-layer="${k}" aria-pressed="${i === 0}">${l}</button>`).join("");
    $("#layerChips").innerHTML = html; $("#layerChips2").innerHTML = html;
    $("#overlayChips2").innerHTML = `<button class="chip ochip" data-ov="cells" aria-pressed="true">Storm cells</button>
      <button class="chip ochip" data-ov="sensors" aria-pressed="false">Sensors</button>
      <button class="chip ochip" data-ov="reports" aria-pressed="true">Field reports</button>`;
    $$(".lchip").forEach(b => b.onclick = () => {
      Map3.layer = b.dataset.layer;
      $$(".lchip").forEach(x => x.setAttribute("aria-pressed", x.dataset.layer === b.dataset.layer));
      Map3.paint();
    });
    $$(".ochip").forEach(b => b.onclick = () => {
      const on = b.getAttribute("aria-pressed") !== "true";
      b.setAttribute("aria-pressed", on); Map3.ov[b.dataset.ov] = on; Map3.overlays();
    });
  },
  /* ── stat cards + weather card ──────────────────────────────────────── */
  statCards() {
    const list = World.D.filter(this.filterFn());
    const scoped = (fn) => this.filterState || this.filterDist || this.filterTier ? list.filter(fn).length : World.D.filter(fn).length;
    const high = World.D.filter(r => r.d.tier !== 3 && r.s.p >= .25).length;
    const mod = World.D.filter(r => r.d.tier !== 3 && r.s.p >= .10 && r.s.p < .25).length;
    const low = World.D.filter(r => r.d.tier === 3 || r.s.p < .10).length;
    const card = (title, value, sub, type, tab) => {
      const map = {
        total: ["bg-emerald-50 text-emerald-600 border-emerald-200", "target", "text-emerald-600"],
        high: ["bg-red-50 text-red-600 border-red-200", "alert", "text-red-500"],
        moderate: ["bg-amber-50 text-amber-600 border-amber-200", "clock", "text-amber-500"],
        low: ["bg-emerald-50 text-emerald-600 border-emerald-200", "shield", "text-emerald-600"],
      }[type];
      return `<div data-goto-tier="${tab || ""}" class="bg-white rounded-xl p-4 border border-slate-200/90 shadow-sm flex items-start gap-3.5 cursor-pointer hover:border-slate-300 hover:shadow transition-all">
        <div class="p-2.5 rounded-xl border flex items-center justify-center flex-shrink-0 ${map[0]}">${ico(map[1], "w-5 h-5")}</div>
        <div class="flex-1 min-w-0">
          <p class="text-[11px] font-medium text-slate-500 truncate leading-none mb-1">${title}</p>
          <div class="flex items-baseline gap-2"><span class="text-2xl font-bold text-slate-900 tracking-tight leading-none num">${value}</span></div>
          <p class="text-[10px] text-slate-400 mt-1 truncate leading-none">${sub}</p>
        </div></div>`;
    };
    $("#statRow").innerHTML = card("Total districts / sites", World.D.length, "28 states & 8 UTs", "total")
      + card("High-risk districts", high, "Himalayan & Ghats corridor", "high", "high")
      + card("Moderate risk", mod, "Under rainfall observation", "moderate", "moderate")
      + card("Low hazard / plains", low, "Generally non-mountainous", "low", "low")
      + this.weatherCardHtml();
    $$("[data-goto-tier]").forEach(c => c.onclick = () => {
      const t = c.dataset.gotoTier;
      if (t) { this.filterTier = t; $("#selTier").value = t; this.applyFilterUI(); }
      this.setTab("live-map");
    });
  },

  weatherCardHtml() {
    const rec = Map3.sel; if (!rec) return "";
    const { d, s } = rec;
    return `<div class="bg-gradient-to-br from-sky-600 to-sky-700 rounded-xl p-4 text-white shadow-sm cursor-pointer" data-goto="weather">
      <div class="flex items-center justify-between">
        <p class="text-[11px] font-medium text-sky-100 truncate">${d.n}, ${d.s}</p>
        ${ico("cloud", "w-4 h-4 text-sky-200")}
      </div>
      <div class="flex items-baseline gap-1 mt-1"><span class="text-2xl font-bold num">${s.temp.toFixed(0)}°</span><span class="text-[11px] text-sky-200">air temp</span></div>
      <p class="text-[10px] text-sky-200 mt-1">Rain 24h <b class="num">${s.r24.toFixed(0)}mm</b> · Sat <b class="num">${(s.store / s.cap * 100).toFixed(0)}%</b></p>
    </div>`;
  },

  /* ── location details card (dashboard + live-map) ───────────────────── */
  onSelect(rec) {
    this.locationCard();
    if (this.tab === "dashboard") { this.donut(); this.rainChart(); this.highRiskTable(); }
    if (this.tab === "risk-analysis") this.risingTable();
    $("#btnInspectTxt").textContent = `Inspect ${rec.d.n}`;
  },

  locationCard() {
    const rec = Map3.sel; if (!rec) return;
    const { d, s } = rec, c = catOf(s.p);
    const chip = (lab, on) => `<span class="text-[10px] px-2 py-0.5 rounded-full font-medium ${on ? "text-white" : "bg-slate-100 text-slate-600"}"${on ? ` style="background:${c.c}"` : ""}>${lab}</span>`;
    let body;
    if (d.tier === 3) {
      body = `<div class="p-4 text-xs text-slate-500 leading-relaxed">
        <p class="font-bold text-slate-800 mb-1.5">Insufficient data for a landslide prediction</p>
        This district sits on flat to gently undulating terrain with no recorded slope-failure inventory. Publishing a score here would be uncalibrated guesswork.
        <div class="grid grid-cols-2 gap-2 mt-3">
          ${this.mcell("Rain 24h", s.r24.toFixed(0), "mm")}${this.mcell("Flood risk", (s.flood * 100).toFixed(0), "%")}
        </div></div>`;
    } else {
      const R = 26, C = 2 * Math.PI * R;
      body = `<div class="p-4 flex items-center gap-3 border-b border-slate-100">
          <svg width="62" height="62" viewBox="0 0 62 62">
            <circle cx="31" cy="31" r="${R}" fill="none" stroke="#f1f5f9" stroke-width="6"/>
            <circle cx="31" cy="31" r="${R}" fill="none" stroke="${c.c}" stroke-width="6" stroke-linecap="round"
              stroke-dasharray="${(s.p * C).toFixed(1)} ${C}" transform="rotate(-90 31 31)"/>
          </svg>
          <div><div class="text-2xl font-bold num" style="color:${c.c}">${(s.p * 100).toFixed(0)}%</div>
            <div class="text-[11px] font-semibold" style="color:${c.c}">${c.lab} risk</div>
            <div class="text-[10px] text-slate-400">±${(s.unc * 100).toFixed(0)} pt spread · FS ${s.fs.toFixed(2)}</div></div>
        </div>
        <div class="grid grid-cols-2 gap-2 p-4 pt-3">
          ${this.mcell("Rain 24h", s.r24.toFixed(0), "mm")}${this.mcell("Rain 72h", s.r72.toFixed(0), "mm")}
          ${this.mcell("Saturation", (s.store / s.cap * 100).toFixed(0), "%")}${this.mcell("Slope", d.sl, "°")}
          ${this.mcell("Flood risk", (s.flood * 100).toFixed(0), "%")}${this.mcell("Snow/ice", s.swe.toFixed(0), "mm")}
        </div>
        <div class="px-4 pb-4 flex gap-2">
          <button data-open-shap class="flex-1 px-2 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-[11px] font-semibold">SHAP analysis</button>
          <button data-open-sim class="flex-1 px-2 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-[11px] font-semibold">Simulate</button>
        </div>`;
    }
    const html = `<div class="bg-white rounded-2xl border border-slate-200/90 shadow-sm h-full flex flex-col overflow-hidden">
      <div class="p-4 pb-3 border-b border-slate-100">
        <div class="flex items-start justify-between gap-2">
          <div><h3 class="text-sm font-bold text-slate-900">${d.n}</h3><p class="text-[11px] text-slate-500">${d.s} · ${d.ll[0].toFixed(2)}°N ${d.ll[1].toFixed(2)}°E</p></div>
          <button data-open-ai class="p-1.5 text-slate-400 hover:text-emerald-700 hover:bg-emerald-50 rounded-lg flex-shrink-0" title="Ask the AI analyst">${ico("sat", "w-4 h-4")}</button>
        </div>
        <div class="flex flex-wrap gap-1 mt-2">
          ${chip(d.tier === 1 ? "Tier 1 · Full monitoring" : d.tier === 2 ? "Tier 2 · Screening" : "Tier 3 · No model", d.tier !== 3)}
          ${chip(ZONE_LABEL[d.z], false)}${chip("Seismic zone " + ["", "I", "II", "III", "IV", "V"][d.seis], false)}
        </div>
      </div>
      <div class="flex-1 overflow-y-auto">${body}</div>
    </div>`;
    $("#locDetailsSlot").innerHTML = html;
    $("#locDetailsSlot2").innerHTML = html;
    [$("#locDetailsSlot"), $("#locDetailsSlot2")].forEach(slot => {
      slot.querySelector("[data-open-shap]")?.addEventListener("click", () => this.openShap());
      slot.querySelector("[data-open-sim]")?.addEventListener("click", () => this.openSim());
      slot.querySelector("[data-open-ai]")?.addEventListener("click", () => this.openAI());
    });
  },
  mcell: (k, v, u) => `<div class="bg-slate-50 border border-slate-100 rounded-lg px-2.5 py-2">
    <div class="text-[9.5px] text-slate-400">${k}</div><div class="text-[13px] font-bold text-slate-800 num">${v}<span class="text-[9.5px] font-normal text-slate-400"> ${u}</span></div></div>`,

  /* ── right column: alert list + outlook ─────────────────────────────── */
  rightCol() {
    const recent = Store.alerts.slice(0, 4);
    const alertsHtml = `<div class="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-4">
      <div class="flex items-center justify-between mb-2.5"><h3 class="text-xs font-bold text-slate-800">Recent alerts</h3>
        <button class="text-[10.5px] font-semibold text-emerald-700 hover:underline" data-goto="alerts">View all</button></div>
      <div class="space-y-2">${recent.length ? recent.map(a => `<div class="flex items-start gap-2.5">
          <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" style="background:${a.color}22;color:${a.color}">${ico("alert", "w-3.5 h-3.5")}</div>
          <div class="min-w-0"><p class="text-[11px] font-semibold text-slate-800 truncate">${a.level} — ${a.dist}</p>
            <p class="text-[10px] text-slate-400">${a.state} · ${a.pct}% · ${a.reach.toLocaleString("en-IN")} reached</p></div>
        </div>`).join("") : `<p class="text-[11px] text-slate-400">No alerts dispatched yet.</p>`}</div>
    </div>`;

    const rec = Map3.sel;
    const fc = rec ? forecast(rec, 24) : [];
    const peak = fc.length ? fc.reduce((a, b) => b.p > a.p ? b : a, fc[0]) : null;
    const outlookHtml = `<div class="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-4 flex-1">
      <div class="flex items-center justify-between mb-1"><h3 class="text-xs font-bold text-slate-800">24-hour outlook</h3>
        <span class="text-[10px] text-slate-400">${rec ? rec.d.n : "—"}</span></div>
      ${peak ? `<p class="text-[10.5px] text-slate-400 mb-2">peak <b class="num" style="color:${catOf(peak.p).c}">${(peak.p * 100).toFixed(0)}%</b> at +${peak.k}h · rain <b class="num">${fc.reduce((t, f) => t + f.rain, 0).toFixed(0)}mm</b></p>` : ""}
      <svg viewBox="0 0 280 90" class="w-full h-[90px]" id="outlookSvg"></svg>
    </div>`;
    $("#rightColSlot").innerHTML = alertsHtml + outlookHtml;
    if (rec) this.drawOutlook(rec, fc);
    $$("[data-goto]").forEach(b => b.onclick = () => this.setTab(b.dataset.goto));
  },

  drawOutlook(rec, fc) {
    const svg = $("#outlookSvg"); if (!svg) return;
    const { s } = rec, W = 280, H = 90, PAST = 24, n = PAST + fc.length, xw = W / n;
    const past = []; for (let k = PAST; k >= 1; k--) past.push(s.hist[s.hist.length - k] ?? s.p);
    const series = past.concat(fc.map(f => f.p));
    const y = v => H - 10 - v * (H - 20);
    const pts = series.map((v, i) => `${(i * xw + xw / 2).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
    const fx = PAST * xw;
    svg.innerHTML = `<rect x="${fx}" y="0" width="${W - fx}" height="${H}" fill="#059669" opacity=".05"/>
      <line x1="${fx}" y1="0" x2="${fx}" y2="${H - 8}" stroke="#94a3b8" stroke-width="1"/>
      <polyline fill="none" stroke="${catOf(s.p).c}" stroke-width="2" stroke-linejoin="round" points="${pts}"/>`;
  },

  /* ── donut, rain chart, high-risk table ─────────────────────────────── */
  donut() {
    const cats = { Low: 0, Moderate: 0, High: 0, Severe: 0, Extreme: 0 };
    for (const r of World.D) { if (r.d.tier === 3) continue; cats[catOf(r.s.p).lab]++; }
    const colors = { Low: "#059669", Moderate: "#d97706", High: "#f97316", Severe: "#dc2626", Extreme: "#86198f" };
    const total = Object.values(cats).reduce((a, b) => a + b, 0) || 1;
    let acc = 0, R = 46, cx = 60, cy = 60, segs = "";
    for (const k in cats) {
      const v = cats[k]; if (!v) continue;
      const a0 = acc / total * 2 * Math.PI - Math.PI / 2, a1 = (acc + v) / total * 2 * Math.PI - Math.PI / 2;
      const large = (v / total) > .5 ? 1 : 0;
      const x0 = cx + R * Math.cos(a0), y0 = cy + R * Math.sin(a0), x1 = cx + R * Math.cos(a1), y1 = cy + R * Math.sin(a1);
      segs += `<path d="M${cx},${cy} L${x0.toFixed(1)},${y0.toFixed(1)} A${R},${R} 0 ${large} 1 ${x1.toFixed(1)},${y1.toFixed(1)} Z" fill="${colors[k]}"/>`;
      acc += v;
    }
    const legend = Object.entries(cats).map(([k, v]) => `<div class="flex items-center gap-1.5 text-[10.5px] text-slate-600">
      <i class="w-2.5 h-2.5 rounded-sm flex-shrink-0" style="background:${colors[k]}"></i>${k}<span class="ml-auto font-semibold num">${v}</span></div>`).join("");
    $("#riskDonut").innerHTML = `<div class="flex items-center gap-4">
      <svg width="120" height="120" viewBox="0 0 120 120"><circle cx="60" cy="60" r="46" fill="#f8fafc"/>${segs}<circle cx="60" cy="60" r="24" fill="#fff"/></svg>
      <div class="flex-1 space-y-1">${legend}</div></div>`;
  },

  rainChart() {
    const rec = Map3.sel; if (!rec) return;
    $("#rainTrendLoc").textContent = `${rec.d.n}, ${rec.d.s} — past 7 days`;
    const s = rec.s, days = [];
    for (let d = 6; d >= 0; d--) {
      let t = 0; for (let h = 1; h <= 24; h++) t += s.rain[(s.ptr - d * 24 - h + 336) % 336];
      days.push(t);
    }
    const W = 300, H = 130, max = Math.max(6, ...days) * 1.15, bw = W / days.length;
    const bars = days.map((v, i) => `<rect x="${(i * bw + bw * .18).toFixed(1)}" y="${(H - 20 - (v / max) * (H - 34)).toFixed(1)}"
      width="${(bw * .64).toFixed(1)}" height="${((v / max) * (H - 34)).toFixed(1)}" rx="3" fill="#0ea5e9"/>
      <text x="${(i * bw + bw / 2).toFixed(1)}" y="${H - 6}" font-size="8.5" fill="#94a3b8" text-anchor="middle">${["S", "M", "T", "W", "T", "F", "S"][(World.now().getUTCDay() - 6 + i + 7) % 7]}</text>`).join("");
    $("#rainChart").innerHTML = bars;
  },

  highRiskTable() {
    const top = World.ranked(null, "risk").slice(0, 6);
    $("#highRiskTable").innerHTML = top.map(r => {
      const c = catOf(r.s.p);
      return `<div class="hrrow flex items-center gap-2 py-1.5 cursor-pointer hover:bg-slate-50 rounded-lg px-1.5 -mx-1.5" data-key="${r.d.key}">
        <div class="flex-1 min-w-0"><p class="text-[11px] font-semibold text-slate-800 truncate">${r.d.n}</p>
          <div class="barrow"><div class="track"><i style="width:${(r.s.p * 100).toFixed(0)}%;background:${c.c}"></i></div></div></div>
        <span class="text-[11.5px] font-bold num flex-shrink-0" style="color:${c.c}">${(r.s.p * 100).toFixed(0)}%</span>
      </div>`;
    }).join("");
    $$(".hrrow").forEach(row => row.onclick = () => { const rec = World.byKey.get(row.dataset.key); if (rec) { Map3.select(rec); Map3.fitTo([rec.d.ll[1] - 1, rec.d.ll[0] - 1, rec.d.ll[1] + 1, rec.d.ll[0] + 1]); } });
  },

  risingTable() {
    const list = World.ranked(null, "rise").slice(0, 10);
    $("#risingTable").innerHTML = list.map(r => {
      const back = r.s.hist.length > 6 ? r.s.hist[r.s.hist.length - 7] : r.s.p, dl = r.s.p - back, c = catOf(r.s.p);
      return `<div class="hrrow flex items-center gap-3 py-2 cursor-pointer hover:bg-slate-50 rounded-lg px-2 -mx-2" data-key="${r.d.key}">
        <div class="flex-1 min-w-0"><p class="text-[11.5px] font-semibold text-slate-800">${r.d.n} <span class="text-slate-400 font-normal">${r.d.s}</span></p></div>
        <span class="text-[10.5px] font-semibold ${dl >= 0 ? "text-orange-500" : "text-emerald-600"} num">${dl >= 0 ? "▲" : "▼"} ${(Math.abs(dl) * 100).toFixed(0)} pt/6h</span>
        <span class="text-[12px] font-bold num w-12 text-right" style="color:${c.c}">${(r.s.p * 100).toFixed(0)}%</span>
      </div>`;
    }).join("");
    $$(".hrrow").forEach(row => row.onclick = () => { const rec = World.byKey.get(row.dataset.key); if (rec) Map3.select(rec); });
  },
  /* ── weather tab ─────────────────────────────────────────────────────── */
  feedGrid() {
    const h = World.h;
    const defs = [["IMD AWS", 1, "1,400 stations"], ["Open-Meteo", 1, "reanalysis blend"], ["GPM IMERG", .5, "precipitation"],
      ["MODIS Terra", 12, "snow cover"], ["Sentinel-1", 144, "InSAR"], ["Sentinel-2", 120, "NDVI / BSI"],
      ["SMAP L4", 3, "soil moisture"], ["NCS seismic", 1, "real time"], ["Bhuvan DEM", 720, "terrain"]];
    $("#feedGrid").innerHTML = defs.map(([n, every, note], i) => {
      const age = (h * 1.0 + i * 3) % (every * 4 + 1), stale = age > every * 2.5;
      const ago = every >= 24 ? `${Math.round(every / 24)}d` : (age < 1 ? `${Math.round(age * 60)}min` : `${age.toFixed(0)}h`);
      return `<div class="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
        <div class="flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full ${stale ? "bg-amber-500" : "bg-emerald-500"}"></span>
        <span class="text-[11px] font-semibold text-slate-700 truncate">${n}</span></div>
        <p class="text-[9.5px] text-slate-400 mt-0.5">${note} · ${ago} ago</p></div>`;
    }).join("");
  },
  weatherGrid() {
    const list = World.D.filter(this.filterFn()).slice(0, 16);
    $("#weatherGrid").innerHTML = list.map(r => {
      const on = Map3.sel && Map3.sel.d.key === r.d.key;
      return `<div class="wcard p-3.5 rounded-xl border cursor-pointer transition-all ${on ? "border-emerald-500 bg-emerald-50/40" : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"} bg-white" data-key="${r.d.key}">
        <div class="flex justify-between items-start">
          <div><h4 class="font-bold text-slate-900 text-xs">${r.d.n}</h4><span class="text-[11px] text-slate-500">${r.d.s}</span></div>
          <span class="text-xs font-bold text-slate-800 num">${r.s.r24.toFixed(0)}mm</span>
        </div>
        <div class="mt-2 text-[10px] text-slate-400 flex justify-between">
          <span>Elev ${r.d.e}m · ${r.s.temp.toFixed(0)}°C</span><span class="font-semibold text-emerald-600">Live</span>
        </div></div>`;
    }).join("");
    $$(".wcard").forEach(c => c.onclick = () => { const rec = World.byKey.get(c.dataset.key); if (rec) { Map3.select(rec); this.weatherGrid(); } });
  },

  /* ── alerts tab ──────────────────────────────────────────────────────── */
  alertPreview() {
    const rec = World.byKey.get($("#alDist").value) || Map3.sel; if (!rec) return;
    const lvl = $("#alLevel").value, lang = $("#alLang").value;
    const txt = MSG[lang][lvl](rec.d, (rec.s.p * 100).toFixed(0), rec.s.r24.toFixed(0));
    $("#alPreview").textContent = txt;
    const segs = Math.ceil(txt.length / (lang === "en" || lang === "mni" ? 160 : 70));
    const on = CHANNELS.filter(c => $(`#ch_${c.k}`)?.checked ?? c.on);
    const reach = Math.round(rec.d.pop * Math.min(.97, on.reduce((t, c) => t + c.reach, 0)));
    $("#alReach").innerHTML = `${txt.length} chars · ${segs} SMS segment${segs > 1 ? "s" : ""} · reaches ~<b class="num">${reach.toLocaleString("en-IN")}</b> of ${rec.d.pop.toLocaleString("en-IN")}`;
  },
  alertLog() {
    $("#alertCountPill").textContent = `${Store.alerts.filter(a => World.now().getTime() - a.t < 86400e3).length} dispatched today`;
    if (!Store.alerts.length) { $("#alertLogList").innerHTML = `<p class="text-[11px] text-slate-400">Nothing dispatched yet. Automatic warnings appear here when a district crosses severe.</p>`; return; }
    $("#alertLogList").innerHTML = Store.alerts.slice(0, 30).map(a => `<div class="flex items-start gap-3 p-3 bg-slate-50 rounded-xl border border-slate-100">
      <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style="background:${a.color}22;color:${a.color}">${ico("alert", "w-4 h-4")}</div>
      <div class="min-w-0 flex-1"><p class="text-xs font-semibold text-slate-800">${a.level} — ${a.dist}, ${a.state} <span class="num" style="color:${a.color}">${a.pct}%</span></p>
        <p class="text-[10.5px] text-slate-400">${a.auto ? "Auto-issued by monitor" : "Issued by duty officer"} · ${a.channels} · ${a.reach.toLocaleString("en-IN")} reached · ${new Date(a.t).toISOString().slice(11, 16)} IST</p></div>
    </div>`).join("");
  },
  issue(rec, level, auto) {
    const lang = $("#alLang")?.value || "en";
    const on = CHANNELS.filter(c => $(`#ch_${c.k}`)?.checked ?? c.on);
    const reach = Math.round(rec.d.pop * Math.min(.97, on.reduce((t, c) => t + c.reach, 0)));
    Store.addAlert({ t: World.now().getTime(), dist: rec.d.n, state: rec.d.s, key: rec.d.key,
      level: level === "evacuate" ? "Evacuate" : level === "alert" ? "Alert" : "Watch",
      pct: (rec.s.p * 100).toFixed(0), color: catOf(rec.s.p).c, auto: !!auto,
      channels: on.map(c => c.lab.split(" ")[0]).join(", "), reach,
      text: MSG[lang][level](rec.d, (rec.s.p * 100).toFixed(0), rec.s.r24.toFixed(0)) });
    if (!auto) this.toast(`Warning issued for ${rec.d.n} — ${reach.toLocaleString("en-IN")} people reached`);
  },
  autoAlerts() {
    for (const e of World.events.slice(0, 6)) {
      if (e.seen || !e.d) continue; e.seen = true;
      const rec = World.byKey.get(e.d.key); if (!rec) continue;
      if (e.kind === "escalation" && rec.s.p >= .45) this.issue(rec, rec.s.p >= .70 ? "evacuate" : "alert", true);
    }
  },

  /* ── field reports tab ───────────────────────────────────────────────── */
  syncBar() {
    const pill = $("#syncPill"); const n = Store.pendingCount();
    pill.className = "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold border " +
      (Store.offline ? "bg-amber-50 border-amber-200 text-amber-700" : "bg-emerald-50 border-emerald-200 text-emerald-700");
    $("#syncTxt").textContent = Store.offline ? `Offline — ${n} held on device` : (n ? `${n} syncing…` : "Connected");
    $("#btnOffline").textContent = Store.offline ? "Reconnect" : "Simulate offline";
  },
  reportList() {
    if (!Store.reports.length) { $("#frList").innerHTML = `<p class="text-[11px] text-slate-400">No reports yet.</p>`; return; }
    $("#frList").innerHTML = Store.reports.slice(0, 25).map(r => {
      const c = CAT[Math.min(4, r.sev)];
      return `<div class="flex items-start gap-2.5 p-2.5 bg-slate-50 rounded-lg border border-slate-100">
        <div class="w-1.5 self-stretch rounded-full flex-shrink-0" style="background:${c.c}"></div>
        <div class="min-w-0"><p class="text-[11.5px] font-semibold text-slate-800">${r.type}</p>
          <p class="text-[10.5px] text-slate-500">${r.dist}, ${r.state}${r.note ? " — " + r.note : ""}</p>
          <p class="text-[9.5px] text-slate-400 mt-0.5">${r.who || "anonymous"} · ${new Date(r.t).toISOString().slice(11, 16)} IST${r.pending ? ' · <span class="text-amber-600">queued</span>' : ""}</p>
        </div></div>`;
    }).join("");
  },

  /* ── modals: simulation, SHAP, AI ────────────────────────────────────── */
  openSim() {
    const rec = Map3.sel; if (!rec) return;
    $("#simLocName").textContent = `${rec.d.n}, ${rec.d.s}`;
    const { d, s } = rec;
    $("#simBody").innerHTML = `
      <div><div class="flex justify-between text-[11px] mb-1"><span class="font-medium text-slate-600">Extra 24h rainfall</span><b class="num" id="simRainV">0 mm</b></div>
        <input type="range" id="simRain" min="0" max="400" value="0" class="w-full"></div>
      <div><div class="flex justify-between text-[11px] mb-1"><span class="font-medium text-slate-600">Soil saturation override</span><b class="num" id="simSatV">current</b></div>
        <input type="range" id="simSat" min="-1" max="100" value="-1" class="w-full"></div>
      <div><div class="flex justify-between text-[11px] mb-1"><span class="font-medium text-slate-600">Seismic event nearby (M)</span><b class="num" id="simQV">none</b></div>
        <input type="range" id="simQ" min="0" max="70" value="0" class="w-full"></div>
      <div class="pt-2 border-t border-slate-100">
        <div class="flex items-center justify-between">
          <div><p class="text-[11px] text-slate-500">Resulting risk</p><p class="text-3xl font-bold num" id="simResult" style="color:${catOf(s.p).c}">${(s.p * 100).toFixed(0)}%</p></div>
          <div class="text-right text-[11px] text-slate-500"><p>Baseline <b class="num">${(s.p * 100).toFixed(0)}%</b></p><p id="simFs">FS ${s.fs.toFixed(2)}</p></div>
        </div>
      </div>`;
    const run = () => {
      const rain = +$("#simRain").value, satPct = +$("#simSat").value, qM = +$("#simQ").value / 10;
      $("#simRainV").textContent = rain + " mm"; $("#simQV").textContent = qM === 0 ? "none" : "M" + qM.toFixed(1);
      $("#simSatV").textContent = satPct < 0 ? "current" : satPct + "%";
      const cs = cloneState(s);
      if (satPct >= 0) cs.store = cs.cap * satPct / 100;
      cs.r24 += rain; cs.api += rain;
      if (qM > 0) Met.quakes.push({ h: World.h, lat: d.ll[0], lon: d.ll[1], mag: qM });
      const p = score(d, cs, World.h);
      if (qM > 0) Met.quakes.pop();
      $("#simResult").textContent = (p * 100).toFixed(0) + "%"; $("#simResult").style.color = catOf(p).c;
      $("#simFs").textContent = "FS " + cs.fs.toFixed(2);
    };
    ["simRain", "simSat", "simQ"].forEach(id => $("#" + id).oninput = run);
    this.openModal("modalSim");
  },

  openShap() {
    const rec = Map3.sel; if (!rec) return;
    $("#shapLocName").textContent = `${rec.d.n}, ${rec.d.s}`;
    const top = rec.s.shap.slice(0, 9), mx = Math.max(...top.map(t => Math.abs(t.v))) || 1;
    $("#shapBody").innerHTML = `<p class="text-[11.5px] text-slate-500">Points of probability added (orange) or removed (green) against the national baseline district. Blended physics FS ${rec.s.fs.toFixed(2)}, susceptibility ${(rec.s.susc * 100).toFixed(0)}%, trigger ${(rec.s.trig * 100).toFixed(0)}%.</p>
      <div class="space-y-2.5">${top.map(t => `<div>
        <div class="flex justify-between text-[11.5px] mb-1"><span class="font-medium text-slate-700">${t.lab}</span>
          <span class="font-bold num ${t.v >= 0 ? "text-orange-600" : "text-emerald-600"}">${t.v >= 0 ? "+" : "−"}${(Math.abs(t.v) * 100).toFixed(1)}</span></div>
        <div class="track"><i style="width:${(Math.abs(t.v) / mx * 100).toFixed(0)}%;background:${t.v >= 0 ? "#f97316" : "#059669"}"></i></div>
      </div>`).join("")}</div>`;
    this.openModal("modalShap");
  },

  async openAI() {
    this.openModal("modalAI");
    if (this._aiBooted) return; this._aiBooted = true;
    try { this.sample = await claude.use("sample"); } catch { this.sample = null; }
    if (!this.sample) { $("#aiBody").innerHTML = `<p class="text-[11.5px] text-slate-400">The analyst isn't available in this view. Everything else on the console works without it.</p>`;
      $("#aiInput").disabled = true; $("#aiSend").disabled = true; return; }
    $("#aiBody").innerHTML = `<p class="text-[11.5px] text-slate-400">Ready. Ask for a duty briefing, a district assessment, or what to tell a district magistrate.</p>
      <div class="flex flex-wrap gap-1.5">${["Write the 06:00 duty briefing", "What should this district do today?", "Which districts need evacuation orders?", "Explain the top driver in plain Hindi"]
        .map(q => `<button class="chip" data-ask="${q}">${q}</button>`).join("")}</div>`;
    $$("[data-ask]").forEach(b => b.onclick = () => this.ask(b.dataset.ask));
  },
  context() {
    const nat = World.national(), top = World.ranked(null, "risk").slice(0, 12), rising = World.ranked(null, "rise").slice(0, 5), sel = Map3.sel;
    const line = r => `${r.d.n} (${r.d.s}): risk ${(r.s.p * 100).toFixed(0)}%, ${catOf(r.s.p).lab}, 24h rain ${r.s.r24.toFixed(0)}mm, saturation ${(r.s.store / r.s.cap * 100).toFixed(0)}%, slope ${r.d.sl}deg, FS ${r.s.fs.toFixed(2)}, top driver ${r.s.shap[0]?.lab}`;
    return `Time: ${World.now().toISOString().slice(0, 16).replace("T", " ")} IST.
National: ${nat.sev} districts severe/extreme, ${nat.hi} high, ~${(nat.pop / 1e6).toFixed(1)}M people in severe-risk districts.
Highest risk:\n${top.map(line).join("\n")}
Rising fastest (6h): ${rising.map(r => `${r.d.n} +${((r.s.p - (r.s.hist[r.s.hist.length - 7] ?? r.s.p)) * 100).toFixed(0)}pt`).join("; ")}
Selected: ${sel ? line(sel) : "none"}
Recent detections: ${World.events.slice(0, 6).map(e => e.msg).join("; ") || "none"}
Field reports: ${Store.reports.slice(0, 5).map(r => `${r.type} in ${r.dist} sev ${r.sev}`).join("; ") || "none"}`;
  },
  async ask(q) {
    if (!this.sample) return;
    $("#aiBody").insertAdjacentHTML("beforeend", `<div class="bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2 text-[11.5px] text-slate-800">${q.replace(/</g, "&lt;")}</div>`);
    const out = document.createElement("div"); out.className = "text-[11.5px] text-slate-700 leading-relaxed whitespace-pre-wrap"; out.textContent = "Reading the model state…";
    $("#aiBody").appendChild(out); $("#aiBody").scrollTop = 1e6;
    try {
      const res = await this.sample([{ role: "user", content: `You are the duty analyst on LANDSAFE, India's national landslide and multi-hazard watch, briefing a State Disaster Management Authority control room.\n\nLive model state:\n${this.context()}\n\nOfficer's question: ${q}\n\nAnswer in plain, direct language. Be specific with districts and numbers from the state above; never invent one. If a district is Tier 3 plains, say the model withholds a landslide score there. Under 250 words, no markdown headers.` }],
        { modelTier: "default", onText: ({ text }) => { out.textContent = text; $("#aiBody").scrollTop = 1e6; } });
      out.textContent = res.text;
    } catch (err) { out.innerHTML = `<span class="text-amber-600">The analyst could not be reached just now.</span>`; }
  },
  openModal(id) { $("#" + id).classList.add("on"); },
  closeModal(id) { $("#" + id).classList.remove("on"); },

  /* ── recommendations tab ─────────────────────────────────────────────── */
  renderRecs() {
    const brief = [
      ["Real-time GIS dashboard and risk heatmaps", "Built — 726-district choropleth with 8 live layers, pan/zoom, and per-district drill-down.", "done"],
      ["AI/ML-based predictive analytics engine", "Built — dual model (slope-stability physics + susceptibility×trigger learned model) with SHAP attribution, cross-validated hourly.", "done"],
      ["Mobile/web application for field reporting and alerts", "Built — field-report form with offline queue and sync; responsive down to mobile width.", "done"],
      ["Integration with IMD weather APIs, satellite feeds, and sensor data", "Simulated here (deterministic monsoon model + synthetic sensor network) — swap in real IMD/GPM/MODIS/Sentinel feeds via the backend, see below.", "partial"],
      ["Automated SMS/app-based early warning system", "Built — 5-language templates, 5 channels including CAP-XML, automatic dispatch on threshold breach, reach estimation.", "done"],
      ["Cloud-based architecture with offline sync for remote regions", "Partially built — offline report queue with sync-on-reconnect works today; production needs an actual cloud deployment (see below).", "partial"],
    ];
    const bStat = { done: ["bg-emerald-50 text-emerald-700 border-emerald-200", "check"], partial: ["bg-amber-50 text-amber-700 border-amber-200", "clock"] };
    $("#recsBrief").innerHTML = `<div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
      <h3 class="text-xs font-bold text-slate-800 uppercase tracking-wide mb-3">Against your brief</h3>
      <div class="space-y-3">${brief.map(([t, d, st]) => `<div class="flex items-start gap-3 py-2 border-b border-slate-50 last:border-0">
        <span class="w-6 h-6 rounded-lg border flex items-center justify-center flex-shrink-0 mt-0.5 ${bStat[st][0]}">${ico(bStat[st][1], "w-3.5 h-3.5")}</span>
        <div><p class="text-xs font-semibold text-slate-800">${t}</p><p class="text-[11px] text-slate-500 mt-0.5">${d}</p></div>
      </div>`).join("")}</div></div>`;

    const mine = [
      ["Port the engine to the FastAPI backend", "Move the susceptibility×trigger model and SHAP attribution from this browser prototype into `ml_service.py` so it scores real IMD/GPM/MODIS input instead of the simulator — this is the highest-leverage next step."],
      ["Retrain on the actual landslide inventory", "NRSC's Landslide Atlas and state SDMA incident logs give real labels to calibrate against, instead of the physically-reasoned but synthetic weights used here."],
      ["A native or PWA mobile app for field responders", "GPS-tagged photo capture, one-tap severity, and background sync — the web form here proves the workflow but a camera-first mobile app will get far higher field adoption."],
      ["IVR and community sirens for last-mile reach", "Included as channels in the alert composer; wiring them to a real telecom gateway and panchayat-operated sirens is what turns the simulation into an actual warning that reaches non-smartphone households."],
      ["Community-sourced verification loop", "Let a second nearby reporter or a local disaster-management volunteer confirm a field report before it's weighted into the model — reduces false positives from a single unreliable submission."],
      ["Drone or high-frequency UAV imagery for Tier-1 hotspots", "Sentinel-1/2 revisit is measured in days; the districts already flagged severe would benefit from a scheduled UAV pass to catch crown-crack development between satellite passes."],
      ["Multilingual IVR + SMS beyond the 5 languages here", "Extend to all 22 scheduled languages for full national reach, prioritized by the population actually living in Tier-1 districts."],
      ["A public-facing lite version", "This console is built for duty officers; a stripped-down public site (risk-by-pincode, plain-language advisories) extends reach to residents directly, similar to how IMD's public site complements its forecaster tools."],
    ];
    $("#recsMine").innerHTML = `<div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
      <h3 class="text-xs font-bold text-slate-800 uppercase tracking-wide mb-3">What I'd add next</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">${mine.map(([t, d]) => `<div class="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
        <p class="text-xs font-semibold text-slate-800">${t}</p><p class="text-[11px] text-slate-500 mt-1 leading-relaxed">${d}</p>
      </div>`).join("")}</div></div>`;
  },

  tierBreakdown() {
    const t1 = World.D.filter(r => r.d.tier === 1).length, t2 = World.D.filter(r => r.d.tier === 2).length, t3 = World.D.filter(r => r.d.tier === 3).length;
    $("#tierBreakdown").innerHTML = `
      <div class="flex justify-between font-medium"><span>Tier 1 — full hazard monitoring</span><span class="font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">${t1} districts</span></div>
      <div class="flex justify-between font-medium"><span>Tier 2 — screening only</span><span class="font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">${t2} districts</span></div>
      <div class="flex justify-between font-medium"><span>Tier 3 — no calibrated model (plains)</span><span class="font-bold text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">${t3} districts</span></div>`;
  },

  /* ── misc ────────────────────────────────────────────────────────────── */
  toast(m) { const t = $("#toast"); t.textContent = m; t.classList.add("on"); clearTimeout(this._tt); this._tt = setTimeout(() => t.classList.remove("on"), 3200); },
  counts() {
    const lastAlert = Store.alerts.filter(a => World.now().getTime() - a.t < 86400e3).length;
    $$(".navbadge-a").forEach(b => { b.textContent = lastAlert; b.classList.toggle("hidden", !lastAlert); });
    $("#bellDot").classList.toggle("hidden", !lastAlert);
    const pend = Store.pendingCount();
    $$(".navbadge-b").forEach(b => { b.textContent = pend; b.classList.toggle("hidden", !pend); });
  },
  applyFilterUI() {
    this.refreshDistricts(); this.statCards(); this.highRiskTable(); this.weatherGrid();
    $("#btnResetFilter").classList.toggle("hidden", !(this.filterState || this.filterDist || this.filterTier));
  },

  tickUI() {
    const t = World.now(), p = n => String(n).padStart(2, "0");
    $("#clockTxt").textContent = `${p(t.getUTCHours())}:${p(t.getUTCMinutes())}`;
    $("#clockDate").textContent = t.toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "UTC" });
    this.feedGrid();
    this.statCards();
    this.locationCard();
    this.rightCol();
    this.highRiskTable();
    if (this.tab === "weather") this.weatherGrid();
    if (this.tab === "risk-analysis") this.risingTable();
    if (this.tab === "dashboard") { this.donut(); this.rainChart(); }
    Map3.paint();
    this.autoAlerts();
    this.alertLog();
    if (this.tab === "alerts") this.alertPreview();
    this.counts();
  },

  bind() {
    World.listeners.push(() => this.tickUI());

    $$(".navbtn, .mobbtn").forEach(b => b.onclick = () => this.setTab(b.dataset.tab));
    $("#btnMobNav").onclick = () => { $("#mobSidebar").classList.remove("-translate-x-full"); $("#navScrim").classList.add("on"); };
    $("#btnCloseNav").onclick = () => this.closeMobNav();
    $("#navScrim").onclick = () => this.closeMobNav();
    $$("[data-goto]").forEach(b => b.onclick = () => this.setTab(b.dataset.goto));

    $("#selState").onchange = e => {
      this.filterState = e.target.value; this.filterDist = "";
      this.applyFilterUI();
      this.buildDistPicker("#frDist"); this.buildDistPicker("#alDist");
      if (this.filterState) {
        const ds = World.D.filter(r => r.d.s === this.filterState).map(r => r.d.ll);
        Map3.fitTo([Math.min(...ds.map(l => l[1])) - .4, Math.min(...ds.map(l => l[0])) - .4, Math.max(...ds.map(l => l[1])) + .4, Math.max(...ds.map(l => l[0])) + .4]);
      } else Map3.setView(Map3.vb.slice(), true);
    };
    $("#selDist").onchange = e => {
      this.filterDist = e.target.value; this.applyFilterUI();
      const rec = World.byKey.get(e.target.value);
      if (rec) { Map3.select(rec); Map3.fitTo([rec.d.ll[1] - 1.1, rec.d.ll[0] - 1.1, rec.d.ll[1] + 1.1, rec.d.ll[0] + 1.1]); }
    };
    $("#selTier").onchange = e => { this.filterTier = e.target.value; this.applyFilterUI(); };
    $("#btnResetFilter").onclick = () => { this.filterState = ""; this.filterDist = ""; this.filterTier = ""; $("#selState").value = ""; $("#selTier").value = ""; this.applyFilterUI(); this.buildDistPicker("#frDist"); this.buildDistPicker("#alDist"); Map3.setView(Map3.vb.slice(), true); };

    $("#searchInput").oninput = e => {
      const q = e.target.value.trim().toLowerCase();
      const drop = $("#searchDrop");
      if (!q) { drop.classList.add("hidden"); return; }
      const matches = World.D.filter(r => r.d.n.toLowerCase().includes(q) || r.d.s.toLowerCase().includes(q)).slice(0, 8);
      drop.innerHTML = matches.map(r => { const c = catOf(r.s.p);
        return `<button data-key="${r.d.key}" class="srow w-full text-left px-3.5 py-2.5 hover:bg-slate-50 flex items-center justify-between border-b border-slate-100 last:border-0 text-xs">
          <span><span class="font-semibold text-slate-800">${r.d.n}</span><span class="text-slate-500 ml-1.5 font-normal">(${r.d.s})</span></span>
          <span class="text-[10px] px-2 py-0.5 rounded-full font-medium text-white" style="background:${c.c}">${r.d.tier === 3 ? "n/a" : c.lab}</span>
        </button>`; }).join("");
      drop.classList.toggle("hidden", !matches.length);
      $$(".srow").forEach(row => row.onclick = () => { const rec = World.byKey.get(row.dataset.key); if (rec) { Map3.select(rec); Map3.fitTo([rec.d.ll[1] - 1, rec.d.ll[0] - 1, rec.d.ll[1] + 1, rec.d.ll[0] + 1]); } this.setTab("live-map"); drop.classList.add("hidden"); e.target.value = ""; });
    };
    document.addEventListener("click", e => { if (!$("#searchWrap").contains(e.target)) $("#searchDrop").classList.add("hidden"); });

    $("#btnBell").onclick = () => this.setTab("alerts");
    $("#btnInspect").onclick = () => this.openShap();
    $("#btnLaunchSim").onclick = () => this.openSim();

    $$("[data-close-modal]").forEach(b => b.onclick = () => this.closeModal(b.dataset.closeModal));
    $$(".modal").forEach(m => m.onclick = e => { if (e.target === m) this.closeModal(m.id); });
    addEventListener("keydown", e => { if (e.key === "Escape") $$(".modal.on").forEach(m => this.closeModal(m.id)); });

    $("#alChannels").innerHTML = CHANNELS.map(c => `<label class="flex items-center gap-1.5 text-[11px] text-slate-600">
      <input type="checkbox" id="ch_${c.k}" ${c.on ? "checked" : ""} class="accent-emerald-600">${c.lab}</label>`).join("");
    ["#alDist", "#alLevel", "#alLang"].forEach(i => $(i).onchange = () => this.alertPreview());
    $("#alChannels").onchange = () => this.alertPreview();
    $("#alSend").onclick = () => { const rec = World.byKey.get($("#alDist").value); if (rec) this.issue(rec, $("#alLevel").value, false); };
    $("#alExport").onclick = () => this.sitrep();

    $("#btnOffline").onclick = async () => { Store.offline = !Store.offline; this.syncBar(); if (!Store.offline) await Store.flush(); else this.toast("Offline mode — reports held on device"); };
    $("#frSubmit").onclick = async () => {
      const key = $("#frDist").value, rec = World.byKey.get(key); if (!rec) return;
      await Store.addReport({ id: "r" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6), t: World.now().getTime(), key,
        dist: rec.d.n, state: rec.d.s, type: $("#frType").value, sev: +$("#frSev").value,
        note: $("#frNote").value.trim().slice(0, 240), who: $("#frWho").value.trim().slice(0, 60) });
      $("#frNote").value = ""; this.toast(Store.offline ? "Report queued on this device" : "Report filed — the model will weight it next cycle");
    };

    $("#aiSend").onclick = () => { const v = $("#aiInput").value.trim(); if (v) { $("#aiInput").value = ""; this.ask(v); } };
    $("#aiInput").onkeydown = e => { if (e.key === "Enter") $("#aiSend").click(); };

    addEventListener("resize", () => { if (Map3.sel) this.rightCol(); });
    this.tierBreakdown();
  },

  async sitrep() {
    const nat = World.national(), t = World.now().toISOString().slice(0, 16).replace("T", " "), top = World.ranked(null, "risk").slice(0, 20);
    const txt = `LANDSAFE NATIONAL SITUATION REPORT\nGenerated ${t} IST\n\nSUMMARY\n  Severe/extreme: ${nat.sev}\n  High: ${nat.hi}\n  Population in severe-risk districts: ${nat.pop.toLocaleString("en-IN")}\n\nDISTRICTS OF CONCERN\n${top.map((r, i) => `${String(i + 1).padStart(2)}. ${r.d.n}, ${r.d.s} — ${(r.s.p * 100).toFixed(0)}% (${catOf(r.s.p).lab}) FS ${r.s.fs.toFixed(2)} rain24 ${r.s.r24.toFixed(0)}mm — ${r.s.shap[0]?.lab}`).join("\n")}\n\nWARNINGS (24h)\n${Store.alerts.slice(0, 15).map(a => `  ${new Date(a.t).toISOString().slice(11, 16)} ${a.level.padEnd(9)} ${a.dist}, ${a.state} — ${a.reach.toLocaleString("en-IN")} reached`).join("\n") || "  none"}\n\nFIELD REPORTS\n${Store.reports.slice(0, 15).map(r => `  ${new Date(r.t).toISOString().slice(11, 16)} sev ${r.sev} ${r.type} — ${r.dist}`).join("\n") || "  none"}\n\nPrototype output. Not an official Government of India warning product.\n`;
    try { const dl = await claude.use("downloads"); if (dl) { await dl.save({ filename: `landsafe-sitrep-${t.slice(0, 10)}.txt`, data: txt }); this.toast("Situation report saved"); return; } } catch {}
    navigator.clipboard?.writeText(txt); this.toast("Situation report copied to clipboard");
  },
};

/* ══════════════════════════════════════════════════════════════════════════
   Boot
   ══════════════════════════════════════════════════════════════════════════ */
World.build(GEO);
Map3.init(GEO);
Store.init();
UI.boot();
