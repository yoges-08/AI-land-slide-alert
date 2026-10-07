import React, { useState, useEffect } from 'react';
import {
  Bell,
  Smartphone,
  CheckCircle2,
  AlertTriangle,
  Send,
  RefreshCw,
  ShieldCheck,
  PhoneCall,
  MessageSquare,
  Clock,
  User,
  MapPin,
  Flame,
  Radio
} from 'lucide-react';
import {
  fetchNotificationLog,
  subscribeNotification,
  sendTestNotification
} from '../services/api';

export default function NotificationPanel({ locations = [], selectedLocation = null }) {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [district, setDistrict] = useState(selectedLocation?.district || selectedLocation?.name || 'All Districts');
  const [userName, setUserName] = useState('');
  
  const [subscribing, setSubscribing] = useState(false);
  const [testing, setTesting] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);
  const [statusType, setStatusType] = useState('success'); // 'success' | 'error'

  const [notificationLog, setNotificationLog] = useState([]);
  const [isDemoMode, setIsDemoMode] = useState(true);
  const [loadingLog, setLoadingLog] = useState(false);

  // Load notification history
  const loadLogs = async () => {
    setLoadingLog(true);
    const data = await fetchNotificationLog(50);
    if (data) {
      setNotificationLog(data.notifications || []);
      setIsDemoMode(Boolean(data.demo_mode));
    }
    setLoadingLog(false);
  };

  useEffect(() => {
    loadLogs();
  }, []);

  // Update district dropdown when selectedLocation changes in dashboard
  useEffect(() => {
    if (selectedLocation) {
      setDistrict(selectedLocation.district || selectedLocation.name || 'All Districts');
    }
  }, [selectedLocation]);

  // Handle Subscribe
  const handleSubscribe = async (e) => {
    e.preventDefault();
    if (!phoneNumber || phoneNumber.trim().length < 10) {
      setStatusType('error');
      setStatusMessage('Please enter a valid 10-digit mobile number.');
      return;
    }

    setSubscribing(true);
    setStatusMessage(null);

    const res = await subscribeNotification(phoneNumber, district, userName || 'Citizen');
    if (res?.success || res?.status) {
      setStatusType('success');
      setStatusMessage(`✅ Mobile ${phoneNumber} successfully registered for alerts in ${district}!`);
      loadLogs();
    } else {
      setStatusType('error');
      setStatusMessage('Failed to register subscription. Please try again.');
    }
    setSubscribing(false);
  };

  // Handle Test Alert
  const handleSendTest = async () => {
    const targetPhone = phoneNumber || '+91 98765 43210';
    setTesting(true);
    setStatusMessage(null);

    const res = await sendTestNotification(targetPhone, district);
    if (res?.success) {
      setStatusType('success');
      setStatusMessage(`🚀 Test alert dispatched to ${targetPhone} (${res.demo_mode ? 'Demo Mode' : 'Live SMS'})!`);
      loadLogs();
    } else {
      setStatusType('error');
      setStatusMessage('Failed to send test alert.');
    }
    setTesting(false);
  };

  // Distinct unique districts from locations
  const uniqueDistricts = Array.from(
    new Set((locations || []).map((l) => l.district || l.name).filter(Boolean))
  ).sort();

  return (
    <div className="space-y-5 animate-in fade-in duration-200">
      {/* Page Title & Demo Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-200 flex items-center justify-center flex-shrink-0">
            <Smartphone className="w-5 h-5 stroke-[2.2]" />
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-900">
              SMS & WhatsApp Multi-Hazard Emergency Alert Dispatcher
            </h1>
            <p className="text-xs text-slate-500">
              Automated high-priority citizen and NDRF broadcast gateway
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
            <Radio className="w-3.5 h-3.5 mr-1 animate-pulse" />
            Twilio / Local Gateway
          </span>
        </div>
      </div>

      {/* Demo Mode Notice */}
      {isDemoMode && (
        <div className="bg-amber-50/90 border border-amber-200 rounded-2xl p-4 flex items-start space-x-3 text-amber-900 shadow-sm">
          <Radio className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <span className="font-bold text-amber-800 text-sm block">
              🔔 Safe Demo / Expo Mode Active
            </span>
            <p className="text-amber-700 leading-relaxed">
              Dispatched emergency notifications are stored in-memory and logged in real-time below without requiring external paid Twilio SMS API keys or active SIM routes.
            </p>
          </div>
        </div>
      )}

      {/* Feedback Banner */}
      {statusMessage && (
        <div
          className={`p-4 rounded-2xl text-xs font-semibold flex items-center justify-between border ${
            statusType === 'success'
              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
              : 'bg-red-50 text-red-800 border-red-200'
          }`}
        >
          <span>{statusMessage}</span>
          <button
            onClick={() => setStatusMessage(null)}
            className="text-slate-400 hover:text-slate-600 text-sm"
          >
            ✕
          </button>
        </div>
      )}

      {/* Grid: Subscription Form (Left 5 Cols) + Real-Time Dispatch Log (Right 7 Cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Register Subscription & Test Trigger */}
        <div className="lg:col-span-5 space-y-5">
          {/* Subscription Card */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center space-x-2">
                <Bell className="w-4 h-4 text-emerald-600" />
                <h2 className="text-sm font-bold text-slate-900">
                  Register Alert Subscription
                </h2>
              </div>
              <span className="text-[10px] text-slate-400 font-medium">+91 SMS & WhatsApp</span>
            </div>

            <form onSubmit={handleSubscribe} className="space-y-3.5 text-xs">
              {/* Phone Input */}
              <div className="space-y-1">
                <label className="font-semibold text-slate-700 flex items-center justify-between">
                  <span>Mobile Phone Number (India)</span>
                  <span className="text-[10px] text-slate-400">10-Digit Mobile</span>
                </label>
                <div className="relative flex items-center">
                  <span className="absolute left-3 font-bold text-slate-500 text-xs select-none">
                    +91
                  </span>
                  <input
                    type="tel"
                    placeholder="98765 43210"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value.replace(/[^0-9 ]/g, ''))}
                    className="w-full pl-12 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                    maxLength={13}
                  />
                </div>
              </div>

              {/* District Dropdown */}
              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Target District Coverage</label>
                <select
                  value={district}
                  onChange={(e) => setDistrict(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                >
                  <option value="All Districts">All High-Risk Monitored Districts</option>
                  {uniqueDistricts.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>

              {/* Name / Organization */}
              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Name / Designation (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. NDRF Duty Officer / Local Resident"
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                />
              </div>

              {/* Submit Buttons */}
              <div className="pt-2 flex flex-col sm:flex-row items-center gap-2">
                <button
                  type="submit"
                  disabled={subscribing}
                  className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center justify-center space-x-2 transition-all shadow-sm disabled:opacity-50"
                >
                  {subscribing ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <CheckCircle2 className="w-3.5 h-3.5" />
                  )}
                  <span>{subscribing ? 'Registering...' : 'Subscribe to Early Warnings'}</span>
                </button>
              </div>
            </form>
          </div>

          {/* Test Trigger Card */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm space-y-3">
            <div className="flex items-center space-x-2 border-b border-slate-100 pb-2.5">
              <Send className="w-4 h-4 text-indigo-600" />
              <h3 className="text-xs font-bold text-slate-900">
                Direct Simulator & Gateway Test
              </h3>
            </div>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Verify message formatting, timestamp conversion (IST), and emergency response templates instantly.
            </p>
            <button
              onClick={handleSendTest}
              disabled={testing}
              className="w-full py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 transition-all disabled:opacity-50"
            >
              {testing ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <PhoneCall className="w-3.5 h-3.5" />
              )}
              <span>{testing ? 'Dispatching...' : `Dispatch Test Alert to ${district}`}</span>
            </button>
          </div>
        </div>

        {/* Right Column: Live Dispatched Log */}
        <div className="lg:col-span-7 bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <div className="flex items-center space-x-2">
                <MessageSquare className="w-4 h-4 text-slate-700" />
                <h2 className="text-sm font-bold text-slate-900">
                  Dispatched Notifications Log
                </h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700">
                  {notificationLog.length} Records
                </span>
              </div>
              <button
                onClick={loadLogs}
                className="p-1 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                title="Refresh log"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingLog ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {/* Notification Stream */}
            <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1">
              {notificationLog.length === 0 ? (
                <div className="text-center py-12 text-slate-400 text-xs">
                  No notifications dispatched yet in this session.
                </div>
              ) : (
                notificationLog.map((notif, idx) => {
                  const isCrit = notif.risk_level === 'Critical' || notif.risk_score >= 80;
                  const isHigh = notif.risk_level === 'High' || (notif.risk_score >= 60 && notif.risk_score < 80);

                  return (
                    <div
                      key={notif.id || idx}
                      className="p-3.5 rounded-xl border border-slate-200/80 bg-slate-50/70 hover:bg-slate-50 transition-colors space-y-2 text-xs"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center space-x-2">
                          <span
                            className={`w-2 h-2 rounded-full ${
                              isCrit ? 'bg-red-500 animate-ping' : isHigh ? 'bg-orange-500' : 'bg-emerald-500'
                            }`}
                          />
                          <span className="font-bold text-slate-900">{notif.district}</span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              isCrit
                                ? 'bg-red-100 text-red-700'
                                : isHigh
                                ? 'bg-orange-100 text-orange-700'
                                : 'bg-amber-100 text-amber-700'
                            }`}
                          >
                            {notif.risk_level} ({notif.risk_score}%)
                          </span>
                        </div>

                        <div className="flex items-center space-x-2 text-[10px] text-slate-400 font-mono">
                          <Clock className="w-3 h-3" />
                          <span>{notif.timestamp_ist || 'Just now'}</span>
                        </div>
                      </div>

                      {/* Message Preview */}
                      <pre className="font-mono text-[11px] bg-white p-2.5 rounded-lg border border-slate-200/80 text-slate-800 whitespace-pre-wrap leading-relaxed shadow-2xs">
                        {notif.message}
                      </pre>

                      {/* Recipient and Status pill */}
                      <div className="flex items-center justify-between text-[10px] pt-1 text-slate-500">
                        <span>Recipient: <span className="font-semibold text-slate-700">{notif.phone_number}</span></span>
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {notif.status === 'DEMO_DELIVERED' ? '✓ Demo Logged' : '✓ SMS Dispatched'}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400">
            <span>In-memory ring buffer (Last 50 entries)</span>
            <span>Emergency Helpline: NDRF 1078 / ERSS 112</span>
          </div>
        </div>
      </div>
    </div>
  );
}
