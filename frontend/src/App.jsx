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
  fetchLocationDetail,
  fetchWeather,
  fetchAlerts
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
  FileSpreadsheet
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [locations, setLocations] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [locationDetail, setLocationDetail] = useState(null);
  const [liveWeather, setLiveWeather] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filter state for Live Map tab
  const [filterState, setFilterState] = useState('');
  const [filterRisk, setFilterRisk] = useState('');

  // Modals state
  const [isSimulationOpen, setIsSimulationOpen] = useState(false);
  const [isAnalysisOpen, setIsAnalysisOpen] = useState(false);

  // Initial Load
  useEffect(() => {
    async function initData() {
      setLoading(true);
      const locs = await fetchLocations();
      setLocations(locs);

      const alertList = await fetchAlerts(8);
      setAlerts(alertList);

      // Default selected location: Gangtok (or first item)
      const defaultLoc = locs.find((l) => l.name === 'Gangtok') || locs[0];
      if (defaultLoc) {
        setSelectedLocation(defaultLoc);
        loadDetailForLocation(defaultLoc.id);
      }

      setLoading(false);
    }
    initData();
  }, []);

  const loadDetailForLocation = async (locId) => {
    const detail = await fetchLocationDetail(locId);
    if (detail) {
      setLocationDetail(detail);
      setLiveWeather(detail.weather);
    }
  };

  const handleSelectLocation = (loc) => {
    setSelectedLocation(loc);
    loadDetailForLocation(loc.id);
  };

  // Counts for top cards
  const highCount = locations.filter((l) => l.risk_category === 'High').length || 18;
  const modCount = locations.filter((l) => l.risk_category === 'Moderate').length || 47;
  const lowCount = locations.filter((l) => l.risk_category === 'Low').length || 185;

  return (
    <div className="flex min-h-screen bg-[#f1f5f9] text-slate-800">
      {/* 1. Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        unreadAlertCount={alerts.filter((a) => !a.is_read).length}
      />

      {/* 2. Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <TopHeader
          locations={locations}
          selectedLocation={selectedLocation}
          onSelectLocation={handleSelectLocation}
          unreadAlertCount={alerts.filter((a) => !a.is_read).length}
          onOpenAlerts={() => setActiveTab('alerts')}
        />

        {/* Dynamic Tab Body */}
        <main className="flex-1 p-5 lg:p-6 space-y-6 max-w-[1600px] mx-auto w-full">
          {/* TAB 1: MAIN DASHBOARD (Matching UI Mockup) */}
          {activeTab === 'dashboard' && (
            <>
              {/* Row 1: 4 Stat Cards + Weather Widget */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                <StatCard
                  title="Total Locations"
                  value={locations.length || 250}
                  change="12%"
                  changeType="up"
                  subtitle="Monitored across NE India"
                  type="total"
                  onClick={() => setActiveTab('live-map')}
                />
                <StatCard
                  title="High Risk Areas"
                  value={highCount}
                  change="5%"
                  changeType="up"
                  subtitle="Requires immediate attention"
                  type="high"
                  onClick={() => {
                    setFilterRisk('High');
                    setActiveTab('live-map');
                  }}
                />
                <StatCard
                  title="Moderate Risk Areas"
                  value={modCount}
                  change="8%"
                  changeType="up"
                  subtitle="Under observation"
                  type="moderate"
                  onClick={() => {
                    setFilterRisk('Moderate');
                    setActiveTab('live-map');
                  }}
                />
                <StatCard
                  title="Low Risk Areas"
                  value={lowCount}
                  change="10%"
                  changeType="up"
                  subtitle="Generally stable"
                  type="low"
                  onClick={() => {
                    setFilterRisk('Low');
                    setActiveTab('live-map');
                  }}
                />
                <WeatherCard
                  weather={liveWeather}
                  locationName={`${selectedLocation?.name || 'Gangtok'}, ${selectedLocation?.state || 'Sikkim'}`}
                  onViewForecast={() => setActiveTab('weather')}
                />
              </div>

              {/* Row 2: Landslide Risk Map + Location Details + Alerts/Forecast Column */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                {/* Center-Left: Leaflet GIS Interactive Map (6 Cols) */}
                <div className="lg:col-span-6 min-h-[460px]">
                  <RiskMap
                    locations={locations}
                    selectedLocation={selectedLocation}
                    onSelectLocation={handleSelectLocation}
                  />
                </div>

                {/* Center-Right: Selected Location Details Panel (3 Cols) */}
                <div className="lg:col-span-3 min-h-[460px]">
                  <LocationDetails
                    location={selectedLocation}
                    liveWeather={liveWeather}
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
            <div className="space-y-4">
              <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-sm flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center space-x-2">
                  <Filter className="w-4 h-4 text-emerald-600" />
                  <span className="text-xs font-bold text-slate-800">Filter Monitored Locations:</span>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <select
                    value={filterState}
                    onChange={(e) => setFilterState(e.target.value)}
                    className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                  >
                    <option value="">All Northeast States (8)</option>
                    <option value="Sikkim">Sikkim</option>
                    <option value="Arunachal Pradesh">Arunachal Pradesh</option>
                    <option value="Assam">Assam</option>
                    <option value="Meghalaya">Meghalaya</option>
                    <option value="Nagaland">Nagaland</option>
                    <option value="Manipur">Manipur</option>
                    <option value="Mizoram">Mizoram</option>
                    <option value="Tripura">Tripura</option>
                  </select>

                  <select
                    value={filterRisk}
                    onChange={(e) => setFilterRisk(e.target.value)}
                    className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                  >
                    <option value="">All Risk Tiers</option>
                    <option value="High">High Risk (≥70%)</option>
                    <option value="Moderate">Moderate Risk (30-70%)</option>
                    <option value="Low">Low Risk (&lt;30%)</option>
                  </select>

                  <button
                    onClick={() => {
                      setFilterState('');
                      setFilterRisk('');
                    }}
                    className="px-3 py-1.5 text-xs text-slate-500 hover:text-slate-800 font-medium transition-colors"
                  >
                    Reset Filters
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
                <div className="lg:col-span-3 min-h-[600px]">
                  <RiskMap
                    locations={locations.filter((l) => {
                      if (filterState && l.state !== filterState) return false;
                      if (filterRisk && l.risk_category !== filterRisk) return false;
                      return true;
                    })}
                    selectedLocation={selectedLocation}
                    onSelectLocation={handleSelectLocation}
                  />
                </div>
                <div className="lg:col-span-1 min-h-[600px]">
                  <LocationDetails
                    location={selectedLocation}
                    liveWeather={liveWeather}
                    onClose={() => setSelectedLocation(null)}
                    onOpenAnalysis={() => setIsAnalysisOpen(true)}
                    onOpenSimulation={() => setIsSimulationOpen(true)}
                  />
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: RISK ANALYSIS & SHAP EXPLAINABILITY */}
          {activeTab === 'risk-analysis' && (
            <div className="space-y-5">
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-slate-900">
                    Comprehensive Hazard & Model Intelligence
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Analyzing multi-factor geotechnical triggers and SHAP tree attributions for Northeast India.
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
                    Landslide Triggering Physics & Feature Weights
                  </h3>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    LANDSAFE-NER combines real-time rainfall intensity-duration saturation thresholds with DEM slope steepness, geological shear vulnerability (Disang shale, Phyllite), and new satellite-derived terrain intelligence.
                  </p>
                  <div className="space-y-2 pt-2">
                    <div className="flex justify-between text-xs font-medium">
                      <span>24h Cumulative Precipitation</span>
                      <span className="font-bold text-red-600">Primary Trigger (35%)</span>
                    </div>
                    <div className="flex justify-between text-xs font-medium">
                      <span>Slope Gradient & Aspect</span>
                      <span className="font-bold text-amber-600">Terrain Instability (30%)</span>
                    </div>
                    <div className="flex justify-between text-xs font-medium">
                      <span>Sentinel-2 Bare Soil Exposure (BSI)</span>
                      <span className="font-bold text-indigo-600">Surface Friability (15%)</span>
                    </div>
                    <div className="flex justify-between text-xs font-medium">
                      <span>NASA MODIS Snowmelt Runoff</span>
                      <span className="font-bold text-cyan-600">Pore Water Influx (10%)</span>
                    </div>
                    <div className="flex justify-between text-xs font-medium">
                      <span>Slope Agriculture (NDVI Change)</span>
                      <span className="font-bold text-emerald-600">Anthropogenic Cut (10%)</span>
                    </div>
                  </div>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
                  <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                    What-If Simulation Sandbox
                  </h3>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Test hypothetical weather events (e.g. cloudburst rainfall of +150mm, sudden spring snowmelt, or slope deforestation) to observe real-time shift in risk probability.
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
                      Northeast India Meteorological Station Network
                    </h2>
                    <p className="text-xs text-slate-500">
                      Live 24/7 ingestion via Open-Meteo API with precipitation tracking and 5-day predictive forecasts.
                    </p>
                  </div>
                  <DataSourceTag source="Open-Meteo" />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
                  {locations.slice(0, 8).map((loc) => (
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
                          <span className="text-[11px] text-slate-500">{loc.state}</span>
                        </div>
                        <span className="text-xs font-bold text-slate-800">
                          {loc.rainfall_24h || 35} mm
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
                    Automated breach notifications triggered when risk probability or 24h precipitation exceeds safety thresholds.
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
                  Hazard Assessment Report Generation
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Generate verified hazard assessment briefs complete with academic disclaimers, terrain intelligence data, and XGBoost SHAP factor logs.
                </p>

                <div className="mt-5 space-y-3">
                  {locations.slice(0, 6).map((loc) => (
                    <div
                      key={loc.id}
                      className="flex items-center justify-between p-3.5 bg-slate-50 rounded-xl border border-slate-200/80"
                    >
                      <div>
                        <span className="font-bold text-slate-800 text-xs">{loc.name}</span>
                        <span className="text-slate-500 text-xs ml-2">({loc.state})</span>
                        <div className="text-[10px] text-slate-400 mt-0.5">
                          Risk: {loc.risk_category} ({Math.round((loc.risk_probability || 0.2) * 100)}%) • Slope: {loc.slope}° • 24h Rain: {loc.rainfall_24h || 30}mm
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
                            a.download = `LANDSAFE_Report_${loc.name}.json`;
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

          {/* TAB 7: SETTINGS */}
          {activeTab === 'settings' && (
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm max-w-2xl space-y-4">
              <h2 className="text-base font-bold text-slate-900">System & Pipeline Configuration</h2>
              <p className="text-xs text-slate-500">
                Data source configuration and alert thresholds.
              </p>

              <div className="space-y-3 pt-2 text-xs">
                <div className="flex justify-between items-center p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <div>
                    <span className="font-bold text-slate-800 block">Open-Meteo Weather API</span>
                    <span className="text-[11px] text-slate-500">Live 24/7 rainfall and forecast ingestion</span>
                  </div>
                  <span className="text-emerald-600 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">Active</span>
                </div>

                <div className="flex justify-between items-center p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <div>
                    <span className="font-bold text-slate-800 block">NASA GIBS Tile Layers</span>
                    <span className="text-[11px] text-slate-500">MODIS / VIIRS base reflectance and snow cover</span>
                  </div>
                  <span className="text-emerald-600 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">Active</span>
                </div>

                <div className="flex justify-between items-center p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <div>
                    <span className="font-bold text-slate-800 block">ISRO Bhuvan Thematic WMS</span>
                    <span className="text-[11px] text-slate-500">LULC & geomorphological map layer</span>
                  </div>
                  <span className="text-orange-600 font-bold bg-orange-50 px-2 py-0.5 rounded border border-orange-200">Toggleable</span>
                </div>

                <div className="flex justify-between items-center p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <div>
                    <span className="font-bold text-slate-800 block">High Risk Threshold</span>
                    <span className="text-[11px] text-slate-500">Prototype trigger percentage</span>
                  </div>
                  <span className="font-bold text-slate-800">≥ 70% Probability</span>
                </div>
              </div>
            </div>
          )}

          {/* Academic Prototype Disclaimer in Footer */}
          <DisclaimerFooter />
        </main>
      </div>

      {/* 3. Interactive Modals */}
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
