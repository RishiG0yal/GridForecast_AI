from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/demand_forecast.db"
    DATA_DIR: Path = Path("data")
    MODELS_DIR: Path = Path("data/models")
    RAW_DIR: Path = Path("data/raw")
    PROCESSED_DIR: Path = Path("data/processed")
    LOGS_DIR: Path = Path("logs")
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1"
    OPEN_METEO_ARCHIVE_URL: str = "https://archive-api.open-meteo.com/v1"
    FORECAST_HORIZON_HOURS: int = 48
    LOOKBACK_DAYS: int = 365
    DEFAULT_LAT: float = 28.6139
    DEFAULT_LON: float = 77.2090
    DEFAULT_GRID_CAPACITY_MW: float = 10000.0
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000"]

    def model_post_init(self, __context):
        for d in [self.DATA_DIR, self.MODELS_DIR, self.RAW_DIR, self.PROCESSED_DIR, self.LOGS_DIR]:
            Path(d).mkdir(parents=True, exist_ok=True)

    class Config:
        env_file = ".env"

settings = Settings()
