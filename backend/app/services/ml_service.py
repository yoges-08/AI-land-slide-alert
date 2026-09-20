"""Model inference and SHAP attribution.

M0, confirmed defect 6: the shipped model was trained on synthetic data whose
labels were computed from a hand-weighted sigmoid of the same features
(train_models.py). Its outputs are not probabilities of anything observable, so
every "probability"/"confidence %" word is removed here and the output is named
what it is: an uncalibrated hazard index.

The SHAP explainer wiring and the main.py startup hook are real, working
infrastructure and are kept untouched. Only the meaning of the number changed.
M6 either retrains on real labelled events with time-based splits, or replaces
this with a susceptibility x trigger index.
"""
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
    # NOT a probability: the model learned to invert a formula, and the output
    # was additionally clamped to [0.02, 0.98] at baseline. Reported as an
    # uncalibrated index on [0,1].
    landslide_index = float(_LANDSLIDE_MODEL.predict_proba(X_proc)[0, 1])
    landslide_index = round(min(0.98, max(0.02, landslide_index)), 4)

    risk_category = "High" if landslide_index >= 0.70 else ("Moderate" if landslide_index >= 0.30 else "Low")

    # Flood prediction
    flood_index = None
    if _FLOOD_MODEL is not None:
        try:
            flood_index = float(_FLOOD_MODEL.predict_proba(X_proc)[0, 1])
            flood_index = round(min(0.98, max(0.01, flood_index)), 4)
        except Exception as exc:
            # Baseline substituted 0.15 here. A failed inference is not a result.
            print(f"Flood model inference failed: {exc}")
            flood_index = None
    flood_category = (None if flood_index is None else
                      ("High" if flood_index >= 0.65 else
                       ("Moderate" if flood_index >= 0.30 else "Low")))

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
    # Key-factor bars are display normalisations of the inputs actually supplied.
    # A factor whose input is absent is None, not a default-derived number.
    def _bar(value, scale, floor=0, cap=100):
        if value is None:
            return None
        return min(cap, max(floor, int((float(value) / scale) * 100)))

    key_factors_pct = {
        "heavy_rainfall": _bar(features.get("rainfall_24h"), 150.0),
        "steep_slope": _bar(features.get("slope"), 48.0),
        "land_cover_change": _bar(features.get("bare_soil_pct"), 65.0),
        "historical_landslide": _bar(features.get("historical_landslides"), 10.0),
    }

    return {
        "hazard_index": landslide_index,
        "risk_category": risk_category,
        "flood_index": flood_index,
        "flood_risk_category": flood_category,
        "key_risk_factors": key_factors_pct,
        "top_factors": top_factors_summary,
        "shap_values": shap_factors,
        "model_version": "LANDSAFE-XGBoost-v1.0",
        "calibration": "UNCALIBRATED",
        "index_note": (
            "Unitless hazard index on [0,1]. NOT a probability, likelihood or "
            "confidence. The model was trained on synthetic, formula-derived "
            "labels and has never been validated against observed landslide "
            "events. Superseded in M6."
        ),
        "training_data": "SYNTHETIC — see backend/ml/train_models.py",
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

    delta_risk = round(simulated_res["hazard_index"] - original_res["hazard_index"], 4)

    return {
        "original_hazard_index": original_res["hazard_index"],
        "simulated_hazard_index": simulated_res["hazard_index"],
        "original_risk_category": original_res["risk_category"],
        "simulated_risk_category": simulated_res["risk_category"],
        "delta_index": delta_risk,
        "simulated_flood_index": simulated_res["flood_index"],
        "simulated_flood_category": simulated_res["flood_risk_category"],
        "simulated_key_factors": simulated_res["key_risk_factors"],
        "factor_changes": {
            "rainfall_24h": {"original": base_features.get("rainfall_24h"), "simulated": sim_features.get("rainfall_24h")},
            "slope": {"original": base_features.get("slope"), "simulated": sim_features.get("slope")},
            "snowmelt_rate": {"original": base_features.get("snowmelt_rate"), "simulated": sim_features.get("snowmelt_rate")},
            "bare_soil_pct": {"original": base_features.get("bare_soil_pct"), "simulated": sim_features.get("bare_soil_pct")},
        }
    }

def get_model_info():
    load_ml_assets()
    base = dict(_METADATA or {"model_name": "LANDSAFE-NER XGBoost"})
    base.update({
        "calibration": "UNCALIBRATED",
        "training_data": "SYNTHETIC — labels generated by formula, not observed events",
        "validated_against_observed_events": False,
        "output_units": "unitless hazard index on [0,1]",
        "supersedes": "M6 replaces this with either a retrain on real labelled "
                      "events (time-based splits, precision/recall by region) or "
                      "a susceptibility x trigger index.",
    })
    return base
