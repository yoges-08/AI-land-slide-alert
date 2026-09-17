import React from 'react';
import { AlertTriangle, AlertCircle, ShieldCheck, ArrowRight, ChevronRight, Droplet } from 'lucide-react';

export default function AlertList({ alerts = [], onSelectAlert, onViewAll }) {
  return (
    <div className="bg-white rounded-xl p-4 border border-slate-200/90 shadow-sm flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-bold text-slate-900 tracking-tight">Recent Alerts</h3>
          <button
            onClick={onViewAll}
            className="text-[11px] font-semibold text-emerald-600 hover:text-emerald-700 inline-flex items-center space-x-1"
          >
            <span>View All</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        <div className="space-y-2.5">
          {alerts.slice(0, 4).map((alert) => {
            let iconBg = 'bg-red-50 text-red-600 border-red-200';
            let Icon = AlertTriangle;
            let titleColor = 'text-red-600';

            if (alert.severity === 'Moderate') {
              iconBg = 'bg-amber-50 text-amber-600 border-amber-200';
              Icon = AlertCircle;
              titleColor = 'text-amber-600';
            } else if (alert.severity === 'Low' || !alert.is_active) {
              iconBg = 'bg-emerald-50 text-emerald-600 border-emerald-200';
              Icon = ShieldCheck;
              titleColor = 'text-emerald-600';
            }

            if (alert.hazard_type === 'Flood') {
              Icon = Droplet;
            }

            return (
              <div
                key={alert.id}
                onClick={() => onSelectAlert && onSelectAlert(alert)}
                className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-50 border border-transparent hover:border-slate-100 transition-colors cursor-pointer group"
              >
                <div className="flex items-center space-x-2.5 min-w-0">
                  <div className={`p-1.5 rounded-lg border flex-shrink-0 ${iconBg}`}>
                    <Icon className="w-3.5 h-3.5 stroke-[2.2]" />
                  </div>
                  <div className="min-w-0">
                    <p className={`text-xs font-semibold ${titleColor} truncate leading-tight`}>
                      {alert.title}
                    </p>
                    <p className="text-[10px] text-slate-500 truncate leading-tight mt-0.5">
                      {alert.location_name}, {alert.state}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-1 flex-shrink-0 ml-2">
                  <span className="text-[10px] text-slate-400 font-normal">{alert.created_at}</span>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-slate-500 transition-colors" />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
