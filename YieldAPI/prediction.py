"""
prediction.py

Loads best_model.joblib (produced by linear_regression/multivariate.ipynb) and exposes
predict_yield(). The artifact is a single dict containing:
  - model             : fitted sklearn regressor (Random Forest, chosen as best)
  - scaler            : StandardScaler fit on the 4 numeric training columns
  - feature_columns   : full ordered list of 115 columns the model expects
                         (4 numeric + 101 one-hot Area_* + 10 one-hot Item_*)
  - numeric_columns    : the 4 numeric column names, in scaler order
  - areas / items      : the exact allowed values for Area / Item (used for validation)
  - model_name, test_mse, target_units : metadata
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
ARTIFACT_PATH = BASE_DIR / "best_model.joblib"

# Realistic bounds for the numeric inputs (Task 2, item 6).
FEATURE_RANGES = {
    "year": (1960, 2035),
    "average_rain_fall_mm_per_year": (0, 4000),
    "pesticides_tonnes": (0, 400000),
    "avg_temp": (-10, 40),
}


def _load_artifact():
    return joblib.load(ARTIFACT_PATH)


# Load once at import time purely to expose the allowed Area/Item lists to the
# API layer (schemas.py, main.py) without re-reading the 20MB file just for that.
_artifact_for_metadata = _load_artifact()
ALLOWED_AREAS = _artifact_for_metadata["areas"]
ALLOWED_ITEMS = _artifact_for_metadata["items"]
MODEL_NAME = _artifact_for_metadata["model_name"]
TEST_MSE = _artifact_for_metadata["test_mse"]
TARGET_UNITS = _artifact_for_metadata["target_units"]
del _artifact_for_metadata


def predict_yield(area: str, item: str, year: int,
                   average_rain_fall_mm_per_year: float,
                   pesticides_tonnes: float, avg_temp: float) -> dict:
    """Predict crop yield (tonnes/ha) from raw field/region inputs.

    Reloads the artifact from disk on every call so a /retrain update is
    picked up immediately, not just at process startup.
    """
    for name, value in [
        ("year", year),
        ("average_rain_fall_mm_per_year", average_rain_fall_mm_per_year),
        ("pesticides_tonnes", pesticides_tonnes),
        ("avg_temp", avg_temp),
    ]:
        lo, hi = FEATURE_RANGES[name]
        if not (lo <= value <= hi):
            raise ValueError(f"{name}={value} is out of the realistic range [{lo}, {hi}]")

    art = _load_artifact()
    model = art["model"]
    scaler = art["scaler"]
    feat_cols = art["feature_columns"]
    num_cols = art["numeric_columns"]

    if area not in art["areas"]:
        raise ValueError(f"Unknown area '{area}'. Must be one of the {len(art['areas'])} "
                          f"supported countries (see GET /metadata).")
    if item not in art["items"]:
        raise ValueError(f"Unknown item '{item}'. Must be one of: {art['items']}")

    row = pd.DataFrame(np.zeros((1, len(feat_cols))), columns=feat_cols)
    row.loc[0, "Year"] = year
    row.loc[0, "average_rain_fall_mm_per_year"] = average_rain_fall_mm_per_year
    row.loc[0, "pesticides_tonnes"] = pesticides_tonnes
    row.loc[0, "avg_temp"] = avg_temp
    row.loc[0, f"Area_{area}"] = 1
    row.loc[0, f"Item_{item}"] = 1

    row[num_cols] = scaler.transform(row[num_cols])

    prediction = float(model.predict(row.values)[0])
    return {
        "predicted_yield_tonnes_per_ha": prediction,
        "model_used": art["model_name"],
    }


if __name__ == "__main__":
    demo = predict_yield(
        area="Rwanda", item="Maize", year=2013,
        average_rain_fall_mm_per_year=1200, pesticides_tonnes=50, avg_temp=19.5,
    )
    print(demo)
