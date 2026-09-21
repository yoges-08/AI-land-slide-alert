import React from 'react';
import {
  CloudRain,
  Cloud,
  Sun,
  CloudSun,
  CloudLightning,
  Snowflake,
  Wind,
  Droplets,
  MapPin,
  ArrowRight
} from 'lucide-react';
import DataSourceTag from './DataSourceTag';

export default function WeatherCard({ weather, locationName = 'Gangtok, Sikkim', onViewForecast }) {
  if (!weather) {
    return (
      <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm flex items-center justify-center text-xs text-slate-400">
        Loading live weather...
      </div>
    );
  }

  const temp = weather.temperature;
  const condition = weather.condition_text || (weather.status === 'OFFLINE' ? 'Observation Offline' : 'No Observation');
  const humidity = weather.humidity;
  const wind = weather.wind_speed;
  const rain1h = weather.rainfall_1h;

  const renderWeatherIcon = () => {
    const text = (condition || '').toLowerCase();
    if (text.includes('thunder')) return <CloudLightning className="w-8 h-8 text-amber-500 animate-pulse" />;
    if (text.includes('snow')) return <Snowflake className="w-8 h-8 text-sky-400" />;
    if (text.includes('rain') || text.includes('drizzle')) return <CloudRain className="w-8 h-8 text-blue-500" />;
    if (text.includes('cloud')) return <CloudSun className="w-8 h-8 text-slate-400" />;
    if (text.includes('clear') || text.includes('sun')) return <Sun className="w-8 h-8 text-amber-400" />;
    return <Cloud className="w-8 h-8 text-slate-300" />;
  };

  return (
    <div className="bg-white rounded-xl p-4 border border-slate-200/90 shadow-sm flex flex-col justify-between">
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-3">
          {renderWeatherIcon()}
          <div>
            <div className="flex items-baseline space-x-1.5">
              <span className="text-2xl font-bold text-slate-900 leading-none">
                {temp != null ? `${temp}°C` : '--'}
              </span>
            </div>
            <span className="text-xs font-medium text-slate-600 block mt-0.5">{condition}</span>
          </div>
        </div>

        <div className="text-right">
          <div className="flex items-center justify-end text-[11px] font-semibold text-slate-700">
            <MapPin className="w-3 h-3 text-emerald-600 mr-1 inline" />
            <span>{locationName}</span>
          </div>
          <div className="mt-1">
            <DataSourceTag source={weather.source || 'Open-Meteo'} isSample={weather.is_sample_data} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 mt-3 pt-2.5 border-t border-slate-100 text-[11px]">
        <div>
          <span className="text-slate-400 block text-[10px]">Humidity</span>
          <span className="font-semibold text-slate-800 flex items-center gap-1">
            <Droplets className="w-3 h-3 text-blue-400 inline" /> {humidity != null ? `${humidity}%` : '--'}
          </span>
        </div>
        <div>
          <span className="text-slate-400 block text-[10px]">Wind</span>
          <span className="font-semibold text-slate-800 flex items-center gap-1">
            <Wind className="w-3 h-3 text-slate-400 inline" /> {wind != null ? `${wind} km/h` : '--'}
          </span>
        </div>
        <div>
          <span className="text-slate-400 block text-[10px]">Rainfall (1h)</span>
          <span className="font-semibold text-slate-800 text-blue-600">{rain1h != null ? `${rain1h} mm` : '--'}</span>
        </div>
      </div>

      <div className="mt-2 text-right">
        <button
          onClick={onViewForecast}
          className="text-[11px] font-semibold text-emerald-600 hover:text-emerald-700 inline-flex items-center space-x-1 transition-colors"
        >
          <span>View Forecast</span>
          <ArrowRight className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}
