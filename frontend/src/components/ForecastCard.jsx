import React from 'react';
import { CloudRain, Cloud, Sun, CloudSun, CloudLightning, ArrowRight } from 'lucide-react';

export default function ForecastCard({ forecast = [], onViewMore }) {
  const renderForecastIcon = (iconName, cond) => {
    const text = (cond || '').toLowerCase();
    if (text.includes('thunder')) return <CloudLightning className="w-5 h-5 text-amber-500 mx-auto" />;
    if (text.includes('rain')) return <CloudRain className="w-5 h-5 text-blue-500 mx-auto" />;
    if (text.includes('cloud') || text.includes('overcast')) return <Cloud className="w-5 h-5 text-slate-400 mx-auto" />;
    if (text.includes('partly')) return <CloudSun className="w-5 h-5 text-amber-400 mx-auto" />;
    return <Sun className="w-5 h-5 text-amber-500 mx-auto" />;
  };

  const hasForecast = Array.isArray(forecast) && forecast.length > 0;
  const displayList = hasForecast ? forecast.slice(0, 5) : [];

  return (
    <div className="bg-white rounded-xl p-4 border border-slate-200/90 shadow-sm flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-bold text-slate-900 tracking-tight">
            Weather Forecast <span className="text-slate-400 font-normal">(Next 5 Days)</span>
          </h3>
          <button
            onClick={onViewMore}
            className="text-[11px] font-semibold text-emerald-600 hover:text-emerald-700 inline-flex items-center space-x-1"
          >
            <span>View More</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        {hasForecast ? (
          <div className="grid grid-cols-5 gap-1.5 text-center">
            {displayList.map((item, idx) => (
              <div
                key={idx}
                className="bg-slate-50/70 hover:bg-slate-100/80 rounded-lg p-2 transition-colors border border-slate-100/80"
              >
                <p className="text-[10px] font-medium text-slate-500 mb-1.5">{item.day}</p>
                <div className="my-1.5 flex justify-center">
                  {renderForecastIcon(item.icon, item.condition)}
                </div>
                <p className="text-[11px] font-bold text-slate-800 leading-tight mt-1">
                  {item.temp_max != null ? `${item.temp_max}°` : '--'}
                  <span className="text-slate-400 font-normal"> / {item.temp_min != null ? `${item.temp_min}°` : '--'}</span>
                </p>
                <p className="text-[9px] text-slate-500 truncate mt-0.5">{item.condition || 'Observation'}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="py-6 flex flex-col items-center justify-center text-center bg-slate-50/50 rounded-lg border border-dashed border-slate-200">
            <Cloud className="w-6 h-6 text-slate-300 mb-1" />
            <p className="text-xs font-medium text-slate-600">No Forecast Observation Available</p>
            <p className="text-[10px] text-slate-400 mt-0.5">Automated meteorological telemetry offline</p>
          </div>
        )}
      </div>
    </div>
  );
}
