import logging
from pathlib import Path

import numpy as np
import pandas as pd

from .ml_models import (
    CNNModel,
    DecisionTreeModel,
    GradientBoostingModel,
    HybridLSTMCNNModel,
    KNNModel,
    LinearRegressionModel,
    LSTMModel,
    NaiveBayesModel,
    RandomForestModel,
    XGBoostModel,
)
from .prophet_model import ProphetModel

logger = logging.getLogger("ModelRegistry")


class ModelRegistry:
    def __init__(self):
        self.models: dict = {}
        self.comparison_df: pd.DataFrame = pd.DataFrame()
        self._default_models = {
            "LinearRegression": LinearRegressionModel,
            "KNN": KNNModel,
            "DecisionTree": DecisionTreeModel,
            "RandomForest": RandomForestModel,
            "XGBoost": XGBoostModel,
            "GradientBoosting": GradientBoostingModel,
            "NaiveBayes": NaiveBayesModel,
            "CNN": CNNModel,
            "LSTM": LSTMModel,
            "HybridLSTMCNN": HybridLSTMCNNModel,
            "Prophet": ProphetModel,
        }

    def register(self, name: str, model):
        self.models[name] = model

    def register_defaults(self, include: list = None):
        targets = include if include else list(self._default_models.keys())
        for name in targets:
            if name in self._default_models:
                self.models[name] = self._default_models[name]()

    def train_all(self, X_train, y_train, X_val=None, y_val=None,
                  df_train=None, progress_callback=None):
        results = {}
        total = len(self.models)
        for i, (name, model) in enumerate(self.models.items()):
            logger.info(f"Training {name} ({i+1}/{total})")
            if progress_callback:
                progress_callback(name, int((i / total) * 100))
            try:
                if name == "Prophet" and df_train is not None:
                    model.train(df_train)
                else:
                    model.train(X_train, y_train, X_val, y_val)
                results[name] = "success"
                logger.info(f"{name} trained successfully")
            except Exception as e:
                results[name] = f"failed: {e}"
                logger.error(f"{name} training failed: {e}")
        if progress_callback:
            progress_callback("done", 100)
        return results

    def evaluate_all(self, X_test, y_test, df_test=None) -> pd.DataFrame:
        rows = []
        for name, model in self.models.items():
            if not model.is_trained:
                continue
            try:
                if name == "Prophet" and df_test is not None:
                    metrics = model.evaluate(df_test, y_test)
                else:
                    metrics = model.evaluate(X_test, y_test)
                rows.append(metrics)
            except Exception as e:
                logger.error(f"{name} evaluation failed: {e}")
        self.comparison_df = pd.DataFrame(rows).sort_values("rmse").reset_index(drop=True)
        return self.comparison_df

    def get_best_model(self, metric: str = "rmse"):
        if self.comparison_df.empty:
            return None
        ascending = metric not in ["r2"]
        best_row = self.comparison_df.sort_values(metric, ascending=ascending).iloc[0]
        best_name = best_row["model"]
        return self.models.get(best_name)

    def ensemble_predict(self, X, top_n: int = 3, weights: list = None) -> np.ndarray:
        if self.comparison_df.empty:
            raise ValueError("Models not evaluated yet. Call evaluate_all() first.")
        top_models = self.comparison_df.head(top_n)["model"].tolist()
        preds = []
        for name in top_models:
            model = self.models.get(name)
            if model and model.is_trained:
                try:
                    p = model.predict(X)
                    preds.append(p)
                except Exception as e:
                    logger.warning(f"Ensemble skip {name}: {e}")
        if not preds:
            raise ValueError("No models available for ensemble prediction")
        if weights is None:
            rmse_vals = self.comparison_df[self.comparison_df["model"].isin(top_models)]["rmse"].values
            inv_rmse = 1.0 / (rmse_vals + 1e-8)
            weights = inv_rmse / inv_rmse.sum()
        stacked = np.column_stack(preds[:len(weights)])
        return np.average(stacked, axis=1, weights=weights[:stacked.shape[1]])

    def save_all(self, directory: str):
        Path(directory).mkdir(parents=True, exist_ok=True)
        for name, model in self.models.items():
            if model.is_trained:
                try:
                    model.save(str(Path(directory) / name.lower()))
                    logger.info(f"Saved {name}")
                except Exception as e:
                    logger.error(f"Save {name} failed: {e}")
        if not self.comparison_df.empty:
            self.comparison_df.to_csv(Path(directory) / "comparison.csv", index=False)

    def load_all(self, directory: str):
        d = Path(directory)
        if not d.exists():
            return
        for name, cls in self._default_models.items():
            model_path = d / name.lower()
            try:
                m = cls()
                m.load(str(model_path))
                self.models[name] = m
                logger.info(f"Loaded {name}")
            except Exception:
                pass
        comp_path = d / "comparison.csv"
        if comp_path.exists():
            self.comparison_df = pd.read_csv(comp_path)

    def get_model_comparison_df(self) -> pd.DataFrame:
        return self.comparison_df
