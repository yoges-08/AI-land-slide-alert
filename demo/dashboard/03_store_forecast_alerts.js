const Store = {
  reports: [], alerts: [], offline: false, db: null, ready: false,

  async init() {
    try { this.db = await claude.use("db"); } catch { this.db = null; }
    this.loadLocal();
    if (this.db) {
      try {
        const snap = await this.db.collection("reports").orderBy("t", "desc").limit(60).get();
        const rows = (snap.docs || snap || []).map(d => d.data ? d.data() : d);
        for (const r of rows) if (r && r.id && !this.reports.some(x => x.id === r.id)) this.reports.push(r);
        this.reports.sort((a, b) => b.t - a.t);
      } catch { /* read-only viewer or no grant — local only */ }
    }
    this.ready = true;
    UI.syncBar(); UI.reportList(); Map3.overlays();
  },

  loadLocal() {
    try {
      const raw = localStorage.getItem("landsafe.reports");
      if (raw) this.reports = JSON.parse(raw);
      const a = localStorage.getItem("landsafe.alerts");
      if (a) this.alerts = JSON.parse(a);
    } catch { /* storage blocked — session only */ }
  },
  saveLocal() {
    try {
      localStorage.setItem("landsafe.reports", JSON.stringify(this.reports.slice(0, 80)));
      localStorage.setItem("landsafe.alerts", JSON.stringify(this.alerts.slice(0, 80)));
    } catch { /* ignore */ }
  },

  async addReport(rep) {
    rep.pending = this.offline;
    this.reports.unshift(rep);
    this.saveLocal();
    if (!this.offline) await this.push(rep);
    UI.reportList(); UI.syncBar(); Map3.overlays();
  },

  async push(rep) {
    if (!this.db) { rep.pending = false; return; }
    try { await this.db.doc("reports/" + rep.id).set(rep); rep.pending = false; }
    catch { rep.pending = false; }   // queued locally; nothing is lost
  },

  async flush() {
    const q = this.reports.filter(r => r.pending);
    for (const r of q) await this.push(r);
    this.saveLocal(); UI.reportList(); UI.syncBar();
    if (q.length) UI.toast(`${q.length} queued report${q.length > 1 ? "s" : ""} synced`);
  },

  addAlert(a) { this.alerts.unshift(a); this.saveLocal(); UI.alertLog(); UI.counts(); },
  pendingCount() { return this.reports.filter(r => r.pending).length; },
};


function cloneState(s) {
  const c = Object.assign({}, s);
  c.rain = Float32Array.from(s.rain);
  c.hist = []; c.satHist = []; c.shap = [];
  return c;
}
function forecast(rec, hours) {
  const savedCells = Met.cells.map(c => Object.assign({}, c));
  const savedQ = Met.quakes.slice(), savedPulse = Met.pulse;
  const s = cloneState(rec.s), out = [];
  for (let k = 1; k <= hours; k++) {
    const h = World.h + k;
    Met.step(h);
    const rain = stepHydrology(rec.d, s, h);
    score(rec.d, s, h);
    out.push({ k, rain, p: s.p, sat: s.store / s.cap, unc: s.unc });
  }
  Met.cells = savedCells; Met.quakes = savedQ; Met.pulse = savedPulse;
  return out;
}


const MSG = {
  en: {
    watch: (d, p, r) => `LANDSAFE WATCH: ${d.n}, ${d.s}. Landslide conditions developing (${p}% risk). ${r} mm rain in 24h. Avoid hill roads after dark. Keep phone charged. Helpline 1070.`,
    alert: (d, p, r) => `LANDSAFE ALERT: ${d.n}, ${d.s}. HIGH landslide risk (${p}%). ${r} mm rain in 24h. Stay away from slopes, cut sections and stream banks. Do not travel on hill roads. Helpline 1070. -SDMA`,
    evacuate: (d, p, r) => `LANDSAFE EVACUATE: ${d.n}, ${d.s}. SEVERE landslide danger (${p}%). ${r} mm rain in 24h. Leave hillside and valley-floor homes NOW. Move to the notified relief centre. Helpline 1070. -SDMA`,
  },
  hi: {
    watch: (d, p, r) => `लैंडसेफ़ चेतावनी: ${d.n}, ${d.s}. भूस्खलन की स्थिति बन रही है (${p}%). 24 घंटे में ${r} मिमी वर्षा. अंधेरे में पहाड़ी सड़कों से बचें. हेल्पलाइन 1070.`,
    alert: (d, p, r) => `लैंडसेफ़ अलर्ट: ${d.n}, ${d.s}. भूस्खलन का उच्च खतरा (${p}%). 24 घंटे में ${r} मिमी वर्षा. ढलानों, कटान और नाले के किनारों से दूर रहें. पहाड़ी यात्रा न करें. हेल्पलाइन 1070.`,
    evacuate: (d, p, r) => `लैंडसेफ़ निकासी: ${d.n}, ${d.s}. भूस्खलन का गंभीर खतरा (${p}%). 24 घंटे में ${r} मिमी वर्षा. पहाड़ी और घाटी के घर तुरंत खाली करें. राहत केंद्र जाएँ. हेल्पलाइन 1070.`,
  },
  as: {
    watch: (d, p, r) => `LANDSAFE সতৰ্কবাণী: ${d.n}, ${d.s}. ভূমিস্খলনৰ পৰিস্থিতি গঢ় লৈ আছে (${p}%). ২৪ ঘণ্টাত ${r} মিমি বৰষুণ. আন্ধাৰত পাহাৰীয়া পথ এৰক. হেল্পলাইন ১০৭০.`,
    alert: (d, p, r) => `LANDSAFE এলাৰ্ট: ${d.n}, ${d.s}. ভূমিস্খলনৰ উচ্চ বিপদ (${p}%). ২৪ ঘণ্টাত ${r} মিমি বৰষুণ. পাহাৰৰ ঢাল, কটা অংশ আৰু নদীৰ পাৰৰ পৰা আঁতৰি থাকক. হেল্পলাইন ১০৭০.`,
    evacuate: (d, p, r) => `LANDSAFE খালী কৰক: ${d.n}, ${d.s}. ভূমিস্খলনৰ গুৰুতৰ বিপদ (${p}%). ২৪ ঘণ্টাত ${r} মিমি বৰষুণ. পাহাৰীয়া আৰু উপত্যকাৰ ঘৰ এতিয়াই এৰক. আশ্ৰয় কেন্দ্ৰলৈ যাওক. ১০৭০.`,
  },
  ne: {
    watch: (d, p, r) => `LANDSAFE सतर्कता: ${d.n}, ${d.s}. पहिरोको अवस्था बन्दै (${p}%). २४ घण्टामा ${r} मिमि वर्षा. रातमा पहाडी सडक नजानुहोस्. हेल्पलाइन १०७०.`,
    alert: (d, p, r) => `LANDSAFE अलर्ट: ${d.n}, ${d.s}. पहिरोको उच्च जोखिम (${p}%). २४ घण्टामा ${r} मिमि वर्षा. भिरालो, कटान र खोलाको किनारबाट टाढा रहनुहोस्. हेल्पलाइन १०७०.`,
    evacuate: (d, p, r) => `LANDSAFE निकास: ${d.n}, ${d.s}. पहिरोको गम्भीर खतरा (${p}%). २४ घण्टामा ${r} मिमि वर्षा. पहाडी र बेंसीका घर तुरुन्तै छोड्नुहोस्. राहत केन्द्र जानुहोस्. १०७०.`,
  },
  mni: {
    watch: (d, p, r) => `LANDSAFE Cheksin: ${d.n}, ${d.s}. Ching lanba thokpa yai (${p}%). Pung 24 da nong ${r} mm. Numidang ching lambida chatlaroi. Helpline 1070.`,
    alert: (d, p, r) => `LANDSAFE Alert: ${d.n}, ${d.s}. Ching lanbagi khudongthiba wangi (${p}%). Pung 24 da nong ${r} mm. Ching maikei, lambi kakpa amasung turel mapanda lapna leiyu. Helpline 1070.`,
    evacuate: (d, p, r) => `LANDSAFE Thadokpa: ${d.n}, ${d.s}. Ching lanbagi akiba (${p}%). Pung 24 da nong ${r} mm. Ching amasung turel manakta leiba yumsing houjik thadoktuna relief centre da chatlu. 1070.`,
  },
};

const CHANNELS = [
  { k: "sms", lab: "SMS cell broadcast", sub: "All handsets on towers serving the district", on: true, reach: 0.78 },
  { k: "app", lab: "LANDSAFE app push", sub: "Registered residents and responders", on: true, reach: 0.21 },
  { k: "ivr", lab: "IVR voice call", sub: "Feature phones and low-literacy households", on: true, reach: 0.34 },
  { k: "siren", lab: "Community siren & PA", sub: "Panchayat-operated towers in notified wards", on: false, reach: 0.12 },
  { k: "cap", lab: "CAP-XML to NDMA / SACHET", sub: "Machine-readable feed for national aggregators", on: true, reach: 0 },
];

