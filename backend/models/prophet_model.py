import logging
from pathlib import Path

import holidays
import joblib
import numpy as np
import pandas as pd

from .base_model import BaseDemandModel

logger = logging.getLogger("ProphetModel")


class ProphetModel(BaseDemandModel):
    def __init__(self, config: dict = None):
        cfg = {
            "changepoint_prior_scale": 0.05,
            "seasonality_prior_scale": 10.0,
            "holidays_prior_scale": 10.0,
            "daily_seasonality": True,
            "weekly_seasonality": True,
            "yearly_seasonality": True,
        }
        if config:
            cfg.update(config)
        super().__init__("Prophet", cfg)
        self._regressors = []

    def _make_holiday_df(self) -> pd.DataFrame:
        india_holidays = holidays.India(years=range(2020, 2028))
        rows = []
        for date, name in india_holidays.items():
            rows.append({"holiday": name[:50], "ds": pd.Timestamp(date),
                         "lower_window": 0, "upper_window": 1})
        return pd.DataFrame(rows)

    def train(self, df: pd.DataFrame, regressor_cols: list = None, X_val=None, y_val=None):
        from prophet import Prophet
        prophet_df = df.copy().reset_index()
        datetime_col = [c for c in prophet_df.columns if "datetime" in c.lower() or c == "index"]
        if datetime_col:
            prophet_df.rename(columns={datetime_col[0]: "ds"}, inplace=True)
        else:
            prophet_df["ds"] = pd.to_datetime(prophet_df.iloc[:, 0])
        if "net_demand" in prophet_df.columns:
            prophet_df["y"] = prophet_df["net_demand"]
        elif "gross_demand_mw" in prophet_df.columns:
            prophet_df["y"] = prophet_df["gross_demand_mw"]
        prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])

        holiday_df = self._make_holiday_df()
        m = Prophet(
            holidays=holiday_df,
            changepoint_prior_scale=self.config["changepoint_prior_scale"],
            seasonality_prior_scale=self.config["seasonality_prior_scale"],
            holidays_prior_scale=self.config["holidays_prior_scale"],
            daily_seasonality=self.config["daily_seasonality"],
            weekly_seasonality=self.config["weekly_seasonality"],
            yearly_seasonality=self.config["yearly_seasonality"],
        )
        available_regressors = []
        if regressor_cols:
            for col in regressor_cols:
                if col in prophet_df.columns and not prophet_df[col].isna().all():
                    m.add_regressor(col)
                    available_regressors.append(col)
        else:
            for col in ["temperature", "humidity", "cloud_cover", "is_weekend", "is_holiday"]:
                if col in prophet_df.columns and not prophet_df[col].isna().all():
                    m.add_regressor(col)
                    available_regressors.append(col)
        self._regressors = available_regressors
        prophet_df = prophet_df.ffill().bfill()
        m.fit(prophet_df[["ds", "y"] + self._regressors])
        self.model = m
        self.is_trained = True
        return self

    def predict(self, future_df: pd.DataFrame = None, periods: int = 48) -> np.ndarray:
        if future_df is None:
            future_df = self.model.make_future_dataframe(periods=periods, freq="h")
        if "ds" not in future_df.columns:
            future_df = future_df.reset_index().rename(columns={future_df.index.name or "index": "ds"})
        future_df["ds"] = pd.to_datetime(future_df["ds"])
        for reg in self._regressors:
            if reg not in future_df.columns:
                future_df[reg] = 0.0
        forecast = self.model.predict(future_df)
        return forecast["yhat"].clip(lower=0).values

    def predict_with_intervals(self, future_df: pd.DataFrame = None, periods: int = 48) -> pd.DataFrame:
        if future_df is None:
            future_df = self.model.make_future_dataframe(periods=periods, freq="h")
        if "ds" not in future_df.columns:
            future_df = future_df.reset_index().rename(columns={future_df.index.name or "index": "ds"})
        future_df["ds"] = pd.to_datetime(future_df["ds"])
        for reg in self._regressors:
            if reg not in future_df.columns:
                future_df[reg] = 0.0
        forecast = self.model.predict(future_df)
        result = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
        result["yhat"] = result["yhat"].clip(lower=0)
        result["yhat_lower"] = result["yhat_lower"].clip(lower=0)
        return result

    def evaluate(self, X_test, y_test) -> dict:
        import numpy as np
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        y_pred = self.predict(X_test)[-len(y_test):]
        y_t = np.array(y_test)
        mae = mean_absolute_error(y_t, y_pred)
        rmse = float(np.sqrt(mean_squared_error(y_t, y_pred)))
        mape = float(np.mean(np.abs((y_t - y_pred) / (np.abs(y_t) + 1e-8))) * 100)
        r2 = float(r2_score(y_t, y_pred))
        self.metrics = {"model": self.model_name, "mae": round(mae, 4),
                        "rmse": round(rmse, 4), "mape": round(mape, 4), "r2": round(r2, 4)}
        return self.metrics

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self.model, "regressors": self._regressors,
                     "config": self.config, "metrics": self.metrics,
                     "feature_columns": self.feature_columns}, path)

    def load(self, path: str):
        data = joblib.load(path)
        self.model = data["model"]
        self._regressors = data.get("regressors", [])
        self.config = data.get("config", {})
        self.metrics = data.get("metrics", {})
        self.feature_columns = data.get("feature_columns", [])
        self.is_trained = True
        return self
