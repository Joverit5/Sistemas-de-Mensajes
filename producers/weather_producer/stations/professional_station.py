"""
Professional weather station implementation
"""
from typing import List

from weather_producer.models import StationType
from weather_producer.stations.base_station import BaseWeatherStation


class ProfessionalWeatherStation(BaseWeatherStation):
    """Professional weather station with all sensors"""
    
    @property
    def station_type(self) -> StationType:
        """Return the type of this station"""
        return StationType.PROFESSIONAL
    
    @property
    def available_sensors(self) -> List[str]:
        """Return the list of sensors available on this station"""
        return [
            "temperature",
            "humidity",
            "pressure",
            "wind_speed",
            "wind_direction",
            "precipitation",
            "solar_radiation",
            "battery_level",
            "uv_index",
            "soil_moisture",
            "soil_temperature",
            "leaf_wetness"
        ]
