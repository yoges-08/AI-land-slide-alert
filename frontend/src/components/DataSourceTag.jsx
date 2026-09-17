import React from 'react';

export default function DataSourceTag({ source = 'Open-Meteo', isSample = false }) {
  let badgeStyle = 'bg-slate-100 text-slate-600 border-slate-200';
  let label = source;

  if (isSample || source.toLowerCase().includes('sample')) {
    badgeStyle = 'bg-amber-50 text-amber-700 border-amber-300 font-semibold';
    label = 'SAMPLE DATA';
  } else if (source.includes('NASA')) {
    badgeStyle = 'bg-blue-50 text-blue-700 border-blue-200';
    label = 'NASA GIBS/MODIS';
  } else if (source.includes('ISRO')) {
    badgeStyle = 'bg-orange-50 text-orange-700 border-orange-200';
    label = 'ISRO Bhuvan';
  } else if (source.includes('Copernicus') || source.includes('Sentinel')) {
    badgeStyle = 'bg-indigo-50 text-indigo-700 border-indigo-200';
    label = 'Sentinel-1/2';
  } else if (source.includes('Open-Meteo')) {
    badgeStyle = 'bg-emerald-50 text-emerald-700 border-emerald-200';
    label = 'Open-Meteo Live';
  }

  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border tracking-wide uppercase ${badgeStyle}`}
      title={`Data source: ${source}`}
    >
      {label}
    </span>
  );
}
