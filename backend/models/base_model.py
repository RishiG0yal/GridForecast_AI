import logging
from abc import ABC, abstractmethod
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


class BaseDemandModel(ABC):
    def __init__(self, model_name: str, config: dict = None):
        self.model_name = model_name
        self.config = config or {}
        self.model = None
        self.is_trained = False
        self.feature_columns = []
        self.target_column = "net_demand"
        self.metrics = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def train(self, X_train, y_train, X_val=None, y_val=None):
        ...

    @abstractmethod
    def predict(self, X) -> np.ndarray:
        ...

    def evaluate(self, X_test, y_test) -> dict:
        y_pred = self.predict(X_test)
        y_test = np.array(y_test)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        mape = float(np.mean(np.abs((y_test - y_pred) / (np.abs(y_test) + 1e-8))) * 100)
        r2 = float(r2_score(y_test, y_pred))
        self.metrics = {
            "model": self.model_name,
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "mape": round(mape, 4),
            "r2": round(r2, 4)
        }
        return self.metrics

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self.model, "config": self.config,
                     "feature_columns": self.feature_columns,
                     "metrics": self.metrics}, path)
        self.logger.info(f"Saved {self.model_name} to {path}")

    def load(self, path: str):
        data = joblib.load(path)
        self.model = data["model"]
        self.config = data.get("config", {})
        self.feature_columns = data.get("feature_columns", [])
        self.metrics = data.get("metrics", {})
        self.is_trained = True
        return self
