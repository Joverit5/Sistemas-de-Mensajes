"""
Data processor interface
"""
from abc import ABC, abstractmethod

from weather_consumer.models import WeatherData


class DataProcessor(ABC):
    """Interface for data processors"""
    
    @abstractmethod
    def process(self, data: WeatherData) -> bool:
        """Process weather data"""
        pass
