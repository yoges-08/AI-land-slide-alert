"""DEMO ONLY. Assembles 01_head.html + 02_body.html + 03_store_forecast_alerts.js + 
04_engine.js + 05_map.js + 06_ui.js + frontend/data/geo_data.json into the standalone
landsafe-dashboard.html.
"""
import os
from pathlib import Path

DIR = Path(__file__).resolve().parent
GEO_PATH = DIR / "geo_data.json"
if not GEO_PATH.exists():
    GEO_PATH = DIR.parent.parent / "frontend" / "data" / "geo_data.json"

geo = open(GEO_PATH, encoding="utf-8").read()
parts = [
    open(DIR / "01_head.html", encoding="utf-8").read(),
    open(DIR / "02_body.html", encoding="utf-8").read(),
    "\n<script>\nconst GEO = " + geo + ";\n</script>\n",
    "<script>\n" + open(DIR / "04_engine.js", encoding="utf-8").read() + "\n</script>\n",
    "<script>\n" + open(DIR / "03_store_forecast_alerts.js", encoding="utf-8").read() + "\n</script>\n",
    "<script>\n" + open(DIR / "05_map.js", encoding="utf-8").read() + "\n</script>\n",
    "<script>\n" + open(DIR / "06_ui.js", encoding="utf-8").read() + "\n</script>\n</body>\n</html>\n",
]
out = DIR / "landsafe-dashboard.html"
open(out, "w", encoding="utf-8").write("".join(parts))
print("built:", out, "-", round(os.path.getsize(out) / 1024), "KB")

