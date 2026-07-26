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

1. Install Flutter and confirm your setup: flutter doctor (fix any red ✗ items first).
2. Clone the repo: git clone https://github.com/k10-j/yield-predictor.git && cd yield-predictor
3. Install dependencies: flutter pub get
4. Open lib/main.dart and confirm this line points at the live API:

const String apiBaseUrl = "https://yield-predictor-mfca.onrender.com";

5. Connect a device or start an emulator, then confirm it's detected: flutter devices
6. Run the app: flutter run — select the Android device/emulator, not Chrome/web.
7. Wait a few seconds for the Country and Crop dropdowns to load (they're fetched from the API).
8. Select a Country and Crop, enter Year, Rainfall, Pesticides, and Average Temperature.
9. Tap Predict — the predicted yield appears in a green box (e.g. "Predicted Yield: 1.7964 tonnes/ha"). A red box appears instead if a field is missing or out of range.


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
