import logging
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ..data.collector import (
    CapacityDataCollector,
    LoadDataCollector,
    SolarGenerationCollector,
    WeatherCollector,
)
from ..data.processor import DataPipeline
from ..models.model_registry import ModelRegistry
from .risk_engine import RiskEngine

logger = logging.getLogger("Forecaster")


class DemandForecaster:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.pipeline = DataPipeline()
        self.registry = ModelRegistry()
        self.risk_engine = RiskEngine()
        self.weather_collector = WeatherCollector()
        self.load_collector = LoadDataCollector()
        self.solar_collector = SolarGenerationCollector()
        self.capacity_collector = CapacityDataCollector()
        self.prepared_df = None
        self.feature_cols = []
        self.X_train = self.y_train = self.X_val = self.y_val = self.X_test = self.y_test = None
        self.df_train = self.df_val = self.df_test = None
        self.lat = self.config.get("lat", 28.6139)
        self.lon = self.config.get("lon", 77.2090)
        self.models_dir = self.config.get("models_dir", "data/models")

    def load_data(self, load_filepath: str, weather_config: dict = None,
                  solar_config: dict = None, capacity_filepath: str = None):
        logger.info("Loading data...")
        load_df = self.load_collector.load_from_csv(load_filepath)

        if weather_config:
            self.lat = weather_config.get("lat", self.lat)
            self.lon = weather_config.get("lon", self.lon)
            start = weather_config.get("start_date",
                    (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"))
            end = weather_config.get("end_date", datetime.now().strftime("%Y-%m-%d"))
            weather_df = self.weather_collector.fetch_historical_weather(self.lat, self.lon, start, end)
        else:
            weather_df = pd.DataFrame(index=load_df.index)

        solar_df = None
        if solar_config:
            solar_df = self.solar_collector.estimate_solar_generation(
                lat=solar_config.get("lat", self.lat),
                lon=solar_config.get("lon", self.lon),
                capacity_kw=solar_config.get("capacity_kw", 1000),
                start_date=solar_config.get("start_date"),
                end_date=solar_config.get("end_date"),
            )

        if capacity_filepath:
            self.capacity_collector.load_capacity_from_csv(capacity_filepath)
            area_caps = self.capacity_collector.get_area_capacity()
            self.risk_engine.capacity_data = area_caps

        self.prepared_df = self.pipeline.prepare_training_data(load_df, weather_df, solar_df)
        logger.info(f"Prepared dataset: {self.prepared_df.shape}")
        return self.prepared_df

    def prepare_features(self, df: pd.DataFrame = None):
        df = df if df is not None else self.prepared_df
        self.feature_cols = self.pipeline.get_feature_columns(df)
        train_df, val_df, test_df = self.pipeline.split_train_val_test(df)
        self.df_train = train_df
        self.df_val = val_df
        self.df_test = test_df
        target = self.pipeline.get_target_column()
        X_tr_raw = train_df[self.feature_cols].values
        X_v_raw = val_df[self.feature_cols].values
        X_te_raw = test_df[self.feature_cols].values
        self.X_train, self.X_val, self.X_test = self.pipeline.scale_features(X_tr_raw, X_v_raw, X_te_raw)
        self.y_train = train_df[target].values
        self.y_val = val_df[target].values
        self.y_test = test_df[target].values
        logger.info(f"Features: {len(self.feature_cols)}, Train: {len(self.X_train)}, "
                    f"Val: {len(self.X_val)}, Test: {len(self.X_test)}")
        return self.X_train, self.y_train

    def train_models(self, model_list: list = None, progress_callback=None):
        self.registry.register_defaults(include=model_list)
        return self.registry.train_all(
            self.X_train, self.y_train, self.X_val, self.y_val,
            df_train=self.df_train, progress_callback=progress_callback
        )

    def evaluate_models(self):
        return self.registry.evaluate_all(self.X_test, self.y_test, df_test=self.df_test)

    def predict_next_48h(self, weather_forecast_df: pd.DataFrame = None, hours: int = 168) -> pd.DataFrame:
        if weather_forecast_df is None:
            weather_forecast_df = self.weather_collector.fetch_forecast_weather(self.lat, self.lon, hours)
        future_idx = pd.date_range(start=datetime.now().replace(minute=0, second=0, microsecond=0),
                                   periods=hours, freq="h")
        best = self.registry.get_best_model()
        if best is None:
            raise ValueError("No trained models available. Train models first.")

        from ..data.processor import FeatureEngineer
        fe = FeatureEngineer()

        last_known = self.prepared_df.tail(200).copy()
        future_weather = weather_forecast_df.reindex(future_idx, method="nearest").copy()
        future_rows = pd.DataFrame(index=future_idx)
        for col in future_weather.columns:
            future_rows[col] = future_weather[col].values

        future_rows["gross_demand_mw"] = last_known["gross_demand_mw"].mean()
        future_rows["net_demand"] = last_known["net_demand"].mean()
        if "solar_generation_mw" in last_known.columns:
            future_rows["solar_generation_mw"] = last_known["solar_generation_mw"].mean()

        combined = pd.concat([last_known, future_rows])
        combined = fe.create_time_features(combined)
        combined = fe.create_season_feature(combined)
        combined = fe.create_weather_features(combined)
        combined = fe.create_interaction_features(combined)
        combined = fe.create_cyclical_features(combined)
        combined = fe.create_lag_features(combined, "net_demand")
        combined = fe.create_rolling_features(combined, "net_demand")
        combined.replace([np.inf, -np.inf], np.nan, inplace=True)
        combined.ffill(inplace=True)
        combined.bfill(inplace=True)

        future_part = combined.loc[future_idx]
        available_features = [c for c in self.feature_cols if c in future_part.columns]
        X_future = self.pipeline.scaler.transform(future_part[available_features].values)

        preds = best.predict(X_future)

        try:
            ensemble = self.registry.ensemble_predict(X_future, top_n=3)
            lower = (ensemble - np.std(preds) * 1.5).clip(min=0)
            upper = ensemble + np.std(preds) * 1.5
        except Exception:
            lower = (preds * 0.92).clip(min=0)
            upper = preds * 1.08
            ensemble = preds

        result = pd.DataFrame({
            "timestamp": future_idx,
            "predicted_demand": np.round(preds, 2),
            "ensemble_prediction": np.round(ensemble, 2),
            "lower_bound": np.round(lower, 2),
            "upper_bound": np.round(upper, 2),
        }).set_index("timestamp")
        return result

    def run_risk_analysis(self, predictions: pd.DataFrame, capacity: float = None) -> dict:
        if capacity:
            self.risk_engine.capacity_data = {"system": {"available_mw": capacity}}
        alerts = self.risk_engine.analyze_system(predictions)
        summary = self.risk_engine.generate_risk_summary(alerts)
        high_risk = self.risk_engine.get_high_risk_hours(alerts)
        return {"alerts": alerts, "summary": summary, "high_risk_hours": high_risk}

    def generate_full_report(self) -> dict:
        metrics_df = self.registry.get_model_comparison_df()
        best = self.registry.get_best_model()
        best_name = best.model_name if best else "N/A"
        try:
            predictions = self.predict_next_48h()
            risk_report = self.run_risk_analysis(predictions)
        except Exception as e:
            predictions = pd.DataFrame()
            risk_report = {"error": str(e)}
        from ..data.processor import DemandCalculator
        dc = DemandCalculator()
        demand_metrics = dc.calculate_demand_metrics(self.prepared_df) if self.prepared_df is not None else {}
        return {
            "model_comparison": metrics_df.to_dict("records"),
            "best_model": best_name,
            "demand_metrics": demand_metrics,
            "predictions": predictions.reset_index().to_dict("records") if not predictions.empty else [],
            "risk_report": risk_report,
            "feature_count": len(self.feature_cols),
            "training_samples": len(self.X_train) if self.X_train is not None else 0,
        }

    def save_state(self, directory: str = "data/models"):
        self.registry.save_all(directory)
        state = {
            "feature_cols": self.feature_cols,
            "lat": self.lat,
            "lon": self.lon,
        }
        joblib.dump(state, str(Path(directory) / "forecaster_state.pkl"))
        joblib.dump(self.pipeline.scaler, str(Path(directory) / "scaler.pkl"))
        logger.info(f"State saved to {directory}")

    def load_state(self, directory: str = "data/models"):
        self.registry.load_all(directory)
        state_path = Path(directory) / "forecaster_state.pkl"
        if state_path.exists():
            state = joblib.load(str(state_path))
            self.feature_cols = state.get("feature_cols", [])
            self.lat = state.get("lat", self.lat)
            self.lon = state.get("lon", self.lon)
        scaler_path = Path(directory) / "scaler.pkl"
        if scaler_path.exists():
            self.pipeline.scaler = joblib.load(str(scaler_path))
        logger.info(f"State loaded from {directory}")
