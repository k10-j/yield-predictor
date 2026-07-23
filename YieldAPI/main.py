"""
main.py - Crop Yield Predictor API (Task 2), rebuilt for the Area/Item model.

Endpoints:
  GET  /            -> health check
  GET  /metadata     -> supported countries, crops, numeric ranges, current model info
  POST /predict       -> predict yield from Area/Item + agroclimatic numbers
  POST /retrain         -> append new labelled records and fully retrain

Run locally:
  uvicorn main:app --reload --port 8000
Docs:
  http://localhost:8000/docs
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

import prediction
from prediction import predict_yield, ALLOWED_AREAS, ALLOWED_ITEMS, FEATURE_RANGES, ARTIFACT_PATH
from schemas import (
    CropFeatures, PredictionResponse, MetadataResponse,
    RetrainRequest, RetrainResponse,
)

BASE_DIR = Path(__file__).resolve().parent
RAW_DATA_PATH = BASE_DIR / "yield_df.csv"

app = FastAPI(
    title="Crop Yield Predictor API",
    description="Predicts crop yield (tonnes/ha) from country, crop, year, rainfall, "
                 "pesticide use, and temperature.",
    version="2.0.0",
)

# --------------------------------------------------------------------------
# CORS - explicitly scoped, no wildcard.
# --------------------------------------------------------------------------
ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
    "http://127.0.0.1",
    "http://127.0.0.1:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Crop Yield Predictor API is running"}


@app.get("/metadata", response_model=MetadataResponse)
def metadata():
    """Everything a client (the Flutter app) needs to build its input form:
    the exact list of supported countries/crops and numeric ranges."""
    return MetadataResponse(
        areas=ALLOWED_AREAS,
        items=ALLOWED_ITEMS,
        ranges={k: {"min": v[0], "max": v[1]} for k, v in FEATURE_RANGES.items()},
        model_used=prediction.MODEL_NAME,
        test_mse=prediction.TEST_MSE,
        target_units=prediction.TARGET_UNITS,
    )


@app.post("/predict", response_model=PredictionResponse)
def predict(features: CropFeatures):
    """Pydantic already enforces types, numeric ranges, and Area/Item membership
    (schemas.py) before this function runs; any bad request gets a 422."""
    try:
        result = predict_yield(
            area=features.area,
            item=features.item,
            year=features.year,
            average_rain_fall_mm_per_year=features.average_rain_fall_mm_per_year,
            pesticides_tonnes=features.pesticides_tonnes,
            avg_temp=features.avg_temp,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return PredictionResponse(
        predicted_yield_tonnes_per_ha=round(result["predicted_yield_tonnes_per_ha"], 4),
        model_used=result["model_used"],
    )


@app.post("/retrain", response_model=RetrainResponse)
def retrain(payload: RetrainRequest):
    """Append newly-labelled records to the training set and fully retrain
    (refits the one-hot columns, the scaler, and a fresh Random Forest) so
    the update is triggered when new season data is uploaded or streamed in.

    Note: records must use Area/Item values already known to the model (see
    GET /metadata) - adding a brand-new country/crop requires re-running the
    notebook, since that changes the one-hot column layout itself.
    """
    if not payload.records:
        raise HTTPException(status_code=400, detail="No records supplied")

    art = joblib.load(ARTIFACT_PATH)
    old_model = art["model"]
    old_scaler = art["scaler"]
    feat_cols = art["feature_columns"]
    num_cols = art["numeric_columns"]

    df = pd.read_csv(RAW_DATA_PATH)
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])
    df["yield_tonnes_per_ha"] = df["hg/ha_yield"] / 10_000
    df = df.drop(columns=["hg/ha_yield"])

    new_rows = [{
        "Area": r.area, "Item": r.item, "Year": r.year,
        "average_rain_fall_mm_per_year": r.average_rain_fall_mm_per_year,
        "pesticides_tonnes": r.pesticides_tonnes, "avg_temp": r.avg_temp,
        "yield_tonnes_per_ha": r.yield_tonnes_per_ha,
    } for r in payload.records]
    new_df = pd.DataFrame(new_rows)
    full_df = pd.concat([df, new_df], ignore_index=True)

    y = full_df["yield_tonnes_per_ha"].copy()
    X_num = full_df[num_cols].copy()
    X_cat = pd.get_dummies(full_df[["Area", "Item"]], drop_first=False).astype(int)
    X = pd.concat([X_num, X_cat], axis=1)
    # keep exactly the original column order/set (guards against a stray new category)
    X = X.reindex(columns=feat_cols, fill_value=0)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # baseline: current model on the new test split
    X_test_old = X_test.copy()
    X_test_old[num_cols] = old_scaler.transform(X_test_old[num_cols])
    test_mse_before = mean_squared_error(y_test, old_model.predict(X_test_old.values))

    new_scaler = StandardScaler()
    X_train_scaled = X_train.copy()
    X_test_scaled = X_test.copy()
    X_train_scaled[num_cols] = new_scaler.fit_transform(X_train[num_cols])
    X_test_scaled[num_cols] = new_scaler.transform(X_test[num_cols])

    new_model = RandomForestRegressor(
        n_estimators=100, min_samples_leaf=2, random_state=42, n_jobs=-1,
    )
    new_model.fit(X_train_scaled.values, y_train.values)
    test_mse_after = mean_squared_error(y_test, new_model.predict(X_test_scaled.values))

    full_df.to_csv(RAW_DATA_PATH.parent / "yield_df_retrained.csv", index=False)
    art.update({
        "model": new_model,
        "scaler": new_scaler,
        "test_mse": float(test_mse_after),
    })
    joblib.dump(art, ARTIFACT_PATH, compress=3)

    return RetrainResponse(
        message="Model retrained on combined dataset",
        n_new_records=len(new_rows),
        n_total_records=len(full_df),
        test_mse_before=round(float(test_mse_before), 4),
        test_mse_after=round(float(test_mse_after), 4),
    )
