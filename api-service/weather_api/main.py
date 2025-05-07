"""
Main module for the Weather API service
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from prometheus_client import Counter, start_http_server
import threading

from weather_api.models import WeatherReading, Station, Alert, AlertConfiguration
from weather_api.repositories.postgres_repository import PostgresRepository
from weather_api.dependencies import get_repository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("weather-api")

# Configure Prometheus metrics
API_REQUESTS = Counter('weather_api_requests_total', 'Total number of API requests', ['endpoint', 'method'])
API_ERRORS = Counter('weather_api_errors_total', 'Total number of API errors', ['endpoint', 'status'])

# Create FastAPI app
app = FastAPI(
    title="Weather Station API",
    description="API for accessing weather station data and alerts",
    version="1.0.0"
)

# Start Prometheus metrics server in a separate thread
def start_metrics_server():
    start_http_server(8003)
    logger.info("Prometheus metrics server started on port 8003")

threading.Thread(target=start_metrics_server, daemon=True).start()


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    API_REQUESTS.labels(endpoint="/", method="GET").inc()
    return {"status": "ok", "message": "Weather Station API is running"}


@app.get("/stations", response_model=List[Station], tags=["Stations"])
async def get_stations(
    repository: PostgresRepository = Depends(get_repository)
):
    """Get all weather stations"""
    API_REQUESTS.labels(endpoint="/stations", method="GET").inc()
    try:
        return repository.get_stations()
    except Exception as e:
        API_ERRORS.labels(endpoint="/stations", status=500).inc()
        logger.error(f"Error getting stations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/stations/{station_id}", response_model=Station, tags=["Stations"])
async def get_station(
    station_id: str,
    repository: PostgresRepository = Depends(get_repository)
):
    """Get a specific weather station"""
    API_REQUESTS.labels(endpoint="/stations/{station_id}", method="GET").inc()
    try:
        station = repository.get_station(station_id)
        if not station:
            API_ERRORS.labels(endpoint="/stations/{station_id}", status=404).inc()
            raise HTTPException(status_code=404, detail="Station not found")
        return station
    except HTTPException:
        raise
    except Exception as e:
        API_ERRORS.labels(endpoint="/stations/{station_id}", status=500).inc()
        logger.error(f"Error getting station {station_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/readings", response_model=List[WeatherReading], tags=["Readings"])
async def get_readings(
    station_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    repository: PostgresRepository = Depends(get_repository)
):
    """Get weather readings with optional filters"""
    API_REQUESTS.labels(endpoint="/readings", method="GET").inc()
    try:
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=1)
            
        return repository.get_readings(
            station_id=station_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        API_ERRORS.labels(endpoint="/readings", status=500).inc()
        logger.error(f"Error getting readings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/readings/latest", response_model=List[WeatherReading], tags=["Readings"])
async def get_latest_readings(
    repository: PostgresRepository = Depends(get_repository)
):
    """Get the latest reading from each station"""
    API_REQUESTS.labels(endpoint="/readings/latest", method="GET").inc()
    try:
        return repository.get_latest_readings()
    except Exception as e:
        API_ERRORS.labels(endpoint="/readings/latest", status=500).inc()
        logger.error(f"Error getting latest readings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/alerts", response_model=List[Alert], tags=["Alerts"])
async def get_alerts(
    station_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    repository: PostgresRepository = Depends(get_repository)
):
    """Get alerts with optional filters"""
    API_REQUESTS.labels(endpoint="/alerts", method="GET").inc()
    try:
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=7)
            
        return repository.get_alerts(
            station_id=station_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        API_ERRORS.labels(endpoint="/alerts", status=500).inc()
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/alert-configurations", response_model=List[AlertConfiguration], tags=["Alerts"])
async def get_alert_configurations(
    repository: PostgresRepository = Depends(get_repository)
):
    """Get all alert configurations"""
    API_REQUESTS.labels(endpoint="/alert-configurations", method="GET").inc()
    try:
        return repository.get_alert_configurations()
    except Exception as e:
        API_ERRORS.labels(endpoint="/alert-configurations", status=500).inc()
        logger.error(f"Error getting alert configurations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
