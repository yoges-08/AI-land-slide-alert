"""DEMO ONLY. Assembles src/*.html + src/*.js + data/geo_data.json into the single
self-contained landsafe-dashboard.html the project publishes/ships.
Run from the frontend/ directory: python3 build.py
"""
import os
geo = open('geo_data.json', encoding='utf-8').read()
parts = [
    open('01_head.html', encoding='utf-8').read(),
    open('02_body.html', encoding='utf-8').read(),
    "\n<script>\nconst GEO = " + geo + ";\n</script>\n",
    "<script>\n" + open('04_engine.js', encoding='utf-8').read() + "\n</script>\n",
    "<script>\n" + open('03_store_forecast_alerts.js', encoding='utf-8').read() + "\n</script>\n",
    "<script>\n" + open('05_map.js', encoding='utf-8').read() + "\n</script>\n",
    "<script>\n" + open('06_ui.js', encoding='utf-8').read() + "\n</script>\n</body>\n</html>\n",
]
out = "landsafe-dashboard.html"
open(out, "w", encoding='utf-8').write("".join(parts))
print("built:", out, "-", round(os.path.getsize(out) / 1024), "KB")
