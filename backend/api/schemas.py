from typing import Any

from pydantic import BaseModel


class LoadDataUploadResponse(BaseModel):
    filename: str
    rows: int
    columns: list[str]
    date_range: dict[str, str]
    message: str


class CapacityUploadResponse(BaseModel):
    filename: str
    plants: int
    total_installed_mw: float
    total_available_mw: float
    message: str


class WeatherDataResponse(BaseModel):
    start_date: str
    end_date: str
    hours: int
    columns: list[str]
    message: str


class TrainingRequest(BaseModel):
    model_list: list[str] | None = None
    lat: float | None = 28.6139
    lon: float | None = 77.2090
    capacity_mw: float | None = None


class TrainingStatusResponse(BaseModel):
    status: str
    progress_pct: int
    current_model: str | None = None
    metrics: dict[str, Any] | None = None
    error: str | None = None


class PredictionPoint(BaseModel):
    timestamp: str
    predicted_demand: float
    ensemble_prediction: float | None = None
    lower_bound: float
    upper_bound: float


class PredictionResponse(BaseModel):
    model_used: str
    horizon_hours: int
    predictions: list[PredictionPoint]
    generated_at: str


class RiskAlertSchema(BaseModel):
    timestamp: str
    risk_level: str
    predicted_demand: float
    available_capacity: float
    utilization_pct: float
    deficit_mw: float
    area: str
    node: str
    message: str
    recommendations: list[str]


class RiskSummaryResponse(BaseModel):
    total_alerts: int
    counts_by_level: dict[str, int]
    peak_utilization_pct: float
    average_utilization_pct: float
    highest_risk_hour: str | None = None
    highest_risk_level: str | None = None
    highest_demand_mw: float | None = None
    total_deficit_mwh: float | None = None
    hours_capacity_exceeded: int = 0
    hours_critical: int = 0


class ModelComparisonRow(BaseModel):
    model: str
    mae: float
    rmse: float
    mape: float
    r2: float


class DemandMetrics(BaseModel):
    peak_mw: float
    off_peak_mw: float
    average_mw: float
    load_factor: float
    total_mwh: float


class DashboardOverviewResponse(BaseModel):
    current_demand_mw: float | None = None
    peak_forecast_mw: float | None = None
    capacity_utilization_pct: float | None = None
    active_alerts: int = 0
    best_model: str | None = None
    data_points: int = 0
    demand_metrics: DemandMetrics | None = None
    risk_level: str = "unknown"


class AreaBreakdownItem(BaseModel):
    area: str
    consumer_type: str
    demand_mw: float
    percentage: float


class CapacityUtilizationItem(BaseModel):
    area: str
    available_mw: float
    predicted_demand_mw: float
    utilization_pct: float
    risk_level: str


class WeatherCorrelationPoint(BaseModel):
    timestamp: str
    demand: float
    temperature: float | None = None
    humidity: float | None = None
    solar_radiation: float | None = None
