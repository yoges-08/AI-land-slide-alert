import React from 'react';
import {
  LayoutDashboard,
  Map as MapIcon,
  LineChart,
  CloudSun,
  Bell,
  History,
  FileText,
  Settings,
  Mountain,
  Sparkles
} from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, unreadAlertCount = 3, onOpenAssistant }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'live-map', label: 'Live Map', icon: MapIcon },
    { id: 'risk-analysis', label: 'Risk Analysis', icon: LineChart },
    { id: 'weather', label: 'Weather & Forecast', icon: CloudSun },
    { id: 'ai-assistant', label: 'AI Assistant', icon: Sparkles, badgeText: 'Beta', isAction: true },
    { id: 'alerts', label: 'Alerts', icon: Bell, badge: unreadAlertCount },
    { id: 'history', label: 'Historical Data', icon: History },
    { id: 'reports', label: 'Reports', icon: FileText },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-[#0d1b1e] text-slate-300 flex flex-col flex-shrink-0 h-screen sticky top-0 border-r border-slate-800 select-none">
      {/* Brand Header */}
      <div className="p-5 flex items-center space-x-3 border-b border-slate-800/80">
        <div className="w-10 h-10 rounded-xl bg-emerald-700/30 border border-emerald-500/40 flex items-center justify-center text-emerald-400 shadow-sm">
          <Mountain className="w-6 h-6 stroke-[2.2]" />
        </div>
        <div>
          <h1 className="text-base font-bold text-white tracking-wide flex items-center gap-1.5">
            LANDSAFE-NER
          </h1>
          <p className="text-[11px] text-slate-400 font-normal leading-tight">
            Landslide Risk Monitoring System
          </p>
          <span className="text-[10px] text-emerald-400/90 font-medium">Northeast India</span>
        </div>
      </div>

      {/* Nav List */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;

          return (
            <button
              key={item.id}
              onClick={() => {
                if (item.id === 'ai-assistant' && onOpenAssistant) {
                  onOpenAssistant();
                } else {
                  setActiveTab(item.id);
                }
              }}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all duration-150 ${
                isActive
                  ? 'bg-emerald-700/80 text-white shadow-sm shadow-emerald-900/30'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
              }`}
            >
              <div className="flex items-center space-x-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-200' : item.id === 'ai-assistant' ? 'text-emerald-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </div>
              {item.badge ? (
                <span className="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center">
                  {item.badge}
                </span>
              ) : item.badgeText ? (
                <span className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider">
                  {item.badgeText}
                </span>
              ) : null}
            </button>
          );
        })}
      </nav>

      {/* Bottom Scenic Card */}
      <div className="p-3.5">
        <div className="relative rounded-xl overflow-hidden border border-slate-700/60 group shadow-md">
          <img
            src="https://images.unsplash.com/photo-1544735716-392fe2489ffa?w=400&auto=format&fit=crop&q=60"
            alt="Northeast Himalayas"
            className="w-full h-24 object-cover brightness-[0.55] transition-transform duration-500 group-hover:scale-105"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent p-2.5 flex flex-col justify-end">
            <p className="text-[11px] font-semibold text-white leading-tight">
              Safer Tomorrow,
            </p>
            <p className="text-[10px] text-emerald-300 font-medium">
              Stronger Northeast
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
