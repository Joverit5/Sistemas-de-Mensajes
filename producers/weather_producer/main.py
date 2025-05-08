#!/usr/bin/env python3
"""
Main module for the Weather Station Producer service
"""
import logging
import os
import sys
import time
from typing import List

from prometheus_client import start_http_server

from weather_producer.factories import StationFactory
from weather_producer.models import StationType
from weather_producer.stations.base_station import BaseWeatherStation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("weather-producer")

# Environment variables
SIMULATION_INTERVAL = int(os.getenv('SIMULATION_INTERVAL', 5))
NUM_STATIONS = int(os.getenv('NUM_STATIONS', 5))


def main():
    """Main function to run the weather station simulation"""
    # Start Prometheus metrics server
    start_http_server(8000)
    logger.info("Prometheus metrics server started on port 8000")
    
    # Create weather station producers using the factory
    factory = StationFactory()
    stations: List[BaseWeatherStation] = []
    
    # Create a mix of different station types
    for i in range(NUM_STATIONS):
        # Alternate between different station types
        if i % 3 == 0:
            station_type = StationType.STANDARD
        elif i % 3 == 1:
            station_type = StationType.ADVANCED
        else:
            station_type = StationType.PROFESSIONAL
            
        station = factory.create_station(station_type)
        stations.append(station)
    
    try:
        logger.info(f"Starting simulation with {len(stations)} weather stations")
        logger.info(f"Data will be sent every {SIMULATION_INTERVAL} seconds")
        
        while True:
            for station in stations:
                station.send_data()
            
            # Wait before next iteration
            time.sleep(SIMULATION_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("Simulation stopped by user")
    finally:
        # Close all connections
        for station in stations:
            station.close()
        logger.info("All connections closed")


if __name__ == "__main__":
    main()
