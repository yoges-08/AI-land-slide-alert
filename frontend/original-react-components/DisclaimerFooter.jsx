import React from 'react';
import { AlertCircle } from 'lucide-react';

export default function DisclaimerFooter() {
  return (
    <footer className="mt-8 border-t border-slate-200/90 py-4 px-6 bg-white/70 backdrop-blur-xs text-center text-xs text-slate-500 rounded-t-xl">
      <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-center gap-2">
        <AlertCircle className="w-4 h-4 text-amber-500 flex-shrink-0" />
        <p className="text-[11px] leading-relaxed text-slate-600">
          <span className="font-semibold text-slate-800">Academic Disclaimer:</span> LANDSAFE-NER is a B.Tech AI & Data Science academic prototype. It is NOT an official government disaster-warning system. Risk levels are based on prototype thresholds for demonstration purposes only. Do not use for real-world emergency decisions.
        </p>
      </div>
      <div className="mt-2 text-[10px] text-slate-400">
        Live Weather: <span className="font-medium text-slate-600">Open-Meteo API</span> • Satellite Layers: <span className="font-medium text-slate-600">NASA GIBS / MODIS & Copernicus Sentinel-1/2</span> • Geomorphology: <span className="font-medium text-slate-600">ISRO Bhuvan / SRTM</span>
      </div>
    </footer>
  );
}
