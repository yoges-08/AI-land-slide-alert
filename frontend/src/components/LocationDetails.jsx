import React from 'react';
import {
  X,
  MapPin,
  AlertTriangle,
  Info,
  ArrowRight,
  Layers,
  Sparkles,
  Compass,
  Mountain,
  Droplet,
  ShieldCheck
} from 'lucide-react';
import RiskFactorBar from './RiskFactorBar';
import DataSourceTag from './DataSourceTag';

export default function LocationDetails({
  location,
  liveWeather,
  onClose,
  onOpenAnalysis,
  onOpenSimulation
}) {
  if (!location) {
    return (
      <div className="bg-white rounded-2xl p-6 border border-slate-200/90 shadow-sm h-full flex flex-col items-center justify-center text-center">
        <MapPin className="w-10 h-10 text-slate-300 mb-2 stroke-1" />
        <p className="text-sm font-semibold text-slate-700">Select a Location / District</p>
        <p className="text-xs text-slate-400 mt-1 max-w-[200px]">
          Click any state or district marker on the map to inspect terrain features and ML hazard predictions.
        </p>
      </div>
    );
  }

  const name = location.name || 'Location';
  const state = location.state || '';
  const district = location.district || state;
  const lat = location.latitude ? location.latitude.toFixed(2) : '--';
  const lon = location.longitude ? location.longitude.toFixed(2) : '--';
  const elevation = location.elevation != null ? location.elevation.toLocaleString() : '--';
  const slope = location.slope != null ? location.slope.toFixed(0) : '--';
  const soilType = location.soil_type || 'Unclassified';
  const rain24h = liveWeather?.rainfall_24h ?? location.rainfall_24h;
  const hasPrediction = location.has_prediction !== false && (location.hazard_index != null || location.risk_probability != null);
  const hazardVal = location.hazard_index ?? location.risk_probability;
  const prob = hazardVal != null ? Math.round(hazardVal * 100) : null;
  const category = location.risk_category || (prob != null ? (prob >= 70 ? 'High Risk' : prob >= 30 ? 'Moderate Risk' : 'Low Risk') : 'No Active Assessment');
  const floodCategory = location.flood_risk_category || 'No Data';

  const factors = location.key_risk_factors || null;

  const imageSrc = location.image_url || 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=500&auto=format&fit=crop&q=60';

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-4 flex flex-col justify-between h-full relative overflow-hidden">
      <div>
        {/* Card Header with Image and Coordinates */}
        <div className="relative rounded-xl overflow-hidden mb-3 border border-slate-100 shadow-sm">
          <img
            src={imageSrc}
            alt={name}
            onError={(e) => {
              e.currentTarget.onerror = null;
              e.currentTarget.src = 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=500&auto=format&fit=crop&q=60';
            }}
            className="w-full h-24 object-cover brightness-[0.95]"
          />
          <button
            onClick={onClose}
            className="absolute top-2 right-2 p-1.5 bg-black/40 hover:bg-black/60 text-white rounded-full transition-colors backdrop-blur-sm"
            title="Close Panel"
          >
            <X className="w-3.5 h-3.5" />
          </button>
          <div className="absolute bottom-2 left-2 bg-black/50 backdrop-blur-sm px-2 py-0.5 rounded text-[10px] text-white font-medium flex items-center gap-1">
            <Compass className="w-3 h-3 text-emerald-300" />
            <span>{lat}° N, {lon}° E</span>
          </div>
        </div>

        {/* Title, District & State */}
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900 leading-tight">{name}</h3>
            <p className="text-xs text-slate-500 font-medium">
              District: <span className="text-slate-800 font-semibold">{district}</span> • {state}
            </p>
          </div>
          <DataSourceTag source={location.satellite_source || 'NASA/Copernicus'} isSample={location.is_sample_data} />
        </div>

        {/* Risk Probability Banner OR Plain District Notice */}
        {hasPrediction && prob != null ? (
          <div className="mt-3 bg-red-50/70 border border-red-100 rounded-xl p-3 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-7 h-7 rounded-lg bg-red-500 text-white flex items-center justify-center shadow-xs">
                <AlertTriangle className="w-4 h-4" />
              </div>
              <div>
                <span className="text-xs font-bold text-red-700 block leading-tight">
                  {category.includes('Risk') ? category : `${category} Risk`}
                </span>
                <span className="text-[10px] text-red-600/80 font-medium">Hazard Index</span>
              </div>
            </div>
            <div className="text-right">
              <span className="text-xl font-extrabold text-red-600 leading-none">{prob}%</span>
              <span className="text-[10px] text-slate-500 block font-medium">Calculated Score</span>
            </div>
          </div>
        ) : (
          <div className="mt-3 bg-slate-50 border border-slate-200 rounded-xl p-3 flex items-center space-x-2.5">
            <ShieldCheck className="w-6 h-6 text-slate-400 flex-shrink-0" />
            <div>
              <span className="text-xs font-bold text-slate-700 block">Awaiting Trigger / Observation</span>
              <p className="text-[10px] text-slate-500 leading-tight mt-0.5">
                Zero-fabrication policy: Real-time hazard scoring requires confirmed meteorological & satellite feeds.
              </p>
            </div>
          </div>
        )}

        {/* Secondary Hazard Badge (Flood Risk) */}
        <div className="mt-2 flex items-center justify-between px-3 py-1.5 bg-blue-50/60 border border-blue-100/80 rounded-lg text-xs">
          <span className="text-blue-800 font-medium text-[11px] flex items-center gap-1">
            <Droplet className="w-3.5 h-3.5 text-blue-500" /> Multi-Hazard Flood Risk:
          </span>
          <span className="font-semibold text-blue-700 text-[11px]">{floodCategory}</span>
        </div>

        {/* 4-Cell Terrain Metrics */}
        <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
          <div className="bg-slate-50/80 p-2.5 rounded-lg border border-slate-100">
            <span className="text-[10px] text-slate-400 block font-medium">Rainfall (24h)</span>
            <span className="font-bold text-slate-900 text-xs">{rain24h != null ? `${rain24h} mm` : '--'}</span>
          </div>
          <div className="bg-slate-50/80 p-2.5 rounded-lg border border-slate-100">
            <span className="text-[10px] text-slate-400 block font-medium">Slope</span>
            <span className="font-bold text-slate-900 text-xs">{slope !== '--' ? `${slope}°` : '--'}</span>
          </div>
          <div className="bg-slate-50/80 p-2.5 rounded-lg border border-slate-100">
            <span className="text-[10px] text-slate-400 block font-medium">Elevation</span>
            <span className="font-bold text-slate-900 text-xs">{elevation !== '--' ? `${elevation} m` : '--'}</span>
          </div>
          <div className="bg-slate-50/80 p-2.5 rounded-lg border border-slate-100">
            <span className="text-[10px] text-slate-400 block font-medium">Soil Type</span>
            <span className="font-bold text-slate-900 text-xs truncate block">{soilType}</span>
          </div>
        </div>

        {/* Key Risk Factors */}
        {hasPrediction && factors && (
          <div className="mt-3.5 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-800 text-xs flex items-center gap-1">
                Key Risk Factors
                <Info className="w-3 h-3 text-slate-400 inline" />
              </span>
              <span className="text-[10px] text-slate-400 font-medium">ML Feature Contribution</span>
            </div>

            {factors.heavy_rainfall != null && <RiskFactorBar label="Heavy Rainfall" percentage={factors.heavy_rainfall} color="red" />}
            {factors.steep_slope != null && <RiskFactorBar label="Steep Slope" percentage={factors.steep_slope} color="orange" />}
            {factors.land_cover_change != null && <RiskFactorBar label="Land Cover Change" percentage={factors.land_cover_change} color="amber" />}
            {factors.historical_landslide != null && <RiskFactorBar label="Historical Landslide" percentage={factors.historical_landslide} color="yellow" />}
          </div>
        )}

        {/* Satellite Terrain Intelligence Breakdown */}
        <div className="mt-3 pt-2.5 border-t border-slate-100">
          <div className="flex items-center justify-between text-[11px] mb-1.5">
            <span className="font-semibold text-slate-700 flex items-center gap-1">
              <Layers className="w-3 h-3 text-emerald-600" /> Satellite Terrain Intelligence
            </span>
            <span className="text-[10px] text-slate-400">Sentinel & MODIS</span>
          </div>
          <div className="grid grid-cols-2 gap-1.5 text-[10px]">
            <div className="bg-slate-50 px-2 py-1 rounded text-slate-600">
              Snow Cover: <span className="font-semibold text-slate-900">{location.snow_cover_pct != null ? `${location.snow_cover_pct}%` : '--'}</span>
            </div>
            <div className="bg-slate-50 px-2 py-1 rounded text-slate-600">
              Bare Soil (BSI): <span className="font-semibold text-slate-900">{location.bare_soil_pct != null ? `${location.bare_soil_pct}%` : '--'}</span>
            </div>
            <div className="bg-slate-50 px-2 py-1 rounded text-slate-600">
              Vegetation (NDVI): <span className="font-semibold text-slate-900">{location.vegetation_index != null ? location.vegetation_index : '--'}</span>
            </div>
            <div className="bg-slate-50 px-2 py-1 rounded text-slate-600">
              Slope Farm: <span className="font-semibold text-slate-900">{location.farm_change_flag ? 'Detected' : 'None'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="mt-4 pt-2 border-t border-slate-100 flex gap-2">
        <button
          onClick={onOpenSimulation}
          className="flex-1 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold flex items-center justify-center space-x-1 transition-all"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-600" />
          <span>Simulate</span>
        </button>
        <button
          onClick={onOpenAnalysis}
          className="flex-1 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all shadow-sm"
        >
          <span>View Full Analysis</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
