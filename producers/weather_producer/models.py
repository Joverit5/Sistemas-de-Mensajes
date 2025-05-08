"""
Data models for the Weather Station Producer
"""
from enum import Enum, auto
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class StationType(Enum):
    """Types of weather stations"""
    STANDARD = auto()
    ADVANCED = auto()
    PROFESSIONAL = auto()


class WeatherData(BaseModel):
    """Weather data model"""
    station_id: str
    timestamp: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[str] = None
    precipitation: Optional[float] = None
    solar_radiation: Optional[float] = None
    battery_level: Optional[float] = None
    status: str = "OK"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StationMetadata(BaseModel):
    """Station metadata model"""
    latitude: float
    longitude: float
    elevation: float
    station_type: StationType
    sensors: List[str] = Field(default_factory=list)
