import json, math, os, re, unicodedata
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

BASE_DIR = os.path.dirname(__file__)
SRC = os.path.join(BASE_DIR, "india_districts.geojson")
REPO = os.path.join(BASE_DIR, "ne_india_locations.json")

W, H = 1000.0, 1120.0
LON0, LON1 = 67.0, 98.5
LAT0, LAT1 = 5.5, 37.6


def merc(lat):
    lat = max(min(lat, 84.0), -84.0)
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


MX0, MX1 = math.radians(LON0), math.radians(LON1)
MY0, MY1 = -merc(LAT1), -merc(LAT0)      # y grows downward
SX = W / (MX1 - MX0)
SY = H / (MY1 - MY0)
S = min(SX, SY)
OX = (W - (MX1 - MX0) * S) / 2
OY = (H - (MY1 - MY0) * S) / 2


def proj(lon, lat):
    return (OX + (math.radians(lon) - MX0) * S, OY + (-merc(lat) - MY0) * S)


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", s.lower())


# ---------------------------------------------------------------- physiography
HIMALAYA = {"Jammu and Kashmir", "Ladakh", "Himachal Pradesh", "Uttarakhand", "Sikkim", "Arunachal Pradesh"}
NE_HILL_STATES = {"Nagaland", "Manipur", "Mizoram", "Meghalaya", "Tripura"}
ASSAM_HILLS = {"dimahasao", "karbianglong", "karbianglongwest", "westkarbianglong", "northcacharhills"}

WESTERN_GHATS = {
    # Maharashtra
    "raigad", "ratnagiri", "sindhudurg", "pune", "satara", "kolhapur", "nashik", "thane", "palghar", "ahmadnagar",
    # Goa
    "northgoa", "southgoa",
    # Karnataka
    "kodagu", "chikmagalur", "chikkamagaluru", "hassan", "shimoga", "shivamogga", "uttarakannada", "dakshinakannada",
    "udupi", "belgaum", "belagavi", "chamarajanagar", "mysore", "mysuru",
    # Kerala
    "idukki", "wayanad", "pathanamthitta", "kottayam", "palakkad", "kollam", "thrissur", "ernakulam", "kannur",
    "kozhikode", "malappuram", "thiruvananthapuram", "alappuzha", "kasaragod",
    # Tamil Nadu
    "nilgiris", "thenilgiris", "coimbatore", "theni", "dindigul", "tirunelveli", "kanniyakumari", "erode", "salem",
    "namakkal", "tiruppur", "virudhunagar", "madurai",
}
EASTERN_GHATS = {
    "visakhapatnam", "vizianagaram", "srikakulam", "eastgodavari", "koraput", "rayagada", "malkangiri",
    "kandhamal", "gajapati", "kalahandi", "nabarangapur", "yellandu", "bhadradrikothagudem", "adilabad",
    "kumurambheemasifabad", "nirmal", "mancherial", "chittoor", "kadapa", "ysr", "nellore", "prakasam",
    "sundargarh", "keonjhar", "mayurbhanj", "angul", "deogarh", "boudh", "phulbani",
}
PLATEAU_HILLS = {
    "ranchi", "gumla", "lohardaga", "latehar", "palamu", "hazaribagh", "chatra", "giridih", "dumka", "godda",
    "pakur", "sahibganj", "westsinghbhum", "eastsinghbhum", "saraikelakharsawan", "khunti", "simdega",
    "mandla", "dindori", "balaghat", "chhindwara", "betul", "seoni", "shahdol", "anuppur", "umaria",
    "sidhi", "singrauli", "rewa", "satna", "panna", "chhatarpur", "damoh", "sagar", "jabalpur", "katni",
    "bastar", "dantewada", "sukma", "bijapur", "narayanpur", "kondagaon", "kanker", "jashpur", "surguja",
    "balrampur", "korea", "koriya", "surajpur", "gariaband", "dhamtari", "mahasamund",
    "udaipur", "sirohi", "rajsamand", "pali", "chittorgarh", "banswara", "dungarpur", "pratapgarh",
    "alwar", "ajmer", "bhilwara", "sawaimadhopur", "karauli", "dholpur", "bundi", "kota", "baran", "jhalawar",
    "sonbhadra", "mirzapur", "chandauli", "chitrakoot",
}
THAR = {"jaisalmer", "barmer", "bikaner", "jodhpur", "churu", "nagaur", "jalore", "hanumangarh", "sriganganagar"}
GANGETIC = {
    "Uttar Pradesh", "Bihar", "Punjab", "Haryana", "Delhi", "Chandigarh", "West Bengal",
}
COASTAL_UT = {"Lakshadweep", "Andaman and Nicobar Islands", "Puducherry",
              "Dadra and Nagar Haveli and Daman and Diu"}

GEOLOGY = {
    "greater_himalaya": "Gneiss & Migmatite",
    "lesser_himalaya": "Phyllite & Schist",
    "siwalik": "Siwalik Sandstone & Conglomerate",
    "ne_hills": "Barail Sandstone & Shale",
    "shillong": "Shillong Quartzite & Gneiss",
    "western_ghats": "Deccan Basalt Traps",
    "wg_south": "Charnockite & Khondalite",
    "eastern_ghats": "Khondalite & Charnockite",
    "plateau": "Gondwana Sandstone & Granite",
    "alluvium": "Quaternary Alluvium",
    "coastal": "Coastal Alluvium & Laterite",
    "desert": "Aeolian Sand over Malani Rhyolite",
    "deccan": "Deccan Trap Basalt",
}
SOILS = {
    "greater_himalaya": "Skeletal / Glacial Till",
    "lesser_himalaya": "Brown Forest Loam",
    "siwalik": "Coarse Loamy",
    "ne_hills": "Red Loamy",
    "shillong": "Lateritic Loam",
    "western_ghats": "Lateritic Clay Loam",
    "wg_south": "Lateritic Clay",
    "eastern_ghats": "Red Sandy Loam",
    "plateau": "Red & Yellow",
    "alluvium": "Alluvial Silt Loam",
    "coastal": "Sandy Coastal Alluvium",
    "desert": "Arid Sandy",
    "deccan": "Black Cotton (Vertisol)",
}


def physiography(state, dname, lat, lon):
    """Return (zone, elevation_m, slope_deg, relief_m)."""
    d = norm(dname)
    if state in ("Ladakh",) or (state == "Jammu and Kashmir" and lat > 34.2):
        return "greater_himalaya", 3900, 33.0, 1900
    if state in HIMALAYA:
        # crude N-S banding: north of the state's own span => higher chain
        if state == "Sikkim":
            return ("greater_himalaya", 3200, 36.0, 1700) if lat > 27.5 else ("lesser_himalaya", 1750, 32.0, 1200)
        if state == "Arunachal Pradesh":
            return ("greater_himalaya", 2900, 34.0, 1600) if lat > 28.2 else ("lesser_himalaya", 1500, 30.0, 1150)
        if state == "Uttarakhand":
            return ("greater_himalaya", 2700, 33.0, 1650) if lat > 30.3 else ("lesser_himalaya", 1200, 27.0, 900)
        if state == "Himachal Pradesh":
            return ("greater_himalaya", 3100, 34.0, 1750) if lat > 32.0 else ("lesser_himalaya", 1400, 28.0, 1000)
        if state == "Jammu and Kashmir":
            return ("lesser_himalaya", 1900, 29.0, 1250)
        return "lesser_himalaya", 1500, 28.0, 1000
    if state == "Meghalaya":
        return "shillong", 1200, 24.0, 850
    if state in NE_HILL_STATES:
        return "ne_hills", 1150, 27.0, 900
    if state == "Assam":
        if d in ASSAM_HILLS:
            return "ne_hills", 800, 24.0, 700
        return "alluvium", 75, 2.0, 60
    if d in WESTERN_GHATS:
        south = lat < 13.5
        return ("wg_south", 900, 22.0, 900) if south else ("western_ghats", 780, 21.0, 850)
    if d in EASTERN_GHATS:
        return "eastern_ghats", 620, 15.0, 550
    if d in PLATEAU_HILLS:
        return "plateau", 480, 11.0, 380
    if d in THAR:
        return "desert", 200, 1.5, 40
    if state in GANGETIC:
        if state == "West Bengal" and d in ("darjeeling", "kalimpong"):
            return "lesser_himalaya", 1900, 31.0, 1400
        return "alluvium", 90, 1.2, 35
    if state in COASTAL_UT or state == "Goa":
        return "coastal", 30, 3.0, 60
    if state in ("Maharashtra", "Telangana", "Karnataka", "Andhra Pradesh", "Tamil Nadu"):
        return "deccan", 480, 6.0, 200
    if state in ("Madhya Pradesh", "Chhattisgarh", "Jharkhand", "Odisha", "Rajasthan", "Gujarat"):
        return "plateau", 330, 6.5, 220
    return "alluvium", 150, 3.0, 80


# ---------------------------------------------------------------- repo overlay
repo = json.load(open(REPO))
overlay = {}
for r in repo:
    k = (norm(r["state"]), norm(r["district"]))
    overlay.setdefault(k, []).append(r)


def avg(rows, key, default=None):
    vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
    return round(sum(vals) / len(vals), 2) if vals else default


# ---------------------------------------------------------------- geometry
gj = json.load(open(SRC))
districts = []
state_geoms = {}

for feat in gj["features"]:
    p = feat["properties"]
    state, dname = p["st_nm"], p.get("district")
    geom = shape(feat["geometry"])
    if geom.is_empty:
        continue
    if not geom.is_valid:
        geom = geom.buffer(0)
    state_geoms.setdefault(state, []).append(geom)
    if not dname:
        continue

    # simplify in degrees; districts are small so tolerance must be modest
    tol = 0.012
    simp = geom.simplify(tol, preserve_topology=True)
    if simp.is_empty:
        simp = geom.simplify(tol / 3, preserve_topology=True)

    polys = list(simp.geoms) if simp.geom_type == "MultiPolygon" else [simp]
    # keep only meaningful parts
    polys = [pg for pg in polys if pg.area > 0.0006] or [max(polys, key=lambda g: g.area)]

    path = []
    for pg in polys:
        coords = list(pg.exterior.coords)
        pts = []
        for lon, lat in coords:
            x, y = proj(lon, lat)
            pts.append(f"{x:.1f},{y:.1f}")
        # drop consecutive duplicates
        ded = [pts[0]]
        for q in pts[1:]:
            if q != ded[-1]:
                ded.append(q)
        if len(ded) < 3:
            continue
        path.append("M" + "L".join(ded) + "Z")
    if not path:
        continue

    c = geom.representative_point()
    lon, lat = c.x, c.y
    cx, cy = proj(lon, lat)

    zone, elev, slope, relief = physiography(state, dname, lat, lon)
    rows = overlay.get((norm(state), norm(dname))) or []
    observed = bool(rows)
    if rows:
        elev = avg(rows, "elevation", elev) or elev
        slope = avg(rows, "slope", slope) or slope
        hist = int(sum(r.get("historical_landslides", 0) for r in rows) / max(len(rows), 1))
        ndvi = avg(rows, "vegetation_index", None)
        bare = avg(rows, "bare_soil_pct", None)
        snow = avg(rows, "snow_cover_pct", None)
        geol = rows[0].get("geology") or GEOLOGY[zone]
        soil = rows[0].get("soil_type") or SOILS[zone]
        sites = sorted({r["name"] for r in rows})[:8]
    else:
        hist = 0
        ndvi = bare = snow = None
        geol, soil = GEOLOGY[zone], SOILS[zone]
        sites = []

    tier = 1 if zone in ("greater_himalaya", "lesser_himalaya", "siwalik", "ne_hills", "shillong",
                         "western_ghats", "wg_south") else (
           2 if zone in ("eastern_ghats", "plateau", "deccan") else 3)

    # area in sq km (rough, equal-area-ish via cos correction)
    area_km2 = geom.area * 12321 * math.cos(math.radians(lat))

    districts.append({
        "n": dname, "s": state, "c": [round(cx, 1), round(cy, 1)],
        "ll": [round(lat, 4), round(lon, 4)],
        "p": "".join(path),
        "z": zone, "e": int(elev), "sl": round(float(slope), 1), "rf": int(relief),
        "hist": hist, "geo": geol, "soil": soil, "tier": tier,
        "obs": observed, "sites": sites,
        "ndvi": ndvi, "bare": bare, "snow": snow,
        "area": int(max(area_km2, 20)),
    })

# state outlines
states_out = {}
for state, geoms in state_geoms.items():
    u = unary_union(geoms).simplify(0.02, preserve_topology=True)
    polys = list(u.geoms) if u.geom_type == "MultiPolygon" else [u]
    polys = [pg for pg in polys if pg.area > 0.004] or [max(polys, key=lambda g: g.area)]
    path = []
    for pg in polys:
        pts = []
        for lon, lat in pg.exterior.coords:
            x, y = proj(lon, lat)
            pts.append(f"{x:.1f},{y:.1f}")
        ded = [pts[0]]
        for q in pts[1:]:
            if q != ded[-1]:
                ded.append(q)
        if len(ded) >= 3:
            path.append("M" + "L".join(ded) + "Z")
    c = unary_union(geoms).representative_point()
    states_out[state] = {"p": "".join(path), "c": [round(proj(c.x, c.y)[0], 1), round(proj(c.x, c.y)[1], 1)]}

# ------------------------------------------------- September rainfall normals
# Mean daily rainfall (mm/day) for mid-September, by physiographic zone,
# modulated by longitude (orographic) and distance from the monsoon trough.
RAIN_BASE = {
    "greater_himalaya": 4.0, "lesser_himalaya": 8.5, "siwalik": 9.0,
    "ne_hills": 13.0, "shillong": 16.0, "western_ghats": 11.0, "wg_south": 12.5,
    "eastern_ghats": 7.0, "plateau": 6.0, "alluvium": 7.5,
    "coastal": 8.0, "desert": 1.2, "deccan": 5.0,
}
for d in districts:
    lat, lon = d["ll"]
    base = RAIN_BASE[d["z"]]
    if lon > 90.0:                       # far NE, retreating monsoon still active
        base *= 1.18
    if d["s"] == "Ladakh" or (d["s"] == "Jammu and Kashmir" and lat > 34.2):
        base *= 0.22                     # rain shadow
    if d["z"] == "alluvium" and lon < 78 and lat > 28:
        base *= 0.55                     # NW plains, monsoon withdrawing
    if d["z"] in ("western_ghats", "wg_south") and lon > 76.8:
        base *= 0.5                      # leeward side
    d["rn"] = round(base, 1)
    # snowline: fraction of the district above ~4500 m
    d["snowline"] = round(max(0.0, min(0.85, (d["e"] - 2600) / 3200)), 3)

xs, ys = [], []
for d in districts:
    for chunk in re.findall(r"[-\d.]+,[-\d.]+", d["p"]):
        a, b = chunk.split(",")
        xs.append(float(a)); ys.append(float(b))
pad = 8
vb = [round(min(xs) - pad, 1), round(min(ys) - pad, 1),
      round(max(xs) - min(xs) + 2 * pad, 1), round(max(ys) - min(ys) + 2 * pad, 1)]
out_vb = vb

out = {"w": W, "h": H, "bbox": [LON0, LAT0, LON1, LAT1],
       "proj": {"ox": round(OX, 4), "oy": round(OY, 4), "s": round(S, 6),
                "mx0": round(MX0, 8), "my0": round(MY0, 8)},
       "vb": out_vb, "states": states_out, "districts": districts}

out_path = os.path.join(BASE_DIR, "geo_data.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(out, f, separators=(",", ":"))

print("districts:", len(districts), "states:", len(states_out))
print("observed:", sum(1 for d in districts if d["obs"]))
print("tier1:", sum(1 for d in districts if d["tier"] == 1),
      "tier2:", sum(1 for d in districts if d["tier"] == 2),
      "tier3:", sum(1 for d in districts if d["tier"] == 3))
print("size KB:", round(os.path.getsize(out_path) / 1024))
