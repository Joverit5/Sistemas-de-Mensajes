"""
Validator factory implementation
"""
import logging
from typing import Dict, Any

from weather_consumer.models import WeatherData
from weather_consumer.validators.data_validator import DataValidator
from weather_consumer.validators.weather_data_validator import WeatherDataValidator

logger = logging.getLogger("weather-consumer")


class ValidatorFactory:
    """Factory for creating data validators"""
    
    def create_validator(self, data: WeatherData) -> DataValidator:
        """Create a validator for the given data"""
        # For now, we only have one validator type
        # In the future, we could create different validators based on station type or data content
        return WeatherDataValidator()
