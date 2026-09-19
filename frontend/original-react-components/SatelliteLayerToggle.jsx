import React from 'react';
import { Snowflake, Mountain, Trees, Droplet, Layers } from 'lucide-react';

export default function SatelliteLayerToggle({
  activeLayer,
  onToggleLayer,
  isroEnabled,
  onToggleIsro
}) {
  const layers = [
    { id: 'none', label: 'Standard Risk', icon: Layers, color: 'text-slate-600' },
    { id: 'snow', label: 'Snow Cover (NDSI)', icon: Snowflake, color: 'text-cyan-500' },
    { id: 'soil', label: 'Bare Soil (BSI)', icon: Mountain, color: 'text-amber-600' },
    { id: 'ndvi', label: 'Vegetation (NDVI)', icon: Trees, color: 'text-emerald-600' },
    { id: 'sar', label: 'Flood Inundation (SAR)', icon: Droplet, color: 'text-blue-500' },
  ];

  return (
    <div className="flex flex-wrap items-center gap-1.5 p-1.5 bg-slate-900/80 backdrop-blur-md rounded-xl border border-slate-700/80 text-xs shadow-lg">
      <div className="flex items-center space-x-1 px-1.5 text-[10px] font-semibold text-slate-300 uppercase tracking-wider">
        <span>Satellite Intelligence:</span>
      </div>

      {layers.map((layer) => {
        const Icon = layer.icon;
        const isActive = activeLayer === layer.id;

        return (
          <button
            key={layer.id}
            onClick={() => onToggleLayer(layer.id)}
            className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
              isActive
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white' : layer.color}`} />
            <span>{layer.label}</span>
          </button>
        );
      })}

      <div className="h-4 w-px bg-slate-700 mx-1 hidden sm:block" />

      {/* ISRO Bhuvan Toggle */}
      <button
        onClick={onToggleIsro}
        className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-all ${
          isroEnabled
            ? 'bg-orange-600 text-white border-orange-500 shadow-xs'
            : 'bg-slate-800/80 text-orange-300 border-orange-700/50 hover:bg-slate-750'
        }`}
        title="Toggle ISRO Bhuvan Thematic Geospatial Layer"
      >
        <span className="w-2 h-2 rounded-full bg-orange-400"></span>
        <span>ISRO Bhuvan Layer</span>
      </button>
    </div>
  );
}
