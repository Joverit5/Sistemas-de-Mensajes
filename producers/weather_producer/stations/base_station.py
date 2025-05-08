"""
Base class for weather stations
"""
import logging
import random
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List

from prometheus_client import Gauge

from weather_producer.messaging.rabbitmq_adapter import RabbitMQAdapter
from weather_producer.models import StationType, WeatherData, StationMetadata

logger = logging.getLogger("weather-producer")

# Prometheus metrics
STATION_TEMPERATURE = Gauge('weather_station_temperature', 'Current temperature reading', ['station_id'])
STATION_HUMIDITY = Gauge('weather_station_humidity', 'Current humidity reading', ['station_id'])
STATION_PRESSURE = Gauge('weather_station_pressure', 'Current pressure reading', ['station_id'])
STATION_WIND_SPEED = Gauge('weather_station_wind_speed', 'Current wind speed reading', ['station_id'])
STATION_PRECIPITATION = Gauge('weather_station_precipitation', 'Current precipitation reading', ['station_id'])
STATION_BATTERY = Gauge('weather_station_battery_level', 'Current battery level', ['station_id'])


class BaseWeatherStation(ABC):
    """Base class for all weather station types"""
    
    def __init__(self, station_id: str, latitude: float, longitude: float, elevation: float):
        """Initialize the weather station"""
        self.station_id = station_id
        self.latitude = latitude
        self.longitude = longitude
        self.elevation = elevation
        
        # Base values for this station (to make readings more realistic)
        self.base_temperature = random.uniform(-5, 30)
        self.base_humidity = random.uniform(30, 80)
        self.base_pressure = random.uniform(980, 1030)
        self.base_wind_speed = random.uniform(0, 15)
        self.base_solar_radiation = random.uniform(0, 800)
        
        # Initialize messaging adapter
        self.messaging = RabbitMQAdapter(station_id)
        
        logger.info(f"Initialized weather station {station_id} at coordinates: "
                   f"{self.latitude}, {self.longitude}, elevation: {self.elevation}m")
    
    @property
    @abstractmethod
    def station_type(self) -> StationType:
        """Return the type of this station"""
        pass
    
    @property
    @abstractmethod
    def available_sensors(self) -> List[str]:
        """Return the list of sensors available on this station"""
        pass
    
    def get_metadata(self) -> StationMetadata:
        """Get station metadata"""
        return StationMetadata(
            latitude=self.latitude,
            longitude=self.longitude,
            elevation=self.elevation,
            station_type=self.station_type,
            sensors=self.available_sensors
        )
    
    def generate_weather_data(self) -> WeatherData:
        """Generate simulated weather data with realistic variations"""
        # Add some random variation to base values
        timestamp = datetime.utcnow().isoformat()
        
        # Time-based variations (simulate day/night cycle)
        hour = datetime.utcnow().hour
        is_daytime = 6 <= hour <= 18
        day_factor = 1.0 if is_daytime else 0.7
        
        # Random variations
        temp_variation = random.uniform(-2, 2)
        humidity_variation = random.uniform(-5, 5)
        pressure_variation = random.uniform(-2, 2)
        
        # Calculate current values
        temperature = self.base_temperature + temp_variation * day_factor
        humidity = min(100, max(0, self.base_humidity + humidity_variation))
        pressure = self.base_pressure + pressure_variation
        wind_speed = max(0, self.base_wind_speed + random.uniform(-3, 3))
        wind_direction = random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])
        precipitation = 0.0 if random.random() > 0.3 else random.uniform(0, 10)
        solar_radiation = self.base_solar_radiation * day_factor * random.uniform(0.8, 1.2)
        battery_level = max(0, min(100, 100 - (random.random() * 0.5)))  # Slowly decreasing
        
        # Occasionally simulate errors or missing data
        status = "OK"
        if random.random() < 0.05:  # 5% chance of error
            error_type = random.choice(["SENSOR_ERROR", "CALIBRATION_ERROR", "COMMUNICATION_ERROR"])
            status = error_type
            
            # Simulate missing or invalid data
            if random.random() < 0.5:
                if random.random() < 0.3:
                    temperature = None
                if random.random() < 0.3:
                    humidity = None
                if random.random() < 0.3:
                    pressure = None
        
        # Update Prometheus metrics
        if temperature is not None:
            STATION_TEMPERATURE.labels(station_id=self.station_id).set(temperature)
        if humidity is not None:
            STATION_HUMIDITY.labels(station_id=self.station_id).set(humidity)
        if pressure is not None:
            STATION_PRESSURE.labels(station_id=self.station_id).set(pressure)
        if wind_speed is not None:
            STATION_WIND_SPEED.labels(station_id=self.station_id).set(wind_speed)
        if precipitation is not None:
            STATION_PRECIPITATION.labels(station_id=self.station_id).set(precipitation)
        if battery_level is not None:
            STATION_BATTERY.labels(station_id=self.station_id).set(battery_level)
        
        # Create data payload
        data = WeatherData(
            station_id=self.station_id,
            timestamp=timestamp,
            temperature=temperature,
            humidity=humidity,
            pressure=pressure,
            wind_speed=wind_speed,
            wind_direction=wind_direction,
            precipitation=precipitation,
            solar_radiation=solar_radiation,
            battery_level=battery_level,
            status=status,
            metadata={
                "latitude": self.latitude,
                "longitude": self.longitude,
                "elevation": self.elevation,
                "station_type": self.station_type.name
            }
        )
        
        return data
    
    def send_data(self) -> None:
        """Generate and send weather data"""
        data = self.generate_weather_data()
        self.messaging.send_message(data.model_dump())
    
    def close(self) -> None:
        """Close the connection to the messaging system"""
        self.messaging.close()
