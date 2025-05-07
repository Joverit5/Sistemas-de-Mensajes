"""
Data models for the Weather API service
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class WeatherReading(BaseModel):
    """Weather reading model"""
    id: int
    station_id: str
    timestamp: datetime
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[str] = None
    precipitation: Optional[float] = None
    solar_radiation: Optional[float] = None
    battery_level: Optional[float] = None
    status: str


class Station(BaseModel):
    """Weather station model"""
    id: str
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation: Optional[float] = None
    type: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


class Alert(BaseModel):
    """Alert model"""
    id: int
    station_id: str
    alert_type: str
    alert_message: str
    alert_value: float
    threshold_value: float
    timestamp: datetime
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None


class AlertConfiguration(BaseModel):
    """Alert configuration model"""
    id: int
    name: str
    field_name: str
    operator: str
    threshold_value: float
    severity: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
