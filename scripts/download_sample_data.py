import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from datetime import datetime, timedelta, timezone, date
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

Path("data/raw").mkdir(parents=True, exist_ok=True)
Path("data/processed").mkdir(parents=True, exist_ok=True)
Path("data/models").mkdir(parents=True, exist_ok=True)
Path("logs").mkdir(exist_ok=True)

print("=" * 60)
print("GridForecast AI - Data Setup")
print("=" * 60)

print("\n[1/3] Downloading real weather data from Open-Meteo (Delhi)...")

end_date = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
start_date = (datetime.now(timezone.utc) - timedelta(days=367)).strftime("%Y-%m-%d")

HOURLY_PARAMS = [
    "temperature_2m", "relative_humidity_2m", "precipitation",
    "windspeed_10m", "cloudcover", "shortwave_radiation",
    "direct_radiation", "apparent_temperature"
]

weather_df = None
for attempt in range(3):
    try:
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": 28.6139,
            "longitude": 77.2090,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(HOURLY_PARAMS),
            "timezone": "Asia/Kolkata"
        }
        with httpx.Client(timeout=90) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
        weather_df = pd.DataFrame(data["hourly"])
        weather_df["datetime"] = pd.to_datetime(weather_df["time"])
        weather_df.drop(columns=["time"], inplace=True)
        weather_df.rename(columns={
            "temperature_2m": "temperature",
            "relative_humidity_2m": "humidity",
            "windspeed_10m": "wind_speed",
            "shortwave_radiation": "solar_radiation",
            "direct_radiation": "direct_radiation",
            "apparent_temperature": "feels_like",
            "cloudcover": "cloud_cover",
            "precipitation": "precipitation"
        }, inplace=True)
        weather_df.to_csv("data/raw/weather_delhi_365days.csv", index=False)
        print(f"    Downloaded {len(weather_df)} hourly records ({start_date} to {end_date})")
        print("    Saved: data/raw/weather_delhi_365days.csv")
        break
    except Exception as e: # noqa: BLE001
        if attempt == 2:
            print(f"    WARNING: Weather download failed ({e}). Using synthetic weather.")
        else:
            print(f"    Retry {attempt + 1}...")
            time.sleep(3 * (attempt + 1))

print("\n[2/3] Generating realistic Indian grid load dataset...")

np.random.seed(42)

idx = pd.date_range(start=start_date, end=end_date, freq="h")

AREAS = {
    "Northern_Region": {
        "base_mw": 3800,
        "nodes": {
            "Delhi": {"fraction": 0.38, "consumer_type": "mixed"},
            "Haryana": {"fraction": 0.25, "consumer_type": "industrial_medium"},
            "Punjab": {"fraction": 0.22, "consumer_type": "agricultural"},
            "UP_West": {"fraction": 0.15, "consumer_type": "mixed"},
        }
    },
    "Western_Region": {
        "base_mw": 4200,
        "nodes": {
            "Mumbai": {"fraction": 0.42, "consumer_type": "commercial"},
            "Gujarat_Industrial": {"fraction": 0.33, "consumer_type": "industrial_large"},
            "Rajasthan": {"fraction": 0.25, "consumer_type": "mixed"},
        }
    },
    "Southern_Region": {
        "base_mw": 3500,
        "nodes": {
            "Tamil_Nadu": {"fraction": 0.40, "consumer_type": "industrial_medium"},
            "Karnataka": {"fraction": 0.35, "consumer_type": "mixed"},
            "Andhra_Pradesh": {"fraction": 0.25, "consumer_type": "agricultural"},
        }
    },
    "Eastern_Region": {
        "base_mw": 2800,
        "nodes": {
            "West_Bengal": {"fraction": 0.45, "consumer_type": "mixed"},
            "Odisha_Industrial": {"fraction": 0.35, "consumer_type": "industrial_large"},
            "Bihar": {"fraction": 0.20, "consumer_type": "residential"},
        }
    },
}

CONSUMER_TYPES = [
    "residential", "commercial", "industrial_small", "industrial_medium",
    "industrial_large", "hospital", "school", "hotel"
]

records = []

SEASON_FACTORS = {1: 0.88, 2: 0.90, 3: 1.05, 4: 1.18, 5: 1.28,
                  6: 1.10, 7: 1.05, 8: 1.05, 9: 1.05, 10: 0.95,
                  11: 0.90, 12: 0.85}

for ts in idx:
    hour = ts.hour
    month = ts.month
    dow = ts.dayofweek

    seasonal = SEASON_FACTORS.get(month, 1.0)

    if 6 <= hour <= 10:
        hourly = 1.12
    elif 18 <= hour <= 22:
        hourly = 1.32
    elif 23 <= hour or hour <= 4:
        hourly = 0.60
    else:
        hourly = 1.00

    weekend_factor = 0.87 if dow >= 5 else 1.0

    if ts.date() in [date(2025, 1, 26), date(2025, 8, 15),
                      date(2025, 10, 2), date(2025, 11, 1)]:
        holiday_factor = 0.82
    else:
        holiday_factor = 1.0

    for area_name, area_cfg in AREAS.items():
        base = area_cfg["base_mw"]
        for node_name, node_cfg in area_cfg["nodes"].items():
            frac = node_cfg["fraction"]
            ctype = node_cfg["consumer_type"]

            noise = np.random.normal(0, 0.025)
            trend = 1.0 + (ts - idx[0]).days * 0.00008

            gross = base * frac * seasonal * hourly * weekend_factor * holiday_factor * trend * (1 + noise)
            gross = max(gross, base * frac * 0.3)

            solar_peak = max(0, np.sin(np.pi * (hour - 6) / 12)) if 6 <= hour <= 18 else 0
            solar = gross * 0.07 * solar_peak * (1 + np.random.normal(0, 0.1))
            solar = max(0, solar)

            net = max(0, gross - solar)
            capacity = gross * 1.18 + base * frac * 0.05

            records.append({
                "datetime": ts,
                "area": area_name,
                "node": node_name,
                "consumer_type": ctype,
                "gross_demand_mw": round(gross, 3),
                "solar_generation_mw": round(solar, 3),
                "net_demand_mw": round(net, 3),
                "available_capacity_mw": round(capacity, 3),
            })

load_df = pd.DataFrame(records)
load_df.to_csv("data/raw/sample_load_data.csv", index=False)
print(f"    Generated {len(load_df):,} records across {len(AREAS)} regions, "
      f"{sum(len(v['nodes']) for v in AREAS.values())} nodes")
print("    Saved: data/raw/sample_load_data.csv")

print("\n[3/3] Generating capacity data...")

capacity_records = [
    {"plant_name": "Singrauli_STPS", "area": "Northern_Region", "fuel_type": "coal",
     "installed_mw": 2000, "availability_factor": 0.85},
    {"plant_name": "Rihand_STPS", "area": "Northern_Region", "fuel_type": "coal",
     "installed_mw": 3000, "availability_factor": 0.82},
    {"plant_name": "Dadri_Gas", "area": "Northern_Region", "fuel_type": "gas",
     "installed_mw": 817, "availability_factor": 0.75},
    {"plant_name": "Tehri_Hydro", "area": "Northern_Region", "fuel_type": "hydro",
     "installed_mw": 1000, "availability_factor": 0.70},
    {"plant_name": "Rajasthan_Atomic", "area": "Western_Region", "fuel_type": "nuclear",
     "installed_mw": 1180, "availability_factor": 0.80},
    {"plant_name": "Mundra_UMPP", "area": "Western_Region", "fuel_type": "coal",
     "installed_mw": 4620, "availability_factor": 0.88},
    {"plant_name": "Kutch_Wind_Farm", "area": "Western_Region", "fuel_type": "wind",
     "installed_mw": 500, "availability_factor": 0.35},
    {"plant_name": "Gujarat_Solar_Park", "area": "Western_Region", "fuel_type": "solar",
     "installed_mw": 700, "availability_factor": 0.22},
    {"plant_name": "Ramagundam_STPS", "area": "Southern_Region", "fuel_type": "coal",
     "installed_mw": 2600, "availability_factor": 0.83},
    {"plant_name": "Kaiga_Nuclear", "area": "Southern_Region", "fuel_type": "nuclear",
     "installed_mw": 880, "availability_factor": 0.82},
    {"plant_name": "Sharavathi_Hydro", "area": "Southern_Region", "fuel_type": "hydro",
     "installed_mw": 1035, "availability_factor": 0.65},
    {"plant_name": "Tamil_Nadu_Wind", "area": "Southern_Region", "fuel_type": "wind",
     "installed_mw": 900, "availability_factor": 0.32},
    {"plant_name": "Farakka_STPS", "area": "Eastern_Region", "fuel_type": "coal",
     "installed_mw": 2100, "availability_factor": 0.80},
    {"plant_name": "Talcher_STPS", "area": "Eastern_Region", "fuel_type": "coal",
     "installed_mw": 3000, "availability_factor": 0.84},
    {"plant_name": "Eastern_Hydro", "area": "Eastern_Region", "fuel_type": "hydro",
     "installed_mw": 600, "availability_factor": 0.60},
]
cap_df = pd.DataFrame(capacity_records)
cap_df.to_csv("data/raw/capacity_data.csv", index=False)
print(f"    Created {len(cap_df)} power plants")
print(f"    Total installed: {cap_df['installed_mw'].sum():,} MW")
total_avail = (cap_df["installed_mw"] * cap_df["availability_factor"]).sum()
print(f"    Total available: {total_avail:,.0f} MW")
print("    Saved: data/raw/capacity_data.csv")

if weather_df is not None:
    print("\n[Bonus] Merging weather with load data for convenience...")
    weather_df.set_index("datetime", inplace=True)
    system_load = load_df.groupby("datetime").agg(
        gross_demand_mw=("gross_demand_mw", "sum"),
        solar_generation_mw=("solar_generation_mw", "sum"),
        net_demand_mw=("net_demand_mw", "sum"),
        available_capacity_mw=("available_capacity_mw", "sum")
    )
    system_load.index = pd.to_datetime(system_load.index)
    merged = system_load.join(weather_df, how="left")
    merged.to_csv("data/raw/system_load_with_weather.csv")
    print(f"    Saved merged dataset: {len(merged)} records")
    print("    Saved: data/raw/system_load_with_weather.csv")

print("\n" + "=" * 60)
print("DATA SETUP COMPLETE")
print("=" * 60)
print("\nFiles created:")
print("  data/raw/sample_load_data.csv    - Area/node-wise load (all regions)")
print("  data/raw/capacity_data.csv       - Power plant capacity data")
if weather_df is not None:
    print("  data/raw/weather_delhi_365days.csv - Real weather data from Open-Meteo")
    print("  data/raw/system_load_with_weather.csv - Merged system dataset")
print("\nTo use REAL data:")
print("  1. Download from POSOCO: https://posoco.in/reports/")
print("  2. Download state SLDC reports from respective state websites")
print("  3. Upload via the dashboard at http://localhost:3000/upload")
print("\nNext step: python -m uvicorn backend.api.main:app --reload")
