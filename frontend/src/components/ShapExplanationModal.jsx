import React, { useState, useEffect } from 'react';
import { X, FileText, CheckCircle, BarChart3, Download, Layers, ShieldAlert, Info } from 'lucide-react';
import { fetchModelInfo, exportReport } from '../services/api';
import DataSourceTag from './DataSourceTag';

export default function ShapExplanationModal({ location, detailData, isOpen, onClose }) {
  if (!isOpen || !location) return null;

  const [modelInfo, setModelInfo] = useState(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    fetchModelInfo().then((res) => {
      if (res) setModelInfo(res);
    });
  }, []);

  const handleDownloadReport = async () => {
    setDownloading(true);
    const report = await exportReport(location.id);
    if (report) {
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `LANDSAFE_Hazard_Report_${location.name.replace(/\s+/g, '_')}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }
    setDownloading(false);
  };

  const shapValues = detailData?.prediction?.shap_values || {};
  const sortedShap = Object.entries(shapValues).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).slice(0, 10);
  const rawProb = detailData?.prediction?.hazard_index ?? detailData?.prediction?.risk_probability;
  const prob = rawProb != null ? Math.round(rawProb * 100) : null;
  const rawFlood = detailData?.prediction?.flood_index ?? detailData?.prediction?.flood_risk_probability;
  const floodProb = rawFlood != null ? Math.round(rawFlood * 100) : null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center z-[9999] p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl max-w-3xl w-full border border-slate-200 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center">
              <BarChart3 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                AI Explainability & Hazard Intelligence Analysis
              </h2>
              <p className="text-xs text-slate-500">
                Detailed assessment for <span className="font-semibold text-slate-800">{location.name}</span> ({location.state})
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 rounded-full transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-5 overflow-y-auto space-y-5 text-xs">
          {/* Top Multi-Hazard Probability Banner */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-red-50/70 border border-red-200/80 rounded-xl p-3.5">
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-[10px] text-red-600 font-bold uppercase tracking-wider">Primary Hazard</span>
                  <h4 className="text-sm font-bold text-red-900 mt-0.5">Landslide Susceptibility Index</h4>
                </div>
                <span className="text-2xl font-extrabold text-red-600">{prob != null ? `${prob}%` : 'NO DATA'}</span>
              </div>
              <p className="text-[11px] text-red-700/80 mt-1">
                Model: XGBoost Classifier with non-linear saturation weighting.
              </p>
            </div>

            <div className="bg-blue-50/70 border border-blue-200/80 rounded-xl p-3.5">
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-[10px] text-blue-600 font-bold uppercase tracking-wider">Secondary Hazard</span>
                  <h4 className="text-sm font-bold text-blue-900 mt-0.5">Flood & Inundation Index</h4>
                </div>
                <span className="text-2xl font-extrabold text-blue-600">{floodProb != null ? `${floodProb}%` : 'NO DATA'}</span>
              </div>
              <p className="text-[11px] text-blue-700/80 mt-1">
                Model: Random Forest + Sentinel-1 SAR Backscatter Ingestion.
              </p>
            </div>
          </div>

          {/* SHAP Feature Contribution Waterfall */}
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-200/90 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-bold text-slate-900 text-xs">
                  Local SHAP Feature Contributions (TreeExplainer)
                </h4>
                <p className="text-[10px] text-slate-500">
                  Exact numerical impact on this location's risk probability score.
                </p>
              </div>
              <span className="text-[10px] bg-emerald-50 text-emerald-700 font-semibold px-2 py-0.5 rounded border border-emerald-200">
                Log-Odds Impact
              </span>
            </div>

            <div className="space-y-2 pt-1">
              {sortedShap.length > 0 ? (
                sortedShap.map(([feature, val]) => {
                  const isPositive = val >= 0;
                  const absVal = Math.min(100, Math.abs(val) * 45);

                  return (
                    <div key={feature} className="space-y-0.5">
                      <div className="flex justify-between text-[11px]">
                        <span className="font-medium text-slate-700 capitalize">
                          {feature.replace(/_/g, ' ')}
                        </span>
                        <span className={`font-mono font-bold ${isPositive ? 'text-red-600' : 'text-emerald-600'}`}>
                          {isPositive ? `+${val.toFixed(3)} (Increases Risk)` : `${val.toFixed(3)} (Decreases Risk)`}
                        </span>
                      </div>
                      <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden flex">
                        <div
                          className={`h-1.5 rounded-full ${isPositive ? 'bg-red-500 ml-auto' : 'bg-emerald-500'}`}
                          style={{ width: `${Math.max(5, absVal)}%` }}
                        />
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-slate-400 py-3 text-center">
                  Calculating SHAP tree attributions...
                </div>
              )}
            </div>
          </div>

          {/* Model Benchmark Comparison Table */}
          {modelInfo?.model_comparison && (
            <div className="space-y-2">
              <h4 className="font-bold text-slate-900 text-xs">
                Model Evaluation Benchmark (Cross-Validation Test Split)
              </h4>
              <div className="overflow-x-auto border border-slate-200 rounded-xl">
                <table className="w-full text-left text-xs divide-y divide-slate-200">
                  <thead className="bg-slate-50 text-slate-500 text-[10px] uppercase font-semibold">
                    <tr>
                      <th className="px-3 py-2">Algorithm</th>
                      <th className="px-3 py-2">Accuracy</th>
                      <th className="px-3 py-2">F1 Score</th>
                      <th className="px-3 py-2">ROC-AUC</th>
                      <th className="px-3 py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {Object.entries(modelInfo.model_comparison).map(([name, m]) => (
                      <tr key={name} className={name.includes('XGBoost') ? 'bg-emerald-50/40 font-semibold' : ''}>
                        <td className="px-3 py-2 text-slate-800">{name}</td>
                        <td className="px-3 py-2 text-slate-600">{(m.accuracy * 100).toFixed(1)}%</td>
                        <td className="px-3 py-2 text-slate-600">{m.f1_score.toFixed(3)}</td>
                        <td className="px-3 py-2 text-slate-600">{m.roc_auc.toFixed(3)}</td>
                        <td className="px-3 py-2">
                          {name.includes('XGBoost') ? (
                            <span className="text-[10px] text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded font-bold">
                              Deployed Best
                            </span>
                          ) : (
                            <span className="text-[10px] text-slate-400">Baseline</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Mandatory Prototype Disclaimer Notice */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-[11px] text-amber-800 space-y-1">
            <div className="flex items-center space-x-1.5 font-bold">
              <ShieldAlert className="w-4 h-4 text-amber-600" />
              <span>Academic Prototype Disclaimer (Section 0 Spec)</span>
            </div>
            <p className="font-normal leading-relaxed text-amber-900/90">
              "LANDSAFE-NER is a B.Tech AI & Data Science academic prototype. It is NOT an official government disaster-warning system. Risk levels are based on prototype thresholds for demonstration purposes only. Do not use for real-world emergency decisions."
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-100 bg-slate-50 flex items-center justify-between">
          <button
            onClick={handleDownloadReport}
            disabled={downloading}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors shadow-xs"
          >
            <Download className="w-3.5 h-3.5" />
            <span>{downloading ? 'Exporting...' : 'Export Hazard Assessment Report (JSON/PDF)'}</span>
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg text-xs font-semibold transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
