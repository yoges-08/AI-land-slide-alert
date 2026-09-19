import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import SatelliteLayerToggle from './SatelliteLayerToggle';

// Map controller to smoothly pan/zoom to selected location or state/district
function MapRecenter({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (center && center[0] && center[1]) {
      map.flyTo(center, zoom || 6, { duration: 1.2 });
    }
  }, [center, zoom, map]);
  return null;
}

export default function RiskMap({
  locations = [],
  selectedLocation,
  onSelectLocation,
  customZoom = null
}) {
  const [baseMap, setBaseMap] = useState('satellite');
  const [activeSatelliteLayer, setActiveSatelliteLayer] = useState('none');
  const [isroEnabled, setIsroEnabled] = useState(false);

  // All-India Geographic Center
  const indiaCenter = [22.8, 82.0];
  const activeCenter = selectedLocation
    ? [selectedLocation.latitude, selectedLocation.longitude]
    : indiaCenter;

  const currentZoom = selectedLocation ? 9 : (customZoom || 5);

  const getMarkerColor = (loc) => {
    // If location is a plain / low risk tier without high hazard monitoring
    if (loc.has_prediction === false) {
      return '#94a3b8'; // Slate/Grey for plain terrain
    }

    if (activeSatelliteLayer === 'snow') {
      const snow = loc.snow_cover_pct || 0;
      return snow > 40 ? '#06b6d4' : snow > 10 ? '#38bdf8' : '#94a3b8';
    }
    if (activeSatelliteLayer === 'soil') {
      const soil = loc.bare_soil_pct || 15;
      return soil > 45 ? '#d97706' : soil > 25 ? '#f59e0b' : '#84cc16';
    }
    if (activeSatelliteLayer === 'ndvi') {
      const veg = loc.vegetation_index || 0.6;
      return veg < 0.4 ? '#dc2626' : veg < 0.65 ? '#eab308' : '#10b981';
    }
    if (activeSatelliteLayer === 'sar') {
      return loc.flood_extent_flag ? '#2563eb' : '#94a3b8';
    }

    // Default Landslide Risk Colors
    const prob = loc.risk_probability || 0.2;
    if (loc.risk_category === 'High' || prob >= 0.70) return '#ef4444';
    if (loc.risk_category === 'Moderate' || prob >= 0.30) return '#f59e0b';
    return '#10b981';
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-4 flex flex-col h-full relative overflow-hidden">
      {/* Map Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3 z-20">
        <div className="flex items-center space-x-2">
          <h2 className="text-sm font-bold text-slate-900 tracking-tight">
            National Multi-Hazard Risk Map — All India (State & District Hierarchy)
          </h2>
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-600 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse mr-1" />
            Live Ingestion
          </span>
        </div>

        {/* Basemap Switcher */}
        <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs">
          <button
            onClick={() => setBaseMap('satellite')}
            className={`px-3 py-1 rounded-md font-semibold transition-all ${
              baseMap === 'satellite'
                ? 'bg-white text-slate-800 shadow-xs'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Satellite
          </button>
          <button
            onClick={() => setBaseMap('terrain')}
            className={`px-3 py-1 rounded-md font-semibold transition-all ${
              baseMap === 'terrain'
                ? 'bg-white text-slate-800 shadow-xs'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Terrain
          </button>
        </div>
      </div>

      {/* Leaflet Map Canvas */}
      <div className="relative flex-1 rounded-xl overflow-hidden min-h-[400px]">
        <MapContainer
          center={indiaCenter}
          zoom={5}
          scrollWheelZoom={true}
          className="w-full h-full"
        >
          <MapRecenter center={activeCenter} zoom={currentZoom} />

          {/* Base Tile Layer */}
          {baseMap === 'satellite' ? (
            <TileLayer
              attribution="Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              maxZoom={18}
            />
          ) : (
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
              url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
              maxZoom={19}
            />
          )}

          {/* Optional ISRO Bhuvan WMS Overlay */}
          {isroEnabled && (
            <TileLayer
              attribution="ISRO / NRSC Bhuvan"
              url="https://bhuvan-vec1.nrsc.gov.in/bhuvan/gwc/service/wms/?service=WMS&request=GetMap&layers=india3&styles=&format=image/png&transparent=true&version=1.1.1&width=256&height=256&srs=EPSG:3857&bbox={bbox-epsg-3857}"
              opacity={0.65}
            />
          )}

          {/* Location Risk Markers */}
          {locations.map((loc) => {
            const isSelected = selectedLocation && selectedLocation.id === loc.id;
            const color = getMarkerColor(loc);
            const isPlain = loc.has_prediction === false;
            const isHighRisk = loc.risk_category === 'High' && activeSatelliteLayer === 'none';

            return (
              <CircleMarker
                key={loc.id}
                center={[loc.latitude, loc.longitude]}
                radius={isSelected ? 10 : isHighRisk ? 7 : 5}
                pathOptions={{
                  color: isSelected ? '#ffffff' : color,
                  weight: isSelected ? 3 : 1.5,
                  fillColor: color,
                  fillOpacity: isSelected ? 0.95 : 0.8,
                }}
                eventHandlers={{
                  click: () => onSelectLocation(loc),
                }}
              >
                <Popup>
                  <div className="p-2 min-w-[180px] text-xs">
                    <div className="border-b border-slate-100 pb-1 mb-1.5">
                      <span className="font-bold text-slate-900 block">{loc.name}</span>
                      <span className="text-[10px] text-slate-500 font-medium">
                        {loc.district}, {loc.state}
                      </span>
                    </div>

                    <div className="space-y-1 text-[11px]">
                      {isPlain ? (
                        <div className="bg-slate-100 p-1 rounded text-[10px] text-slate-600 font-medium">
                          Plain Terrain (Insufficient slope/hazard history for landslide prediction)
                        </div>
                      ) : (
                        <div className="flex justify-between">
                          <span className="text-slate-500">Landslide Risk:</span>
                          <span className="font-bold" style={{ color }}>
                            {loc.risk_category} ({Math.round((loc.risk_probability || 0.2) * 100)}%)
                          </span>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span className="text-slate-500">Elevation / Slope:</span>
                        <span className="font-semibold text-slate-800">{loc.elevation}m / {loc.slope}°</span>
                      </div>
                    </div>

                    <button
                      onClick={() => onSelectLocation(loc)}
                      className="w-full mt-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[11px] font-semibold transition-colors"
                    >
                      Inspect District
                    </button>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>

        {/* Floating Satellite Intelligence Layer Switcher */}
        <div className="absolute top-3 left-3 z-[1000] max-w-[95%]">
          <SatelliteLayerToggle
            activeLayer={activeSatelliteLayer}
            onToggleLayer={setActiveSatelliteLayer}
            isroEnabled={isroEnabled}
            onToggleIsro={() => setIsroEnabled(!isroEnabled)}
          />
        </div>

        {/* Floating Bottom Legend */}
        <div className="absolute bottom-3 left-3 z-[1000] bg-white/95 backdrop-blur-md px-3 py-1.5 rounded-xl border border-slate-200/90 shadow-md text-xs flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <span className="text-[11px] font-medium text-slate-700">Low Risk</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span className="text-[11px] font-medium text-slate-700">Moderate Risk</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
            <span className="text-[11px] font-medium text-slate-700">High Risk</span>
          </div>
          <div className="flex items-center space-x-1.5 border-l border-slate-200 pl-2">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-400" />
            <span className="text-[11px] font-medium text-slate-500">Plain / Low Hazard</span>
          </div>
        </div>
      </div>
    </div>
  );
}
