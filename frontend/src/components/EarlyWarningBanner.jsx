import React from 'react';
import { ShieldAlert, ArrowRight, Bell } from 'lucide-react';

export default function EarlyWarningBanner({ onManageAlerts }) {
  return (
    <div className="relative rounded-2xl overflow-hidden border border-emerald-500/30 bg-gradient-to-r from-emerald-950 via-teal-900 to-slate-900 text-white p-4 sm:p-5 shadow-sm">
      <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-400/40 flex items-center justify-center text-emerald-300 shadow-sm flex-shrink-0">
            <ShieldAlert className="w-5 h-5 stroke-[2.2]" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">
              Early Warning System
            </h3>
            <p className="text-xs text-slate-300 font-normal mt-0.5">
              Stay informed. Stay safe. Get real-time automated threshold alerts for high-risk landslide & flood zones.
            </p>
          </div>
        </div>

        <button
          onClick={onManageAlerts}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all shadow-sm hover:shadow-md flex-shrink-0"
        >
          <span>Manage Alerts</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Background mountain contour line */}
      <div className="absolute right-0 bottom-0 top-0 w-1/3 opacity-15 pointer-events-none bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-emerald-300 via-transparent to-transparent" />
    </div>
  );
}
