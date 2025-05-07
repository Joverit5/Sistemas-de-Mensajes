"""
Weather data processor implementation
"""
import logging
from typing import Dict, Any

from weather_consumer.models import WeatherData
from weather_consumer.processors.data_processor import DataProcessor
from weather_consumer.repositories.data_repository import DataRepository
from weather_consumer.validators.validator_factory import ValidatorFactory

logger = logging.getLogger("weather-consumer")


class WeatherDataProcessor(DataProcessor):
    """Weather data processor implementation"""
    
    def __init__(self, repository: DataRepository, validator_factory: ValidatorFactory):
        """Initialize the weather data processor"""
        self.repository = repository
        self.validator_factory = validator_factory
    
    def process(self, data: WeatherData) -> bool:
        """Process weather data"""
        try:
            # Get appropriate validator for the data
            validator = self.validator_factory.create_validator(data)
            
            # Validate data
            validation_result = validator.validate(data)
            if not validation_result.is_valid:
                logger.warning(f"Invalid data: {validation_result.error_message}")
                return False
            
            # Store data in repository
            if self.repository.save(data):
                logger.info(f"Stored data for station {data.station_id}")
                return True
            else:
                logger.error(f"Failed to store data for station {data.station_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            return False
