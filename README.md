# Crop Yield Predictor

## Mission

Farmers and agricultural planners need reliable yield forecasts before planting season to guide
fertilizer, insurance, and export decisions. This project predicts crop yield (tonnes/hectare)
from a country, a crop, and three agroclimatic inputs — rainfall, pesticide use, and average
temperature — trained on a 28,242-row FAO/World Bank dataset covering 101 countries and 10 crops.

## API Endpoint

- **Base URL:** `https://yield-predictor-mfca.onrender.com/` 
- **Swagger UI (for testing):** `https://yield-predictor-mfca.onrender.com/docs`
- **Example request** — `POST /predict`:
  ```json
  {
    "area": "Algeria",
    "item": "Maize",
    "year": 2013,
    "average_rain_fall_mm_per_year": 600,
    "pesticides_tonnes": 200,
    "avg_temp": 22
  }
  ```
  → `{"predicted_yield_tonnes_per_ha": 1.7964, "model_used": "Random Forest"}`

> Note: the Render free tier spins down after ~15 minutes of inactivity — the first request after
> idling can take 30–60 seconds to respond while it cold-starts.

## Video Demo

🎥 **[Watch the demo](<https://drive.google.com/drive/folders/14G7jXEIv9BoFxZr5TsyX-CFz4gSd2uIS?usp=sharing>)** (≤ 7 minutes)

## Running the Mobile App

```bash
cd YieldAPI/../ 
flutter pub get
flutter run
```

Before running, open `lib/main.dart` and confirm `apiBaseUrl` points at the deployed API above
(not `10.0.2.2` or `localhost`):

```dart
const String apiBaseUrl = "https://yield-predictor-mfca.onrender.com/";
```

The app fetches `GET /metadata` on launch to populate the Country and Crop dropdowns, then lets
you enter Year, Rainfall, Pesticides, and Average Temperature, and shows the predicted yield (or a
validation error) after tapping **Predict**.
