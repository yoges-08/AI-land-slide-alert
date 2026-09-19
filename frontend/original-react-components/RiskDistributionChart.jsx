import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

export default function RiskDistributionChart({ highCount = 18, moderateCount = 47, lowCount = 185 }) {
  const total = highCount + moderateCount + lowCount || 250;
  const highPct = Math.round((highCount / total) * 100);
  const modPct = Math.round((moderateCount / total) * 100);
  const lowPct = 100 - highPct - modPct;

  const data = [
    { name: 'High Risk', value: highCount, color: '#ef4444' },
    { name: 'Moderate Risk', value: moderateCount, color: '#f59e0b' },
    { name: 'Low Risk', value: lowCount, color: '#10b981' }
  ];

  return (
    <div className="bg-white rounded-xl p-4 border border-slate-200/90 shadow-sm flex flex-col justify-between">
      <h3 className="text-xs font-bold text-slate-900 tracking-tight mb-2">Risk Distribution</h3>
      
      <div className="relative h-44 flex items-center justify-center">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              innerRadius={50}
              outerRadius={68}
              paddingAngle={3}
              dataKey="value"
              strokeWidth={0}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-xl font-extrabold text-slate-900 leading-none">{total}</span>
          <span className="text-[10px] text-slate-400 font-medium leading-tight mt-0.5">Total Locations</span>
        </div>
      </div>

      {/* Legend */}
      <div className="space-y-1.5 pt-2 border-t border-slate-100 text-xs">
        <div className="flex items-center justify-between text-[11px]">
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
            <span className="text-slate-600 font-medium">High Risk</span>
          </div>
          <span className="font-bold text-slate-800">{highCount} <span className="text-slate-400 font-normal">({highPct}%)</span></span>
        </div>

        <div className="flex items-center justify-between text-[11px]">
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span className="text-slate-600 font-medium">Moderate Risk</span>
          </div>
          <span className="font-bold text-slate-800">{moderateCount} <span className="text-slate-400 font-normal">({modPct}%)</span></span>
        </div>

        <div className="flex items-center justify-between text-[11px]">
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <span className="text-slate-600 font-medium">Low Risk</span>
          </div>
          <span className="font-bold text-slate-800">{lowCount} <span className="text-slate-400 font-normal">({lowPct}%)</span></span>
        </div>
      </div>
    </div>
  );
}
