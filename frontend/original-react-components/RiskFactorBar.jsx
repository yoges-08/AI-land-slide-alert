import React from 'react';

export default function RiskFactorBar({ label, percentage, color = 'red' }) {
  let barColor = 'bg-red-500';
  if (color === 'orange') barColor = 'bg-amber-600';
  if (color === 'amber') barColor = 'bg-amber-500';
  if (color === 'yellow') barColor = 'bg-yellow-500';
  if (color === 'emerald') barColor = 'bg-emerald-500';

  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center text-xs">
        <span className="text-slate-600 font-medium text-[11px]">{label}</span>
        <span className="text-slate-900 font-bold text-[11px]">{percentage}%</span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-1.5 rounded-full transition-all duration-700 ${barColor}`}
          style={{ width: `${Math.min(100, Math.max(2, percentage))}%` }}
        />
      </div>
    </div>
  );
}
