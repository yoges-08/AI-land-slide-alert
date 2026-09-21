import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid
} from 'recharts';

export default function RainfallChart({ rainfallTrend = [] }) {
  const hasData = rainfallTrend && rainfallTrend.length > 0 && rainfallTrend.some((d) => d.rainfall_mm != null);
  const data = (rainfallTrend || []).map((d) => ({
    date: d.date || '',
    rainfall_mm: d.rainfall_mm != null ? d.rainfall_mm : 0,
  }));
  const peak = hasData ? Math.max(...data.map((d) => d.rainfall_mm || 0)) : 0;

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-900 text-white text-xs px-2.5 py-1.5 rounded-lg shadow-lg border border-slate-700">
          <p className="text-[10px] text-slate-400">{label}</p>
          <p className="font-bold text-sky-400">{payload[0].value} mm</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white rounded-xl p-4 border border-slate-200/90 shadow-sm flex flex-col justify-between">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-bold text-slate-900 tracking-tight">
          Rainfall Trend <span className="text-slate-400 font-normal">(Last 7 Days)</span>
        </h3>
        {hasData ? (
          <span className="text-[10px] bg-sky-50 text-sky-700 border border-sky-200 font-semibold px-2 py-0.5 rounded-full">
            Peak: {peak} mm
          </span>
        ) : (
          <span className="text-[10px] bg-slate-100 text-slate-500 font-semibold px-2 py-0.5 rounded-full">
            Awaiting Feed
          </span>
        )}
      </div>

      <div className="h-44 w-full flex items-center justify-center">
        {hasData ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
            <defs>
              <linearGradient id="rainGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0284c7" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#0284c7" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: '#94a3b8' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 10, fill: '#94a3b8' }}
              axisLine={false}
              tickLine={false}
              domain={[0, 'auto']}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="rainfall_mm"
              stroke="#0284c7"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#rainGrad)"
              dot={{ r: 3, fill: '#0284c7', strokeWidth: 1.5, stroke: '#fff' }}
              activeDot={{ r: 5, fill: '#0369a1', strokeWidth: 2, stroke: '#fff' }}
            />
          </AreaChart>
        </ResponsiveContainer>
        ) : (
          <div className="flex flex-col items-center justify-center text-center p-4">
            <svg className="w-8 h-8 text-slate-300 mb-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 00-9.78 2.096A4.001 4.001 0 003 15z" />
            </svg>
            <p className="text-xs font-medium text-slate-500">No Historical Rainfall Recorded</p>
            <p className="text-[10px] text-slate-400 mt-0.5">Awaiting automated meteorological telemetry</p>
          </div>
        )}
      </div>

      <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
        <span>Continuous 24h accumulation</span>
        <span className="font-semibold text-slate-700">Open-Meteo Ingestion</span>
      </div>
    </div>
  );
}
