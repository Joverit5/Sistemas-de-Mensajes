"""
Weather data validator implementation
"""
import logging
from datetime import datetime

from weather_consumer.models import WeatherData, ValidationResult
from weather_consumer.validators.data_validator import DataValidator

logger = logging.getLogger("weather-consumer")


class WeatherDataValidator(DataValidator):
    """Weather data validator implementation"""
    
    def validate(self, data: WeatherData) -> ValidationResult:
        """Validate weather data against expected ranges and formats"""
        # Required fields
        required_fields = ['station_id', 'timestamp', 'status']
        for field in required_fields:
            if not getattr(data, field, None):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required field: {field}"
                )
        
        # Validate timestamp format
        try:
            if isinstance(data.timestamp, str):
                datetime.fromisoformat(data.timestamp.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                error_message="Invalid timestamp format"
            )
        
        # Validate numeric ranges if present
        validations = [
            ('temperature', -80, 60),
            ('humidity', 0, 100),
            ('pressure', 800, 1200),
            ('wind_speed', 0, 200),
            ('precipitation', 0, 500),
            ('battery_level', 0, 100)
        ]
        
        for field, min_val, max_val in validations:
            value = getattr(data, field, None)
            if value is not None:
                try:
                    value_float = float(value)
                    if value_float < min_val or value_float > max_val:
                        return ValidationResult(
                            is_valid=False,
                            error_message=f"{field} out of range: {value} (expected {min_val}-{max_val})"
                        )
                except (ValueError, TypeError):
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Invalid {field} value: {value}"
                    )
        
        return ValidationResult(is_valid=True)
