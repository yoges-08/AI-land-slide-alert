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

const WMO_MAP = {
  0: ['Clear sky', 'Sun'],
  1: ['Mainly clear', 'SunMedium'],
  2: ['Partly cloudy', 'CloudSun'],
  3: ['Overcast', 'Cloud'],
  45: ['Foggy', 'CloudFog'],
  48: ['Depositing rime fog', 'CloudFog'],
  51: ['Light drizzle', 'CloudDrizzle'],
  53: ['Moderate drizzle', 'CloudDrizzle'],
  55: ['Dense drizzle', 'CloudDrizzle'],
  61: ['Slight rain', 'CloudRain'],
  63: ['Moderate rain', 'CloudRain'],
  65: ['Heavy rain', 'CloudRainWind'],
  71: ['Slight snow', 'CloudSnow'],
  73: ['Moderate snow', 'CloudSnow'],
  75: ['Heavy snow', 'Snowflake'],
  80: ['Slight rain showers', 'CloudRain'],
  81: ['Moderate rain showers', 'CloudRain'],
  82: ['Violent rain showers', 'CloudRainWind'],
  95: ['Thunderstorm', 'CloudLightning'],
  96: ['Thunderstorm with hail', 'CloudLightning'],
  99: ['Heavy thunderstorm with hail', 'CloudLightning'],
};

export async function fetchDirectOpenMeteo(lat, lon) {
  try {
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m&hourly=precipitation,rain&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max&timezone=Asia%2FKolkata&past_days=6&forecast_days=6`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const current = data.current || {};
    const daily = data.daily || {};
    const hourly = data.hourly || {};

    const wmoCode = current.weather_code ?? 0;
    const [condText, icon] = WMO_MAP[wmoCode] || ['Clear sky', 'Sun'];

    // 24h rainfall sum from recent 24 hourly records
    const hourlyPrecip = hourly.precipitation || [];
    const recent24 = hourlyPrecip.slice(Math.max(0, hourlyPrecip.length - 24));
    const rainfall24h = Math.round((recent24.reduce((a, b) => a + (Number(b) || 0), 0)) * 10) / 10;

    // 7-day trend (past 7 days up to today)
    const dailyTimes = daily.time || [];
    const dailyPrecip = daily.precipitation_sum || [];
    const rainfallTrend7d = [];
    for (let i = 0; i < Math.min(7, dailyTimes.length); i++) {
      const dtStr = dailyTimes[i];
      const d = new Date(dtStr);
      const formattedDate = !isNaN(d.getTime()) ? d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : dtStr;
      rainfallTrend7d.push({
        date: formattedDate,
        iso_date: dtStr,
        rainfall_mm: dailyPrecip[i] != null ? Math.round(dailyPrecip[i] * 10) / 10 : 0,
      });
    }

    const rainfall7d = Math.round((rainfallTrend7d.reduce((a, b) => a + (b.rainfall_mm || 0), 0)) * 10) / 10;

    // 5-day forecast
    const forecast5d = [];
    const dailyCodes = daily.weather_code || [];
    const dailyMax = daily.temperature_2m_max || [];
    const dailyMin = daily.temperature_2m_min || [];
    for (let i = 6; i < Math.min(11, dailyTimes.length); i++) {
      const dtStr = dailyTimes[i];
      const d = new Date(dtStr);
      const dayName = !isNaN(d.getTime()) ? d.toLocaleDateString('en-US', { weekday: 'short' }) : `Day ${i - 5}`;
      const code = dailyCodes[i] ?? 0;
      const [fCond, fIcon] = WMO_MAP[code] || ['Clear', 'Sun'];
      forecast5d.push({
        day: dayName,
        date: dtStr,
        condition: fCond,
        icon: fIcon,
        temp_max: dailyMax[i] != null ? Math.round(dailyMax[i]) : 30,
        temp_min: dailyMin[i] != null ? Math.round(dailyMin[i]) : 20,
        precipitation_sum: dailyPrecip[i] || 0,
      });
    }

    return {
      status: 'LIVE',
      source: 'Open-Meteo Live',
      temperature: current.temperature_2m != null ? Math.round(current.temperature_2m * 10) / 10 : 26.5,
      humidity: current.relative_humidity_2m ?? 65,
      wind_speed: current.wind_speed_10m != null ? Math.round(current.wind_speed_10m * 10) / 10 : 12.0,
      rainfall_1h: current.precipitation != null ? Math.round(current.precipitation * 10) / 10 : 0.0,
      rainfall_24h: rainfall24h,
      rainfall_7d_cumulative: rainfall7d,
      weather_code: wmoCode,
      condition_text: condText,
      icon_name: icon,
      rainfall_trend_7d: rainfallTrend7d,
      forecast_5d: forecast5d,
      observed: {
        rainfall_1h: current.precipitation || 0.0,
        rainfall_24h: rainfall24h,
        rainfall_7d_cumulative: rainfall7d,
      },
      last_updated: new Date().toISOString(),
    };
  } catch (err) {
    console.warn('Direct Open-Meteo client fetch error:', err);
    return null;
  }
}

export async function predictLandslide(features) {
  try {
    const payload = {
      latitude: features.latitude || 27.33,
      longitude: features.longitude || 88.61,
      elevation: features.elevation || 1650.0,
      slope: features.slope || 25.0,
      rainfall_1h: features.rainfall_1h || 0.0,
      rainfall_24h: features.rainfall_24h != null ? features.rainfall_24h : 0.0,
      rainfall_7d_cumulative: features.rainfall_7d_cumulative || 0.0,
      rainfall_intensity: features.rainfall_intensity || features.rainfall_1h || 0.0,
      soil_type: features.soil_type || 'Clay Loam',
      geology: features.geology || 'Sedimentary',
      distance_road: features.distance_road || 200.0,
      distance_river: features.distance_river || 500.0,
      historical_landslides: features.historical_landslides || 0,
      aspect: features.aspect || 'N',
      land_cover: features.land_cover || 'Dense Forest',
      snow_cover_pct: features.snow_cover_pct || 0.0,
      snowmelt_rate: features.snowmelt_rate || 0.0,
      bare_soil_pct: features.bare_soil_pct || 10.0,
      vegetation_index: features.vegetation_index || 0.6,
      farm_change_flag: features.farm_change_flag || false,
    };
    const res = await fetch(`${API_BASE}/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Predict API error:', err);
    return null;
  }
}

export async function fetchLocationDetail(locId) {
  try {
    const res = await fetch(`${API_BASE}/location/${locId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // If backend weather was rate-limited (OFFLINE) on Render, fetch direct live weather
    if (!data.weather || data.weather.status === 'OFFLINE' || data.weather.temperature == null) {
      const directWeather = await fetchDirectOpenMeteo(data.location.latitude, data.location.longitude);
      if (directWeather) {
        data.weather = directWeather;

        // Trigger real ML model inference via /api/predict using observed physical features
        const prediction = await predictLandslide({
          ...data.location,
          ...directWeather,
          rainfall_1h: directWeather.rainfall_1h,
          rainfall_24h: directWeather.rainfall_24h,
          rainfall_7d_cumulative: directWeather.rainfall_7d_cumulative,
        });
        if (prediction) {
          data.prediction = {
            hazard_index: prediction.hazard_index,
            risk_category: prediction.risk_category,
            flood_index: prediction.flood_index,
            flood_risk_category: prediction.flood_risk_category,
            top_factors: prediction.top_factors,
            shap_values: prediction.shap_values,
            status: 'LIVE_MODEL_INFERENCE',
            inputs: {
              weather: { status: 'LIVE', source: 'Open-Meteo Live Telemetry' },
              satellite: data.satellite?.data_status || { status: 'STANDBY', source: 'NASA/Copernicus' }
            }
          };
        }
      }
    }
    return data;
  } catch (err) {
    console.warn(`Location detail fetch error for id ${locId}:`, err);
    return null;
  }
}

export async function fetchWeather(lat, lon) {
  try {
    const res = await fetch(`${API_BASE}/weather/${lat}/${lon}`);
    if (res.ok) {
      const data = await res.json();
      if (data && data.status !== 'OFFLINE' && data.temperature != null) {
        return data;
      }
    }
  } catch (err) {
    console.warn('Backend weather fetch error, trying direct Open-Meteo:', err);
  }
  return await fetchDirectOpenMeteo(lat, lon);
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
