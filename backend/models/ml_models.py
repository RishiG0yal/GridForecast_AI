from pathlib import Path

import joblib
import numpy as np
import xgboost as xgb
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import KBinsDiscretizer
from sklearn.tree import DecisionTreeRegressor

from .base_model import BaseDemandModel


class LinearRegressionModel(BaseDemandModel):
    def __init__(self, config: dict = None):
        super().__init__("LinearRegression", config)

    def train(self, X_train, y_train, X_val=None, y_val=None):
        self.model = LinearRegression(**self.config)
        self.model.fit(X_train, y_train)
        self.is_trained = True
        return self

    def predict(self, X) -> np.ndarray:
        return self.model.predict(X)


class KNNModel(BaseDemandModel):
    def __init__(self, config: dict = None):
        cfg = {"n_neighbors": 7, "weights": "distance", "n_jobs": -1}
        if config:
            cfg.update(config)
        super().__init__("KNN", cfg)

    def train(self, X_train, y_train, X_val=None, y_val=None):
        self.model = KNeighborsRegressor(**self.config)
        self.model.fit(X_train, y_train)
        self.is_trained = True
        return self

    def predict(self, X) -> np.ndarray:
        return self.model.predict(X)


class DecisionTreeModel(BaseDemandModel):
    def __init__(self, config: dict = None):
        cfg = {"max_depth": 12, "min_samples_split": 10, "min_samples_leaf": 5, "random_state": 42}
        if config:
            cfg.update(config)
        super().__init__("DecisionTree", cfg)

    def train(self, X_train, y_train, X_val=None, y_val=None):
        self.model = DecisionTreeRegressor(**self.config)
        self.model.fit(X_train, y_train)
        self.is_trained = True
        return self

    def predict(self, X) -> np.ndarray:
        return self.model.predict(X)


class RandomForestModel(BaseDemandModel):
    def __init__(self, config: dict = None):
        cfg = {"n_estimators": 200, "max_depth": 15, "min_samples_split": 5,
               "n_jobs": -1, "random_state": 42}
        if config:
            cfg.update(config)
        super().__init__("RandomForest", cfg)

    def train(self, X_train, y_train, X_val=None, y_val=None):
        self.model = RandomForestRegressor(**self.config)
        self.model.fit(X_train, y_train)
        self.is_trained = True
        self.feature_importances_ = self.model.feature_importances_
        return self

    def predict(self, X) -> np.ndarray:
        return self.model.predict(X)


class XGBoostModel(BaseDemandModel):
    def __init__(self, config: dict = None):
        cfg = {"learning_rate": 0.07, "n_estimators": 500, "max_depth": 7,
               "subsample": 0.8, "colsample_bytree": 0.8, "random_state": 42,
               "tree_method": "hist", "n_jobs": -1}
        if config:
            cfg.update(config)
        super().__init__("XGBoost", cfg)

    def train(self, X_train, y_train, X_val=None, y_val=None):
        eval_set = [(X_train, y_train)]
        if X_val is not None and y_val is not None:
            eval_set.append((X_val, y_val))
        params = {k: v for k, v in self.config.items()}
        self.model = xgb.XGBRegressor(**params, early_stopping_rounds=30)
        self.model.fit(X_train, y_train, eval_set=eval_set, verbose=False)
        self.is_trained = True
        return self

    def predict(self, X) -> np.ndarray:
        return self.model.predict(X)

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.model.save_model(path + ".xgb")
        joblib.dump({"config": self.config, "feature_columns": self.feature_columns,
                     "metrics": self.metrics}, path + ".meta")

    def load(self, path: str):
        self.model = xgb.XGBRegressor()
        self.model.load_model(path + ".xgb")
        meta = joblib.load(path + ".meta")
        self.config = meta.get("config", {})
        self.feature_columns = meta.get("feature_columns", [])
        self.metrics = meta.get("metrics", {})
        self.is_trained = True
        return self


class GradientBoostingModel(BaseDemandModel):
    def __init__(self, config: dict = None):
        cfg = {"n_estimators": 300, "learning_rate": 0.05, "max_depth": 6,
               "subsample": 0.8, "random_state": 42}
        if config:
            cfg.update(config)
        super().__init__("GradientBoosting", cfg)

    def train(self, X_train, y_train, X_val=None, y_val=None):
        self.model = GradientBoostingRegressor(**self.config)
        self.model.fit(X_train, y_train)
        self.is_trained = True
        return self

    def predict(self, X) -> np.ndarray:
        return self.model.predict(X)


class NaiveBayesModel(BaseDemandModel):
    def __init__(self, config: dict = None):
        cfg = {"n_bins": 50}
        if config:
            cfg.update(config)
        super().__init__("NaiveBayes", cfg)
        self._discretizer = None
        self._bin_means = None

    def train(self, X_train, y_train, X_val=None, y_val=None):
        n_bins = self.config.get("n_bins", 50)
        self._discretizer = KBinsDiscretizer(n_bins=n_bins, encode="ordinal", strategy="quantile")
        y_binned = self._discretizer.fit_transform(y_train.reshape(-1, 1)).ravel().astype(int)
        bin_edges = self._discretizer.bin_edges_[0]
        self._bin_means = [(bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(len(bin_edges) - 1)]
        self.model = GaussianNB()
        self.model.fit(X_train, y_binned)
        self.is_trained = True
        return self

    def predict(self, X) -> np.ndarray:
        bin_preds = self.model.predict(X).astype(int)
        return np.array([self._bin_means[min(b, len(self._bin_means) - 1)] for b in bin_preds])

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self.model, "discretizer": self._discretizer,
                     "bin_means": self._bin_means, "config": self.config,
                     "feature_columns": self.feature_columns,
                     "metrics": self.metrics}, path)

    def load(self, path: str):
        data = joblib.load(path)
        self.model = data["model"]
        self._discretizer = data["discretizer"]
        self._bin_means = data["bin_means"]
        self.config = data.get("config", {})
        self.feature_columns = data.get("feature_columns", [])
        self.metrics = data.get("metrics", {})
        self.is_trained = True
        return self


class CNNModel(BaseDemandModel):
    def __init__(self, config: dict = None):
        cfg = {"lookback": 24, "epochs": 30, "batch_size": 64, "learning_rate": 0.001}
        if config:
            cfg.update(config)
        super().__init__("CNN", cfg)
        self._tf_model = None

    def _build_model(self, n_features: int):
        import tensorflow as tf
        from tensorflow.keras import layers, models
        inp = tf.keras.Input(shape=(self.config["lookback"], n_features))
        x = layers.Conv1D(64, 3, activation="relu", padding="same")(inp)
        x = layers.Conv1D(32, 3, activation="relu", padding="same")(x)
        x = layers.GlobalAveragePooling1D()(x)
        x = layers.Dense(64, activation="relu")(x)
        x = layers.Dropout(0.2)(x)
        out = layers.Dense(1)(x)
        model = models.Model(inp, out)
        model.compile(optimizer=tf.keras.optimizers.Adam(self.config["learning_rate"]),
                      loss="mse", metrics=["mae"])
        return model

    def _create_sequences(self, X, y=None):
        lb = self.config["lookback"]
        Xs = np.array([X[i - lb:i] for i in range(lb, len(X))])
        if y is not None:
            ys = np.array(y[lb:])
            return Xs, ys
        return Xs

    def train(self, X_train, y_train, X_val=None, y_val=None):
        try:
            import tensorflow as tf
        except ImportError:
            raise RuntimeError('TensorFlow is not installed. CNN/LSTM require Python <=3.12 (current: 3.14). Use XGBoost/RandomForest instead.')
        X_seq, y_seq = self._create_sequences(X_train, y_train)
        val_data = None
        if X_val is not None and y_val is not None:
            X_vseq, y_vseq = self._create_sequences(X_val, y_val)
            val_data = (X_vseq, y_vseq)
        self._tf_model = self._build_model(X_train.shape[1])
        cb = [tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True)]
        self._tf_model.fit(X_seq, y_seq, epochs=self.config["epochs"],
                           batch_size=self.config["batch_size"],
                           validation_data=val_data, callbacks=cb, verbose=0)
        self.is_trained = True
        return self

    def predict(self, X) -> np.ndarray:
        lb = self.config["lookback"]
        if len(X) <= lb:
            X = np.vstack([np.zeros((lb - len(X) + 1, X.shape[1])), X])
        X_seq = self._create_sequences(X)
        preds = self._tf_model.predict(X_seq, verbose=0).ravel()
        pad = np.full(lb, preds[0])
        return np.concatenate([pad, preds])[:len(X)]

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._tf_model.save(path + "_cnn.keras")
        joblib.dump({"config": self.config, "feature_columns": self.feature_columns,
                     "metrics": self.metrics}, path + ".meta")

    def load(self, path: str):
        try:
            import tensorflow as tf
        except ImportError:
            raise RuntimeError('TensorFlow not available on Python 3.14')
        self._tf_model = tf.keras.models.load_model(path + "_cnn.keras")
        meta = joblib.load(path + ".meta")
        self.config = meta.get("config", {})
        self.feature_columns = meta.get("feature_columns", [])
        self.metrics = meta.get("metrics", {})
        self.is_trained = True
        return self


class LSTMModel(BaseDemandModel):
    def __init__(self, config: dict = None):
        cfg = {"lookback": 24, "epochs": 30, "batch_size": 64, "learning_rate": 0.001}
        if config:
            cfg.update(config)
        super().__init__("LSTM", cfg)
        self._tf_model = None

    def _build_model(self, n_features: int):
        import tensorflow as tf
        from tensorflow.keras import layers, models
        inp = tf.keras.Input(shape=(self.config["lookback"], n_features))
        x = layers.LSTM(128, return_sequences=True)(inp)
        x = layers.Dropout(0.2)(x)
        x = layers.LSTM(64)(x)
        x = layers.Dense(32, activation="relu")(x)
        x = layers.Dropout(0.2)(x)
        out = layers.Dense(1)(x)
        model = models.Model(inp, out)
        model.compile(optimizer=tf.keras.optimizers.Adam(self.config["learning_rate"]),
                      loss="mse", metrics=["mae"])
        return model

    def _create_sequences(self, X, y=None):
        lb = self.config["lookback"]
        Xs = np.array([X[i - lb:i] for i in range(lb, len(X))])
        if y is not None:
            ys = np.array(y[lb:])
            return Xs, ys
        return Xs

    def train(self, X_train, y_train, X_val=None, y_val=None):
        try:
            import tensorflow as tf
        except ImportError:
            raise RuntimeError('TensorFlow is not installed. CNN/LSTM require Python <=3.12 (current: 3.14). Use XGBoost/RandomForest instead.')
        X_seq, y_seq = self._create_sequences(X_train, y_train)
        val_data = None
        if X_val is not None and y_val is not None:
            X_vseq, y_vseq = self._create_sequences(X_val, y_val)
            val_data = (X_vseq, y_vseq)
        self._tf_model = self._build_model(X_train.shape[1])
        cb = [tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True)]
        self._tf_model.fit(X_seq, y_seq, epochs=self.config["epochs"],
                           batch_size=self.config["batch_size"],
                           validation_data=val_data, callbacks=cb, verbose=0)
        self.is_trained = True
        return self

    def predict(self, X) -> np.ndarray:
        lb = self.config["lookback"]
        if len(X) <= lb:
            X = np.vstack([np.zeros((lb - len(X) + 1, X.shape[1])), X])
        X_seq = self._create_sequences(X)
        preds = self._tf_model.predict(X_seq, verbose=0).ravel()
        pad = np.full(lb, preds[0])
        return np.concatenate([pad, preds])[:len(X)]

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._tf_model.save(path + "_lstm.keras")
        joblib.dump({"config": self.config, "feature_columns": self.feature_columns,
                     "metrics": self.metrics}, path + ".meta")

    def load(self, path: str):
        try:
            import tensorflow as tf
        except ImportError:
            raise RuntimeError('TensorFlow not available on Python 3.14')
        self._tf_model = tf.keras.models.load_model(path + "_lstm.keras")
        meta = joblib.load(path + ".meta")
        self.config = meta.get("config", {})
        self.feature_columns = meta.get("feature_columns", [])
        self.metrics = meta.get("metrics", {})
        self.is_trained = True
        return self


class HybridLSTMCNNModel(BaseDemandModel):
    def __init__(self, config: dict = None):
        cfg = {"lookback": 24, "epochs": 30, "batch_size": 64, "learning_rate": 0.001}
        if config:
            cfg.update(config)
        super().__init__("HybridLSTMCNN", cfg)
        self._tf_model = None

    def _build_model(self, n_features: int):
        import tensorflow as tf
        from tensorflow.keras import layers, models
        inp = tf.keras.Input(shape=(self.config["lookback"], n_features))
        cnn_branch = layers.Conv1D(64, 3, activation="relu", padding="same")(inp)
        cnn_branch = layers.MaxPooling1D(2)(cnn_branch)
        cnn_branch = layers.Flatten()(cnn_branch)
        lstm_branch = layers.LSTM(64)(inp)
        merged = layers.Concatenate()([cnn_branch, lstm_branch])
        x = layers.Dense(64, activation="relu")(merged)
        x = layers.Dropout(0.2)(x)
        out = layers.Dense(1)(x)
        model = models.Model(inp, out)
        model.compile(optimizer=tf.keras.optimizers.Adam(self.config["learning_rate"]),
                      loss="mse", metrics=["mae"])
        return model

    def _create_sequences(self, X, y=None):
        lb = self.config["lookback"]
        Xs = np.array([X[i - lb:i] for i in range(lb, len(X))])
        if y is not None:
            ys = np.array(y[lb:])
            return Xs, ys
        return Xs

    def train(self, X_train, y_train, X_val=None, y_val=None):
        try:
            import tensorflow as tf
        except ImportError:
            raise RuntimeError('TensorFlow is not installed. CNN/LSTM require Python <=3.12 (current: 3.14). Use XGBoost/RandomForest instead.')
        X_seq, y_seq = self._create_sequences(X_train, y_train)
        val_data = None
        if X_val is not None and y_val is not None:
            X_vseq, y_vseq = self._create_sequences(X_val, y_val)
            val_data = (X_vseq, y_vseq)
        self._tf_model = self._build_model(X_train.shape[1])
        cb = [tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True)]
        self._tf_model.fit(X_seq, y_seq, epochs=self.config["epochs"],
                           batch_size=self.config["batch_size"],
                           validation_data=val_data, callbacks=cb, verbose=0)
        self.is_trained = True
        return self

    def predict(self, X) -> np.ndarray:
        lb = self.config["lookback"]
        if len(X) <= lb:
            X = np.vstack([np.zeros((lb - len(X) + 1, X.shape[1])), X])
        X_seq = self._create_sequences(X)
        preds = self._tf_model.predict(X_seq, verbose=0).ravel()
        pad = np.full(lb, preds[0])
        return np.concatenate([pad, preds])[:len(X)]

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._tf_model.save(path + "_hybrid.keras")
        joblib.dump({"config": self.config, "feature_columns": self.feature_columns,
                     "metrics": self.metrics}, path + ".meta")

    def load(self, path: str):
        try:
            import tensorflow as tf
        except ImportError:
            raise RuntimeError('TensorFlow not available on Python 3.14')
        self._tf_model = tf.keras.models.load_model(path + "_hybrid.keras")
        meta = joblib.load(path + ".meta")
        self.config = meta.get("config", {})
        self.feature_columns = meta.get("feature_columns", [])
        self.metrics = meta.get("metrics", {})
        self.is_trained = True
        return self
