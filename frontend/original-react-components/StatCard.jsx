import React from 'react';
import { TrendingUp, TrendingDown, MapPin, AlertTriangle, AlertCircle, ShieldCheck } from 'lucide-react';

export default function StatCard({
  title,
  value,
  change,
  changeType = 'up',
  subtitle,
  type = 'total', // 'total' | 'high' | 'moderate' | 'low'
  onClick
}) {
  let iconBg = 'bg-emerald-50 text-emerald-600 border-emerald-200';
  let Icon = MapPin;
  let changeColor = 'text-emerald-600';

  if (type === 'high') {
    iconBg = 'bg-red-50 text-red-600 border-red-200';
    Icon = AlertTriangle;
    changeColor = 'text-red-500';
  } else if (type === 'moderate') {
    iconBg = 'bg-amber-50 text-amber-600 border-amber-200';
    Icon = AlertCircle;
    changeColor = 'text-amber-500';
  } else if (type === 'low') {
    iconBg = 'bg-emerald-50 text-emerald-600 border-emerald-200';
    Icon = ShieldCheck;
    changeColor = 'text-emerald-600';
  }

  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-xl p-4 border border-slate-200/90 shadow-sm flex items-start space-x-3.5 ${
        onClick ? 'cursor-pointer hover:border-slate-300 hover:shadow transition-all' : ''
      }`}
    >
      <div className={`p-2.5 rounded-xl border flex items-center justify-center flex-shrink-0 ${iconBg}`}>
        <Icon className="w-5 h-5 stroke-[2.2]" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[11px] font-medium text-slate-500 truncate leading-none mb-1">{title}</p>
        <div className="flex items-baseline space-x-2">
          <span className="text-2xl font-bold text-slate-900 tracking-tight leading-none">{value}</span>
          {change && (
            <span className={`text-[11px] font-semibold flex items-center space-x-0.5 ${changeColor}`}>
              {changeType === 'up' ? '↑' : '↓'} {change}
            </span>
          )}
        </div>
        {subtitle && (
          <p className="text-[10px] text-slate-400 mt-1 truncate leading-none">{subtitle}</p>
        )}
      </div>
    </div>
  );
}
