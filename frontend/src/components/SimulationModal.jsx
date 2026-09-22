import React, { useState, useEffect } from 'react';
import { X, Sparkles, Sliders, RefreshCw, AlertTriangle, ArrowRight, CheckCircle2 } from 'lucide-react';
import { runSimulation } from '../services/api';

export default function SimulationModal({ location, isOpen, onClose }) {
  if (!isOpen || !location) return null;

  const [rainDelta, setRainDelta] = useState(50);
  const [slopeOverride, setSlopeOverride] = useState(location.slope || 34);
  const [snowmeltOverride, setSnowmeltOverride] = useState(location.snowmelt_rate || 2.0);
  const [bareSoilOverride, setBareSoilOverride] = useState(location.bare_soil_pct || 30);
  const [farmFlag, setFarmFlag] = useState(location.farm_change_flag || false);

  const [loading, setLoading] = useState(false);
  const [simResult, setSimResult] = useState(null);

  // Execute simulation when sliders change
  const executeSimulation = async () => {
    setLoading(true);
    const payload = {
      location_id: location.id,
      rainfall_24h_delta: rainDelta,
      slope_override: slopeOverride,
      snowmelt_rate_override: snowmeltOverride,
      bare_soil_pct_override: bareSoilOverride,
      farm_change_flag_override: farmFlag
    };

    const res = await runSimulation(payload);
    if (res) {
      setSimResult(res);
    }
    setLoading(false);
  };

  useEffect(() => {
    executeSimulation();
  }, [rainDelta, slopeOverride, snowmeltOverride, bareSoilOverride, farmFlag]);

  const rawOrig = simResult?.original_hazard_index ?? location.hazard_index ?? location.risk_probability;
  const origProb = rawOrig != null ? Math.round(rawOrig * 100) : null;
  const rawSim = simResult?.simulated_hazard_index;
  const simProb = rawSim != null ? Math.round(rawSim * 100) : origProb;
  const delta = (simProb != null && origProb != null) ? (simProb - origProb) : 0;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center z-[9999] p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl max-w-2xl w-full border border-slate-200 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                What-If Hazard Simulation Engine
              </h2>
              <p className="text-xs text-slate-500">
                Simulating scenario for <span className="font-semibold text-slate-800">{location.name}</span>, {location.state}
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

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto space-y-5">
          {/* Result Comparison Banner */}
          <div className="grid grid-cols-3 gap-3 bg-slate-900 text-white rounded-xl p-4">
            <div>
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Baseline Hazard Index</span>
              <p className="text-xl font-bold text-slate-200 mt-0.5">{origProb != null ? `${origProb}%` : '--'}</p>
              <span className="text-[10px] text-slate-400">{simResult?.original_risk_category || location.risk_category || 'Baseline'}</span>
            </div>
            <div className="text-center border-x border-slate-800 px-2">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Simulated Hazard Index</span>
              <p className="text-2xl font-extrabold text-amber-400 mt-0.5">{simProb != null ? `${simProb}%` : '--'}</p>
              <span className="text-[10px] font-semibold text-amber-300">
                {simResult?.simulated_risk_category || 'Simulated'}
              </span>
            </div>
            <div className="text-right">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Net Shift</span>
              <p className={`text-xl font-bold mt-0.5 ${delta >= 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                {origProb != null && simProb != null ? (delta >= 0 ? `+${delta}%` : `${delta}%`) : '--'}
              </p>
              <span className="text-[10px] text-slate-400">
                {delta > 15 ? 'Significant destabilization' : 'Moderate change'}
              </span>
            </div>
          </div>

          {/* Interactive Sliders */}
          <div className="space-y-4 pt-1">
            {/* 1. Rainfall Delta Slider */}
            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 space-y-1.5">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-slate-800">Simulated 24h Rainfall Addition</span>
                <span className="font-bold text-blue-600">+{rainDelta} mm</span>
              </div>
              <input
                type="range"
                min="0"
                max="250"
                step="5"
                value={rainDelta}
                onChange={(e) => setRainDelta(Number(e.target.value))}
                className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>0 mm (Normal)</span>
                <span>+100 mm (Cloudburst)</span>
                <span>+250 mm (Extreme Monsoon)</span>
              </div>
            </div>

            {/* 2. Slope Override Slider */}
            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 space-y-1.5">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-slate-800">Slope Gradient Angle</span>
                <span className="font-bold text-amber-600">{slopeOverride}°</span>
              </div>
              <input
                type="range"
                min="5"
                max="55"
                step="1"
                value={slopeOverride}
                onChange={(e) => setSlopeOverride(Number(e.target.value))}
                className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-amber-600"
              />
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>5° (Gentle)</span>
                <span>30° (Standard Hill)</span>
                <span>55° (Steep Cliff)</span>
              </div>
            </div>

            {/* 3. Snowmelt Rate Slider */}
            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 space-y-1.5">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-slate-800">Satellite Snowmelt Runoff Rate</span>
                <span className="font-bold text-cyan-600">{snowmeltOverride} mm/day</span>
              </div>
              <input
                type="range"
                min="0"
                max="10"
                step="0.5"
                value={snowmeltOverride}
                onChange={(e) => setSnowmeltOverride(Number(e.target.value))}
                className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-cyan-600"
              />
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>0 mm/day</span>
                <span>5 mm/day (Spring Melt)</span>
                <span>10 mm/day (Flash Melt)</span>
              </div>
            </div>

            {/* 4. Bare Soil Exposure Slider */}
            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 space-y-1.5">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-slate-800">Sentinel-2 Bare Soil Exposure (BSI)</span>
                <span className="font-bold text-orange-600">{bareSoilOverride}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="80"
                step="1"
                value={bareSoilOverride}
                onChange={(e) => setBareSoilOverride(Number(e.target.value))}
                className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-orange-600"
              />
            </div>

            {/* 5. Farm Change Toggle */}
            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-200/80 text-xs">
              <div>
                <span className="font-semibold text-slate-800 block">Slope Agriculture (Jhum Clearing)</span>
                <span className="text-[10px] text-slate-400">Flags recent vegetation loss on steep hillside</span>
              </div>
              <input
                type="checkbox"
                checked={farmFlag}
                onChange={(e) => setFarmFlag(e.target.checked)}
                className="w-4 h-4 rounded text-emerald-600 focus:ring-emerald-500 accent-emerald-600"
              />
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-100 bg-slate-50 flex items-center justify-between">
          <span className="text-[10px] text-slate-400">
            Real-time XGBoost ML Inference Response
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold transition-colors"
          >
            Apply & Close
          </button>
        </div>
      </div>
    </div>
  );
}
