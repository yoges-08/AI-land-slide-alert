const BACKEND_URL = import.meta.env.VITE_API_BASE_URL || (import.meta.env.PROD ? 'https://ai-land-slide-alert.onrender.com' : '');
const API_BASE = BACKEND_URL ? `${BACKEND_URL.replace(/\/+$/, '')}/api` : '/api';

export async function fetchLocations(state = '', district = '', risk = '') {
  try {
    const params = new URLSearchParams();
    if (state) params.append('state', state);
    if (district) params.append('district', district);
    if (risk) params.append('risk', risk);
    const url = `${API_BASE}/locations${params.toString() ? `?${params.toString()}` : ''}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Locations fetch error:', err);
    return [];
  }
}

export async function fetchHierarchy() {
  try {
    const res = await fetch(`${API_BASE}/hierarchy`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Hierarchy fetch error:', err);
    return [];
  }
}

export async function fetchLocationDetail(locId) {
  try {
    const res = await fetch(`${API_BASE}/location/${locId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`Location detail fetch error for id ${locId}:`, err);
    return null;
  }
}

export async function fetchWeather(lat, lon) {
  try {
    const res = await fetch(`${API_BASE}/weather/${lat}/${lon}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Weather fetch error:', err);
    return null;
  }
}

export async function fetchAlerts(limit = 10) {
  try {
    const res = await fetch(`${API_BASE}/alerts?limit=${limit}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Alerts fetch error:', err);
    return [];
  }
}

export async function runSimulation(simData) {
  try {
    const res = await fetch(`${API_BASE}/simulation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(simData),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Simulation error:', err);
    return null;
  }
}

export async function fetchModelInfo() {
  try {
    const res = await fetch(`${API_BASE}/model/info`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Model info fetch error:', err);
    return null;
  }
}

export async function exportReport(locId) {
  try {
    const res = await fetch(`${API_BASE}/export/report/${locId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Report export error:', err);
    return null;
  }
}
