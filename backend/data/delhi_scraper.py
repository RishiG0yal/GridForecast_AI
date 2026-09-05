import logging
import re
import time
from datetime import date, datetime
from pathlib import Path

import httpx
import pandas as pd
from bs4 import BeautifulSoup

logger = logging.getLogger("delhi_scraper")


class DelhiSLDCScraper:
    HOME_URL = "https://www.delhisldc.org/HomeSldc.aspx"
    LOAD_URL = "https://www.delhisldc.org/Loaddata.aspx"
    OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
    OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"

    WEATHER_PARAMS = [
        "temperature_2m", "relative_humidity_2m", "precipitation",
        "windspeed_10m", "cloudcover", "shortwave_radiation",
        "direct_radiation", "apparent_temperature"
    ]

    LAT = 28.6139
    LON = 77.2090

    def __init__(self, data_dir: str = "data/raw"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_cache = {}
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        }

    def _fetch_rendered(self, url: str) -> str:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            html = page.content()
            browser.close()
        return html

    def scrape_realtime_snapshot(self) -> dict:
        html = self._fetch_rendered(self.HOME_URL)
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(separator=" ", strip=True)

        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "source": "Delhi SLDC",
            "url": self.HOME_URL,
        }

        delhi_load = re.search(r"DELHI LOAD\s*([\d,]+)\s*MW", text)
        if delhi_load:
            snapshot["delhi_load_mw"] = float(delhi_load.group(1).replace(",", ""))

        scheduled = re.search(r"SCHEDULED LOAD\s*([\d,]+)\s*MW", text)
        if scheduled:
            snapshot["scheduled_load_mw"] = float(scheduled.group(1).replace(",", ""))

        drawal = re.search(r"DRAWAL FROM ISTS\s*([\d,]+)\s*MW", text)
        if drawal:
            snapshot["drawal_from_ists_mw"] = float(drawal.group(1).replace(",", ""))

        od_ud = re.search(r"OD\s*/\s*UD\s*(-?[\d,]+)\s*MW", text)
        if od_ud:
            snapshot["od_ud_mw"] = float(od_ud.group(1).replace(",", ""))

        gen = re.search(r"TOTAL GENERATION\s*\(?Delhi\)?\s*([\d,]+)\s*MW", text, re.IGNORECASE)
        if gen:
            snapshot["total_generation_mw"] = float(gen.group(1).replace(",", ""))

        freq = re.search(r"GRID FREQUENCY\s*\(?Delhi\)?\s*([\d.]+)\s*Hz", text, re.IGNORECASE)
        if freq:
            snapshot["grid_frequency_hz"] = float(freq.group(1))

        peak_today = re.search(r"Peak Demand \(Today\)\s*([\d,]+)\s*MW\s*at\s*([\d:]+)", text)
        if peak_today:
            snapshot["peak_demand_today_mw"] = float(peak_today.group(1).replace(",", ""))
            snapshot["peak_demand_today_time"] = peak_today.group(2)

        peak_yesterday = re.search(r"Peak Demand \(Yesterday\)\s*([\d,]+)\s*MW\s*at\s*([\d:]+)", text)
        if peak_yesterday:
            snapshot["peak_demand_yesterday_mw"] = float(peak_yesterday.group(1).replace(",", ""))

        max_demand = re.search(r"Maximum Demand \([\d-]+\)\s*([\d,]+)\s*MW\s*(\d{1,2}\s+\w+\s+\d{4})", text)
        if max_demand:
            snapshot["max_demand_year_mw"] = float(max_demand.group(1).replace(",", ""))
            snapshot["max_demand_date"] = max_demand.group(2)

        snapshot_time = re.search(r"DELHI DEMAND SNAPSHOT As on\s*([\d]+\s+\w+\s+\d{4}),\s*([\d:]+)", text)
        if snapshot_time:
            snapshot["data_as_on"] = f"{snapshot_time.group(1)} {snapshot_time.group(2)}"

        logger.info(f"Scraped snapshot: Delhi Load={snapshot.get('delhi_load_mw')} MW")
        self._snapshot_cache = snapshot
        return snapshot

    def scrape_today_timeslot_data(self) -> pd.DataFrame:
        html = self._fetch_rendered(self.LOAD_URL)
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table", id="ContentPlaceHolder3_DGGridAv")
        if not table:
            logger.warning("Loaddata table not found, returning empty DataFrame")
            return pd.DataFrame()

        rows = table.find_all("tr")
        if len(rows) < 2:
            logger.warning("No data rows in Loaddata table")
            return pd.DataFrame()

        headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
        data = []
        today = date.today()
        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if cells and len(cells) == len(headers):
                row_dict = dict(zip(headers, cells))
                timeslot = row_dict.get("TIMESLOT", "")
                if timeslot:
                    try:
                        hour, minute = map(int, timeslot.split(":"))
                        dt = datetime.combine(today, __import__("datetime").time(hour, minute))
                        row_dict["datetime"] = dt
                    except Exception:
                        row_dict["datetime"] = None
                for col in ["DELHI", "BRPL", "BYPL", "NDPL", "NDMC", "MES"]:
                    if col in row_dict:
                        try:
                            row_dict[col] = float(str(row_dict[col]).replace(",", ""))
                        except Exception:
                            row_dict[col] = None
                data.append(row_dict)

        df = pd.DataFrame(data)
        if "DELHI" in df.columns:
            df.rename(columns={
                "DELHI": "gross_demand_mw",
                "BRPL": "brpl_mw",
                "BYPL": "bypl_mw",
                "NDPL": "ndpl_mw",
                "NDMC": "ndmc_mw",
                "MES": "mes_mw",
            }, inplace=True)
        return df

    def fetch_weather_now(self) -> dict:
        params = {
            "latitude": self.LAT,
            "longitude": self.LON,
            "current": ",".join([
                "temperature_2m", "relative_humidity_2m", "apparent_temperature",
                "precipitation", "windspeed_10m", "cloudcover", "shortwave_radiation"
            ]),
            "timezone": "Asia/Kolkata"
        }
        try:
            with httpx.Client(timeout=20) as client:
                r = client.get(self.OPEN_METEO_FORECAST, params=params)
                r.raise_for_status()
                data = r.json()
            current = data.get("current", {})
            return {
                "timestamp": datetime.now().isoformat(),
                "temperature": current.get("temperature_2m"),
                "humidity": current.get("relative_humidity_2m"),
                "feels_like": current.get("apparent_temperature"),
                "precipitation": current.get("precipitation"),
                "wind_speed": current.get("windspeed_10m"),
                "cloud_cover": current.get("cloudcover"),
                "solar_radiation": current.get("shortwave_radiation"),
                "lat": self.LAT,
                "lon": self.LON,
                "location": "Delhi, India"
            }
        except Exception:
            logger.error("Weather fetch failed")
            return {}

    def fetch_weather_forecast(self, hours: int = 48) -> pd.DataFrame:
        params = {
            "latitude": self.LAT,
            "longitude": self.LON,
            "hourly": ",".join(self.WEATHER_PARAMS),
            "forecast_days": max(2, hours // 24 + 1),
            "timezone": "Asia/Kolkata"
        }
        with httpx.Client(timeout=30) as client:
            r = client.get(self.OPEN_METEO_FORECAST, params=params)
            r.raise_for_status()
            data = r.json()
        df = pd.DataFrame(data["hourly"])
        df["datetime"] = pd.to_datetime(df["time"])
        df.drop(columns=["time"], inplace=True)
        df.rename(columns={
            "temperature_2m": "temperature",
            "relative_humidity_2m": "humidity",
            "windspeed_10m": "wind_speed",
            "shortwave_radiation": "solar_radiation",
            "apparent_temperature": "feels_like",
            "cloudcover": "cloud_cover",
        }, inplace=True)
        df.set_index("datetime", inplace=True)
        return df.iloc[:hours]

    def fetch_historical_weather(self, start_date: str, end_date: str) -> pd.DataFrame:
        params = {
            "latitude": self.LAT,
            "longitude": self.LON,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(self.WEATHER_PARAMS),
            "timezone": "Asia/Kolkata"
        }
        for attempt in range(3):
            try:
                with httpx.Client(timeout=90) as client:
                    r = client.get(self.OPEN_METEO_ARCHIVE, params=params)
                    r.raise_for_status()
                    data = r.json()
                df = pd.DataFrame(data["hourly"])
                df["datetime"] = pd.to_datetime(df["time"])
                df.drop(columns=["time"], inplace=True)
                df.rename(columns={
                    "temperature_2m": "temperature",
                    "relative_humidity_2m": "humidity",
                    "windspeed_10m": "wind_speed",
                    "shortwave_radiation": "solar_radiation",
                    "apparent_temperature": "feels_like",
                    "cloudcover": "cloud_cover",
                }, inplace=True)
                df.set_index("datetime", inplace=True)
                return df
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(3 * (attempt + 1))

    def fetch_real_demand(self, start_date: str, end_date: str) -> pd.DataFrame:
        import time as _time
        from datetime import datetime, timedelta

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt   = datetime.strptime(end_date,   "%Y-%m-%d")

        dates, cur = [], start_dt
        while cur <= end_dt:
            dates.append(cur)
            cur += timedelta(days=1)

        logger.info(f"Downloading {len(dates)} days of real demand from delhisldc.org API...")
        all_records = []
        failed = []

        with httpx.Client(timeout=20, headers=self._headers) as client:
            for i, dt in enumerate(dates):
                date_str = dt.strftime("%d/%m/%Y")
                try:
                    r = client.get(
                        f"https://delhisldc.org/api/load-curve-discom?fordate={date_str}"
                    )
                    data = r.json()
                    if isinstance(data, list) and len(data) > 0:
                        all_records.extend(data)
                    else:
                        failed.append(date_str)
                except Exception:
                    failed.append(date_str)
                if (i + 1) % 10 == 0:
                    _time.sleep(0.2)

        logger.info(f"Downloaded {len(all_records):,} records, {len(failed)} days failed")

        if not all_records:
            raise ValueError("No demand data returned from delhisldc.org API")

        df = pd.DataFrame(all_records)
        df["datetime"] = pd.to_datetime(
            df["FORDATE"].str.strip() + " " + df["TIMESLOT"].str.strip(),
            format="%d/%m/%Y %H:%M", errors="coerce"
        )
        df["VALUE"] = pd.to_numeric(df["VALUE"], errors="coerce")
        df = df.dropna(subset=["datetime", "VALUE"])

        entities = ["Delhi", "BRPL", "BYPL", "NDPL", "NDMC", "MES"]
        pivot = df[df["ENTITY"].isin(entities)].pivot_table(
            index="datetime", columns="ENTITY", values="VALUE", aggfunc="mean"
        )
        pivot.columns.name = None
        pivot.rename(columns={
            "Delhi": "gross_demand_mw",
            "BRPL": "brpl_mw", "BYPL": "bypl_mw",
            "NDPL": "ndpl_mw", "NDMC": "ndmc_mw", "MES": "mes_mw"
        }, inplace=True)
        hourly = pivot.resample("h").mean().dropna(subset=["gross_demand_mw"])
        return hourly

    def build_historical_dataset(self, days: int = 365) -> pd.DataFrame:
        from datetime import datetime, timedelta

        import numpy as np

        end_dt   = datetime.now() - timedelta(days=1)
        start_dt = datetime.now() - timedelta(days=days + 1)
        end   = end_dt.strftime("%Y-%m-%d")
        start = start_dt.strftime("%Y-%m-%d")

        logger.info(f"Fetching {days} days of real weather from Open-Meteo ({start} to {end})")
        weather_df = self.fetch_historical_weather(start, end)

        # Use real demand from the API first
        try:
            logger.info("Fetching real demand from delhisldc.org API...")
            demand_df = self.fetch_real_demand(start, end)
            merged = weather_df.join(demand_df, how="inner")
            merged["solar_generation_mw"] = self._estimate_solar(weather_df)
            merged["net_demand"] = (merged["gross_demand_mw"] - merged["solar_generation_mw"]).clip(lower=0)
            merged["available_capacity_mw"] = 9500.0
            merged["area"] = "Delhi"
            merged["node"] = "System"
            import numpy as np
            merged.replace([np.inf, -np.inf], np.nan, inplace=True)
            merged.ffill(inplace=True)
            merged.bfill(inplace=True)
            merged = merged.dropna(subset=["gross_demand_mw"])
            merged.to_csv(self.data_dir / "delhi_live_dataset.csv")
            logger.info(f"Real dataset: {len(merged)} rows, {merged['gross_demand_mw'].min():.0f}–{merged['gross_demand_mw'].max():.0f} MW")
            return merged
        except Exception as e:
            logger.warning(f"Real API fetch failed ({e}), falling back to calibrated synthetic demand")

        # Fallback only if API is down
        import numpy as np
        demand = self._generate_delhi_calibrated_demand(weather_df)
        merged = weather_df.copy()
        merged["gross_demand_mw"] = demand
        merged["solar_generation_mw"] = self._estimate_solar(weather_df)
        merged["net_demand"] = (merged["gross_demand_mw"] - merged["solar_generation_mw"]).clip(lower=0)
        merged["available_capacity_mw"] = 9500.0
        merged["area"] = "Delhi"
        merged["node"] = "System"
        merged.to_csv(self.data_dir / "delhi_live_dataset.csv")
        logger.info(f"Synthetic fallback dataset: {len(merged)} rows")
        return merged

    def _generate_delhi_calibrated_demand(self, weather_df: pd.DataFrame) -> pd.Series:
        import numpy as np
        idx = weather_df.index
        demand = pd.Series(index=idx, dtype=float)

        PEAK_RECORD = 8748
        TYPICAL_WINTER_MIN = 2800
        BASE = 4500

        for ts in idx:
            hour = ts.hour
            month = ts.month
            dow = ts.dayofweek

            if month in [5, 6, 7]:
                seasonal = 1.55
            elif month in [4, 8]:
                seasonal = 1.35
            elif month in [3, 9]:
                seasonal = 1.10
            elif month in [10, 11]:
                seasonal = 0.85
            elif month in [12, 1]:
                seasonal = 0.72
            elif month == 2:
                seasonal = 0.78

            if 18 <= hour <= 22:
                hourly = 1.30
            elif 10 <= hour <= 17:
                hourly = 1.18
            elif 6 <= hour <= 9:
                hourly = 1.10
            elif 0 <= hour <= 4:
                hourly = 0.58
            else:
                hourly = 0.80

            weekend_factor = 0.87 if dow >= 6 else 1.0

            temp = weather_df.loc[ts, "temperature"] if "temperature" in weather_df.columns else 25
            if pd.notna(temp):
                if temp > 35:
                    ac_load = (temp - 35) * 85
                elif temp < 12:
                    ac_load = (12 - temp) * 60
                else:
                    ac_load = 0
            else:
                ac_load = 0

            noise = np.random.normal(0, 0.018)
            d = BASE * seasonal * hourly * weekend_factor * (1 + noise) + ac_load
            d = max(TYPICAL_WINTER_MIN * 0.8, min(d, PEAK_RECORD))
            demand[ts] = round(d, 1)

        return demand

    def _estimate_solar(self, weather_df: pd.DataFrame) -> pd.Series:
        if "solar_radiation" not in weather_df.columns:
            return pd.Series(0.0, index=weather_df.index)
        capacity_mw = 800
        efficiency = 0.17
        return (weather_df["solar_radiation"] * capacity_mw * efficiency / 1000).clip(lower=0)

    def save_snapshot(self, snapshot: dict):
        path = self.data_dir / "delhi_sldc_snapshots.csv"
        row = {
            "datetime": snapshot.get("data_as_on", snapshot.get("timestamp", datetime.now().isoformat())),
            "gross_demand_mw": snapshot.get("delhi_load_mw"),
            "scheduled_load_mw": snapshot.get("scheduled_load_mw"),
            "drawal_ists_mw": snapshot.get("drawal_from_ists_mw"),
            "generation_mw": snapshot.get("total_generation_mw"),
            "grid_frequency_hz": snapshot.get("grid_frequency_hz"),
            "od_ud_mw": snapshot.get("od_ud_mw"),
        }
        df_new = pd.DataFrame([row])
        if path.exists():
            df_existing = pd.read_csv(path)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.drop_duplicates(subset=["datetime"], keep="last", inplace=True)
        else:
            df_combined = df_new
        df_combined.to_csv(path, index=False)
        logger.info(f"Snapshot saved. Total snapshots: {len(df_combined)}")

    def get_latest_snapshot(self) -> dict:
        if self._snapshot_cache:
            return self._snapshot_cache
        path = self.data_dir / "delhi_sldc_snapshots.csv"
        if path.exists():
            df = pd.read_csv(path)
            if not df.empty:
                return df.iloc[-1].to_dict()
        return {}
