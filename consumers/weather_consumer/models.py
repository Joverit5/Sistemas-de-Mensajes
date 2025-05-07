"""
Data models for the Weather Data Consumer
"""
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


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
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for database storage"""
        # Convert timestamp string to datetime object if needed
        timestamp = self.timestamp
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
        return {
            "station_id": self.station_id,
            "timestamp": timestamp,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "pressure": self.pressure,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "precipitation": self.precipitation,
            "solar_radiation": self.solar_radiation,
            "battery_level": self.battery_level,
            "status": self.status
        }


class ValidationResult(BaseModel):
    """Validation result model"""
    is_valid: bool
    error_message: Optional[str] = None
