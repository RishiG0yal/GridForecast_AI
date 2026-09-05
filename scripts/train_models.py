import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from backend.engine.forecaster import DemandForecaster

print("Initializing forecaster...")
forecaster = DemandForecaster()

print("Loading data...")
weather_config = {
    "lat": 28.6139, "lon": 77.2090,
    "start_date": (datetime.now() - timedelta(days=367)).strftime("%Y-%m-%d"),
    "end_date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
}

load_path = "data/raw/sample_load_data.csv"
if os.path.exists("data/raw/delhi_real_dataset.csv"):
    load_path = "data/raw/delhi_real_dataset.csv"
elif os.path.exists("data/raw/system_load_with_weather.csv"):
    load_path = "data/raw/system_load_with_weather.csv"

forecaster.load_data(load_path, weather_config=weather_config)

print("Preparing features...")
forecaster.prepare_features()

print("Training models...")
forecaster.train_models(
    model_list=["LinearRegression", "DecisionTree", "RandomForest",
                "XGBoost", "GradientBoosting", "NaiveBayes"]
)

print("Evaluating models...")
metrics = forecaster.evaluate_models()
print(metrics)

print("Saving models to data/models...")
forecaster.save_state("data/models")
print("Done!")
