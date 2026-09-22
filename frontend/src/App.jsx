import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import TopHeader from './components/TopHeader';
import StatCard from './components/StatCard';
import WeatherCard from './components/WeatherCard';
import ForecastCard from './components/ForecastCard';
import LocationDetails from './components/LocationDetails';
import AlertList from './components/AlertList';
import RiskMap from './components/RiskMap';
import RiskDistributionChart from './components/RiskDistributionChart';
import RainfallChart from './components/RainfallChart';
import HighRiskTable from './components/HighRiskTable';
import EarlyWarningBanner from './components/EarlyWarningBanner';
import SimulationModal from './components/SimulationModal';
import ShapExplanationModal from './components/ShapExplanationModal';
import DisclaimerFooter from './components/DisclaimerFooter';
import DataSourceTag from './components/DataSourceTag';

import {
  fetchLocations,
  fetchHierarchy,
  fetchLocationDetail,
  fetchAlerts,
  fetchWeather
} from './services/api';

import {
  Filter,
  Download,
  Bell,
  RefreshCw,
  Layers,
  MapPin,
  TrendingUp,
  AlertTriangle,
  Globe2,
  ChevronRight
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [locations, setLocations] = useState([]);
  const [hierarchy, setHierarchy] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [locationDetail, setLocationDetail] = useState(null);
  const [liveWeather, setLiveWeather] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [backendError, setBackendError] = useState(false);

  // Hierarchical State & District Filter
  const [selectedState, setSelectedState] = useState('');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [selectedRiskTier, setSelectedRiskTier] = useState('');

  // Modals state
  const [isSimulationOpen, setIsSimulationOpen] = useState(false);
  const [isAnalysisOpen, setIsAnalysisOpen] = useState(false);

  // Initial Load and Reconnect
  const loadAllData = async () => {
    setLoading(true);
    try {
      const [locs, hier, alertList] = await Promise.all([
        fetchLocations(),
        fetchHierarchy(),
        fetchAlerts(8)
      ]);

      if (!locs || locs.length === 0) {
        setBackendError(true);
      } else {
        setBackendError(false);
      }

      // Compute physical geomorphological risk baseline for all locations
      const enrichedLocs = (locs || []).map((l) => {
        let riskCat = l.risk_category;
        let hazIdx = l.hazard_index;
        if (!riskCat) {
          const slope = Number(l.slope) || 0;
          const elev = Number(l.elevation) || 0;
          if (slope >= 30 && elev >= 1000) {
            riskCat = 'High';
            hazIdx = 0.78;
          } else if (slope >= 15 || elev >= 450) {
            riskCat = 'Moderate';
            hazIdx = 0.44;
          } else {
            riskCat = 'Low';
            hazIdx = 0.12;
          }
        }
        return {
          ...l,
          risk_category: riskCat,
          hazard_index: hazIdx,
        };
      });

      setLocations(enrichedLocs);
      setHierarchy(hier || []);
      setAlerts(alertList || []);

      // Default selected location: Gangtok (or first high-hazard location)
      const defaultLoc = enrichedLocs.find((l) => l.name === 'Gangtok' || l.district === 'East Sikkim') || enrichedLocs[0];
      if (defaultLoc) {
        setSelectedLocation(defaultLoc);
        loadDetailForLocation(defaultLoc.id, defaultLoc);
      }
    } catch (err) {
      console.error('Initial data load error:', err);
      setBackendError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const loadDetailForLocation = async (locId, locObj = null) => {
    const targetLoc = locObj || (locations || []).find((l) => l && l.id === locId);
    if (targetLoc?.latitude && targetLoc?.longitude) {
      fetchWeather(targetLoc.latitude, targetLoc.longitude).then((w) => {
        if (w) setLiveWeather(w);
      });
    }
    const detail = await fetchLocationDetail(locId, targetLoc);
    if (detail) {
      setLocationDetail(detail);
      if (detail.weather) {
        setLiveWeather(detail.weather);
      }
      if (detail.location && detail.prediction) {
        setSelectedLocation((prev) => ({
          ...(prev || locObj || detail.location),
          ...detail.location,
          hazard_index: detail.prediction.hazard_index ?? prev?.hazard_index,
          risk_category: detail.prediction.risk_category ?? prev?.risk_category,
        }));
      }
    }
  };

  const handleSelectLocation = (loc) => {
    setSelectedLocation(loc);
    loadDetailForLocation(loc.id, loc);
  };

  // When state changes in cascade filter, update district dropdown and center map
  const handleStateChange = (st) => {
    setSelectedState(st);
    setSelectedDistrict('');
    if (st) {
      const match = locations.find((l) => l.state === st);
      if (match) handleSelectLocation(match);
    }
  };

  const handleDistrictChange = (dist) => {
    setSelectedDistrict(dist);
    if (dist) {
      const match = locations.find((l) => (l.district === dist || l.name.includes(dist)));
      if (match) handleSelectLocation(match);
    }
  };

  // Available districts for the currently selected state
  const activeStateObj = hierarchy.find((h) => h.state === selectedState);
  const availableDistricts = activeStateObj ? activeStateObj.districts : [];

  // Filter locations based on cascade controls
  const filteredLocations = (locations || []).filter((l) => {
    if (!l) return false;
    if (selectedState && l.state !== selectedState) return false;
    if (selectedDistrict && l.district !== selectedDistrict) return false;
    if (selectedRiskTier && !(l.risk_category || '').toLowerCase().includes(selectedRiskTier.toLowerCase())) return false;
    return true;
  });

  // Counts for top cards
  const highCount = (locations || []).filter((l) => (l?.risk_category || '') === 'High').length;
  const modCount = (locations || []).filter((l) => (l?.risk_category || '') === 'Moderate').length;
  const lowCount = (locations || []).filter((l) => (l?.risk_category || '').includes('Low') || (l?.risk_category || '').includes('Plain')).length;

  return (
    <div className="flex min-h-screen bg-[#f1f5f9] text-slate-800">
      {/* Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        unreadAlertCount={alerts.filter((a) => !a.is_read).length}
      />

      {/* Main Content Body */}
      <div className="flex-1 flex flex-col min-w-0">
        <TopHeader
          locations={locations}
          selectedLocation={selectedLocation}
          onSelectLocation={handleSelectLocation}
          unreadAlertCount={alerts.filter((a) => !a.is_read).length}
          onOpenAlerts={() => setActiveTab('alerts')}
        />

        <main className="flex-1 p-5 lg:p-6 space-y-5 max-w-[1600px] mx-auto w-full">
          {backendError && !loading && (
            <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-amber-900 shadow-sm">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div className="text-xs space-y-1">
                  <span className="font-bold text-amber-800 text-sm block">Backend API Connecting / Standby</span>
                  <p className="text-amber-700 leading-relaxed">
                    Render free instances sleep when inactive. Connecting to live backend at <code className="bg-amber-100 px-1.5 py-0.5 rounded text-[11px] font-mono font-semibold">ai-land-slide-alert.onrender.com</code>.
                  </p>
                </div>
              </div>
              <button
                onClick={() => loadAllData()}
                className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition-all shadow-sm flex-shrink-0"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry Connection</span>
              </button>
            </div>
          )}

          {/* HIERARCHICAL STATE -> DISTRICT CASCADE SELECTOR BAR */}
          <div className="bg-white p-3.5 rounded-2xl border border-slate-200/90 shadow-sm flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center space-x-2">
              <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
                <Globe2 className="w-4 h-4" />
              </div>
              <div>
                <span className="text-xs font-bold text-slate-800 block leading-tight">
                  All-India Geographic Hierarchy
                </span>
                <span className="text-[10px] text-slate-400 font-medium">
                  {hierarchy.length} States & UTs • {locations.length} Monitored Districts/Sectors
                </span>
              </div>
            </div>

            {/* Cascade Dropdowns */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              {/* 1. State Selector */}
              <div className="flex items-center space-x-1">
                <span className="text-slate-400 font-medium text-[11px]">State:</span>
                <select
                  value={selectedState}
                  onChange={(e) => handleStateChange(e.target.value)}
                  className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                >
                  <option value="">All India (28 States + 8 UTs)</option>
                  {hierarchy.map((h) => (
                    <option key={h.state} value={h.state}>
                      {h.state} {h.hazard_monitoring_active ? '★ (High Hazard)' : ''}
                    </option>
                  ))}
                </select>
              </div>

              {/* 2. District Selector */}
              <div className="flex items-center space-x-1">
                <span className="text-slate-400 font-medium text-[11px]">District:</span>
                <select
                  value={selectedDistrict}
                  onChange={(e) => handleDistrictChange(e.target.value)}
                  disabled={!selectedState}
                  className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 disabled:opacity-50"
                >
                  <option value="">
                    {selectedState ? 'All Districts in State' : 'Select State First'}
                  </option>
                  {availableDistricts.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>

              {/* 3. Risk Tier Filter */}
              <div className="flex items-center space-x-1">
                <span className="text-slate-400 font-medium text-[11px]">Hazard:</span>
                <select
                  value={selectedRiskTier}
                  onChange={(e) => setSelectedRiskTier(e.target.value)}
                  className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                >
                  <option value="">All Hazard Tiers</option>
                  <option value="High">High Hazard (≥70%)</option>
                  <option value="Moderate">Moderate Hazard (30-70%)</option>
                  <option value="Low">Low Hazard / Plain</option>
                </select>
              </div>

              {(selectedState || selectedDistrict || selectedRiskTier) && (
                <button
                  onClick={() => {
                    setSelectedState('');
                    setSelectedDistrict('');
                    setSelectedRiskTier('');
                  }}
                  className="px-2 py-1 text-[11px] text-slate-500 hover:text-red-600 font-medium transition-colors"
                >
                  Reset
                </button>
              )}
            </div>
          </div>

          {/* TAB 1: MAIN DASHBOARD */}
          {activeTab === 'dashboard' && (
            <>
              {/* Row 1: Stat Cards + Live Weather */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                <StatCard
                  title="Total Districts / Sites"
                  value={filteredLocations.length || locations.length}
                  change="All India"
                  changeType="up"
                  subtitle="28 States & 8 UTs"
                  type="total"
                  onClick={() => setActiveTab('live-map')}
                />
                <StatCard
                  title="High Risk Districts"
                  value={highCount}
                  change="Critical"
                  changeType="up"
                  subtitle="Himalayan & Ghats corridor"
                  type="high"
                  onClick={() => {
                    setSelectedRiskTier('High');
                    setActiveTab('live-map');
                  }}
                />
                <StatCard
                  title="Moderate Risk Areas"
                  value={modCount}
                  change="Watch"
                  changeType="up"
                  subtitle="Under rainfall observation"
                  type="moderate"
                  onClick={() => {
                    setSelectedRiskTier('Moderate');
                    setActiveTab('live-map');
                  }}
                />
                <StatCard
                  title="Low Hazard / Plains"
                  value={lowCount}
                  change="Stable"
                  changeType="up"
                  subtitle="Generally non-mountainous"
                  type="low"
                  onClick={() => {
                    setSelectedRiskTier('Low');
                    setActiveTab('live-map');
                  }}
                />
                <WeatherCard
                  weather={liveWeather}
                  locationName={`${selectedLocation?.name || 'Gangtok'}, ${selectedLocation?.state || 'Sikkim'}`}
                  onViewForecast={() => setActiveTab('weather')}
                />
              </div>

              {/* Row 2: Leaflet GIS Map + Location Details + Alerts/Forecast Column */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                {/* Center-Left: Leaflet GIS Interactive Map (6 Cols) */}
                <div className="lg:col-span-6 min-h-[460px]">
                  <RiskMap
                    locations={filteredLocations}
                    selectedLocation={selectedLocation}
                    onSelectLocation={handleSelectLocation}
                    customZoom={selectedDistrict ? 9 : selectedState ? 7 : 5}
                  />
                </div>

                {/* Center-Right: Selected Location Details Panel (3 Cols) */}
                <div className="lg:col-span-3 min-h-[460px]">
                  <LocationDetails
                    location={selectedLocation}
                    liveWeather={liveWeather}
                    prediction={locationDetail?.prediction}
                    onClose={() => setSelectedLocation(null)}
                    onOpenAnalysis={() => setIsAnalysisOpen(true)}
                    onOpenSimulation={() => setIsSimulationOpen(true)}
                  />
                </div>

                {/* Right Column: Recent Alerts + 5-Day Forecast (3 Cols) */}
                <div className="lg:col-span-3 space-y-4 flex flex-col justify-between">
                  <AlertList
                    alerts={alerts}
                    onSelectAlert={(a) => {
                      const loc = locations.find((l) => l.id === a.location_id);
                      if (loc) handleSelectLocation(loc);
                    }}
                    onViewAll={() => setActiveTab('alerts')}
                  />
                  <ForecastCard
                    forecast={liveWeather?.forecast_5d}
                    onViewMore={() => setActiveTab('weather')}
                  />
                </div>
              </div>

              {/* Row 3: Analytics Row (Risk Distribution, Rainfall Trend, High-Risk Table) */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <RiskDistributionChart
                  highCount={highCount}
                  moderateCount={modCount}
                  lowCount={lowCount}
                />
                <RainfallChart
                  rainfallTrend={liveWeather?.rainfall_trend_7d}
                />
                <HighRiskTable
                  locations={locations}
                  onSelectLocation={handleSelectLocation}
                  onViewAll={() => setActiveTab('live-map')}
                />
              </div>

              {/* Row 4: Early Warning System Action Banner */}
              <EarlyWarningBanner onManageAlerts={() => setActiveTab('alerts')} />
            </>
          )}

          {/* TAB 2: LIVE MAP EXPANDED VIEW */}
          {activeTab === 'live-map' && (
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
              <div className="lg:col-span-3 min-h-[620px]">
                <RiskMap
                  locations={filteredLocations}
                  selectedLocation={selectedLocation}
                  onSelectLocation={handleSelectLocation}
                  customZoom={selectedDistrict ? 9 : selectedState ? 7 : 5}
                />
              </div>
              <div className="lg:col-span-1 min-h-[620px]">
                <LocationDetails
                  location={selectedLocation}
                  liveWeather={liveWeather}
                  prediction={locationDetail?.prediction}
                  onClose={() => setSelectedLocation(null)}
                  onOpenAnalysis={() => setIsAnalysisOpen(true)}
                  onOpenSimulation={() => setIsSimulationOpen(true)}
                />
              </div>
            </div>
          )}

          {/* TAB 3: RISK ANALYSIS */}
          {activeTab === 'risk-analysis' && (
            <div className="space-y-5">
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-slate-900">
                    National Multi-Hazard & SHAP Explainability Dashboard
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Analyzing geotechnical triggers across Himalayas, Western Ghats, and Northeast India.
                  </p>
                </div>
                <button
                  onClick={() => setIsAnalysisOpen(true)}
                  className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-semibold flex items-center space-x-1.5"
                >
                  <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Inspect Selected Location ({selectedLocation?.name})</span>
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
                  <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                    National Geomorphology & Hazard Zonation
                  </h3>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    LANDSAFE-NER covers high-landslide zones across <strong>Northeast India</strong> (Sikkim, Assam, Arunachal, Meghalaya, Nagaland, Manipur, Mizoram, Tripura), the <strong>Himalayan belt</strong> (Uttarakhand, Himachal Pradesh, J&K, Ladakh), and the <strong>Western Ghats</strong> (Kerala Wayanad/Idukki, Maharashtra Raigad/Pune, Karnataka Kodagu, Tamil Nadu Nilgiris).
                  </p>
                  <div className="space-y-2 pt-2 text-xs">
                    <div className="flex justify-between font-medium">
                      <span>Tier 1: Full Hazard Monitoring (Himalayas & Ghats)</span>
                      <span className="font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        Active ML + Satellite
                      </span>
                    </div>
                    <div className="flex justify-between font-medium">
                      <span>Tier 2: Non-Mountainous Plain Districts</span>
                      <span className="font-bold text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                        Low Hazard Notice
                      </span>
                    </div>
                  </div>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
                  <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                    What-If Simulation Sandbox
                  </h3>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Test hypothetical extreme rainfall, slope modifications, and snowmelt triggers across any monitored district in India.
                  </p>
                  <button
                    onClick={() => setIsSimulationOpen(true)}
                    className="w-full mt-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold flex items-center justify-center space-x-2 transition-all shadow-sm"
                  >
                    <span>Launch Scenario Simulation Sandbox</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: WEATHER & FORECAST */}
          {activeTab === 'weather' && (
            <div className="space-y-5">
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-base font-bold text-slate-900">
                      All-India Meteorological Station Network
                    </h2>
                    <p className="text-xs text-slate-500">
                      Live 24/7 ingestion via Open-Meteo API across monitored states and districts.
                    </p>
                  </div>
                  <DataSourceTag source="Open-Meteo" />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
                  {filteredLocations.slice(0, 12).map((loc) => (
                    <div
                      key={loc.id}
                      onClick={() => handleSelectLocation(loc)}
                      className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                        selectedLocation?.id === loc.id
                          ? 'border-emerald-500 bg-emerald-50/40 shadow-xs'
                          : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <h4 className="font-bold text-slate-900 text-xs">{loc.name}</h4>
                          <span className="text-[11px] text-slate-500">{loc.district}, {loc.state}</span>
                        </div>
                        <span className="text-xs font-bold text-slate-800">
                          {loc.rainfall_24h != null ? `${loc.rainfall_24h} mm` : '--'}
                        </span>
                      </div>
                      <div className="mt-2 text-[10px] text-slate-400 flex justify-between">
                        <span>Elevation: {loc.elevation}m</span>
                        <span className="font-semibold text-emerald-600">Open-Meteo Live</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: ALERTS */}
          {activeTab === 'alerts' && (
            <div className="space-y-4">
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-slate-900">
                    Active Early Warnings & Threshold Monitoring
                  </h2>
                  <p className="text-xs text-slate-500">
                    Automated breach notifications triggered when risk probability or 24h precipitation exceeds thresholds.
                  </p>
                </div>
                <span className="text-xs font-bold text-red-600 bg-red-50 border border-red-200 px-3 py-1 rounded-full">
                  {alerts.length} Active Notifications
                </span>
              </div>

              <div className="space-y-3">
                {alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-sm flex items-start justify-between gap-4"
                  >
                    <div className="flex items-start space-x-3.5">
                      <div
                        className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${
                          alert.severity === 'High'
                            ? 'bg-red-50 text-red-600 border border-red-200'
                            : 'bg-amber-50 text-amber-600 border border-amber-200'
                        }`}
                      >
                        <AlertTriangle className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <h4 className="text-xs font-bold text-slate-900">{alert.title}</h4>
                          <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-medium">
                            {alert.hazard_type}
                          </span>
                        </div>
                        <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                          {alert.message}
                        </p>
                        <div className="flex items-center space-x-3 text-[10px] text-slate-400 mt-2">
                          <span className="font-semibold text-slate-700">{alert.location_name}, {alert.state}</span>
                          <span>•</span>
                          <span>{alert.created_at}</span>
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => {
                        const loc = locations.find((l) => l.id === alert.location_id);
                        if (loc) {
                          handleSelectLocation(loc);
                          setActiveTab('dashboard');
                        }
                      }}
                      className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium flex-shrink-0 transition-colors"
                    >
                      Locate on Map
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 6: REPORTS & EXPORT */}
          {activeTab === 'reports' && (
            <div className="space-y-5">
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                <h2 className="text-base font-bold text-slate-900">
                  National Hazard Assessment Report Generation
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Export hazard assessment briefs with academic disclaimers, terrain intelligence, and XGBoost SHAP logs.
                </p>

                <div className="mt-5 space-y-3">
                  {filteredLocations.slice(0, 8).map((loc) => (
                    <div
                      key={loc.id}
                      className="flex items-center justify-between p-3.5 bg-slate-50 rounded-xl border border-slate-200/80"
                    >
                      <div>
                        <span className="font-bold text-slate-800 text-xs">{loc.name}</span>
                        <span className="text-slate-500 text-xs ml-2">({loc.district}, {loc.state})</span>
                        <div className="text-[10px] text-slate-400 mt-0.5">
                          Tier: {loc.coverage_tier} • Elevation: {loc.elevation}m • Slope: {loc.slope}°
                        </div>
                      </div>

                      <button
                        onClick={async () => {
                          const rep = await (await import('./services/api')).exportReport(loc.id);
                          if (rep) {
                            const blob = new Blob([JSON.stringify(rep, null, 2)], { type: 'application/json' });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = `LANDSAFE_Report_${loc.name.replace(/\s+/g, '_')}.json`;
                            a.click();
                            URL.revokeObjectURL(url);
                          }
                        }}
                        className="px-3 py-1.5 bg-white hover:bg-slate-100 text-slate-800 border border-slate-300 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors shadow-2xs"
                      >
                        <Download className="w-3.5 h-3.5 text-slate-500" />
                        <span>Export Report</span>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Academic Prototype Disclaimer in Footer */}
          <DisclaimerFooter />
        </main>
      </div>

      {/* Interactive Modals */}
      <SimulationModal
        location={selectedLocation}
        isOpen={isSimulationOpen}
        onClose={() => setIsSimulationOpen(false)}
      />

      <ShapExplanationModal
        location={selectedLocation}
        detailData={locationDetail}
        isOpen={isAnalysisOpen}
        onClose={() => setIsAnalysisOpen(false)}
      />
    </div>
  );
}
