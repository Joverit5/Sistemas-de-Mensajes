"""
Factory classes for creating weather stations
"""
import logging
import random
from faker import Faker

from weather_producer.models import StationType
from weather_producer.stations.standard_station import StandardWeatherStation
from weather_producer.stations.advanced_station import AdvancedWeatherStation
from weather_producer.stations.professional_station import ProfessionalWeatherStation

logger = logging.getLogger("weather-producer")
fake = Faker()


class StationFactory:
    """Factory for creating different types of weather stations"""
    
    def create_station(self, station_type: StationType):
        """Create a weather station of the specified type"""
        station_id = f"WS-{fake.unique.random_int(min=1000, max=9999)}"
        
        # Generate random coordinates
        latitude = float(fake.latitude())
        longitude = float(fake.longitude())
        elevation = random.uniform(0, 2000)
        
        if station_type == StationType.STANDARD:
            logger.info(f"Creating Standard Weather Station {station_id}")
            return StandardWeatherStation(
                station_id=station_id,
                latitude=latitude,
                longitude=longitude,
                elevation=elevation
            )
        elif station_type == StationType.ADVANCED:
            logger.info(f"Creating Advanced Weather Station {station_id}")
            return AdvancedWeatherStation(
                station_id=station_id,
                latitude=latitude,
                longitude=longitude,
                elevation=elevation
            )
        elif station_type == StationType.PROFESSIONAL:
            logger.info(f"Creating Professional Weather Station {station_id}")
            return ProfessionalWeatherStation(
                station_id=station_id,
                latitude=latitude,
                longitude=longitude,
                elevation=elevation
            )
        else:
            raise ValueError(f"Unknown station type: {station_type}")
