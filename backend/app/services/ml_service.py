import os
import json
from pathlib import Path
from typing import Dict, Any
import numpy as np
import pandas as pd
import joblib
import shap

MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "ml" / "models"

# Global lazy loaded models
_LANDSLIDE_MODEL = None
_PREPROCESSOR = None
_FLOOD_MODEL = None
_METADATA = None
_SHAP_EXPLAINER = None

def load_ml_assets():
    global _LANDSLIDE_MODEL, _PREPROCESSOR, _FLOOD_MODEL, _METADATA, _SHAP_EXPLAINER
    if _LANDSLIDE_MODEL is None:
        model_path = MODELS_DIR / "best_landslide_model.joblib"
        prep_path = MODELS_DIR / "preprocessor.joblib"
        flood_path = MODELS_DIR / "flood_model.joblib"
        meta_path = MODELS_DIR / "model_metadata.json"

        if model_path.exists() and prep_path.exists():
            _LANDSLIDE_MODEL = joblib.load(model_path)
            _PREPROCESSOR = joblib.load(prep_path)
            if flood_path.exists():
                _FLOOD_MODEL = joblib.load(flood_path)
            if meta_path.exists():
                with open(meta_path, "r", encoding="utf-8") as f:
                    _METADATA = json.load(f)
            
            try:
                # Initialize TreeExplainer for XGBoost
                _SHAP_EXPLAINER = shap.TreeExplainer(_LANDSLIDE_MODEL)
            except Exception as e:
                print(f"Warning initializing SHAP explainer: {e}")

def prepare_feature_dataframe(features: Dict[str, Any]) -> pd.DataFrame:
    """
    Constructs a single-row DataFrame aligned with training columns.
    """
    row = {
        "rainfall_1h": float(features.get("rainfall_1h", 0.0)),
        "rainfall_24h": float(features.get("rainfall_24h", 0.0)),
        "rainfall_7d_cumulative": float(features.get("rainfall_7d_cumulative", 0.0)),
        "rainfall_intensity": float(features.get("rainfall_intensity", 0.0)),
        "slope": float(features.get("slope", 20.0)),
        "elevation": float(features.get("elevation", 500.0)),
        "distance_road": float(features.get("distance_road", 200.0)),
        "distance_river": float(features.get("distance_river", 500.0)),
        "historical_landslides": int(features.get("historical_landslides", 0)),
        "snow_cover_pct": float(features.get("snow_cover_pct", 0.0)),
        "snowmelt_rate": float(features.get("snowmelt_rate", 0.0)),
        "bare_soil_pct": float(features.get("bare_soil_pct", 15.0)),
        "vegetation_index": float(features.get("vegetation_index", 0.65)),
        "latitude": float(features.get("latitude", 26.0)),
        "longitude": float(features.get("longitude", 92.0)),
        "soil_type": str(features.get("soil_type", "Loam")),
        "land_cover": str(features.get("land_cover", "Dense Forest")),
        "geology": str(features.get("geology", "Phyllite & Schist")),
        "aspect": str(features.get("aspect", "N")),
        "farm_change_flag": int(bool(features.get("farm_change_flag", False))),
    }
    return pd.DataFrame([row])

def predict_risk(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes inference pipeline and computes SHAP feature importance breakdown.
    """
    load_ml_assets()
    if _LANDSLIDE_MODEL is None or _PREPROCESSOR is None:
        raise RuntimeError("ML model or preprocessor not loaded.")

    df_in = prepare_feature_dataframe(features)
    X_proc = _PREPROCESSOR.transform(df_in)

    # Landslide prediction
    prob_landslide = float(_LANDSLIDE_MODEL.predict_proba(X_proc)[0, 1])
    prob_landslide = round(min(0.98, max(0.02, prob_landslide)), 4)

    risk_category = "High" if prob_landslide >= 0.70 else ("Moderate" if prob_landslide >= 0.30 else "Low")

    # Flood prediction
    prob_flood = 0.0
    if _FLOOD_MODEL is not None:
        try:
            prob_flood = float(_FLOOD_MODEL.predict_proba(X_proc)[0, 1])
            prob_flood = round(min(0.98, max(0.01, prob_flood)), 4)
        except Exception:
            prob_flood = 0.15
    flood_category = "High" if prob_flood >= 0.65 else ("Moderate" if prob_flood >= 0.30 else "Low")

    # SHAP feature attributions
    shap_factors = {}
    top_factors_summary = {}

    if _SHAP_EXPLAINER is not None and _METADATA is not None:
        try:
            shap_values = _SHAP_EXPLAINER.shap_values(X_proc)
            if isinstance(shap_values, list):
                shap_arr = shap_values[1][0]
            elif len(shap_values.shape) == 2:
                shap_arr = shap_values[0]
            else:
                shap_arr = shap_values[0]

            feat_names = _METADATA.get("transformed_feature_names", [])
            for f_name, s_val in zip(feat_names, shap_arr):
                # Clean up one-hot encoded naming for display
                clean_name = f_name.replace("cat__", "").replace("num__", "").replace("bool__", "")
                shap_factors[clean_name] = round(float(s_val), 4)

            # Sort top positive drivers
            sorted_shap = sorted(shap_factors.items(), key=lambda x: abs(x[1]), reverse=True)
            top_factors_summary = {k: v for k, v in sorted_shap[:6]}
        except Exception as e:
            print(f"SHAP computation warning: {e}")

    # Calculate normalized key factor percentage bars matching UI specs
    rain_24h = features.get("rainfall_24h", 45.0)
    slope = features.get("slope", 25.0)
    bare_soil = features.get("bare_soil_pct", 20.0)
    farm_flag = features.get("farm_change_flag", False)
    hist = features.get("historical_landslides", 1)

    key_factors_pct = {
        "heavy_rainfall": min(98, max(10, int((rain_24h / 150.0) * 85 + (prob_landslide * 15)))),
        "steep_slope": min(96, max(12, int((slope / 48.0) * 82 + (prob_landslide * 14)))),
        "land_cover_change": min(92, max(8, int((bare_soil / 65.0) * 60 + (30 if farm_flag else 0)))),
        "historical_landslide": min(95, max(5, int((hist / 10.0) * 80 + 10)))
    }

    return {
        "risk_probability": prob_landslide,
        "risk_category": risk_category,
        "flood_risk_probability": prob_flood,
        "flood_risk_category": flood_category,
        "key_risk_factors": key_factors_pct,
        "top_factors": top_factors_summary,
        "shap_values": shap_factors,
        "model_version": "LANDSAFE-XGBoost-v1.0"
    }

def simulate_scenario(base_features: Dict[str, Any], sim_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs 'What-If' scenario simulation.
    Adjusts rainfall delta, slope, snowmelt rate, bare soil %, and re-evaluates risk.
    """
    sim_features = dict(base_features)

    # Apply rainfall delta
    rain_delta = sim_params.get("rainfall_24h_delta", 0.0)
    sim_features["rainfall_24h"] = max(0.0, float(sim_features.get("rainfall_24h", 0.0)) + rain_delta)
    sim_features["rainfall_7d_cumulative"] = max(0.0, float(sim_features.get("rainfall_7d_cumulative", 0.0)) + rain_delta)
    sim_features["rainfall_1h"] = max(0.0, float(sim_features.get("rainfall_1h", 0.0)) + (rain_delta * 0.15))
    sim_features["rainfall_intensity"] = sim_features["rainfall_1h"]

    # Overrides
    if sim_params.get("slope_override") is not None:
        sim_features["slope"] = float(sim_params["slope_override"])
    if sim_params.get("snowmelt_rate_override") is not None:
        sim_features["snowmelt_rate"] = float(sim_params["snowmelt_rate_override"])
    if sim_params.get("bare_soil_pct_override") is not None:
        sim_features["bare_soil_pct"] = float(sim_params["bare_soil_pct_override"])
    if sim_params.get("farm_change_flag_override") is not None:
        sim_features["farm_change_flag"] = bool(sim_params["farm_change_flag_override"])

    original_res = predict_risk(base_features)
    simulated_res = predict_risk(sim_features)

    delta_risk = round(simulated_res["risk_probability"] - original_res["risk_probability"], 4)

    return {
        "original_risk_probability": original_res["risk_probability"],
        "simulated_risk_probability": simulated_res["risk_probability"],
        "original_risk_category": original_res["risk_category"],
        "simulated_risk_category": simulated_res["risk_category"],
        "delta_risk": delta_risk,
        "simulated_flood_probability": simulated_res["flood_risk_probability"],
        "simulated_flood_category": simulated_res["flood_risk_category"],
        "simulated_key_factors": simulated_res["key_risk_factors"],
        "factor_changes": {
            "rainfall_24h": {"original": base_features.get("rainfall_24h"), "simulated": sim_features["rainfall_24h"]},
            "slope": {"original": base_features.get("slope"), "simulated": sim_features["slope"]},
            "snowmelt_rate": {"original": base_features.get("snowmelt_rate"), "simulated": sim_features["snowmelt_rate"]},
            "bare_soil_pct": {"original": base_features.get("bare_soil_pct"), "simulated": sim_features["bare_soil_pct"]},
        }
    }

def get_model_info():
    load_ml_assets()
    return _METADATA or {
        "model_name": "LANDSAFE-NER XGBoost Ensemble",
        "description": "Multi-hazard landslide & flood susceptibility model with satellite terrain feature intelligence."
    }
