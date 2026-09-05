import logging
import shutil
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from ..data.live_scheduler import (
    get_latest_snapshot,
    get_latest_weather,
    get_live_status,
    start_live_scheduler,
    stop_live_scheduler,
)
from ..engine.forecaster import DemandForecaster
from ..utils.database import init_db
from .schemas import (
    CapacityUploadResponse,
    DashboardOverviewResponse,
    DemandMetrics,
    LoadDataUploadResponse,
    PredictionPoint,
    PredictionResponse,
    RiskAlertSchema,
    RiskSummaryResponse,
    TrainingRequest,
    TrainingStatusResponse,
    WeatherDataResponse,
)

logger = logging.getLogger("api")

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

_forecaster: DemandForecaster = None
_training_status = {
    "status": "idle", "progress_pct": 0, "current_model": None,
    "metrics": None, "error": None
}
_load_filepath: str = None
_capacity_filepath: str = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _forecaster
    await init_db()
    _forecaster = DemandForecaster()

    try:
        _forecaster.load_state("data/models")
        logger.info("Loaded existing model state")
    except Exception:
        logger.info("No saved state found")

    dataset_loaded = False
    for dataset_path in [
        "data/raw/delhi_real_dataset.csv",
        "data/raw/delhi_live_dataset.csv",
        "data/raw/system_load_with_weather.csv",
    ]:
        if Path(dataset_path).exists():
            try:
                import pandas as pd
                df = pd.read_csv(dataset_path, index_col=0, parse_dates=True)
                if "net_demand_mw" in df.columns and "net_demand" not in df.columns:
                    df["net_demand"] = df["net_demand_mw"]
                _forecaster._raw_df = df
                _forecaster.prepared_df = _forecaster.pipeline.prepare_training_data(df)
                logger.info(f"Auto-loaded {dataset_path} ({len(_forecaster.prepared_df)} rows)")
                dataset_loaded = True
                break
            except Exception as e:
                logger.warning(f"Could not auto-load {dataset_path}: {e}")

    if dataset_loaded and _forecaster.registry.comparison_df.empty:
        import threading

        def _auto_train():
            try:
                _training_status.update({"status": "loading_data", "progress_pct": 5})
                for dp in ["data/raw/delhi_real_dataset.csv",
                           "data/raw/delhi_live_dataset.csv",
                           "data/raw/system_load_with_weather.csv"]:
                    if Path(dp).exists():
                        load_path = dp
                        break
                weather_config = {
                    "lat": 28.6139, "lon": 77.2090,
                    "start_date": (datetime.now() - timedelta(days=367)).strftime("%Y-%m-%d"),
                    "end_date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
                }
                _training_status.update({"status": "fetching_weather", "progress_pct": 15})
                _forecaster.load_data(load_path, weather_config=weather_config)
                _training_status.update({"status": "engineering_features", "progress_pct": 30})
                _forecaster.prepare_features()

                def progress_cb(model_name, pct):
                    _training_status.update({
                        "status": "training",
                        "current_model": model_name,
                        "progress_pct": 30 + int(pct * 0.55)
                    })

                _forecaster.train_models(
                    model_list=["LinearRegression", "DecisionTree", "RandomForest",
                                "XGBoost", "GradientBoosting", "NaiveBayes"],
                    progress_callback=progress_cb
                )
                _training_status.update({"status": "evaluating", "progress_pct": 88})
                metrics_df = _forecaster.evaluate_models()
                _training_status.update({"status": "saving", "progress_pct": 95})
                _forecaster.save_state("data/models")
                best = _forecaster.registry.get_best_model()
                _training_status.update({
                    "status": "completed", "progress_pct": 100, "current_model": None,
                    "metrics": metrics_df.to_dict("records") if not metrics_df.empty else []
                })
                logger.info(f"Auto-training done. Best: {best.model_name if best else 'N/A'}")
            except Exception as e:
                logger.error(f"Auto-training failed: {e}", exc_info=True)
                _training_status.update({"status": "failed", "error": str(e)})

        threading.Thread(target=_auto_train, daemon=True).start()
        logger.info("Auto-training started in background")

    try:
        start_live_scheduler(_forecaster, scrape_interval_minutes=15)
        logger.info("Live Delhi SLDC scheduler started")
    except Exception as e:
        logger.warning(f"Live scheduler start failed: {e}")
    yield
    stop_live_scheduler()


app = FastAPI(
    title="GridForecast AI",
    description="Electricity Demand Forecasting System — Delhi Grid",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/api/data/upload/load", response_model=LoadDataUploadResponse)
async def upload_load_data(file: UploadFile = File(...)):
    global _load_filepath
    if not file.filename.endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(400, "Only CSV and Excel files supported")
    dest = RAW_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    _load_filepath = str(dest)
    try:
        df = pd.read_csv(dest) if str(dest).endswith(".csv") else pd.read_excel(dest)
        date_range = {}
        for col in df.columns:
            try:
                parsed = pd.to_datetime(df[col])
                date_range = {"start": str(parsed.min()), "end": str(parsed.max())}
                break
            except Exception:
                pass
        return LoadDataUploadResponse(
            filename=file.filename,
            rows=len(df),
            columns=df.columns.tolist(),
            date_range=date_range,
            message="Load data uploaded successfully"
        )
    except Exception as e:
        raise HTTPException(500, f"File parsing error: {e}")


@app.post("/api/data/upload/capacity", response_model=CapacityUploadResponse)
async def upload_capacity_data(file: UploadFile = File(...)):
    global _capacity_filepath
    dest = RAW_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    _capacity_filepath = str(dest)
    try:
        df = pd.read_csv(dest)
        installed_col = next(
            (c for c in df.columns if "installed" in c.lower() or "capacity" in c.lower()), None
        )
        total_installed = float(df[installed_col].sum()) if installed_col else 0.0
        factor_col = next((c for c in df.columns if "factor" in c.lower()), None)
        if factor_col and installed_col:
            total_avail = float((df[installed_col] * df[factor_col]).sum())
        else:
            total_avail = total_installed * 0.85
        return CapacityUploadResponse(
            filename=file.filename,
            plants=len(df),
            total_installed_mw=round(total_installed, 2),
            total_available_mw=round(total_avail, 2),
            message="Capacity data uploaded successfully"
        )
    except Exception as e:
        raise HTTPException(500, f"File parsing error: {e}")


@app.get("/api/data/weather")
async def fetch_weather(
    lat: float = Query(28.6139),
    lon: float = Query(77.2090),
    start: str = Query(None),
    end: str = Query(None)
):
    from ..data.collector import WeatherCollector
    wc = WeatherCollector()
    if not start:
        start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end:
        end = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    try:
        df = wc.fetch_historical_weather(lat, lon, start, end)
        return WeatherDataResponse(
            start_date=start,
            end_date=end,
            hours=len(df),
            columns=df.columns.tolist(),
            message="Weather data fetched successfully"
        )
    except Exception as e:
        raise HTTPException(500, f"Weather API error: {e}")


@app.get("/api/data/status")
async def data_status():
    load_exists = _load_filepath and Path(_load_filepath).exists()
    cap_exists = _capacity_filepath and Path(_capacity_filepath).exists()
    models_trained = not _forecaster.registry.comparison_df.empty if _forecaster else False
    return {
        "load_data_uploaded": load_exists,
        "capacity_data_uploaded": cap_exists,
        "models_trained": models_trained,
        "training_status": _training_status["status"],
        "data_prepared": _forecaster.prepared_df is not None if _forecaster else False,
    }


def _run_training(request: TrainingRequest):
    global _training_status
    try:
        _training_status.update({"status": "loading_data", "progress_pct": 5})

        if _load_filepath and Path(_load_filepath).exists():
            load_path = _load_filepath
        else:
            live_path = Path("data/raw/delhi_live_dataset.csv")
            synthetic_path = Path("data/raw/sample_load_data.csv")
            if live_path.exists():
                load_path = str(live_path)
            elif synthetic_path.exists():
                load_path = str(synthetic_path)
            else:
                area_config = {
                    "Delhi": {"base_mw": 5000, "nodes": {
                        "North_Delhi": {"fraction": 0.28, "type": "mixed"},
                        "South_Delhi": {"fraction": 0.32, "type": "commercial"},
                        "East_Delhi": {"fraction": 0.22, "type": "residential"},
                        "West_Delhi": {"fraction": 0.18, "type": "industrial_medium"},
                    }}
                }
                from ..data.collector import LoadDataCollector
                lc = LoadDataCollector()
                load_df = lc.generate_synthetic_base(area_config, days=365)
                load_df.to_csv("data/raw/synthetic_load.csv")
                load_path = "data/raw/synthetic_load.csv"

        weather_config = {
            "lat": request.lat,
            "lon": request.lon,
            "start_date": (datetime.now() - timedelta(days=367)).strftime("%Y-%m-%d"),
            "end_date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
        }

        _training_status.update({"status": "fetching_weather", "progress_pct": 15})
        _forecaster.load_data(
            load_path,
            weather_config=weather_config,
            capacity_filepath=_capacity_filepath
        )

        _training_status.update({"status": "engineering_features", "progress_pct": 30})
        _forecaster.prepare_features()

        def progress_cb(model_name, pct):
            _training_status.update({
                "status": "training",
                "current_model": model_name,
                "progress_pct": 30 + int(pct * 0.55)
            })

        _training_status.update({"status": "training", "progress_pct": 35})
        _forecaster.train_models(
            model_list=request.model_list,
            progress_callback=progress_cb
        )

        _training_status.update({"status": "evaluating", "progress_pct": 88})
        metrics_df = _forecaster.evaluate_models()

        _training_status.update({"status": "saving", "progress_pct": 95})
        _forecaster.save_state("data/models")

        best = _forecaster.registry.get_best_model()
        _training_status.update({
            "status": "completed",
            "progress_pct": 100,
            "current_model": None,
            "metrics": metrics_df.to_dict("records") if not metrics_df.empty else []
        })
        logger.info(f"Training done. Best: {best.model_name if best else 'N/A'}")

    except Exception as e:
        logger.error(f"Training error: {e}", exc_info=True)
        _training_status.update({"status": "failed", "error": str(e), "progress_pct": 0})


@app.post("/api/train")
async def start_training(request: TrainingRequest, background_tasks: BackgroundTasks):
    if _training_status["status"] in ("training", "loading_data", "fetching_weather",
                                       "engineering_features", "evaluating", "saving"):
        raise HTTPException(409, "Training already in progress")
    _training_status.update({"status": "queued", "progress_pct": 0, "error": None})
    background_tasks.add_task(_run_training, request)
    return {"message": "Training started", "status": "queued"}


@app.get("/api/train/status", response_model=TrainingStatusResponse)
async def training_status():
    return TrainingStatusResponse(**_training_status)


@app.get("/api/models/comparison")
async def model_comparison():
    if _forecaster is None or _forecaster.registry.comparison_df.empty:
        return {"models": [], "best_model": None}
    df = _forecaster.registry.comparison_df
    best = _forecaster.registry.get_best_model()
    return {"models": df.to_dict("records"), "best_model": best.model_name if best else None}


@app.get("/api/predict")
async def predict(
    hours: int = Query(48),
    lat: float = Query(28.6139),
    lon: float = Query(77.2090)
):
    if _forecaster is None:
        raise HTTPException(503, "Forecaster not initialized")
    if _forecaster.registry.comparison_df.empty:
        raise HTTPException(400, "Models not trained yet")
    try:
        from ..data.collector import WeatherCollector
        wc = WeatherCollector()
        weather_fc = wc.fetch_forecast_weather(lat, lon, hours)
        preds_df = _forecaster.predict_next_48h(weather_fc, hours=hours)
        best = _forecaster.registry.get_best_model()
        points = [
            PredictionPoint(
                timestamp=str(idx),
                predicted_demand=row["predicted_demand"],
                ensemble_prediction=row.get("ensemble_prediction"),
                lower_bound=row["lower_bound"],
                upper_bound=row["upper_bound"]
            )
            for idx, row in preds_df.iterrows()
        ]
        return PredictionResponse(
            model_used=best.model_name if best else "ensemble",
            horizon_hours=hours,
            predictions=points,
            generated_at=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(500, f"Prediction error: {e}")


@app.get("/api/predict/horizons")
async def predict_horizons(lat: float = Query(28.6139), lon: float = Query(77.2090)):
    if _forecaster is None or _forecaster.registry.comparison_df.empty:
        raise HTTPException(400, "Models not trained yet")
    try:
        from ..data.collector import WeatherCollector
        from ..engine.risk_engine import RiskEngine
        wc = WeatherCollector()
        weather_fc = wc.fetch_forecast_weather(lat, lon, hours=168)
        preds_df = _forecaster.predict_next_48h(weather_fc, hours=168)
        best = _forecaster.registry.get_best_model()
        model_name = best.model_name if best else "ensemble"

        cap = _forecaster.capacity_collector.get_area_capacity()
        default_cap = (
            sum(v.get("available_mw", 0) for v in cap.values())
            if cap else 9500.0
        )
        re = RiskEngine()

        def summarize(hours: int, label: str) -> dict:
            sl = preds_df.iloc[:hours]
            peak = float(sl["predicted_demand"].max())
            util = round(peak / default_cap * 100, 1) if default_cap > 0 else None
            return {
                "label": label,
                "hours": hours,
                "next_value_mw": round(float(sl.iloc[0]["predicted_demand"]), 1),
                "peak_mw": round(peak, 1),
                "avg_mw": round(float(sl["predicted_demand"].mean()), 1),
                "end_value_mw": round(float(sl.iloc[-1]["predicted_demand"]), 1),
                "lower_bound": round(float(sl.iloc[0]["lower_bound"]), 1),
                "upper_bound": round(float(sl.iloc[0]["upper_bound"]), 1),
                "utilization_pct": util,
                "risk_level": re.classify_risk(util or 0).value,
                "timestamps": [str(i) for i in sl.index],
                "values": [round(float(v), 1) for v in sl["predicted_demand"].values],
                "lower": [round(float(v), 1) for v in sl["lower_bound"].values],
                "upper": [round(float(v), 1) for v in sl["upper_bound"].values],
            }

        return {
            "model_used": model_name,
            "generated_at": datetime.now().isoformat(),
            "horizons": [
                summarize(1, "Next 1 Hour"),
                summarize(2, "Next 2 Hours"),
                summarize(24, "Next 24 Hours"),
                summarize(min(168, len(preds_df)), "Next 7 Days"),
            ],
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/risk/analysis")
async def risk_analysis():
    if _forecaster is None or _forecaster.registry.comparison_df.empty:
        raise HTTPException(400, "Models not trained yet")
    try:
        preds = _forecaster.predict_next_48h(hours=48)
        report = _forecaster.run_risk_analysis(preds)
        alerts = [
            RiskAlertSchema(
                timestamp=str(a.timestamp),
                risk_level=a.risk_level.value,
                predicted_demand=a.predicted_demand,
                available_capacity=a.available_capacity,
                utilization_pct=a.utilization_pct,
                deficit_mw=a.deficit_mw,
                area=a.area,
                node=a.node,
                message=a.message,
                recommendations=a.recommendations
            )
            for a in report["alerts"]
        ]
        return {"alerts": alerts, "summary": report["summary"]}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/risk/alerts")
async def risk_alerts():
    if _forecaster is None or _forecaster.registry.comparison_df.empty:
        return {"alerts": [], "message": "No models trained"}
    try:
        preds = _forecaster.predict_next_48h(hours=48)
        report = _forecaster.run_risk_analysis(preds)
        alerts = [
            RiskAlertSchema(
                timestamp=str(a.timestamp),
                risk_level=a.risk_level.value,
                predicted_demand=a.predicted_demand,
                available_capacity=a.available_capacity,
                utilization_pct=a.utilization_pct,
                deficit_mw=a.deficit_mw,
                area=a.area,
                node=a.node,
                message=a.message,
                recommendations=a.recommendations
            )
            for a in report.get("high_risk_hours", [])
        ]
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as e:
        return {"alerts": [], "error": str(e)}


@app.get("/api/risk/summary")
async def risk_summary():
    if _forecaster is None or _forecaster.registry.comparison_df.empty:
        return RiskSummaryResponse(
            total_alerts=0, counts_by_level={},
            peak_utilization_pct=0, average_utilization_pct=0
        )
    try:
        preds = _forecaster.predict_next_48h(hours=48)
        report = _forecaster.run_risk_analysis(preds)
        return RiskSummaryResponse(**report["summary"])
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/dashboard/overview", response_model=DashboardOverviewResponse)
async def dashboard_overview():
    if _forecaster is None:
        return DashboardOverviewResponse()
    try:
        data_points = len(_forecaster.prepared_df) if _forecaster.prepared_df is not None else 0
        best = _forecaster.registry.get_best_model()
        metrics = None
        current_demand = None
        peak_forecast = None
        cap_util = None
        active_alerts = 0
        risk_level = "unknown"

        if _forecaster.prepared_df is not None:
            from ..data.processor import DemandCalculator
            m = DemandCalculator().calculate_demand_metrics(_forecaster.prepared_df)
            metrics = DemandMetrics(**m)
            current_demand = float(_forecaster.prepared_df["net_demand"].iloc[-1])

        if not _forecaster.registry.comparison_df.empty:
            try:
                preds = _forecaster.predict_next_48h(hours=48)
                peak_forecast = float(preds["predicted_demand"].max())
                report = _forecaster.run_risk_analysis(preds)
                active_alerts = len(report.get("high_risk_hours", []))
                cap_util = report["summary"].get("peak_utilization_pct")
                risk_level = report["summary"].get("highest_risk_level", "normal")
            except Exception:
                pass

        return DashboardOverviewResponse(
            current_demand_mw=round(current_demand, 2) if current_demand else None,
            peak_forecast_mw=round(peak_forecast, 2) if peak_forecast else None,
            capacity_utilization_pct=round(cap_util, 2) if cap_util else None,
            active_alerts=active_alerts,
            best_model=best.model_name if best else None,
            data_points=data_points,
            demand_metrics=metrics,
            risk_level=risk_level
        )
    except Exception as e:
        logger.error(f"Dashboard overview error: {e}")
        return DashboardOverviewResponse()


@app.get("/api/dashboard/demand-chart")
async def demand_chart(hours: int = Query(48)):
    if _forecaster is None or _forecaster.prepared_df is None:
        return {"actual": [], "predicted": []}
    try:
        actual_df = _forecaster.prepared_df.tail(hours)[["net_demand", "gross_demand_mw"]].copy()
        actual = [
            {
                "timestamp": str(idx),
                "actual_demand": round(float(row["net_demand"]), 2),
                "gross_demand": round(float(row["gross_demand_mw"]), 2)
            }
            for idx, row in actual_df.iterrows()
        ]
        predicted = []
        if not _forecaster.registry.comparison_df.empty:
            preds = _forecaster.predict_next_48h(hours=hours)
            predicted = [
                {
                    "timestamp": str(idx),
                    "predicted_demand": round(float(row["predicted_demand"]), 2),
                    "lower_bound": round(float(row["lower_bound"]), 2),
                    "upper_bound": round(float(row["upper_bound"]), 2)
                }
                for idx, row in preds.iterrows()
            ]
        return {"actual": actual, "predicted": predicted}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/dashboard/area-breakdown")
async def area_breakdown():
    if _forecaster is None:
        return {"areas": [], "consumer_types": []}
    try:
        raw_df = getattr(_forecaster, "_raw_df", None)
        df = raw_df if raw_df is not None else _forecaster.prepared_df
        if df is None:
            return {"areas": [], "consumer_types": []}

        DISCOM_MAP = {
            "brpl_mw": "BRPL (South/West Delhi)",
            "bypl_mw": "BYPL (East/Central Delhi)",
            "ndpl_mw": "NDPL (North Delhi)",
            "ndmc_mw": "NDMC (New Delhi Muncipal)",
            "mes_mw":  "MES (Cantonment)",
        }

        areas = []
        available = {col: label for col, label in DISCOM_MAP.items() if col in df.columns}

        if available:
            total = sum(float(df[col].mean()) for col in available)
            for col, label in available.items():
                avg = float(df[col].mean())
                areas.append({
                    "area": label,
                    "consumer_type": col.replace("_mw", "").upper(),
                    "demand_mw": round(avg, 2),
                    "percentage": round(avg / total * 100, 2) if total > 0 else 0,
                })
        elif "area" in df.columns:
            grp_col = "consumer_type" if "consumer_type" in df.columns else None
            demand_col = "gross_demand_mw" if "gross_demand_mw" in df.columns else "net_demand"
            if grp_col:
                grp = df.groupby(["area", grp_col])[demand_col].mean().reset_index()
            else:
                grp = df.groupby("area")[demand_col].mean().reset_index()
                grp["consumer_type"] = "mixed"
                grp.rename(columns={demand_col: demand_col}, inplace=True)
            total = float(grp[demand_col].sum())
            for _, row in grp.iterrows():
                areas.append({
                    "area": str(row["area"]),
                    "consumer_type": str(row.get("consumer_type", "mixed")),
                    "demand_mw": round(float(row[demand_col]), 2),
                    "percentage": round(float(row[demand_col]) / total * 100, 2) if total > 0 else 0,
                })

        return {"areas": areas, "consumer_types": list({a["consumer_type"] for a in areas})}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/dashboard/weather-correlation")
async def weather_correlation(hours: int = Query(168)):
    if _forecaster is None or _forecaster.prepared_df is None:
        return {"data": []}
    try:
        cols = ["net_demand"]
        for c in ["temperature", "humidity", "solar_radiation", "cloud_cover"]:
            if c in _forecaster.prepared_df.columns:
                cols.append(c)
        df = _forecaster.prepared_df.tail(hours)[cols].copy()
        data = []
        for idx, row in df.iterrows():
            point = {"timestamp": str(idx), "demand": round(float(row["net_demand"]), 2)}
            for c in ["temperature", "humidity", "solar_radiation", "cloud_cover"]:
                if c in row:
                    point[c] = round(float(row[c]), 2) if not pd.isna(row[c]) else None
            data.append(point)
        return {"data": data}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/dashboard/capacity-utilization")
async def capacity_utilization():
    if _forecaster is None:
        return {"areas": []}
    try:
        from ..engine.risk_engine import RiskEngine
        cap_data = _forecaster.capacity_collector.get_area_capacity()
        default_cap = 9500.0
        areas = []
        if _forecaster.registry.comparison_df.empty:
            for area, cap_info in (cap_data.items() if cap_data else {"system": {"available_mw": default_cap}}.items()):
                areas.append({
                    "area": area,
                    "available_mw": cap_info.get("available_mw", default_cap),
                    "predicted_demand_mw": 0,
                    "utilization_pct": 0,
                    "risk_level": "unknown"
                })
        else:
            preds = _forecaster.predict_next_48h(hours=48)
            peak_pred = float(preds["predicted_demand"].max())
            re = RiskEngine()
            for area, cap_info in (cap_data.items() if cap_data else {"system": {"available_mw": default_cap}}.items()):
                avail = cap_info.get("available_mw", default_cap)
                util = (peak_pred / avail * 100) if avail > 0 else 0
                areas.append({
                    "area": area,
                    "available_mw": round(avail, 2),
                    "predicted_demand_mw": round(peak_pred, 2),
                    "utilization_pct": round(util, 2),
                    "risk_level": re.classify_risk(util).value
                })
        return {"areas": areas}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/dashboard/model-performance")
async def model_performance():
    if _forecaster is None or _forecaster.registry.comparison_df.empty:
        return {"models": [], "best_model": None}
    df = _forecaster.registry.comparison_df
    best = _forecaster.registry.get_best_model()
    return {"models": df.to_dict("records"), "best_model": best.model_name if best else None}


@app.get("/api/live/snapshot")
async def live_snapshot():
    snap = get_latest_snapshot()
    weather = get_latest_weather()
    status = get_live_status()
    return {
        "snapshot": snap,
        "weather": weather,
        "scheduler_status": status,
        "is_live": status.get("is_live", False),
        "source": "Delhi SLDC (www.delhisldc.org)",
        "discoms": [
            "BRPL (South/West Delhi)",
            "BYPL (East/Central Delhi)",
            "NDPL (North Delhi)",
            "NDMC",
            "MES"
        ],
    }


@app.get("/api/live/status")
async def live_status():
    return get_live_status()


@app.post("/api/live/scrape-now")
async def scrape_now(background_tasks: BackgroundTasks):
    from ..data.live_scheduler import _scrape_job, _weather_job
    background_tasks.add_task(_scrape_job)
    background_tasks.add_task(_weather_job)
    return {"message": "Live scrape triggered", "timestamp": datetime.now().isoformat()}


@app.get("/api/live/history")
async def live_history(days: int = Query(7)):
    path = Path("data/raw/delhi_sldc_snapshots.csv")
    if not path.exists():
        return {"data": [], "message": "No live history yet"}
    df = pd.read_csv(path)
    df = df.tail(days * 24 * 4)
    return {
        "data": df.fillna(0).to_dict("records"),
        "total_records": len(df),
        "source": "Delhi SLDC live scrapes"
    }


@app.post("/api/live/build-dataset")
async def build_live_dataset(background_tasks: BackgroundTasks, days: int = Query(365)):
    def _build():
        from ..data.delhi_scraper import DelhiSLDCScraper
        scraper = DelhiSLDCScraper()
        df = scraper.build_historical_dataset(days=days)
        logger.info(f"Built live dataset: {len(df)} rows")
    background_tasks.add_task(_build)
    return {"message": f"Building {days}-day Delhi dataset", "status": "running"}


DISCOM_CONSUMER_PROFILE = {
    "BRPL": {
        "label": "BRPL (South/West Delhi)",
        "residential_pct": 42,
        "commercial_pct": 28,
        "low_industrial_pct": 8,
        "medium_industrial_pct": 10,
        "high_industrial_pct": 5,
        "hospital_24x7_pct": 5,
        "others_pct": 2,
        "area_sqkm": 182,
        "population_lakh": 45,
        "rooftop_solar_potential_mw": 420,
    },
    "BYPL": {
        "label": "BYPL (East/Central Delhi)",
        "residential_pct": 48,
        "commercial_pct": 20,
        "low_industrial_pct": 10,
        "medium_industrial_pct": 8,
        "high_industrial_pct": 3,
        "hospital_24x7_pct": 6,
        "others_pct": 5,
        "area_sqkm": 200,
        "population_lakh": 38,
        "rooftop_solar_potential_mw": 310,
    },
    "NDPL": {
        "label": "NDPL (North Delhi)",
        "residential_pct": 38,
        "commercial_pct": 22,
        "low_industrial_pct": 12,
        "medium_industrial_pct": 14,
        "high_industrial_pct": 8,
        "hospital_24x7_pct": 4,
        "others_pct": 2,
        "area_sqkm": 510,
        "population_lakh": 52,
        "rooftop_solar_potential_mw": 580,
    },
    "NDMC": {
        "label": "NDMC (New Delhi Municipal)",
        "residential_pct": 20,
        "commercial_pct": 45,
        "low_industrial_pct": 2,
        "medium_industrial_pct": 3,
        "high_industrial_pct": 2,
        "hospital_24x7_pct": 18,
        "others_pct": 10,
        "area_sqkm": 43,
        "population_lakh": 3,
        "rooftop_solar_potential_mw": 80,
    },
    "MES": {
        "label": "MES (Cantonment)",
        "residential_pct": 35,
        "commercial_pct": 15,
        "low_industrial_pct": 5,
        "medium_industrial_pct": 5,
        "high_industrial_pct": 20,
        "hospital_24x7_pct": 15,
        "others_pct": 5,
        "area_sqkm": 65,
        "population_lakh": 2,
        "rooftop_solar_potential_mw": 40,
    },
}

CONSUMER_COLORS = {
    "residential": "#38bdf8",
    "commercial": "#a78bfa",
    "low_industrial": "#fb923c",
    "medium_industrial": "#f59e0b",
    "high_industrial": "#ef4444",
    "hospital_24x7": "#34d399",
    "others": "#94a3b8",
}


@app.get("/api/areas/consumer-breakdown")
async def consumer_breakdown():
    raw_df = getattr(_forecaster, "_raw_df", None) if _forecaster else None
    result = []
    for key, profile in DISCOM_CONSUMER_PROFILE.items():
        col = f"{key.lower()}_mw"
        if raw_df is not None and col in raw_df.columns:
            avg_demand = float(raw_df[col].mean())
        else:
            avg_demand = 0.0
        categories = [
            {"category": "Residential",       "key": "residential",    "pct": profile["residential_pct"],    "demand_mw": round(avg_demand * profile["residential_pct"] / 100, 1)},
            {"category": "Commercial",         "key": "commercial",     "pct": profile["commercial_pct"],     "demand_mw": round(avg_demand * profile["commercial_pct"] / 100, 1)},
            {"category": "Low Industrial",     "key": "low_industrial", "pct": profile["low_industrial_pct"], "demand_mw": round(avg_demand * profile["low_industrial_pct"] / 100, 1)},
            {"category": "Medium Industrial",  "key": "medium_industrial","pct": profile["medium_industrial_pct"],"demand_mw": round(avg_demand * profile["medium_industrial_pct"] / 100, 1)},
            {"category": "High Industrial",    "key": "high_industrial","pct": profile["high_industrial_pct"],"demand_mw": round(avg_demand * profile["high_industrial_pct"] / 100, 1)},
            {"category": "Hospital / 24×7",    "key": "hospital_24x7", "pct": profile["hospital_24x7_pct"], "demand_mw": round(avg_demand * profile["hospital_24x7_pct"] / 100, 1)},
            {"category": "Others",             "key": "others",         "pct": profile["others_pct"],         "demand_mw": round(avg_demand * profile["others_pct"] / 100, 1)},
        ]
        result.append({
            "discom": key,
            "label": profile["label"],
            "total_demand_mw": round(avg_demand, 1),
            "categories": categories,
        })
    return {"discoms": result, "category_colors": CONSUMER_COLORS}


@app.get("/api/areas/load-balancing")
async def load_balancing():
    from ..engine.risk_engine import RiskEngine
    raw_df = getattr(_forecaster, "_raw_df", None) if _forecaster else None
    re = RiskEngine()
    recommendations = []
    system_total = 0.0
    system_capacity = 9500.0

    discom_status = []
    for key, profile in DISCOM_CONSUMER_PROFILE.items():
        col = f"{key.lower()}_mw"
        if raw_df is not None and col in raw_df.columns:
            current = float(raw_df[col].iloc[-1])
            avg = float(raw_df[col].mean())
            peak = float(raw_df[col].max())
        else:
            current = avg = peak = 0.0

        capacity_share = system_capacity * (profile["residential_pct"] + profile["commercial_pct"] +
                          profile["low_industrial_pct"] + profile["medium_industrial_pct"] +
                          profile["high_industrial_pct"] + profile["hospital_24x7_pct"] +
                          profile["others_pct"]) / 500
        capacity = round(system_capacity * current / max(sum(
            float(raw_df[f"{k.lower()}_mw"].iloc[-1]) for k in DISCOM_CONSUMER_PROFILE
            if raw_df is not None and f"{k.lower()}_mw" in raw_df.columns
        ), 1), 1) if raw_df is not None else system_capacity / 5

        util = round(current / capacity * 100, 1) if capacity > 0 else 0
        risk = re.classify_risk(util).value
        system_total += current

        actions = []
        if util >= 95:
            actions = [
                f"CRITICAL: Immediately shed {round(current * 0.05, 0):.0f} MW non-essential load",
                "Activate all available DG sets in industrial feeders",
                "Request emergency import from neighboring DISCOM",
                "Alert high-tension consumers to reduce load by 10%",
            ]
        elif util >= 85:
            actions = [
                f"Reduce high industrial load by {round(current * 0.04, 0):.0f} MW",
                "Activate time-of-use pricing signal to large consumers",
                "Pre-position load shedding schedule for residential feeders",
                "Coordinate with NDMC for shared reserve margin",
            ]
        elif util >= 70:
            actions = [
                "Monitor closely — approaching elevated threshold",
                f"Request {round(current * 0.02, 0):.0f} MW demand response from industrial consumers",
                "Ensure all standby feeders are in ready state",
            ]
        else:
            actions = [
                "Normal operations",
                "Maintain standard monitoring interval",
                f"Reserve margin available: {round(capacity - current, 0):.0f} MW",
            ]

        dr_potential = round(
            current * (profile["low_industrial_pct"] + profile["medium_industrial_pct"]) / 100 * 0.15, 1
        )
        interruptible = round(current * profile["high_industrial_pct"] / 100 * 0.30, 1)

        discom_status.append({
            "discom": key,
            "label": profile["label"],
            "current_mw": round(current, 1),
            "capacity_mw": round(capacity, 1),
            "utilization_pct": util,
            "risk_level": risk,
            "demand_response_potential_mw": dr_potential,
            "interruptible_load_mw": interruptible,
            "actions": actions,
            "load_factor": round(avg / peak, 3) if peak > 0 else 0,
        })
        recommendations.extend([{"discom": key, "action": a, "priority": risk} for a in actions[:2]])

    system_util = round(system_total / system_capacity * 100, 1)
    system_risk = re.classify_risk(system_util).value

    total_dr = sum(d["demand_response_potential_mw"] for d in discom_status)
    total_interruptible = sum(d["interruptible_load_mw"] for d in discom_status)

    return {
        "system_total_mw": round(system_total, 1),
        "system_capacity_mw": system_capacity,
        "system_utilization_pct": system_util,
        "system_risk": system_risk,
        "total_demand_response_mw": round(total_dr, 1),
        "total_interruptible_mw": round(total_interruptible, 1),
        "discoms": discom_status,
        "top_recommendations": sorted(recommendations, key=lambda x: ["normal","elevated","high","critical","capacity_exceeded"].index(x["priority"]), reverse=True)[:8],
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/solar/prediction")
async def solar_prediction():
    raw_df = getattr(_forecaster, "_raw_df", None) if _forecaster else None
    weather_now = get_latest_weather()
    solar_radiation = float(weather_now.get("solar_radiation", 350))
    cloud_cover = float(weather_now.get("cloud_cover", 30))

    PANEL_EFFICIENCY = 0.18
    PERFORMANCE_RATIO = 0.80
    AVG_ROOFTOP_SIZE_KW = 5.0
    PEAK_SUN_HOURS = 6.0
    UNITS_PER_KW_PER_DAY = PEAK_SUN_HOURS * PANEL_EFFICIENCY * PERFORMANCE_RATIO

    areas = []
    system_gross = 0.0
    system_solar = 0.0

    for key, profile in DISCOM_CONSUMER_PROFILE.items():
        col = f"{key.lower()}_mw"
        avg_demand = float(raw_df[col].mean()) if (raw_df is not None and col in raw_df.columns) else 0.0

        potential_mw = profile["rooftop_solar_potential_mw"]
        cloud_factor = 1.0 - (cloud_cover / 100) * 0.75
        current_gen_mw = round(potential_mw * cloud_factor * PANEL_EFFICIENCY * (solar_radiation / 1000), 2)
        current_gen_mw = min(current_gen_mw, potential_mw)

        daily_gen_mwh = round(potential_mw * UNITS_PER_KW_PER_DAY * 1000 / 1000, 1)
        rooftops_needed = int(avg_demand * 1000 / (AVG_ROOFTOP_SIZE_KW * UNITS_PER_KW_PER_DAY))
        rooftops_existing = int(potential_mw * 1000 / AVG_ROOFTOP_SIZE_KW)
        solar_coverage_pct = round(min(current_gen_mw / avg_demand * 100, 100), 1) if avg_demand > 0 else 0
        residual_mw = round(max(avg_demand - current_gen_mw, 0), 1)
        grid_savings_pct = round(current_gen_mw / avg_demand * 100, 1) if avg_demand > 0 else 0

        system_gross += avg_demand
        system_solar += current_gen_mw

        areas.append({
            "discom": key,
            "label": profile["label"],
            "area_sqkm": profile["area_sqkm"],
            "avg_demand_mw": round(avg_demand, 1),
            "rooftop_solar_potential_mw": potential_mw,
            "current_solar_generation_mw": current_gen_mw,
            "daily_generation_mwh": daily_gen_mwh,
            "solar_coverage_pct": solar_coverage_pct,
            "residual_demand_mw": residual_mw,
            "grid_savings_pct": grid_savings_pct,
            "rooftops_installed_estimate": rooftops_existing,
            "additional_rooftops_needed": max(0, rooftops_needed - rooftops_existing),
            "avg_units_per_rooftop_per_day": round(UNITS_PER_KW_PER_DAY * AVG_ROOFTOP_SIZE_KW, 2),
        })

    system_residual = round(system_gross - system_solar, 1)
    system_solar_pct = round(system_solar / system_gross * 100, 1) if system_gross > 0 else 0

    return {
        "weather_conditions": {
            "solar_radiation_wm2": solar_radiation,
            "cloud_cover_pct": cloud_cover,
            "timestamp": datetime.now().isoformat(),
        },
        "system_summary": {
            "total_demand_mw": round(system_gross, 1),
            "total_solar_generation_mw": round(system_solar, 1),
            "total_residual_demand_mw": system_residual,
            "solar_coverage_pct": system_solar_pct,
            "total_rooftop_potential_mw": sum(p["rooftop_solar_potential_mw"] for p in DISCOM_CONSUMER_PROFILE.values()),
        },
        "areas": areas,
        "assumptions": {
            "panel_efficiency_pct": PANEL_EFFICIENCY * 100,
            "performance_ratio": PERFORMANCE_RATIO,
            "avg_rooftop_size_kw": AVG_ROOFTOP_SIZE_KW,
            "peak_sun_hours": 6,
        },
    }
