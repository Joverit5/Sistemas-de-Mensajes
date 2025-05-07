"""
Data validator interface
"""
from abc import ABC, abstractmethod

from weather_consumer.models import WeatherData, ValidationResult


class DataValidator(ABC):
    """Interface for data validators"""
    
    @abstractmethod
    def validate(self, data: WeatherData) -> ValidationResult:
        """Validate weather data"""
        pass
