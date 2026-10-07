import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  MapPin,
  Navigation,
  Share2,
  Copy,
  Check,
  PhoneCall,
  ExternalLink,
  AlertTriangle,
  Clock,
  ShieldCheck,
  X,
  Compass,
  ArrowRight
} from 'lucide-react';
import { fetchEvacuationPlan } from '../services/api';

export default function EvacuationPanel({
  location,
  onClose,
  onRouteSelected,
  onFocusMap
}) {
  const [loading, setLoading] = useState(true);
  const [planData, setPlanData] = useState(null);
  const [selectedRouteType, setSelectedRouteType] = useState('primary'); // 'primary' | 'alternative'
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!location) return;

    let isMounted = true;
    setLoading(true);

    const loadPlan = async () => {
      const data = await fetchEvacuationPlan(location.id || location.district || location.name);
      if (isMounted && data) {
        setPlanData(data);
        if (onRouteSelected) {
          onRouteSelected(
            data.primary_route,
            data.available_shelters || (data.target_shelter ? [data.target_shelter] : [])
          );
        }
      }
      if (isMounted) setLoading(false);
    };

    loadPlan();

    return () => {
      isMounted = false;
    };
  }, [location]);

  const handleToggleRoute = (type) => {
    setSelectedRouteType(type);
    if (planData && onRouteSelected) {
      const routeObj = type === 'primary' ? planData.primary_route : planData.alternative_route;
      onRouteSelected(
        routeObj,
        planData.available_shelters || (planData.target_shelter ? [planData.target_shelter] : [])
      );
    }
  };

  const handleCopyPlan = () => {
    if (!planData) return;
    const textToCopy = planData.whatsapp_share_text || 'Emergency evacuation plan';
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleWhatsAppShare = () => {
    if (!planData) return;
    const shareText = encodeURIComponent(planData.whatsapp_share_text || '');
    window.open(`https://wa.me/?text=${shareText}`, '_blank');
  };

  if (!location) return null;

  const targetShelter = planData?.target_shelter;
  const activeRoute = selectedRouteType === 'primary' ? planData?.primary_route : planData?.alternative_route;

  return (
    <div className="bg-white rounded-2xl border border-red-200 shadow-lg p-5 space-y-4 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center space-x-2.5">
          <div className="w-9 h-9 rounded-xl bg-red-50 text-red-600 border border-red-200 flex items-center justify-center flex-shrink-0">
            <ShieldAlert className="w-5 h-5 stroke-[2.2]" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
              AI Emergency Evacuation Route Planner
            </h2>
            <p className="text-[11px] text-slate-500">
              Corridor for <span className="font-semibold text-slate-800">{location.name}</span> ({location.district || location.state})
            </p>
          </div>
        </div>

        {onClose && (
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Evacuation Warning Banner */}
      <div className="bg-red-500 text-white rounded-xl p-3.5 flex items-center justify-between shadow-xs">
        <div className="flex items-center space-x-2.5">
          <AlertTriangle className="w-5 h-5 text-white animate-bounce flex-shrink-0" />
          <div>
            <span className="text-xs font-black uppercase tracking-wider block">
              🚨 Immediate Evacuation Recommended
            </span>
            <span className="text-[10px] text-red-100 font-medium">
              Geotechnical slope strain exceeding safety coefficient
            </span>
          </div>
        </div>
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-white text-red-700">
          Priority 1
        </span>
      </div>

      {/* Target Shelter Summary Card */}
      {targetShelter && (
        <div className="bg-slate-50 rounded-xl p-4 border border-slate-200/90 space-y-2.5 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" /> Nearest Designated Safe Zone
            </span>
            <span className="text-[10px] font-mono text-slate-500">
              Capacity: {targetShelter.capacity} people
            </span>
          </div>

          <div>
            <h3 className="text-sm font-bold text-slate-900">{targetShelter.name}</h3>
            <span className="text-[11px] text-slate-500">{targetShelter.type} • {targetShelter.district}</span>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-200/60 text-[11px]">
            <div className="bg-white p-2 rounded-lg border border-slate-200/80">
              <span className="text-slate-400 text-[10px] block">Transit Distance</span>
              <span className="font-bold text-slate-800 text-sm">
                {activeRoute?.distance_km ?? targetShelter.distance_km} km
              </span>
            </div>
            <div className="bg-white p-2 rounded-lg border border-slate-200/80">
              <span className="text-slate-400 text-[10px] block">Estimated Travel Time</span>
              <span className="font-bold text-blue-600 text-sm">
                ~{activeRoute?.estimated_minutes ?? targetShelter.estimated_minutes} mins
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Route Selector Buttons */}
      <div className="space-y-1.5">
        <label className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block">
          Evacuation Corridor Selection:
        </label>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => handleToggleRoute('primary')}
            className={`p-2.5 rounded-xl border text-xs font-semibold text-left transition-all ${
              selectedRouteType === 'primary'
                ? 'bg-blue-50 border-blue-400 text-blue-900 shadow-xs'
                : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            <div className="flex items-center space-x-1.5">
              <Navigation className="w-3.5 h-3.5 text-blue-600" />
              <span>Primary Corridor</span>
            </div>
            <p className="text-[10px] text-slate-500 mt-1">Valley bypass (Fastest)</p>
          </button>

          <button
            onClick={() => handleToggleRoute('alternative')}
            className={`p-2.5 rounded-xl border text-xs font-semibold text-left transition-all ${
              selectedRouteType === 'alternative'
                ? 'bg-blue-50 border-blue-400 text-blue-900 shadow-xs'
                : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            <div className="flex items-center space-x-1.5">
              <Compass className="w-3.5 h-3.5 text-indigo-600" />
              <span>Alternative Ridge Path</span>
            </div>
            <p className="text-[10px] text-slate-500 mt-1">High ground (Avoids flood)</p>
          </button>
        </div>
      </div>

      {/* Action Buttons: Copy Plan + WhatsApp Share */}
      <div className="pt-2 flex flex-col sm:flex-row items-center gap-2">
        <button
          onClick={handleCopyPlan}
          className="w-full sm:w-1/2 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold flex items-center justify-center space-x-1.5 transition-all shadow-sm"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'Plan Copied!' : 'Copy Evacuation Plan'}</span>
        </button>

        <button
          onClick={handleWhatsAppShare}
          className="w-full sm:w-1/2 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center justify-center space-x-1.5 transition-all shadow-sm"
        >
          <Share2 className="w-3.5 h-3.5" />
          <span>Share via WhatsApp</span>
        </button>
      </div>

      {/* Emergency Contact Bar */}
      <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-[11px] text-amber-900 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <PhoneCall className="w-4 h-4 text-amber-700 flex-shrink-0" />
          <span>
            Emergency Helpline: <strong>{targetShelter?.contact || '1078 (NDRF)'}</strong>
          </span>
        </div>
        <span className="text-[10px] text-amber-700 font-bold">24/7 Response</span>
      </div>
    </div>
  );
}
