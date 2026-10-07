import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, CircleMarker, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import SatelliteLayerToggle from './SatelliteLayerToggle';

// Custom pulsing div icons for Leaflet
const criticalIcon = L.divIcon({
  className: '',
  html: '<div class="marker-pulse-critical"><span class="w-1.5 h-1.5 rounded-full bg-white animate-ping"></span></div>',
  iconSize: [16, 16],
  iconAnchor: [8, 8],
  popupAnchor: [0, -10],
});

const highRiskIcon = L.divIcon({
  className: '',
  html: '<div class="marker-pulse-high"></div>',
  iconSize: [14, 14],
  iconAnchor: [7, 7],
  popupAnchor: [0, -9],
});

const shelterIcon = L.divIcon({
  className: '',
  html: '<div class="marker-safe-shelter"><span>🛡️</span></div>',
  iconSize: [22, 22],
  iconAnchor: [11, 11],
  popupAnchor: [0, -12],
});

// Audio beep tone using Web Audio API
const playAlertBeep = () => {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    if (ctx.state === 'suspended') {
      ctx.resume().catch(() => {});
    }
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, ctx.currentTime); // A5 note
    gain.gain.setValueAtTime(0.12, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.35);
  } catch (e) {
    // Audio autoplay restrictions gracefully handled
  }
};

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
  customZoom = null,
  evacuationRoute = null,
  safeShelters = [],
  onShelterClick = null
}) {
  const [baseMap, setBaseMap] = useState('satellite');
  const [activeSatelliteLayer, setActiveSatelliteLayer] = useState('none');
  const [isroEnabled, setIsroEnabled] = useState(false);
  const beepTriggeredRef = useRef(false);

  // Trigger audio alert when critical locations are present on first load / updates
  useEffect(() => {
    const hasCritical = locations.some((loc) => {
      const prob = loc.hazard_index ?? loc.risk_probability;
      return loc.risk_category === 'Critical' || (prob != null && prob >= 0.80);
    });

    if (hasCritical && !beepTriggeredRef.current) {
      playAlertBeep();
      beepTriggeredRef.current = true;
    }
  }, [locations]);

  // All-India Geographic Center
  const indiaCenter = [22.8, 82.0];
  const activeCenter = selectedLocation
    ? [selectedLocation.latitude, selectedLocation.longitude]
    : indiaCenter;

  const currentZoom = selectedLocation ? 9 : (customZoom || 5);

  const getMarkerColor = (loc) => {
    if (loc.has_prediction === false) {
      return '#94a3b8'; // Slate/Grey for plain terrain
    }

    if (activeSatelliteLayer === 'snow') {
      if (loc.snow_cover_pct == null) return '#94a3b8';
      const snow = loc.snow_cover_pct;
      return snow > 40 ? '#06b6d4' : snow > 10 ? '#38bdf8' : '#94a3b8';
    }
    if (activeSatelliteLayer === 'soil') {
      if (loc.bare_soil_pct == null) return '#94a3b8';
      const soil = loc.bare_soil_pct;
      return soil > 45 ? '#d97706' : soil > 25 ? '#f59e0b' : '#84cc16';
    }
    if (activeSatelliteLayer === 'ndvi') {
      if (loc.vegetation_index == null) return '#94a3b8';
      const veg = loc.vegetation_index;
      return veg < 0.4 ? '#dc2626' : veg < 0.65 ? '#eab308' : '#10b981';
    }
    if (activeSatelliteLayer === 'sar') {
      return loc.flood_extent_flag ? '#2563eb' : '#94a3b8';
    }

    // Default Landslide Risk Colors
    const prob = loc.hazard_index ?? loc.risk_probability;
    if (loc.risk_category === 'Critical' || (prob != null && prob >= 0.80)) return '#ef4444';
    if (loc.risk_category === 'High' || (prob != null && prob >= 0.60)) return '#f97316';
    if (loc.risk_category === 'Moderate' || (prob != null && prob >= 0.40)) return '#eab308';
    if (loc.risk_category === 'Low' || (prob != null && prob < 0.40)) return '#10b981';
    return '#64748b'; // Neutral slate
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-4 flex flex-col h-full relative overflow-hidden">
      {/* Map Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3 z-20">
        <div className="flex items-center space-x-2">
          <h2 className="text-sm font-bold text-slate-900 tracking-tight">
            National Multi-Hazard Risk Map — All India
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
              attribution='&copy; <a href="https://www.esri.com/">Esri</a>, Earthstar Geographics, Maxar'
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              maxZoom={19}
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

          {/* Evacuation Route Polyline if available */}
          {evacuationRoute && evacuationRoute.coordinates && (
            <Polyline
              positions={evacuationRoute.coordinates}
              pathOptions={{
                color: '#2563eb',
                weight: 5,
                opacity: 0.9,
                dashArray: evacuationRoute.isAlternative ? '8, 8' : undefined,
                lineJoin: 'round'
              }}
            />
          )}

          {/* Safe Shelters Markers */}
          {safeShelters.map((shelter, idx) => (
            <Marker
              key={`shelter-${idx}-${shelter.name}`}
              position={[shelter.lat, shelter.lng]}
              icon={shelterIcon}
              eventHandlers={{
                click: () => onShelterClick && onShelterClick(shelter)
              }}
            >
              <Popup>
                <div className="p-2 min-w-[180px] text-xs">
                  <div className="border-b border-emerald-100 pb-1 mb-1.5 flex items-center gap-1.5">
                    <span className="text-emerald-600 font-bold">🛡️ {shelter.type || 'Safe Shelter'}</span>
                  </div>
                  <div className="font-bold text-slate-900">{shelter.name}</div>
                  <div className="text-[11px] text-slate-500">{shelter.district}, {shelter.state || ''}</div>
                  <div className="mt-1.5 pt-1.5 border-t border-slate-100 flex justify-between text-[11px]">
                    <span className="text-slate-500">Capacity:</span>
                    <span className="font-semibold text-slate-800">{shelter.capacity} people</span>
                  </div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-slate-500">Contact / Helpline:</span>
                    <span className="font-bold text-emerald-700">{shelter.contact || '1078'}</span>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}

          {/* Location Risk Markers */}
          {locations.map((loc) => {
            const isSelected = selectedLocation && selectedLocation.id === loc.id;
            const color = getMarkerColor(loc);
            const isPlain = loc.has_prediction === false;
            const rawHazard = loc.hazard_index ?? loc.risk_probability;
            const isCritical = (loc.risk_category === 'Critical' || (rawHazard != null && rawHazard >= 0.80)) && activeSatelliteLayer === 'none';
            const isHigh = !isCritical && (loc.risk_category === 'High' || (rawHazard != null && rawHazard >= 0.60)) && activeSatelliteLayer === 'none';

            const popupContent = (
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
                          {rawHazard != null ? `${loc.risk_category || 'Active'} (${Math.round(rawHazard * 100)}%)` : 'NO DATA'}
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
            );

            // Use animated pulsing DivIcon markers for Critical and High risk
            if (isCritical) {
              return (
                <Marker
                  key={loc.id}
                  position={[loc.latitude, loc.longitude]}
                  icon={criticalIcon}
                  eventHandlers={{
                    click: () => onSelectLocation(loc),
                  }}
                >
                  {popupContent}
                </Marker>
              );
            }

            if (isHigh) {
              return (
                <Marker
                  key={loc.id}
                  position={[loc.latitude, loc.longitude]}
                  icon={highRiskIcon}
                  eventHandlers={{
                    click: () => onSelectLocation(loc),
                  }}
                >
                  {popupContent}
                </Marker>
              );
            }

            // Standard Circle Markers for Moderate, Low, or other layer overlays
            return (
              <CircleMarker
                key={loc.id}
                center={[loc.latitude, loc.longitude]}
                radius={isSelected ? 10 : 5}
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
                {popupContent}
              </CircleMarker>
            );
          })}
        </MapContainer>

        {/* Floating Satellite Intelligence Layer Switcher */}
        <div className="absolute top-3 left-3 z-20 max-w-[95%]">
          <SatelliteLayerToggle
            activeLayer={activeSatelliteLayer}
            onToggleLayer={setActiveSatelliteLayer}
            isroEnabled={isroEnabled}
            onToggleIsro={() => setIsroEnabled(!isroEnabled)}
          />
        </div>

        {/* Floating Bottom Legend */}
        <div className="absolute bottom-3 left-3 z-20 bg-white/95 backdrop-blur-md px-3 py-1.5 rounded-xl border border-slate-200/90 shadow-md text-xs flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping" />
            <span className="text-[11px] font-bold text-red-600">Critical (≥80%)</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-orange-500" />
            <span className="text-[11px] font-medium text-slate-700">High (60-79%)</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
            <span className="text-[11px] font-medium text-slate-700">Moderate (40-59%)</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <span className="text-[11px] font-medium text-slate-700">Low (&lt;40%)</span>
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
