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
  const defaultTrend = [
    { date: 'Apr 21', rainfall_mm: 15 },
    { date: 'Apr 22', rainfall_mm: 45 },
    { date: 'Apr 23', rainfall_mm: 92 },
    { date: 'Apr 24', rainfall_mm: 56 },
    { date: 'Apr 25', rainfall_mm: 78 },
    { date: 'Apr 26', rainfall_mm: 110 },
    { date: 'Apr 27', rainfall_mm: 142 },
  ];

  const data = rainfallTrend && rainfallTrend.length > 0 ? rainfallTrend : defaultTrend;
  const peak = Math.max(...data.map((d) => d.rainfall_mm || 0));

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
        <span className="text-[10px] bg-sky-50 text-sky-700 border border-sky-200 font-semibold px-2 py-0.5 rounded-full">
          Peak: {peak} mm
        </span>
      </div>

      <div className="h-44 w-full">
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
      </div>

      <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
        <span>Continuous 24h accumulation</span>
        <span className="font-semibold text-slate-700">Open-Meteo Ingestion</span>
      </div>
    </div>
  );
}
