"""
Data repository interface
"""
from abc import ABC, abstractmethod

from weather_consumer.models import WeatherData


class DataRepository(ABC):
    """Interface for data repositories"""
    
    @abstractmethod
    def save(self, data: WeatherData) -> bool:
        """Save weather data to the repository"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the repository connection"""
        pass
