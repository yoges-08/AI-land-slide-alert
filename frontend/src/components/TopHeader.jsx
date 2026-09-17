import React, { useState, useRef, useEffect } from 'react';
import { Search, Bell, ChevronDown, UserCheck, AlertTriangle } from 'lucide-react';

export default function TopHeader({
  locations = [],
  selectedLocation,
  onSelectLocation,
  unreadAlertCount = 3,
  onOpenAlerts
}) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const searchRef = useRef(null);

  // Filter locations based on search query
  const filtered = query.trim() === ''
    ? []
    : locations.filter(
        (loc) =>
          loc.name.toLowerCase().includes(query.toLowerCase()) ||
          loc.state.toLowerCase().includes(query.toLowerCase())
      ).slice(0, 8);

  // Close search dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e) {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="h-16 bg-white border-b border-slate-200/90 px-6 flex items-center justify-between sticky top-0 z-30 shadow-sm">
      {/* Search Input */}
      <div className="relative w-96" ref={searchRef}>
        <div className="relative flex items-center">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            placeholder="Search location (e.g., Gangtok, Assam, etc.)"
            className="w-full pl-9 pr-4 py-2 bg-slate-50 hover:bg-slate-100/80 focus:bg-white text-xs text-slate-800 placeholder-slate-400 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 transition-all"
          />
        </div>

        {/* Dynamic Autocomplete Dropdown */}
        {isOpen && filtered.length > 0 && (
          <div className="absolute left-0 right-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-xl overflow-hidden z-50 max-h-72 overflow-y-auto">
            {filtered.map((loc) => (
              <button
                key={loc.id}
                onClick={() => {
                  onSelectLocation(loc);
                  setQuery('');
                  setIsOpen(false);
                }}
                className="w-full text-left px-3.5 py-2.5 hover:bg-slate-50 flex items-center justify-between border-b border-slate-100 last:border-b-0 text-xs transition-colors"
              >
                <div>
                  <span className="font-semibold text-slate-800">{loc.name}</span>
                  <span className="text-slate-500 ml-1.5 font-normal">({loc.state})</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                      loc.risk_category === 'High'
                        ? 'bg-red-50 text-red-600 border border-red-200'
                        : loc.risk_category === 'Moderate'
                        ? 'bg-amber-50 text-amber-600 border border-amber-200'
                        : 'bg-emerald-50 text-emerald-600 border border-emerald-200'
                    }`}
                  >
                    {loc.risk_category}
                  </span>
                  <span className="text-[11px] text-slate-400">{loc.elevation}m</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Right Header Actions */}
      <div className="flex items-center space-x-4">
        {/* Academic Prototype Pill */}
        <div className="hidden lg:flex items-center space-x-1.5 px-2.5 py-1 bg-amber-50 border border-amber-200 text-amber-800 rounded-full text-[11px] font-medium" title="Academic prototype for demonstration only.">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
          <span>Academic Prototype</span>
        </div>

        {/* Notification Bell */}
        <button
          onClick={onOpenAlerts}
          className="relative p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-full transition-colors"
          title="View Alerts"
        >
          <Bell className="w-5 h-5" />
          {unreadAlertCount > 0 && (
            <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-red-500 rounded-full ring-2 ring-white"></span>
          )}
        </button>

        {/* User Profile */}
        <div className="flex items-center space-x-2.5 pl-3 border-l border-slate-200">
          <div className="w-8 h-8 rounded-full bg-slate-800 text-white flex items-center justify-center font-bold text-xs shadow-sm">
            <UserCheck className="w-4 h-4 text-emerald-300" />
          </div>
          <div className="hidden sm:block text-left">
            <span className="text-xs font-semibold text-slate-800 block leading-tight">Admin</span>
            <span className="text-[10px] text-slate-400 block leading-tight">Analyst Role</span>
          </div>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
        </div>
      </div>
    </header>
  );
}
