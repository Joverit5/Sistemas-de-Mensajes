#!/usr/bin/env python3
"""
Weather Station Data Producer
Simulates weather stations sending data to RabbitMQ
"""
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from typing import Dict, Any

import pika
from faker import Faker
from prometheus_client import start_http_server, Counter, Gauge

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("weather-producer")

# Configure Prometheus metrics
MESSAGES_SENT = Counter('weather_producer_messages_sent_total', 'Total number of messages sent', ['station_id'])
PRODUCER_ERRORS = Counter('weather_producer_errors_total', 'Total number of producer errors', ['type'])
STATION_TEMPERATURE = Gauge('weather_station_temperature', 'Current temperature reading', ['station_id'])
STATION_HUMIDITY = Gauge('weather_station_humidity', 'Current humidity reading', ['station_id'])
STATION_PRESSURE = Gauge('weather_station_pressure', 'Current pressure reading', ['station_id'])

# Environment variables
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'weather_user')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'weather_password')
EXCHANGE_NAME = os.getenv('EXCHANGE_NAME', 'weather_exchange')
ROUTING_KEY = os.getenv('ROUTING_KEY', 'weather.data')
SIMULATION_INTERVAL = int(os.getenv('SIMULATION_INTERVAL', 5))
NUM_STATIONS = int(os.getenv('NUM_STATIONS', 5))

# Initialize Faker for generating realistic data
fake = Faker()

class WeatherStationProducer:
    """Simulates a weather station and sends data to RabbitMQ"""
    
    def __init__(self, station_id: str):
        """Initialize the weather station producer"""
        self.station_id = station_id
        self.connection = None
        self.channel = None
        self.connect_to_rabbitmq()
        
        # Base values for this station (to make readings more realistic)
        self.base_temperature = random.uniform(-5, 30)
        self.base_humidity = random.uniform(30, 80)
        self.base_pressure = random.uniform(980, 1030)
        self.base_wind_speed = random.uniform(0, 15)
        self.base_solar_radiation = random.uniform(0, 800)
        
        # Station location
        self.latitude = float(fake.latitude())
        self.longitude = float(fake.longitude())
        self.elevation = random.uniform(0, 2000)
        
        logger.info(f"Initialized weather station {station_id} at coordinates: "
                   f"{self.latitude}, {self.longitude}, elevation: {self.elevation}m")
    
    def connect_to_rabbitmq(self) -> None:
        """Establish connection to RabbitMQ with retry logic"""
        retry_count = 0
        max_retries = 10
        retry_delay = 5
        
        while retry_count < max_retries:
            try:
                # Connection parameters
                credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
                parameters = pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    port=RABBITMQ_PORT,
                    credentials=credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
                
                # Establish connection
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                
                # Declare exchange - type 'topic' allows for flexible routing patterns
                self.channel.exchange_declare(
                    exchange=EXCHANGE_NAME,
                    exchange_type='topic',
                    durable=True
                )
                
                logger.info(f"Station {self.station_id} connected to RabbitMQ at {RABBITMQ_HOST}:{RABBITMQ_PORT}")
                return
                
            except pika.exceptions.AMQPConnectionError as error:
                retry_count += 1
                PRODUCER_ERRORS.labels(type='connection').inc()
                logger.error(f"Connection attempt {retry_count} failed: {error}")
                
                if retry_count < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.critical("Max retries reached. Could not connect to RabbitMQ.")
                    raise
    
    def generate_weather_data(self) -> Dict[str, Any]:
        """Generate simulated weather data with realistic variations"""
        # Add some random variation to base values
        timestamp = datetime.utcnow().isoformat()
        
        # Time-based variations (simulate day/night cycle)
        hour = datetime.utcnow().hour
        is_daytime = 6 <= hour <= 18
        day_factor = 1.0 if is_daytime else 0.7
        
        # Random variations
        temp_variation = random.uniform(-2, 2)
        humidity_variation = random.uniform(-5, 5)
        pressure_variation = random.uniform(-2, 2)
        
        # Calculate current values
        temperature = self.base_temperature + temp_variation * day_factor
        humidity = min(100, max(0, self.base_humidity + humidity_variation))
        pressure = self.base_pressure + pressure_variation
        wind_speed = max(0, self.base_wind_speed + random.uniform(-3, 3))
        wind_direction = random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])
        precipitation = 0.0 if random.random() > 0.3 else random.uniform(0, 10)
        solar_radiation = self.base_solar_radiation * day_factor * random.uniform(0.8, 1.2)
        battery_level = max(0, min(100, 100 - (random.random() * 0.5)))  # Slowly decreasing
        
        # Occasionally simulate errors or missing data
        status = "OK"
        if random.random() < 0.05:  # 5% chance of error
            error_type = random.choice(["SENSOR_ERROR", "CALIBRATION_ERROR", "COMMUNICATION_ERROR"])
            status = error_type
            
            # Simulate missing or invalid data
            if random.random() < 0.5:
                if random.random() < 0.3:
                    temperature = None
                if random.random() < 0.3:
                    humidity = None
                if random.random() < 0.3:
                    pressure = None
        
        # Update Prometheus metrics
        if temperature is not None:
            STATION_TEMPERATURE.labels(station_id=self.station_id).set(temperature)
        if humidity is not None:
            STATION_HUMIDITY.labels(station_id=self.station_id).set(humidity)
        if pressure is not None:
            STATION_PRESSURE.labels(station_id=self.station_id).set(pressure)
        
        # Create data payload
        data = {
            "station_id": self.station_id,
            "timestamp": timestamp,
            "temperature": temperature,
            "humidity": humidity,
            "pressure": pressure,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction,
            "precipitation": precipitation,
            "solar_radiation": solar_radiation,
            "battery_level": battery_level,
            "status": status,
            "metadata": {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "elevation": self.elevation
            }
        }
        
        return data
    
    def send_data(self) -> None:
        """Generate and send weather data to RabbitMQ"""
        try:
            # Check if connection is closed and reconnect if necessary
            if not self.connection or self.connection.is_closed:
                logger.warning(f"Connection closed for station {self.station_id}. Reconnecting...")
                self.connect_to_rabbitmq()
            
            # Generate weather data
            data = self.generate_weather_data()
            message = json.dumps(data)
            
            # Send message with persistent delivery mode
            self.channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=ROUTING_KEY,
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            # Update metrics
            MESSAGES_SENT.labels(station_id=self.station_id).inc()
            
            logger.info(f"Station {self.station_id} sent data: temp={data['temperature']}, "
                       f"humidity={data['humidity']}, status={data['status']}")
            
        except (pika.exceptions.AMQPError, ConnectionError) as error:
            PRODUCER_ERRORS.labels(type='publish').inc()
            logger.error(f"Error sending data from station {self.station_id}: {error}")
            # Try to reconnect
            try:
                self.connect_to_rabbitmq()
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect: {reconnect_error}")
    
    def close(self) -> None:
        """Close the connection to RabbitMQ"""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info(f"Connection closed for station {self.station_id}")


def main():
    """Main function to run the weather station simulation"""
    # Start Prometheus metrics server
    start_http_server(8000)
    logger.info("Prometheus metrics server started on port 8000")
    
    # Create weather station producers
    stations = []
    for i in range(NUM_STATIONS):
        station_id = f"WS-{fake.unique.random_int(min=1000, max=9999)}"
        station = WeatherStationProducer(station_id)
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
