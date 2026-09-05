import json
import logging
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger("live_scheduler")

_scheduler: BackgroundScheduler = None
_scraper = None
_last_snapshot: dict = {}
_live_status = {
    "last_scraped": None,
    "last_weather": None,
    "snapshots_today": 0,
    "current_demand_mw": None,
    "grid_frequency_hz": None,
    "is_live": False,
    "error": None,
}


def _scrape_job():
    global _last_snapshot, _live_status
    try:
        logger.info("Running live Delhi SLDC scrape...")
        snap = _scraper.scrape_realtime_snapshot()
        _scraper.save_snapshot(snap)
        _last_snapshot = snap
        _live_status.update({
            "last_scraped": datetime.now().isoformat(),
            "snapshots_today": _live_status.get("snapshots_today", 0) + 1,
            "current_demand_mw": snap.get("delhi_load_mw"),
            "scheduled_load_mw": snap.get("scheduled_load_mw"),
            "generation_mw": snap.get("total_generation_mw"),
            "grid_frequency_hz": snap.get("grid_frequency_hz"),
            "peak_demand_today_mw": snap.get("peak_demand_today_mw"),
            "od_ud_mw": snap.get("od_ud_mw"),
            "is_live": True,
            "error": None,
        })
        logger.info(f"Live scrape OK: Delhi Load={snap.get('delhi_load_mw')} MW, "
                    f"Freq={snap.get('grid_frequency_hz')} Hz")

        snapshot_path = Path("data/raw/latest_snapshot.json")
        with open(snapshot_path, "w") as f:
            json.dump(snap, f, indent=2, default=str)

    except Exception as e:
        logger.error(f"Live scrape failed: {e}", exc_info=True)
        _live_status["error"] = str(e)
        _live_status["is_live"] = False


def _weather_job():
    global _live_status
    try:
        logger.info("Fetching live weather...")
        weather = _scraper.fetch_weather_now()
        _live_status["last_weather"] = datetime.now().isoformat()
        _live_status["weather"] = weather
        weather_path = Path("data/raw/latest_weather.json")
        with open(weather_path, "w") as f:
            json.dump(weather, f, indent=2, default=str)
        logger.info(f"Weather OK: {weather.get('temperature')}°C, {weather.get('humidity')}% RH")
    except Exception as e:
        logger.error(f"Weather fetch failed: {e}")


def _retrain_job(forecaster=None):
    if forecaster is None:
        return
    try:
        logger.info("Scheduled model retrain starting...")
        dataset_path = "data/raw/delhi_live_dataset.csv"
        weather_path = "data/raw/weather_delhi_live.csv"
        if not Path(dataset_path).exists():
            logger.warning("No Delhi live dataset found for retrain")
            return
        import pandas as pd
        df = pd.read_csv(dataset_path)
        df["datetime"] = pd.to_datetime(df.index if "datetime" not in df.columns else df["datetime"])
        if "datetime" in df.columns:
            df.set_index("datetime", inplace=True)
        weather_df = pd.DataFrame()
        if Path(weather_path).exists():
            weather_df = pd.read_csv(weather_path)
            weather_df["datetime"] = pd.to_datetime(weather_df.index if "datetime" not in weather_df.columns else weather_df["datetime"])
            if "datetime" in weather_df.columns:
                weather_df.set_index("datetime", inplace=True)
        forecaster.pipeline.prepare_training_data(df, weather_df)
        forecaster.prepare_features()
        forecaster.train_models()
        forecaster.evaluate_models()
        forecaster.save_state()
        logger.info("Scheduled retrain complete")
    except Exception as e:
        logger.error(f"Retrain failed: {e}", exc_info=True)


def start_live_scheduler(forecaster=None, scrape_interval_minutes: int = 15):
    global _scheduler, _scraper

    from .delhi_scraper import DelhiSLDCScraper
    _scraper = DelhiSLDCScraper()

    _scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    _scheduler.add_job(
        _scrape_job,
        trigger=IntervalTrigger(minutes=scrape_interval_minutes),
        id="live_scrape",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=120
    )

    _scheduler.add_job(
        _weather_job,
        trigger=IntervalTrigger(minutes=10),
        id="live_weather",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=60
    )

    if forecaster:
        _scheduler.add_job(
            lambda: _retrain_job(forecaster),
            trigger=CronTrigger(hour=2, minute=30),
            id="nightly_retrain",
            replace_existing=True,
        )

    _scheduler.start()
    logger.info(f"Live scheduler started. Scraping Delhi SLDC every {scrape_interval_minutes} min")

    _scrape_job()
    _weather_job()

    return _scheduler


def stop_live_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def get_live_status() -> dict:
    return _live_status.copy()


def get_latest_snapshot() -> dict:
    path = Path("data/raw/latest_snapshot.json")
    if path.exists():
        with open(path) as f:
            return json.load(f)
    if _scraper:
        return _scraper.get_latest_snapshot()
    return {}


def get_latest_weather() -> dict:
    path = Path("data/raw/latest_weather.json")
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}
