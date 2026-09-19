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

  const defaultForecast = [
    { day: 'Today', condition: 'Rain', temp_max: 24, temp_min: 18 },
    { day: 'Tomorrow', condition: 'Light Rain', temp_max: 26, temp_min: 19 },
    { day: 'Wed', condition: 'Cloudy', temp_max: 27, temp_min: 20 },
    { day: 'Thu', condition: 'Mostly Cloudy', temp_max: 28, temp_min: 21 },
    { day: 'Fri', condition: 'Partly Cloudy', temp_max: 29, temp_min: 22 },
  ];

  const displayList = forecast && forecast.length >= 5 ? forecast.slice(0, 5) : defaultForecast;

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
                {item.temp_max}°<span className="text-slate-400 font-normal"> / {item.temp_min}°</span>
              </p>
              <p className="text-[9px] text-slate-500 truncate mt-0.5">{item.condition}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
