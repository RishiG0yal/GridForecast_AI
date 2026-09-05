import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

Path("data/raw").mkdir(parents=True, exist_ok=True)
Path("data/processed").mkdir(parents=True, exist_ok=True)
Path("data/models").mkdir(parents=True, exist_ok=True)
Path("logs").mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Referer": "https://delhisldc.org/grid-watch/"
}

print("GridForecast AI — Downloading Real Delhi Data")
print("=" * 50)

# ── 1. Real demand from Delhi SLDC API ───────────────────────
print("\n[1/3] Downloading real demand from delhisldc.org...")
print("      Source: https://delhisldc.org/api/load-curve-discom")

start_dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
end_dt   = datetime.now(timezone.utc) - timedelta(days=1)

dates, cur = [], start_dt
while cur <= end_dt:
    dates.append(cur)
    cur += timedelta(days=1)

print(f"      Fetching {len(dates)} days ({start_dt.date()} → {end_dt.date()})...")

all_records = []
failed = []

with httpx.Client(timeout=20, headers=HEADERS) as client:
    for i, dt in enumerate(dates):
        date_str = dt.strftime("%d/%m/%Y")
        try:
            r = client.get(f"https://delhisldc.org/api/load-curve-discom?fordate={date_str}")
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                all_records.extend(data)
            else:
                failed.append(date_str)
        except Exception as e:
            print(f"Error: {e}")
            failed.append(date_str)
        if (i + 1) % 50 == 0:
            pct = int((i + 1) / len(dates) * 100)
            print(f"      {pct}% — {len(all_records):,} records", flush=True)
        if (i + 1) % 10 == 0:
            time.sleep(0.2)

print(f"      Done: {len(all_records):,} records, {len(failed)} days failed")

if len(all_records) < 100:
    print("      WARNING: Very few records downloaded. Check internet connection.")
    print("      Falling back to calibrated synthetic data...")
    use_synthetic = True
else:
    use_synthetic = False
    df_raw = pd.DataFrame(all_records)
    df_raw.to_csv("data/raw/delhi_real_demand_raw.csv", index=False)
    print("      Saved: data/raw/delhi_real_demand_raw.csv")

# ── 2. Real weather from Open-Meteo ──────────────────────────
print("\n[2/3] Downloading real weather from Open-Meteo...")
print("      Source: https://archive-api.open-meteo.com (free, no API key)")

end_weather   = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
start_weather = (datetime.now(timezone.utc) - timedelta(days=600)).strftime("%Y-%m-%d")

WEATHER_PARAMS = [
    "temperature_2m", "relative_humidity_2m", "precipitation",
    "windspeed_10m", "cloudcover", "shortwave_radiation",
    "direct_radiation", "apparent_temperature"
]

weather_df = None
for attempt in range(3):
    try:
        params = {
            "latitude": 28.6139, "longitude": 77.2090,
            "start_date": start_weather, "end_date": end_weather,
            "hourly": ",".join(WEATHER_PARAMS),
            "timezone": "Asia/Kolkata"
        }
        with httpx.Client(timeout=90) as client:
            r = client.get("https://archive-api.open-meteo.com/v1/archive", params=params)
            r.raise_for_status()
            wdata = r.json()
        weather_df = pd.DataFrame(wdata["hourly"])
        weather_df["datetime"] = pd.to_datetime(weather_df["time"])
        weather_df = weather_df.drop(columns=["time"]).set_index("datetime")
        weather_df.rename(columns={
            "temperature_2m": "temperature",
            "relative_humidity_2m": "humidity",
            "windspeed_10m": "wind_speed",
            "shortwave_radiation": "solar_radiation",
            "apparent_temperature": "feels_like",
            "cloudcover": "cloud_cover",
        }, inplace=True)
        weather_df.to_csv("data/raw/weather_delhi_365days.csv")
        print(f"      Downloaded {len(weather_df):,} hourly weather records")
        print("      Saved: data/raw/weather_delhi_365days.csv")
        break
    except Exception as e: # noqa: BLE001
        if attempt == 2:
            print(f"      WARNING: Weather download failed ({e})")
        else:
            print(f"      Retry {attempt + 1}...")
            time.sleep(3)

# ── 3. Process and merge ──────────────────────────────────────
print("\n[3/3] Merging demand + weather...")

if not use_synthetic:
    df_raw = pd.read_csv("data/raw/delhi_real_demand_raw.csv")
    df_raw["datetime"] = pd.to_datetime(
        df_raw["FORDATE"].str.strip() + " " + df_raw["TIMESLOT"].str.strip(),
        format="%d/%m/%Y %H:%M", errors="coerce"
    )
    df_raw["VALUE"] = pd.to_numeric(df_raw["VALUE"], errors="coerce")
    df_raw = df_raw.dropna(subset=["datetime", "VALUE"])

    entities = ["Delhi", "BRPL", "BYPL", "NDPL", "NDMC", "MES"]
    pivot = df_raw[df_raw["ENTITY"].isin(entities)].pivot_table(
        index="datetime", columns="ENTITY", values="VALUE", aggfunc="mean"
    )
    pivot.columns.name = None
    pivot.rename(columns={
        "Delhi": "gross_demand_mw",
        "BRPL": "brpl_mw", "BYPL": "bypl_mw",
        "NDPL": "ndpl_mw", "NDMC": "ndmc_mw", "MES": "mes_mw"
    }, inplace=True)
    demand_hourly = pivot.resample("h").mean().dropna(subset=["gross_demand_mw"])
else:
    # Synthetic calibrated fallback
    idx = weather_df.index if weather_df is not None else pd.date_range("2025-01-01", periods=8760, freq="h")
    np.random.seed(42)
    records = []
    SEASON = {1:0.72,2:0.78,3:1.05,4:1.18,5:1.28,6:1.10,7:1.05,8:1.05,9:1.05,10:0.95,11:0.90,12:0.72}
    HOUR = {**{h:1.30 for h in range(18,23)}, **{h:1.18 for h in range(10,18)},
            **{h:1.10 for h in range(6,10)}, **{h:0.58 for h in range(5)}}
    for ts in idx:
        s = SEASON.get(ts.month, 1.0)
        h = HOUR.get(ts.hour, 0.80)
        w = 0.87 if ts.dayofweek >= 6 else 1.0
        d = 4500 * s * h * w * (1 + np.random.normal(0, 0.018))
        temp = weather_df.loc[ts, "temperature"] if weather_df is not None and ts in weather_df.index else 25
        if pd.notna(temp):
            if temp > 35: d += (temp - 35) * 85
            elif temp < 12: d += (12 - temp) * 60
        records.append({"datetime": ts, "gross_demand_mw": max(1400, min(d, 8748))})
    demand_hourly = pd.DataFrame(records).set_index("datetime")

if weather_df is not None:
    merged = demand_hourly.join(weather_df, how="inner")
else:
    merged = demand_hourly.copy()

merged["solar_generation_mw"] = 0.0
if "solar_radiation" in merged.columns:
    merged["solar_generation_mw"] = (merged["solar_radiation"] * 800 * 0.17 / 1000).clip(lower=0)
merged["net_demand"] = (merged["gross_demand_mw"] - merged["solar_generation_mw"]).clip(lower=0)
merged["available_capacity_mw"] = 9500.0
merged["area"] = "Delhi"
merged["node"] = "System"
merged.replace([np.inf, -np.inf], np.nan, inplace=True)
merged.ffill(inplace=True)
merged.bfill(inplace=True)
merged = merged.dropna(subset=["gross_demand_mw"])

merged.to_csv("data/raw/delhi_real_dataset.csv")
print(f"      Merged dataset: {len(merged):,} hourly records")
print(f"      Demand range: {merged['gross_demand_mw'].min():.0f} – {merged['gross_demand_mw'].max():.0f} MW")
print(f"      Source: {'REAL delhisldc.org data' if not use_synthetic else 'Calibrated synthetic (API unavailable)'}")
print("      Saved: data/raw/delhi_real_dataset.csv")

# ── Capacity data ─────────────────────────────────────────────
cap_path = Path("data/raw/capacity_data.csv")
if not cap_path.exists():
    import pandas as pd
    cap = pd.DataFrame([
        {"plant_name": "Singrauli_STPS",    "area": "Northern", "fuel_type": "coal",    "installed_mw": 2000, "availability_factor": 0.85},
        {"plant_name": "Rihand_STPS",        "area": "Northern", "fuel_type": "coal",    "installed_mw": 3000, "availability_factor": 0.82},
        {"plant_name": "Dadri_Gas",          "area": "Northern", "fuel_type": "gas",     "installed_mw": 817,  "availability_factor": 0.75},
        {"plant_name": "Tehri_Hydro",        "area": "Northern", "fuel_type": "hydro",   "installed_mw": 1000, "availability_factor": 0.70},
        {"plant_name": "Rajasthan_Atomic",   "area": "Western",  "fuel_type": "nuclear", "installed_mw": 1180, "availability_factor": 0.80},
        {"plant_name": "Mundra_UMPP",        "area": "Western",  "fuel_type": "coal",    "installed_mw": 4620, "availability_factor": 0.88},
        {"plant_name": "Ramagundam_STPS",    "area": "Southern", "fuel_type": "coal",    "installed_mw": 2600, "availability_factor": 0.83},
        {"plant_name": "Kaiga_Nuclear",      "area": "Southern", "fuel_type": "nuclear", "installed_mw": 880,  "availability_factor": 0.82},
        {"plant_name": "Farakka_STPS",       "area": "Eastern",  "fuel_type": "coal",    "installed_mw": 2100, "availability_factor": 0.80},
        {"plant_name": "Talcher_STPS",       "area": "Eastern",  "fuel_type": "coal",    "installed_mw": 3000, "availability_factor": 0.84},
    ])
    cap.to_csv(cap_path, index=False)

print("\n" + "=" * 50)
print("DATA DOWNLOAD COMPLETE")
print(f"  Demand records : {len(merged):,} hourly  ({'REAL' if not use_synthetic else 'calibrated'})")
print(f"  Weather records: {len(weather_df) if weather_df is not None else 0:,} hourly  (REAL)")
print("=" * 50)
