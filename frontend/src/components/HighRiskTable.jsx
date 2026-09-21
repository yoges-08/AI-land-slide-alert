import React from 'react';
import { ArrowRight, ChevronRight } from 'lucide-react';

export default function HighRiskTable({ locations = [], onSelectLocation, onViewAll }) {
  // Sort high risk locations first
  const highRiskSorted = [...locations]
    .sort((a, b) => (b.risk_probability || 0) - (a.risk_probability || 0))
    .slice(0, 5);

  return (
    <div className="bg-white rounded-xl p-4 border border-slate-200/90 shadow-sm flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-2.5">
          <h3 className="text-xs font-bold text-slate-900 tracking-tight">Recent High-Risk Locations</h3>
          <button
            onClick={onViewAll}
            className="text-[11px] font-semibold text-emerald-600 hover:text-emerald-700 inline-flex items-center space-x-1"
          >
            <span>View All</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-100 text-[10px] text-slate-400 font-semibold uppercase tracking-wider">
                <th className="pb-2">Location</th>
                <th className="pb-2">State</th>
                <th className="pb-2">Risk</th>
                <th className="pb-2 text-right">Probability</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {highRiskSorted.map((loc) => {
                const rawProb = loc.hazard_index ?? loc.risk_probability;
                const prob = rawProb != null ? Math.round(rawProb * 100) : null;
                const isHigh = loc.risk_category === 'High' || (prob != null && prob >= 70);

                return (
                  <tr
                    key={loc.id}
                    onClick={() => onSelectLocation && onSelectLocation(loc)}
                    className="hover:bg-slate-50 cursor-pointer transition-colors group"
                  >
                    <td className="py-2 font-medium text-slate-800 flex items-center gap-1.5">
                      <span className="truncate max-w-[100px]">{loc.name}</span>
                    </td>
                    <td className="py-2 text-slate-500 text-[11px] truncate max-w-[90px]">{loc.state}</td>
                    <td className="py-2">
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold">
                        <span
                          className={`w-2 h-2 rounded-full ${
                            isHigh ? 'bg-red-500' : 'bg-amber-500'
                          }`}
                        />
                        <span className={isHigh ? 'text-red-600' : 'text-amber-600'}>
                          {loc.risk_category || (isHigh ? 'High' : 'Moderate')}
                        </span>
                      </span>
                    </td>
                    <td className="py-2 text-right font-bold text-slate-900 text-[11px]">
                      {prob != null ? `${prob}%` : '--'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
