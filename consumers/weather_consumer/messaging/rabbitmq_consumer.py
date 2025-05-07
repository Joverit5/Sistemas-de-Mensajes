"""
RabbitMQ consumer implementation
"""
import json
import logging
import os
import time
from typing import Dict, Any

import pika
from prometheus_client import Counter, Gauge, Histogram

from weather_consumer.models import WeatherData
from weather_consumer.processors.data_processor import DataProcessor

logger = logging.getLogger("weather-consumer")

# Configure Prometheus metrics
MESSAGES_PROCESSED = Counter('weather_consumer_messages_processed_total', 'Total number of messages processed')
MESSAGES_FAILED = Counter('weather_consumer_messages_failed_total', 'Total number of messages that failed processing', ['reason'])
PROCESSING_TIME = Histogram('weather_consumer_processing_time_seconds', 'Time taken to process a message')
QUEUE_SIZE = Gauge('weather_consumer_queue_size', 'Current size of the RabbitMQ queue')

# Environment variables
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'weather_user')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'weather_password')
EXCHANGE_NAME = os.getenv('EXCHANGE_NAME', 'weather_exchange')
QUEUE_NAME = os.getenv('QUEUE_NAME', 'weather_queue')
ROUTING_KEY = os.getenv('ROUTING_KEY', 'weather.data')


class RabbitMQConsumer:
    """RabbitMQ consumer implementation"""
    
    def __init__(self, processor: DataProcessor):
        """Initialize the RabbitMQ consumer"""
        self.processor = processor
        self.connection = None
        self.channel = None
        self.should_reconnect = False
        self.was_consuming = False
        self._connect()
    
    def _connect(self) -> None:
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
                
                # Declare exchange
                self.channel.exchange_declare(
                    exchange=EXCHANGE_NAME,
                    exchange_type='topic',
                    durable=True
                )
                
                # Declare queue
                self.channel.queue_declare(
                    queue=QUEUE_NAME,
                    durable=True,
                    arguments={
                        'x-message-ttl': 86400000,  # 24 hours in milliseconds
                        'x-dead-letter-exchange': f"{EXCHANGE_NAME}.dlx",
                        'x-dead-letter-routing-key': f"{ROUTING_KEY}.dead"
                    }
                )
                
                # Declare dead-letter exchange and queue for failed messages
                self.channel.exchange_declare(
                    exchange=f"{EXCHANGE_NAME}.dlx",
                    exchange_type='topic',
                    durable=True
                )
                
                self.channel.queue_declare(
                    queue=f"{QUEUE_NAME}.dead",
                    durable=True
                )
                
                # Bind queues to exchanges
                self.channel.queue_bind(
                    exchange=EXCHANGE_NAME,
                    queue=QUEUE_NAME,
                    routing_key=ROUTING_KEY
                )
                
                self.channel.queue_bind(
                    exchange=f"{EXCHANGE_NAME}.dlx",
                    queue=f"{QUEUE_NAME}.dead",
                    routing_key=f"{ROUTING_KEY}.dead"
                )
                
                # Set QoS prefetch count to 1 for fair dispatch
                self.channel.basic_qos(prefetch_count=1)
                
                logger.info(f"Connected to RabbitMQ at {RABBITMQ_HOST}:{RABBITMQ_PORT}")
                return
                
            except pika.exceptions.AMQPConnectionError as error:
                retry_count += 1
                logger.error(f"RabbitMQ connection attempt {retry_count} failed: {error}")
                
                if retry_count < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.critical("Max retries reached. Could not connect to RabbitMQ.")
                    raise
    
    def _process_message(self, ch, method, properties, body) -> None:
        """Process a message from RabbitMQ"""
        start_time = time.time()
        
        try:
            # Parse JSON message
            data = json.loads(body)
            logger.info(f"Received message from station {data.get('station_id', 'unknown')}")
            
            # Convert to WeatherData model
            weather_data = WeatherData(**data)
            
            # Process data
            if self.processor.process(weather_data):
                # Acknowledge the message
                ch.basic_ack(delivery_tag=method.delivery_tag)
                MESSAGES_PROCESSED.inc()
            else:
                # Negative acknowledge to requeue the message
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                MESSAGES_FAILED.labels(reason='processing').inc()
            
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON message")
            MESSAGES_FAILED.labels(reason='json_parse').inc()
            # Acknowledge the message to remove it from the queue
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Unexpected error processing message: {e}")
            MESSAGES_FAILED.labels(reason='unexpected').inc()
            # Negative acknowledge to requeue the message
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            
        finally:
            # Record processing time
            processing_time = time.time() - start_time
            PROCESSING_TIME.observe(processing_time)
    
    def start_consuming(self) -> None:
        """Start consuming messages from RabbitMQ"""
        try:
            # Set up consumer
            self.channel.basic_consume(
                queue=QUEUE_NAME,
                on_message_callback=self._process_message,
                auto_ack=False
            )
            
            # Update queue size metric periodically
            def update_queue_size():
                try:
                    queue_info = self.channel.queue_declare(queue=QUEUE_NAME, passive=True)
                    QUEUE_SIZE.set(queue_info.method.message_count)
                except Exception as e:
                    logger.error(f"Failed to get queue size: {e}")
            
            # Start consuming
            logger.info(f"Started consuming from queue: {QUEUE_NAME}")
            self.was_consuming = True
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("Stopping consumer due to keyboard interrupt")
            self.channel.stop_consuming()
            
        except pika.exceptions.ConnectionClosedByBroker:
            logger.warning("Connection closed by broker")
            self.should_reconnect = True
            
        except pika.exceptions.AMQPChannelError as err:
            logger.error(f"Channel error: {err}")
            # Do not reconnect on channel errors
            
        except pika.exceptions.AMQPConnectionError:
            logger.warning("Connection was closed, reconnecting...")
            self.should_reconnect = True
    
    def close(self) -> None:
        """Close connection to RabbitMQ"""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("RabbitMQ connection closed")
    
    def run(self) -> None:
        """Run the consumer with reconnection logic"""
        while True:
            self.should_reconnect = False
            self.start_consuming()
            
            if self.should_reconnect:
                self.close()
                logger.info("Reconnecting...")
                time.sleep(5)
                try:
                    self._connect()
                except Exception as e:
                    logger.error(f"Failed to reconnect: {e}")
                    time.sleep(5)
            else:
                break
