"""
Standard weather station implementation
"""
from typing import List

from weather_producer.models import StationType
from weather_producer.stations.base_station import BaseWeatherStation


class StandardWeatherStation(BaseWeatherStation):
    """Standard weather station with basic sensors"""
    
    @property
    def station_type(self) -> StationType:
        """Return the type of this station"""
        return StationType.STANDARD
    
    @property
    def available_sensors(self) -> List[str]:
        """Return the list of sensors available on this station"""
        return [
            "temperature",
            "humidity",
            "pressure",
            "wind_speed",
            "wind_direction"
        ]
