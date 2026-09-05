import logging

import holidays
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger("processor")

INDIA_HOLIDAYS = holidays.India()

SEASONS = {1: "winter", 2: "winter", 3: "summer", 4: "summer", 5: "summer",
           6: "monsoon", 7: "monsoon", 8: "monsoon", 9: "monsoon",
           10: "post_monsoon", 11: "post_monsoon", 12: "winter"}


class FeatureEngineer:
    def create_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        idx = df.index if isinstance(df.index, pd.DatetimeIndex) else pd.to_datetime(df.index)
        df = df.copy()
        df["hour"] = idx.hour
        df["day_of_week"] = idx.dayofweek
        df["day_of_month"] = idx.day
        df["month"] = idx.month
        df["year"] = idx.year
        df["quarter"] = idx.quarter
        df["week_of_year"] = idx.isocalendar().week.values
        df["is_weekend"] = (idx.dayofweek >= 5).astype(int)
        df["is_holiday"] = idx.map(lambda d: int(d.date() in INDIA_HOLIDAYS)).values
        df["day_name"] = idx.day_name()
        return df

    def create_season_feature(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if "month" not in df.columns:
            df = self.create_time_features(df)
        df["season"] = df["month"].map(SEASONS)
        season_map = {"winter": 0, "summer": 1, "monsoon": 2, "post_monsoon": 3}
        df["season_code"] = df["season"].map(season_map)
        return df

    def create_lag_features(self, df: pd.DataFrame, target_col: str,
                             lags: list = [1, 2, 3, 6, 12, 24, 48, 168]) -> pd.DataFrame:
        df = df.copy()
        for lag in lags:
            df[f"{target_col}_lag_{lag}h"] = df[target_col].shift(lag)
        return df

    def create_rolling_features(self, df: pd.DataFrame, target_col: str,
                                 windows: list = [3, 6, 12, 24, 168]) -> pd.DataFrame:
        df = df.copy()
        for w in windows:
            df[f"{target_col}_roll_mean_{w}h"] = df[target_col].shift(1).rolling(w).mean()
            df[f"{target_col}_roll_std_{w}h"] = df[target_col].shift(1).rolling(w).std()
            df[f"{target_col}_roll_min_{w}h"] = df[target_col].shift(1).rolling(w).min()
            df[f"{target_col}_roll_max_{w}h"] = df[target_col].shift(1).rolling(w).max()
        return df

    def create_weather_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if "temperature" in df.columns and "humidity" in df.columns:
            T = df["temperature"]
            H = df["humidity"]
            df["heat_index"] = -8.78469 + 1.61139 * T + 2.33855 * H - 0.14611 * T * H \
                               - 0.01230 * T**2 - 0.01642 * H**2 + 0.00221 * T**2 * H \
                               + 0.00072 * T * H**2 - 0.00000358 * T**2 * H**2
            df["dewpoint"] = T - ((100 - H) / 5.0)
            df["discomfort_index"] = 0.4 * (T + df["dewpoint"]) + 4.8
        if "temperature" in df.columns:
            df["temp_above_30"] = (df["temperature"] - 30).clip(lower=0)
            df["temp_below_15"] = (15 - df["temperature"]).clip(lower=0)
        if "solar_radiation" in df.columns:
            df["solar_radiation_sq"] = df["solar_radiation"] ** 2
        return df

    def create_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if "temperature" in df.columns and "humidity" in df.columns:
            df["temp_x_humidity"] = df["temperature"] * df["humidity"] / 100
        if "temperature" in df.columns and "hour" in df.columns:
            df["hour_x_temp"] = df["hour"] * df["temperature"]
        if "hour" in df.columns and "is_weekend" in df.columns:
            df["hour_x_weekend"] = df["hour"] * df["is_weekend"]
        if "season_code" in df.columns and "temperature" in df.columns:
            df["season_x_temp"] = df["season_code"] * df["temperature"]
        return df

    def create_cyclical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if "hour" in df.columns:
            df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
            df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
        if "day_of_week" in df.columns:
            df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
            df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
        if "month" in df.columns:
            df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
            df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
        return df

    def run_all(self, df: pd.DataFrame, target_col: str = "net_demand") -> pd.DataFrame:
        df = self.create_time_features(df)
        df = self.create_season_feature(df)
        df = self.create_weather_features(df)
        df = self.create_interaction_features(df)
        df = self.create_cyclical_features(df)
        if target_col in df.columns:
            df = self.create_lag_features(df, target_col)
            df = self.create_rolling_features(df, target_col)
        return df


class LoadClassifier:
    CONSUMER_PROFILES = {
        "residential": {"peak_hours": range(18, 23), "base_factor": 0.55, "weekend_boost": 1.10},
        "commercial": {"peak_hours": range(9, 19), "base_factor": 0.40, "weekend_boost": 0.75},
        "industrial_small": {"peak_hours": range(8, 18), "base_factor": 0.70, "weekend_boost": 0.60},
        "industrial_medium": {"peak_hours": range(6, 22), "base_factor": 0.75, "weekend_boost": 0.70},
        "industrial_large": {"peak_hours": range(24), "base_factor": 0.90, "weekend_boost": 0.95},
        "hospital": {"peak_hours": range(24), "base_factor": 0.85, "weekend_boost": 1.00},
        "school": {"peak_hours": range(8, 16), "base_factor": 0.30, "weekend_boost": 0.10},
        "hotel": {"peak_hours": range(17, 23), "base_factor": 0.60, "weekend_boost": 1.20},
    }

    def classify_load_profile(self, df: pd.DataFrame, consumer_type_col: str = "consumer_type") -> pd.DataFrame:
        df = df.copy()
        if consumer_type_col in df.columns:
            df["load_category"] = df[consumer_type_col].str.lower().map(
                lambda x: x if x in self.CONSUMER_PROFILES else "mixed"
            )
        else:
            df["load_category"] = "mixed"
        return df

    def aggregate_by_area(self, df: pd.DataFrame) -> pd.DataFrame:
        if "area" not in df.columns:
            return df
        return df.groupby(["area", pd.Grouper(freq="h")])["gross_demand_mw"].sum().reset_index()

    def aggregate_by_node(self, df: pd.DataFrame) -> pd.DataFrame:
        if "node" not in df.columns:
            return df
        return df.groupby(["node", pd.Grouper(freq="h")])["gross_demand_mw"].sum().reset_index()

    def get_load_composition(self, df: pd.DataFrame, area: str = None) -> dict:
        data = df[df["area"] == area] if area and "area" in df.columns else df
        if "consumer_type" not in data.columns:
            return {}
        total = data["gross_demand_mw"].sum()
        if total == 0:
            return {}
        comp = data.groupby("consumer_type")["gross_demand_mw"].sum()
        return (comp / total * 100).round(2).to_dict()


class DemandCalculator:
    def calculate_net_demand(self, df: pd.DataFrame,
                              gross_col: str = "gross_demand_mw",
                              solar_col: str = "solar_generation_mw",
                              other_gen_col: str = None) -> pd.DataFrame:
        df = df.copy()
        if df.index.duplicated().any():
            df = df[~df.index.duplicated(keep="last")]
        net = df[gross_col].values.copy().astype(float)
        if solar_col in df.columns:
            net -= np.nan_to_num(df[solar_col].values.astype(float), nan=0.0)
        if other_gen_col and other_gen_col in df.columns:
            net -= np.nan_to_num(df[other_gen_col].values.astype(float), nan=0.0)
        df["net_demand"] = np.clip(net, 0, None)
        return df

    def calculate_system_demand(self, area_dfs: dict) -> pd.DataFrame:
        frames = []
        for area, adf in area_dfs.items():
            adf = adf.copy()
            adf["area"] = area
            frames.append(adf)
        combined = pd.concat(frames)
        system = combined.groupby(combined.index)[["gross_demand_mw", "net_demand",
                                                    "solar_generation_mw"]].sum()
        return system

    def calculate_demand_metrics(self, df: pd.DataFrame, col: str = "net_demand") -> dict:
        if col not in df.columns:
            col = "gross_demand_mw"
        peak = df[col].max()
        off_peak = df[col].min()
        avg = df[col].mean()
        load_factor = avg / peak if peak > 0 else 0
        return {
            "peak_mw": round(peak, 2),
            "off_peak_mw": round(off_peak, 2),
            "average_mw": round(avg, 2),
            "load_factor": round(load_factor, 4),
            "total_mwh": round(df[col].sum(), 2)
        }


class DataPipeline:
    def __init__(self):
        self.fe = FeatureEngineer()
        self.dc = DemandCalculator()
        self.scaler = StandardScaler()
        self._feature_cols = []
        self._target_col = "net_demand"

    def prepare_training_data(self, load_df: pd.DataFrame,
                               weather_df: pd.DataFrame = None,
                               solar_df: pd.DataFrame = None) -> pd.DataFrame:
        load_df = load_df.copy()
        if not isinstance(load_df.index, pd.DatetimeIndex):
            load_df.index = pd.to_datetime(load_df.index)
        if load_df.index.duplicated().any():
            load_df = load_df[~load_df.index.duplicated(keep="last")]
        load_df = load_df.loc[:, ~load_df.columns.duplicated(keep="last")]
        numeric_cols = load_df.select_dtypes(include=[np.number]).columns.tolist()
        load_df = load_df[numeric_cols].resample("h").mean()

        if weather_df is not None and not weather_df.empty:
            if not isinstance(weather_df.index, pd.DatetimeIndex):
                weather_df.index = pd.to_datetime(weather_df.index)
            new_cols = [c for c in weather_df.columns if c not in load_df.columns]
            merged = load_df.join(weather_df[new_cols], how="left") if new_cols else load_df
        else:
            merged = load_df

        if solar_df is not None:
            if not isinstance(solar_df.index, pd.DatetimeIndex):
                solar_df.index = pd.to_datetime(solar_df.index)
            new_cols = [c for c in solar_df.columns if c not in merged.columns]
            if new_cols:
                merged = merged.join(solar_df[new_cols], how="left")

        if "solar_generation_mw" not in merged.columns:
            merged["solar_generation_mw"] = 0.0

        if "net_demand_mw" in merged.columns and "net_demand" not in merged.columns:
            merged["net_demand"] = merged["net_demand_mw"]
        if "gross_demand_mw" not in merged.columns and "net_demand" not in merged.columns:
            raise ValueError("Load DataFrame must contain 'gross_demand_mw' or 'net_demand'")
        if "gross_demand_mw" not in merged.columns and "net_demand" in merged.columns:
            merged["gross_demand_mw"] = merged["net_demand"]

        merged = self.dc.calculate_net_demand(merged)
        merged = self.fe.run_all(merged, target_col=self._target_col)
        merged.replace([np.inf, -np.inf], np.nan, inplace=True)
        merged.ffill(inplace=True)
        merged.bfill(inplace=True)
        merged.dropna(subset=[self._target_col], inplace=True)
        return merged

    def get_feature_columns(self, df: pd.DataFrame) -> list:
        exclude = {
            self._target_col, "gross_demand_mw", "net_demand_mw",
            "area", "node", "consumer_type", "load_category", "season", "day_name",
            "solar_generation_mw", "available_capacity_mw",
            "discom_brpl_mw", "discom_bypl_mw", "discom_ndpl_mw",
            "discom_ndmc_mw", "discom_mes_mw",
            "brpl_mw", "bypl_mw", "ndpl_mw", "ndmc_mw", "mes_mw",
            "scheduled_load_mw", "drawal_ists_mw", "generation_mw",
        }
        numeric = df.select_dtypes(include=[np.number]).columns.tolist()
        return [c for c in numeric if c not in exclude]

    def split_train_val_test(self, df: pd.DataFrame, val_ratio: float = 0.1,
                              test_ratio: float = 0.1):
        n = len(df)
        test_n = int(n * test_ratio)
        val_n = int(n * val_ratio)
        train = df.iloc[:n - val_n - test_n]
        val = df.iloc[n - val_n - test_n:n - test_n]
        test = df.iloc[n - test_n:]
        return train, val, test

    def scale_features(self, X_train, X_val, X_test):
        X_tr = self.scaler.fit_transform(X_train)
        X_v = self.scaler.transform(X_val)
        X_te = self.scaler.transform(X_test)
        return X_tr, X_v, X_te

    def get_target_column(self) -> str:
        return self._target_col
