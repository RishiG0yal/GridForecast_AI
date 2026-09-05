import logging
import time
from datetime import datetime, timedelta

import httpx
import numpy as np
import pandas as pd

logger = logging.getLogger("collector")


class WeatherCollector:
    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    HOURLY_PARAMS = [
        "temperature_2m", "relative_humidity_2m", "precipitation",
        "windspeed_10m", "cloudcover", "shortwave_radiation",
        "direct_radiation", "apparent_temperature"
    ]

    def _get(self, url: str, params: dict, retries: int = 3) -> dict:
        for attempt in range(retries):
            try:
                with httpx.Client(timeout=60) as client:
                    r = client.get(url, params=params)
                    r.raise_for_status()
                    return r.json()
            except Exception:
                if attempt == retries - 1:
                    raise
                time.sleep(2 ** attempt)

    def fetch_historical_weather(self, lat: float, lon: float, start_date: str, end_date: str) -> pd.DataFrame:
        params = {
            "latitude": lat, "longitude": lon,
            "start_date": start_date, "end_date": end_date,
            "hourly": ",".join(self.HOURLY_PARAMS),
            "timezone": "Asia/Kolkata"
        }
        data = self._get(self.ARCHIVE_URL, params)
        df = pd.DataFrame(data["hourly"])
        df["datetime"] = pd.to_datetime(df["time"])
        df.drop(columns=["time"], inplace=True)
        df.set_index("datetime", inplace=True)
        df.rename(columns={
            "temperature_2m": "temperature",
            "relative_humidity_2m": "humidity",
            "windspeed_10m": "wind_speed",
            "shortwave_radiation": "solar_radiation",
            "direct_radiation": "direct_radiation",
            "apparent_temperature": "feels_like",
            "cloudcover": "cloud_cover",
            "precipitation": "precipitation"
        }, inplace=True)
        return df

    def fetch_forecast_weather(self, lat: float, lon: float, hours: int = 48) -> pd.DataFrame:
        params = {
            "latitude": lat, "longitude": lon,
            "hourly": ",".join(self.HOURLY_PARAMS),
            "forecast_days": max(2, hours // 24 + 1),
            "timezone": "Asia/Kolkata"
        }
        data = self._get(self.FORECAST_URL, params)
        df = pd.DataFrame(data["hourly"])
        df["datetime"] = pd.to_datetime(df["time"])
        df.drop(columns=["time"], inplace=True)
        df.set_index("datetime", inplace=True)
        df.rename(columns={
            "temperature_2m": "temperature",
            "relative_humidity_2m": "humidity",
            "windspeed_10m": "wind_speed",
            "shortwave_radiation": "solar_radiation",
            "direct_radiation": "direct_radiation",
            "apparent_temperature": "feels_like",
            "cloudcover": "cloud_cover",
            "precipitation": "precipitation"
        }, inplace=True)
        return df.iloc[:hours]


class SolarGenerationCollector:
    def estimate_solar_generation(self, lat: float, lon: float, capacity_kw: float,
                                   start_date: str, end_date: str, efficiency: float = 0.17) -> pd.DataFrame:
        wc = WeatherCollector()
        weather = wc.fetch_historical_weather(lat, lon, start_date, end_date)
        weather["solar_generation_kw"] = (
            weather["solar_radiation"] * capacity_kw * efficiency / 1000
        ).clip(lower=0)
        return weather[["solar_generation_kw"]]


class LoadDataCollector:
    def load_from_csv(self, filepath: str, date_col: str = None, load_col: str = None,
                      area_col: str = None, node_col: str = None) -> pd.DataFrame:
        df = pd.read_csv(filepath)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        if date_col is None:
            candidates = [c for c in df.columns if any(k in c for k in ["date", "time", "datetime", "timestamp"])]
            date_col = candidates[0] if candidates else df.columns[0]
        if load_col is None:
            candidates = [c for c in df.columns if any(k in c for k in ["demand", "load", "mw", "consumption", "actual"])]
            load_col = candidates[0] if candidates else df.columns[1]
        df[date_col] = pd.to_datetime(df[date_col])
        df.rename(columns={date_col: "datetime", load_col: "gross_demand_mw"}, inplace=True)
        df.set_index("datetime", inplace=True)
        if area_col and area_col in df.columns:
            df.rename(columns={area_col: "area"}, inplace=True)
        if node_col and node_col in df.columns:
            df.rename(columns={node_col: "node"}, inplace=True)
        return df

    def load_from_excel(self, filepath: str, sheet_name=0, date_col: str = None,
                        load_col: str = None) -> pd.DataFrame:
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        tmp_path = "/tmp/_tmp_load.csv"
        df.to_csv(tmp_path, index=False)
        return self.load_from_csv(tmp_path, date_col=date_col, load_col=load_col)

    def parse_posoco_format(self, filepath: str) -> pd.DataFrame:
        df = pd.read_csv(filepath, skiprows=1)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        date_col = [c for c in df.columns if "date" in c][0]
        time_col = [c for c in df.columns if "time" in c or "slot" in c]
        actual_col = [c for c in df.columns if "actual" in c][0]
        df["datetime"] = pd.to_datetime(df[date_col].astype(str) + " " + (df[time_col[0]].astype(str) if time_col else "00:00"))
        df.rename(columns={actual_col: "gross_demand_mw"}, inplace=True)
        df["gross_demand_mw"] = pd.to_numeric(df["gross_demand_mw"], errors="coerce")
        df.set_index("datetime", inplace=True)
        df = df.resample("h").mean()
        return df[["gross_demand_mw"]].dropna()

    def parse_state_sldc_format(self, filepath: str) -> pd.DataFrame:
        df = pd.read_csv(filepath)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        date_col = [c for c in df.columns if "date" in c][0]
        hour_col = [c for c in df.columns if "hour" in c or "block" in c]
        demand_col = [c for c in df.columns if "demand" in c or "actual" in c or "mw" in c][0]
        if hour_col:
            df["datetime"] = pd.to_datetime(df[date_col]) + pd.to_timedelta(df[hour_col[0]].astype(int) - 1, unit="h")
        else:
            df["datetime"] = pd.to_datetime(df[date_col])
        df.rename(columns={demand_col: "gross_demand_mw"}, inplace=True)
        df.set_index("datetime", inplace=True)
        return df[["gross_demand_mw"]].dropna()

    def generate_synthetic_base(self, area_config: dict, days: int = 365) -> pd.DataFrame:
        np.random.seed(42)
        start = datetime.now() - timedelta(days=days)
        idx = pd.date_range(start=start, periods=days * 24, freq="h")
        records = []
        for area, cfg in area_config.items():
            base = cfg.get("base_mw", 1000)
            for ts in idx:
                hour = ts.hour
                month = ts.month
                dow = ts.dayofweek
                seasonal = 1.0
                if month in [4, 5, 6]:
                    seasonal = 1.25
                elif month in [12, 1, 2]:
                    seasonal = 0.85
                elif month in [7, 8, 9]:
                    seasonal = 1.05
                if 6 <= hour <= 10:
                    hourly = 1.15
                elif 18 <= hour <= 22:
                    hourly = 1.30
                elif 0 <= hour <= 4:
                    hourly = 0.65
                else:
                    hourly = 1.0
                weekend_factor = 0.88 if dow >= 5 else 1.0
                noise = np.random.normal(0, 0.03)
                demand = base * seasonal * hourly * weekend_factor * (1 + noise)
                solar = max(0, base * 0.08 * np.sin(np.pi * max(0, hour - 6) / 12) * (1 if 6 <= hour <= 18 else 0))
                capacity = base * 1.2
                for node_name, node_cfg in cfg.get("nodes", {"main": {"fraction": 1.0, "type": "mixed"}}).items():
                    frac = node_cfg.get("fraction", 1.0)
                    ctype = node_cfg.get("type", "mixed")
                    records.append({
                        "datetime": ts, "area": area, "node": node_name,
                        "consumer_type": ctype,
                        "gross_demand_mw": round(demand * frac, 2),
                        "solar_generation_mw": round(solar * frac * 0.5, 2),
                        "available_capacity_mw": round(capacity * frac, 2)
                    })
        df = pd.DataFrame(records)
        df.set_index("datetime", inplace=True)
        return df


class CapacityDataCollector:
    def __init__(self):
        self.capacity_data = {}

    def load_capacity_from_csv(self, filepath: str) -> dict:
        df = pd.read_csv(filepath)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        for _, row in df.iterrows():
            plant = str(row.get("plant_name", row.get("name", f"plant_{_}")))
            self.capacity_data[plant] = {
                "installed_mw": float(row.get("installed_mw", row.get("capacity_mw", 0))),
                "availability_factor": float(row.get("availability_factor", row.get("availability", 0.85))),
                "fuel_type": str(row.get("fuel_type", row.get("type", "thermal"))),
                "area": str(row.get("area", "system"))
            }
        return self.capacity_data

    def get_available_capacity(self, date: datetime = None, maintenance_schedule: dict = None) -> float:
        total = 0.0
        for plant, info in self.capacity_data.items():
            af = info["availability_factor"]
            if maintenance_schedule and plant in maintenance_schedule:
                sched = maintenance_schedule[plant]
                if date and sched.get("start") <= date <= sched.get("end"):
                    af = 0.0
            total += info["installed_mw"] * af
        return total

    def get_area_capacity(self) -> dict:
        areas = {}
        for plant, info in self.capacity_data.items():
            area = info["area"]
            areas.setdefault(area, {"total_mw": 0, "available_mw": 0, "plants": []})
            available = info["installed_mw"] * info["availability_factor"]
            areas[area]["total_mw"] += info["installed_mw"]
            areas[area]["available_mw"] += available
            areas[area]["plants"].append(plant)
        return areas
