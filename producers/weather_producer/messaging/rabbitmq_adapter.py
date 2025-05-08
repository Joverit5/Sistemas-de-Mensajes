"""
RabbitMQ adapter for the Weather Station Producer
"""
import json
import logging
import os
import time
from typing import Dict, Any

import pika
from prometheus_client import Counter

logger = logging.getLogger("weather-producer")

# Prometheus metrics
PRODUCER_ERRORS = Counter('weather_producer_errors_total', 'Total number of producer errors', ['type'])
MESSAGES_SENT = Counter('weather_producer_messages_sent_total', 'Total number of messages sent', ['station_id'])

# Environment variables
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'weather_user')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'weather_password')
EXCHANGE_NAME = os.getenv('EXCHANGE_NAME', 'weather_exchange')
ROUTING_KEY = os.getenv('ROUTING_KEY', 'weather.data')


class RabbitMQAdapter:
    """Adapter for RabbitMQ messaging"""
    
    def __init__(self, station_id: str):
        """Initialize the RabbitMQ adapter"""
        self.station_id = station_id
        self.connection = None
        self.channel = None
        self.connect()
    
    def connect(self) -> None:
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
    
    def send_message(self, data: Dict[str, Any]) -> bool:
        """Send a message to RabbitMQ"""
        try:
            # Check if connection is closed and reconnect if necessary
            if not self.connection or self.connection.is_closed:
                logger.warning(f"Connection closed for station {self.station_id}. Reconnecting...")
                self.connect()
            
            # Convert data to JSON
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
            
            logger.info(f"Station {self.station_id} sent data: temp={data.get('temperature')}, "
                       f"humidity={data.get('humidity')}, status={data.get('status')}")
            
            return True
            
        except (pika.exceptions.AMQPError, ConnectionError) as error:
            PRODUCER_ERRORS.labels(type='publish').inc()
            logger.error(f"Error sending data from station {self.station_id}: {error}")
            # Try to reconnect
            try:
                self.connect()
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect: {reconnect_error}")
            
            return False
    
    def close(self) -> None:
        """Close the connection to RabbitMQ"""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info(f"Connection closed for station {self.station_id}")
