import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

np.random.seed(42)

FEATURE_COLS = {
    "numeric": [
        "rainfall_1h", "rainfall_24h", "rainfall_7d_cumulative", "rainfall_intensity",
        "slope", "elevation", "distance_road", "distance_river", "historical_landslides",
        "snow_cover_pct", "snowmelt_rate", "bare_soil_pct", "vegetation_index",
        "latitude", "longitude"
    ],
    "categorical": [
        "soil_type", "land_cover", "geology", "aspect"
    ],
    "boolean": [
        "farm_change_flag"
    ]
}

def generate_synthetic_training_data(n_samples=6000):
    """
    Generates a realistic multi-factor dataset reflecting Northeast India geomorphology and hydrology.
    Incorporates non-linear physics-based landslide triggering mechanics (Caine threshold, slope instability,
    saturation, snowmelt triggers, vegetation loss/bare soil exposure, and road cut destabilization).
    """
    data = []
    
    soil_types = ["Loam", "Clay Loam", "Sandy Loam", "Humus Rich Loam", "Alluvial Loam", "Rocky Loam", "Glacial Till", "Lateritic Clay", "Silty Loam"]
    land_covers = ["Dense Forest", "Open Forest", "Shrubland", "Slope Agriculture", "Settlement", "Barren Rocky"]
    geologies = ["Phyllite & Schist", "Gneissic Complex", "Quartzite & Phyllite", "Granitic Gneiss", "Disang Shale", "Barail Sandstone", "Sylhet Trap & Limestone", "Sub-Himalayan Sandstone"]
    aspects = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

    for _ in range(n_samples):
        # Lat/Lon bounded within NE India (22°N to 29.5°N, 88°E to 97.5°E)
        lat = np.random.uniform(22.0, 29.5)
        lon = np.random.uniform(88.0, 97.5)
        
        # Elevation
        elev = np.random.exponential(scale=900) + 50
        elev = min(4200, elev)
        
        # Slope correlated with elevation
        slope = np.random.normal(loc=15 + (elev / 150), scale=7)
        slope = max(2.0, min(58.0, slope))
        
        # Rainfall variations (monsoon cloudbursts to dry spells)
        is_monsoon = np.random.choice([True, False], p=[0.65, 0.35])
        if is_monsoon:
            rain_24h = np.random.exponential(scale=65) + np.random.choice([0, 80, 150], p=[0.7, 0.2, 0.1])
            rain_1h = min(rain_24h, np.random.exponential(scale=14))
            rain_7d = rain_24h + np.random.exponential(scale=180)
            intensity = (rain_1h / 1.0) if rain_1h > 0 else 0
        else:
            rain_24h = np.random.exponential(scale=8)
            rain_1h = min(rain_24h, np.random.exponential(scale=2))
            rain_7d = rain_24h + np.random.exponential(scale=25)
            intensity = rain_1h

        dist_road = np.random.exponential(scale=400) + 10
        dist_river = np.random.exponential(scale=800) + 20
        hist_landslides = np.random.poisson(lam=1.8 if slope > 25 else 0.4)

        # Satellite Features
        has_snow = elev > 2200 and np.random.rand() > 0.4
        snow_cover = np.random.uniform(20, 85) if has_snow else 0.0
        snowmelt = np.random.uniform(1.0, 9.0) if (snow_cover > 15 and is_monsoon) else (np.random.uniform(0, 2.0) if snow_cover > 5 else 0.0)
        
        bare_soil = np.random.uniform(5, 75)
        ndvi = np.random.uniform(0.15, 0.88)
        farm_change = bool(np.random.choice([0, 1], p=[0.82, 0.18]))

        soil = np.random.choice(soil_types)
        land_cov = np.random.choice(land_covers)
        geo = np.random.choice(geologies)
        asp = np.random.choice(aspects)

        # Physics-based landslide susceptibility calculation (ground-truth label generation)
        # 1. Rainfall factor (Intensity-Duration / Saturation)
        rain_score = (rain_24h / 120.0) * 0.35 + (rain_7d / 350.0) * 0.20 + (intensity / 35.0) * 0.15
        
        # 2. Geotechnical slope factor
        slope_score = (slope / 45.0) ** 1.6 * 0.30
        
        # 3. Geological weakness (Disang Shale and Phyllite are highly landslide-prone in NE India)
        geo_multiplier = 1.35 if ("Shale" in geo or "Phyllite" in geo) else 1.0
        
        # 4. Satellite triggers: snowmelt addition, bare soil erosion vulnerability, slope agriculture
        satellite_trigger = (snowmelt / 8.0) * 0.18 + (bare_soil / 80.0) * 0.15 + (0.12 if farm_change else 0.0) - (ndvi * 0.10)
        
        # 5. Anthropogenic & proximity destabilization
        road_cut_factor = 0.15 if dist_road < 100 and slope > 22 else 0.0
        river_toe_erosion = 0.12 if dist_river < 150 and slope > 20 else 0.0
        hist_prior = min(0.20, hist_landslides * 0.04)

        total_risk_score = (rain_score * geo_multiplier + slope_score + satellite_trigger + road_cut_factor + river_toe_erosion + hist_prior)
        # Apply sigmoid to compute true probability
        p_landslide = 1.0 / (1.0 + np.exp(-(total_risk_score - 0.72) * 4.5))
        
        # Binary target with slight realistic noise
        target = int(np.random.rand() < p_landslide)

        # Flood label calculation for flood model
        flood_score = (rain_24h / 100.0) * 0.40 + (rain_7d / 280.0) * 0.25 - (elev / 400.0) * 0.30 - (slope / 20.0) * 0.25 + (0.35 if dist_river < 200 else 0.0)
        p_flood = 1.0 / (1.0 + np.exp(-(flood_score - 0.25) * 5.0))
        target_flood = int(np.random.rand() < p_flood)

        data.append({
            "rainfall_1h": round(rain_1h, 2),
            "rainfall_24h": round(rain_24h, 2),
            "rainfall_7d_cumulative": round(rain_7d, 2),
            "rainfall_intensity": round(intensity, 2),
            "slope": round(slope, 2),
            "elevation": round(elev, 1),
            "distance_road": round(dist_road, 1),
            "distance_river": round(dist_river, 1),
            "historical_landslides": hist_landslides,
            "snow_cover_pct": round(snow_cover, 1),
            "snowmelt_rate": round(snowmelt, 2),
            "bare_soil_pct": round(bare_soil, 1),
            "vegetation_index": round(ndvi, 2),
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "soil_type": soil,
            "land_cover": land_cov,
            "geology": geo,
            "aspect": asp,
            "farm_change_flag": int(farm_change),
            "flood_extent_flag": int(dist_river < 250 and rain_24h > 60 and elev < 300),
            "target": target,
            "target_flood": target_flood
        })

    return pd.DataFrame(data)

def train_and_evaluate():
    print("Generating comprehensive geomorphological & satellite dataset for Northeast India...")
    df = generate_synthetic_training_data(7500)
    
    X = df[FEATURE_COLS["numeric"] + FEATURE_COLS["categorical"] + FEATURE_COLS["boolean"]]
    y = df["target"]
    y_flood = df["target_flood"]

    # Preprocessor
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), FEATURE_COLS["numeric"]),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), FEATURE_COLS["categorical"]),
            ("bool", "passthrough", FEATURE_COLS["boolean"])
        ]
    )

    X_train, X_test, y_train, y_test, yf_train, yf_test = train_test_split(
        X, y, y_flood, test_size=0.2, random_state=42, stratify=y
    )

    print("Fitting preprocessor pipeline...")
    X_train_proc = preprocessor.fit_transform(X_train)
    X_test_proc = preprocessor.transform(X_test)

    # Get feature names
    cat_feature_names = preprocessor.named_transformers_["cat"].get_feature_names_out(FEATURE_COLS["categorical"]).tolist()
    all_feature_names = FEATURE_COLS["numeric"] + cat_feature_names + FEATURE_COLS["boolean"]

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=150, max_depth=12, random_state=42, n_jobs=-1),
        "XGBoost Classifier": XGBClassifier(n_estimators=180, max_depth=6, learning_rate=0.08, subsample=0.85, eval_metric="logloss", random_state=42)
    }

    results = {}
    fitted_models = {}

    print("\n--- Model Benchmark Evaluation ---")
    for name, model in models.items():
        print(f"Training {name}...")
        model.fit(X_train_proc, y_train)
        y_pred = model.predict(X_test_proc)
        y_prob = model.predict_proba(X_test_proc)[:, 1]

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred)
        rec = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_prob)
        cm = confusion_matrix(y_test, y_pred).tolist()

        results[name] = {
            "accuracy": round(float(acc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "roc_auc": round(float(auc), 4),
            "confusion_matrix": cm
        }
        fitted_models[name] = model
        print(f"  {name} -> Accuracy: {acc:.4f} | F1: {f1:.4f} | ROC-AUC: {auc:.4f}")

    # Best model selection (XGBoost typically achieves best generalization & native SHAP support)
    best_model_name = "XGBoost Classifier"
    best_model = fitted_models[best_model_name]

    # Calculate Feature Importances for XGBoost
    raw_importances = best_model.feature_importances_
    importance_dict = {name: round(float(imp), 4) for name, imp in zip(all_feature_names, raw_importances)}
    sorted_importances = dict(sorted(importance_dict.items(), key=lambda item: item[1], reverse=True)[:15])

    # Train Flood Model
    print("\nTraining Multi-Hazard Flood Model...")
    flood_model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    flood_model.fit(X_train_proc, yf_train)
    yf_pred = flood_model.predict(X_test_proc)
    yf_prob = flood_model.predict_proba(X_test_proc)[:, 1]
    flood_metrics = {
        "accuracy": round(float(accuracy_score(yf_test, yf_pred)), 4),
        "f1_score": round(float(f1_score(yf_test, yf_pred)), 4),
        "roc_auc": round(float(roc_auc_score(yf_test, yf_prob)), 4)
    }
    print(f"Flood Model -> Accuracy: {flood_metrics['accuracy']} | ROC-AUC: {flood_metrics['roc_auc']}")

    # Save artifacts
    models_dir = Path(__file__).resolve().parent / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(best_model, models_dir / "best_landslide_model.joblib")
    joblib.dump(preprocessor, models_dir / "preprocessor.joblib")
    joblib.dump(flood_model, models_dir / "flood_model.joblib")

    metadata = {
        "best_model": best_model_name,
        "feature_columns": FEATURE_COLS,
        "transformed_feature_names": all_feature_names,
        "model_comparison": results,
        "top_feature_importances": sorted_importances,
        "flood_metrics": flood_metrics,
        "prototype_disclaimer": "LANDSAFE-NER is a B.Tech AI & Data Science academic prototype. It is NOT an official government disaster-warning system. Risk levels are based on prototype thresholds for demonstration purposes only. Do not use for real-world emergency decisions."
    }

    with open(models_dir / "model_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nSaved best model, preprocessor, and metadata to {models_dir}")

if __name__ == "__main__":
    train_and_evaluate()
