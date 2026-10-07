import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Sparkles,
  Sliders,
  RefreshCw,
  AlertTriangle,
  Layers,
  ArrowRight,
  TrendingUp,
  Shield,
  Activity,
  Copy,
  Check
} from 'lucide-react';
import { runSimulateWhatIf } from '../services/api';

const PRESETS = [
  {
    name: 'Wayanad 2024 Disaster Conditions',
    desc: '350mm intense cloudburst, saturated Western Ghats slope',
    values: {
      rainfall_intensity: 350,
      soil_moisture: 92,
      slope: 38,
      earthquake_magnitude: 0.0,
      vegetation_cover: 30,
      duration: 48,
    }
  },
  {
    name: 'Joshimath 2023 Subsidence & Slump',
    desc: 'Moderate rainfall with seismic tremors & overburdening',
    values: {
      rainfall_intensity: 120,
      soil_moisture: 75,
      slope: 32,
      earthquake_magnitude: 3.2,
      vegetation_cover: 20,
      duration: 24,
    }
  },
  {
    name: 'Chamoli 2021 Glacier Burst',
    desc: 'High elevation steep terrain flash runoff',
    values: {
      rainfall_intensity: 80,
      soil_moisture: 85,
      slope: 45,
      earthquake_magnitude: 2.1,
      vegetation_cover: 10,
      duration: 12,
    }
  },
  {
    name: 'Normal Monsoon Day',
    desc: 'Steady rain with healthy vegetation cover',
    values: {
      rainfall_intensity: 45,
      soil_moisture: 40,
      slope: 22,
      earthquake_magnitude: 0.0,
      vegetation_cover: 65,
      duration: 6,
    }
  },
  {
    name: 'Extreme Multi-Hazard Event',
    desc: 'Severe cloudburst combined with tectonic trigger',
    values: {
      rainfall_intensity: 450,
      soil_moisture: 95,
      slope: 50,
      earthquake_magnitude: 4.5,
      vegetation_cover: 15,
      duration: 72,
    }
  }
];

export default function SimulationModal({ location, isOpen, onClose }) {
  if (!isOpen || !location) return null;

  // 6 Core Simulation Sliders
  const [rainfall, setRainfall] = useState(80);
  const [soilMoisture, setSoilMoisture] = useState(55);
  const [slope, setSlope] = useState(Number(location.slope) || 30);
  const [earthquake, setEarthquake] = useState(0.0);
  const [vegetation, setVegetation] = useState(
    location.vegetation_index != null ? Math.round(location.vegetation_index * 100) : 50
  );
  const [duration, setDuration] = useState(24);
  const [selectedPreset, setSelectedPreset] = useState('');

  const [loading, setLoading] = useState(false);
  const [simResult, setSimResult] = useState(null);
  const [savedScenarios, setSavedScenarios] = useState([]);
  const debounceTimerRef = useRef(null);

  // Apply preset handler
  const handleApplyPreset = (presetName) => {
    setSelectedPreset(presetName);
    const found = PRESETS.find((p) => p.name === presetName);
    if (found) {
      setRainfall(found.values.rainfall_intensity);
      setSoilMoisture(found.values.soil_moisture);
      setSlope(found.values.slope);
      setEarthquake(found.values.earthquake_magnitude);
      setVegetation(found.values.vegetation_cover);
      setDuration(found.values.duration);
    }
  };

  // Debounced API call to /api/simulate
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(async () => {
      setLoading(true);
      const payload = {
        rainfall_intensity: Number(rainfall),
        soil_moisture: Number(soilMoisture),
        slope: Number(slope),
        earthquake_magnitude: Number(earthquake),
        vegetation_cover: Number(vegetation),
        duration: Number(duration),
        location_id: location.id,
      };

      const res = await runSimulateWhatIf(payload);
      if (res) {
        setSimResult(res);
      }
      setLoading(false);
    }, 250);

    return () => clearTimeout(debounceTimerRef.current);
  }, [rainfall, soilMoisture, slope, earthquake, vegetation, duration, location.id]);

  const riskProb = simResult ? Math.round(simResult.probability * 100) : 50;
  const riskLevel = simResult ? simResult.risk_level : 'Moderate';

  // Risk Gauge Color
  const getGaugeColor = (prob) => {
    if (prob >= 80) return '#ef4444'; // Red
    if (prob >= 60) return '#f97316'; // Orange
    if (prob >= 40) return '#eab308'; // Yellow
    return '#10b981'; // Green
  };

  const gaugeColor = getGaugeColor(riskProb);

  // Save current scenario for side-by-side comparison
  const handleSaveScenario = () => {
    if (savedScenarios.length >= 3) {
      // Rotate out oldest
      setSavedScenarios((prev) => [
        ...prev.slice(1),
        {
          id: Date.now(),
          name: selectedPreset || `Scenario #${prev.length + 1}`,
          prob: riskProb,
          level: riskLevel,
          rainfall,
          slope,
          soilMoisture,
          earthquake,
          duration,
        }
      ]);
    } else {
      setSavedScenarios((prev) => [
        ...prev,
        {
          id: Date.now(),
          name: selectedPreset || `Scenario #${prev.length + 1}`,
          prob: riskProb,
          level: riskLevel,
          rainfall,
          slope,
          soilMoisture,
          earthquake,
          duration,
        }
      ]);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center z-[9999] p-3 sm:p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl max-w-4xl w-full border border-slate-200 shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-sm font-bold text-slate-900">
                  Enhanced What-If Multi-Hazard Simulator
                </h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
                  Real-Time ML + SHAP
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Testing parameter sensitivity for <span className="font-semibold text-slate-800">{location.name}</span>, {location.state}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 rounded-full transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-5 overflow-y-auto space-y-5">
          {/* Preset Disaster Conditions Dropdown */}
          <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/90 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 text-emerald-600" />
              <div>
                <span className="text-xs font-bold text-slate-800 block">Preset Disaster Scenarios:</span>
                <span className="text-[11px] text-slate-500">
                  Quickly benchmark against historical Indian geological events
                </span>
              </div>
            </div>
            <select
              value={selectedPreset}
              onChange={(e) => handleApplyPreset(e.target.value)}
              className="px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
            >
              <option value="">-- Choose Historical Preset --</option>
              {PRESETS.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Top Row: Circular Risk Gauge + Primary Status */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-5 items-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white rounded-2xl p-5 shadow-inner">
            {/* Circular Gauge */}
            <div className="md:col-span-4 flex flex-col items-center justify-center">
              <div className="relative w-36 h-36 flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    className="text-slate-700/60"
                    strokeWidth="9"
                    stroke="currentColor"
                    fill="transparent"
                  />
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    stroke={gaugeColor}
                    strokeWidth="9"
                    strokeDasharray={251.2}
                    strokeDashoffset={251.2 - (251.2 * riskProb) / 100}
                    strokeLinecap="round"
                    fill="transparent"
                    className="transition-all duration-500 ease-out"
                  />
                </svg>
                <div className="absolute flex flex-col items-center">
                  <span className="text-3xl font-black tracking-tight" style={{ color: gaugeColor }}>
                    {riskProb}%
                  </span>
                  <span className="text-[10px] uppercase font-bold text-slate-300">Hazard Index</span>
                </div>
              </div>
            </div>

            {/* Assessment Details & Controls */}
            <div className="md:col-span-8 space-y-2.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span
                  className="px-3 py-1 rounded-lg text-xs font-extrabold uppercase tracking-wide border"
                  style={{
                    backgroundColor: `${gaugeColor}20`,
                    color: gaugeColor,
                    borderColor: `${gaugeColor}40`,
                  }}
                >
                  {riskLevel} Hazard Level
                </span>
                {loading && (
                  <span className="text-xs text-amber-300 flex items-center gap-1">
                    <RefreshCw className="w-3 h-3 animate-spin" /> Computing XGBoost inference...
                  </span>
                )}
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">
                {riskProb >= 80
                  ? '⚠️ Critical destabilization threshold reached. Immediate slope failure and debris flow imminent under these meteorological conditions.'
                  : riskProb >= 60
                  ? '⚡ High risk of localized slope failure and road blockage. Geotechnical pore pressures exceeding shear threshold.'
                  : riskProb >= 40
                  ? '⚠️ Moderate vulnerability. Monitored rainfall infiltration approaching critical saturation limit.'
                  : '✅ Stable slope configuration. Soil retention capacity adequate under current simulated loads.'}
              </p>

              {/* Action Buttons */}
              <div className="pt-2 flex flex-wrap items-center gap-2">
                <button
                  onClick={handleSaveScenario}
                  className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm"
                >
                  <Copy className="w-3.5 h-3.5" />
                  <span>Save to Comparison ({savedScenarios.length}/3)</span>
                </button>
                <button
                  onClick={() => {
                    setRainfall(80);
                    setSoilMoisture(50);
                    setSlope(Number(location.slope) || 30);
                    setEarthquake(0.0);
                    setVegetation(50);
                    setDuration(24);
                    setSelectedPreset('');
                  }}
                  className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-xs font-medium transition-colors"
                >
                  Reset Sliders
                </button>
              </div>
            </div>
          </div>

          {/* Saved Scenarios Comparison Cards */}
          {savedScenarios.length > 0 && (
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/90 space-y-2">
              <span className="text-xs font-bold text-slate-800 block">
                Saved Scenario Comparisons:
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {savedScenarios.map((sc, idx) => (
                  <div key={sc.id} className="bg-white p-3 rounded-lg border border-slate-200 shadow-xs text-xs space-y-1">
                    <div className="flex justify-between items-center font-bold">
                      <span className="truncate text-slate-800">{sc.name}</span>
                      <span style={{ color: getGaugeColor(sc.prob) }}>{sc.prob}%</span>
                    </div>
                    <div className="text-[10px] text-slate-500 space-y-0.5">
                      <div>Rain: {sc.rainfall}mm ({sc.duration}h) • Slope: {sc.slope}°</div>
                      <div>Soil: {sc.soilMoisture}% • EQ: {sc.earthquake}M</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 6 Interactive Sliders Grid */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              1. Multi-Hazard Parameter Sliders
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              {/* Slider 1: Rainfall Intensity */}
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-slate-800">Rainfall Intensity</span>
                  <div className="flex items-center space-x-1">
                    <input
                      type="number"
                      min="0"
                      max="500"
                      value={rainfall}
                      onChange={(e) => setRainfall(Math.max(0, Math.min(500, Number(e.target.value))))}
                      className="w-16 px-1.5 py-0.5 text-right font-bold text-blue-600 bg-white border border-slate-200 rounded text-xs"
                    />
                    <span className="text-blue-600 font-bold">mm</span>
                  </div>
                </div>
                <input
                  type="range"
                  min="0"
                  max="500"
                  step="5"
                  value={rainfall}
                  onChange={(e) => setRainfall(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>0 mm (Dry)</span>
                  <span>150 mm (Heavy)</span>
                  <span>500 mm (Cloudburst)</span>
                </div>
              </div>

              {/* Slider 2: Soil Moisture */}
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-slate-800">Soil Moisture Saturation</span>
                  <span className="font-bold text-amber-600">{soilMoisture}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={soilMoisture}
                  onChange={(e) => setSoilMoisture(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-amber-600"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>0% (Arid)</span>
                  <span>50% (Damp)</span>
                  <span>100% (Fully Saturated)</span>
                </div>
              </div>

              {/* Slider 3: Slope Angle */}
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-slate-800">Slope Gradient Angle</span>
                  <span className="font-bold text-orange-600">{slope}°</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="90"
                  step="1"
                  value={slope}
                  onChange={(e) => setSlope(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-orange-600"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>0° (Flat)</span>
                  <span>35° (Mountain Slope)</span>
                  <span>90° (Vertical Cliff)</span>
                </div>
              </div>

              {/* Slider 4: Earthquake Magnitude */}
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-slate-800">Earthquake Magnitude (USGS/NCS)</span>
                  <span className="font-bold text-red-600">{earthquake} M</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="9.0"
                  step="0.1"
                  value={earthquake}
                  onChange={(e) => setEarthquake(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-red-600"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>0 M (None)</span>
                  <span>4.0 M (Moderate)</span>
                  <span>9.0 M (Catastrophic)</span>
                </div>
              </div>

              {/* Slider 5: Vegetation Cover */}
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-slate-800">Vegetation & Canopy Cover</span>
                  <span className="font-bold text-emerald-600">{vegetation}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={vegetation}
                  onChange={(e) => setVegetation(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>0% (Bare Soil/Deforested)</span>
                  <span>50% (Scrub/Agriculture)</span>
                  <span>100% (Dense Forest)</span>
                </div>
              </div>

              {/* Slider 6: Duration */}
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-slate-800">Rainfall Cumulative Duration</span>
                  <span className="font-bold text-indigo-600">{duration} hours</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="72"
                  step="1"
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>1 hr (Flash)</span>
                  <span>24 hrs (1 Day)</span>
                  <span>72 hrs (3 Days)</span>
                </div>
              </div>
            </div>
          </div>

          {/* SHAP Waterfall Mini-Chart */}
          {simResult?.contributions && (
            <div className="space-y-2 pt-2 border-t border-slate-200">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  2. SHAP Factor Contribution Breakdown
                </h3>
                <span className="text-[10px] text-slate-400">
                  Red: increases hazard | Green: protective
                </span>
              </div>

              <div className="space-y-2">
                {simResult.contributions.map((c, i) => {
                  const isPos = c.contribution > 0;
                  const absVal = Math.min(100, Math.round(Math.abs(c.contribution) * 150));
                  return (
                    <div key={i} className="bg-slate-50 p-2.5 rounded-xl border border-slate-200/80 text-xs">
                      <div className="flex justify-between items-center mb-1">
                        <div className="flex items-center space-x-1.5">
                          <span className="font-bold text-slate-800">{c.factor}</span>
                          <span className="text-[10px] text-slate-500 font-mono">({c.value})</span>
                        </div>
                        <span
                          className={`font-mono font-bold text-[11px] ${
                            isPos ? 'text-red-600' : 'text-emerald-600'
                          }`}
                        >
                          {c.contribution > 0 ? `+${c.contribution}` : c.contribution}
                        </span>
                      </div>
                      <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-300 ${
                            isPos ? 'bg-red-500' : 'bg-emerald-500'
                          }`}
                          style={{ width: `${Math.max(5, absVal)}%` }}
                        />
                      </div>
                      <span className="text-[9px] text-slate-400 mt-1 block">{c.description}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-100 bg-slate-50 flex items-center justify-between">
          <span className="text-[10px] text-slate-400">
            Advisory simulator. Official early warnings are issued by IMD and NDMA.
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
