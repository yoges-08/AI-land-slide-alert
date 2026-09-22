# LANDSAFE-NER: Live Data Sources & Satellite Telemetry Guide

This document provides a comprehensive technical breakdown of all data sources integrated into the **LANDSAFE-NER** Early Warning System, detailing which source provides which live data, the underlying satellites and sensors, update frequencies, and how each metric feeds into the machine learning hazard prediction engine.

---

## 1. Quick Reference Matrix

| Source / Provider | Satellites & Sensors | Live Telemetry / Data Fields Provided | Update Frequency | API & Integration Layer |
| :--- | :--- | :--- | :--- | :--- |
| **🇪🇺 Copernicus CDSE** *(European Space Agency)* | **Sentinel-2 L2A** *(Multispectral Instrument - MSI)* | • **Vegetation Index (NDVI)** (Band 8 / Band 4)<br>• **Bare Soil Index (BSI)** (%)<br>• Cloud-filtered surface reflectance | 10-day composite cloudless sweep (real-time query) | Sentinel Hub Statistics API (`/api/v1/statistics`) |
| **🇺🇸 NASA FIRMS** *(NASA EOSDIS)* | **VIIRS (SNPP / NOAA-20/21)** *(Thermal Infrared)* | • **Active Thermal / Wildfire Hotspots**<br>• Vegetation burn-off detection (soil destabilization flag) | Near Real-Time (NRT) | NASA FIRMS Area API (`/api/area/csv`) |
| **🌐 Open-Meteo Telemetry** | **Global In-Situ & Radar Stations** *(ECMWF, GFS, DWD)* | • **1-Hour Rainfall (mm)**<br>• **24-Hour Observed Rainfall (mm)**<br>• **7-Day Cumulative Rainfall (mm)**<br>• **Topsoil Moisture (0–1 cm depth)** (%)<br>• **Temperature (°C), Humidity (%), Wind Speed (km/h)**<br>• **WMO Weather Code & 5-Day Daily Forecast** | Hourly / 15-minute station updates | Open-Meteo Forecast & Historical API |
| **🇺🇸 NASA GIBS** *(NASA EOSDIS)* | **MODIS (Terra & Aqua Satellites)** | • **True-Color Visible Optical Satellite Base Layer** (WMTS Tiles) | Daily global satellite sweep | NASA GIBS WMTS Tile Service (`EPSG:3857`) |
| **🇮🇳 ISRO Bhuvan & SRTM** | **Cartosat DEM & Shuttle Radar Topography Mission** | • **Digital Elevation (meters ASL)**<br>• **Slope Gradient (degrees)**<br>• **Proximity to Drainage / River Channels (meters)** | Static Geomorphological Baseline | Geomorphological Baseline Database |
| **🇮🇳 Geological Survey of India (GSI) & LGD** | **National Landslide Susceptibility Mapping (NLSM)** | • **Historical Landslide Incident Counts**<br>• **Soil Taxonomy** *(e.g., Clay Loam, Sandy Loam)*<br>• **Geological Lithology** *(Sedimentary, Metamorphic, Igneous)* | Official Government District Baseline | 788 Local Government Directory (LGD) Districts |

---

## 2. Detailed Technical Breakdown by Source

### 🛰️ 1. Copernicus Sentinel-2 L2A (European Space Agency CDSE)

* **Provider**: Copernicus Data Space Ecosystem (CDSE) / European Space Agency (ESA).
* **Sensor**: Multi-Spectral Instrument (MSI) aboard Sentinel-2A and Sentinel-2B.
* **Spatial Resolution**: 10m to 20m per pixel (samples 65,536 satellite pixels per query box).
* **Live Telemetry Extracted**:
  1. **NDVI (Normalized Difference Vegetation Index)**:
     $$\text{NDVI} = \frac{\text{B08 (NIR)} - \text{B04 (Red)}}{\text{B08 (NIR)} + \text{B04 (Red)}}$$
     * **Significance**: Quantifies vegetation density and slope root anchoring. Dense root networks bind topsoil against shearing forces.
  2. **Bare Soil Index (BSI)**:
     * **Significance**: Calculates percentage of exposed, loose soil devoid of canopy cover. High bare soil exposure significantly increases rainfall infiltration rate and rapid slope liquefaction risk.
* **Backend Module**: [`backend/app/services/satellite_service.py`](file:///c:/Users/yoges/OneDrive/Documents/ai%20land%20slide/backend/app/services/satellite_service.py) (`_fetch_sentinel2_indices`).

---

### 🔥 2. NASA FIRMS (Fire Information for Resource Management System)

* **Provider**: NASA Earth Observing System Data and Information System (EOSDIS).
* **Sensor**: Visible Infrared Imaging Radiometer Suite (VIIRS) aboard Suomi-NPP and NOAA-20 satellites (375m thermal bands).
* **Live Telemetry Extracted**:
  1. **Active Wildfire / Thermal Hotspot Detection**:
     * Scans a $0.5^\circ \times 0.5^\circ$ (~50 km radius) bounding box around the selected district.
     * Returns a boolean flag: `fire_detected: true | false`.
     * **Significance**: Hillsides burned by wildfires lose surface vegetation and organic binding agents, creating hydrophobic soil crusts that drastically increase debris-flow susceptibility during subsequent monsoon downpours.
* **Backend Module**: [`backend/app/services/satellite_service.py`](file:///c:/Users/yoges/OneDrive/Documents/ai%20land%20slide/backend/app/services/satellite_service.py) (`_fetch_nasa_firms_fire`).

---

### 🌧️ 3. Open-Meteo (Live Meteorological Ingestion)

* **Provider**: Open-Meteo Global Meteorological Telemetry.
* **Live Telemetry Extracted**:
  1. **Current Rainfall (1h)**: Instantaneous rain intensity in mm/hr.
  2. **24-Hour Observed Rainfall**: Past 24 hours cumulative precipitation sum ($R_{24}$).
  3. **7-Day Cumulative Rainfall & Trend**: 7-day antecedent precipitation sum ($R_{7d}$) for saturation modeling.
  4. **Soil Moisture (0–1 cm)**: Topsoil volumetric water content in percentage.
  5. **Atmospheric Parameters**: Ambient temperature ($^\circ\text{C}$), relative humidity (%), wind speed ($\text{km/h}$), WMO code (rain, storm, drizzle, etc.).
  6. **5-Day Daily Weather Forecast**: Temperature highs/lows, rain probability, and weather condition predictions.
* **Significance**: Rainfall is the primary dynamic trigger for landslides in the Himalayas and Western Ghats. High 24-hour rain combined with saturated antecedent 7-day soil creates pore-water pressure that triggers slope collapse.
* **Backend Module**: [`backend/app/services/weather_service.py`](file:///c:/Users/yoges/OneDrive/Documents/ai%20land%20slide/backend/app/services/weather_service.py) & [`frontend/src/services/api.js`](file:///c:/Users/yoges/OneDrive/Documents/ai%20land%20slide/frontend/src/services/api.js).

---

### 🗺️ 4. NASA GIBS (Global Imagery Browse Services)

* **Provider**: NASA EOSDIS.
* **Sensor**: MODIS (Moderate Resolution Imaging Spectroradiometer) on Terra & Aqua satellites.
* **Live Telemetry Extracted**:
  * **Daily Corrected Reflectance True-Color Imagery**: Streams high-resolution WMTS optical satellite map tiles directly onto the interactive Leaflet GIS map.
  * **Usage**: Allows users to inspect visual satellite imagery showing mountain passes, active cloud formations, snow lines, and river valleys across India.
* **Frontend Component**: [`frontend/src/components/RiskMap.jsx`](file:///c:/Users/yoges/OneDrive/Documents/ai%20land%20slide/frontend/src/components/RiskMap.jsx).

---

### ⛰️ 5. ISRO Bhuvan & SRTM (Geomorphology & Terrain Baseline)

* **Provider**: ISRO National Remote Sensing Centre (NRSC) & NASA/USGS SRTM.
* **Telemetry Extracted**:
  1. **Elevation (m ASL)**: Altitude above sea level.
  2. **Slope Angle ($^\circ$)**: Terrain incline angle. Slopes steeper than $25^\circ\text{--}35^\circ$ carry exponential gravitational shear stress.
  3. **Hydrological Drainage Distance (m)**: Proximity to nearest active river channel or toe-cutting stream.
* **Backend Module**: Integrated into District Terrain Geomorphology Profiles.

---

### 🏛️ 6. Geological Survey of India (GSI) & National Disaster Management Authority (NDMA)

* **Provider**: Geological Survey of India (NLSM) & Ministry of Panchayati Raj Local Government Directory (LGD).
* **Baseline Parameters**:
  1. **Historical Landslide Frequency**: Recorded historical slide counts per district.
  2. **Soil Taxonomy**: Soil grain type (`Clay Loam`, `Sandy Loam`, `Silty Clay`, etc.).
  3. **Geological Lithology**: Rock formation classification (`Sedimentary`, `Metamorphic`, `Igneous`).
  4. **788 LGD District Mappings**: Complete administrative coverage across all Indian states and Union Territories.

---

## 3. How the Machine Learning Engine Uses This Live Data

All live streams converge in real time into the Gradient Boosting Hazard Prediction Model:

```
┌─────────────────────────────────────────────────────────┐
│                     LIVE DATA STREAMS                   │
├────────────────────────────┬────────────────────────────┤
│  Copernicus Sentinel-2     │  • Vegetation Index (NDVI) │
│  (Optical Satellite)       │  • Bare Soil %             │
├────────────────────────────┼────────────────────────────┤
│  NASA FIRMS                │  • Active Thermal Hotspots │
│  (Thermal Satellite)       │  • Burn-off Area Flag      │
├────────────────────────────┼────────────────────────────┤
│  Open-Meteo                │  • 24h Rainfall & 7d Rain  │
│  (Live Meteorological)     │  • Topsoil Moisture %      │
├────────────────────────────┼────────────────────────────┤
│  ISRO / GSI / SRTM         │  • Slope, Elevation, Rocks │
│  (Geomorphological)        │  • Soil Type, River Dist   │
└────────────────────────────┴─────────────┬──────────────┘
                                           │
                                           ▼
                 ┌──────────────────────────────────┐
                 │  Gradient Boosting ML Classifier │
                 │      & SHAP Explainability       │
                 └─────────────────┬────────────────┘
                                   │
                                   ▼
        ┌───────────────────────────────────────────────────────┐
        │                 REAL-TIME PLATFORM OUTPUTS            │
        ├───────────────────────────────────────────────────────┤
        │ • Hazard Probability Index (0.00 – 1.00)              │
        │ • Hazard Level (Low / Moderate / High Risk)           │
        │ • SHAP Factor Importance Breakdown                    │
        │ • Early Warning Threshold Alerts & SMS Dispatch       │
        └───────────────────────────────────────────────────────┘
```

---

## 4. Viewing Live Data on the Website

1. **Location Details Panel**:
   * Click on any district marker (e.g. *Anantnag*, *East Sikkim*, *Wayanad*).
   * The **Satellite Terrain Intelligence** card displays real-time **NDVI**, **Bare Soil %**, **NASA FIRMS Fire Hotspot**, and **Data Freshness**.
2. **Interactive Map Layer Switcher**:
   * Switch base layer to **Satellite** to view daily **NASA MODIS True-Color** imagery.
   * Toggle **Satellite Intelligence** overlays for **NDVI Vegetation Health**, **Soil Saturation**, and **SAR Terrain**.
3. **SHAP Factor Breakdown Modal**:
   * Click **View Full Analysis** to see the exact weight of each live satellite and weather metric in the final hazard computation.
