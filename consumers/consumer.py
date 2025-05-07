
"""
Weather Station Data Consumer
Processes messages from RabbitMQ and stores them in PostgreSQL
"""
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import pika
import psycopg2
from psycopg2 import pool
from prometheus_client import start_http_server, Counter, Gauge, Histogram

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("weather-consumer")

# Configure Prometheus metrics
MESSAGES_PROCESSED = Counter('weather_consumer_messages_processed_total', 'Total number of messages processed')
MESSAGES_FAILED = Counter('weather_consumer_messages_failed_total', 'Total number of messages that failed processing', ['reason'])
DB_OPERATIONS = Counter('weather_consumer_db_operations_total', 'Total number of database operations', ['operation'])
PROCESSING_TIME = Histogram('weather_consumer_processing_time_seconds', 'Time taken to process a message')
QUEUE_SIZE = Gauge('weather_consumer_queue_size', 'Current size of the RabbitMQ queue')
DB_CONNECTION_POOL_SIZE = Gauge('weather_consumer_db_connection_pool_size', 'Current size of the database connection pool')

# Environment variables
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'weather_user')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'weather_password')
EXCHANGE_NAME = os.getenv('EXCHANGE_NAME', 'weather_exchange')
QUEUE_NAME = os.getenv('QUEUE_NAME', 'weather_queue')
ROUTING_KEY = os.getenv('ROUTING_KEY', 'weather.data')

POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
POSTGRES_USER = os.getenv('POSTGRES_USER', 'weather_user')
POSTGRES_PASS = os.getenv('POSTGRES_PASS', 'weather_password')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'weather_db')
DB_POOL_MIN = int(os.getenv('DB_POOL_MIN', 1))
DB_POOL_MAX = int(os.getenv('DB_POOL_MAX', 10))

class WeatherDataConsumer:
    """Consumes weather data from RabbitMQ and stores it in PostgreSQL"""
    
    def __init__(self):
        """Initialize the consumer with RabbitMQ and PostgreSQL connections"""
        self.connection = None
        self.channel = None
        self.db_pool = None
        self.should_reconnect = False
        self.was_consuming = False
        
        # Initialize connections
        self._init_db_connection_pool()
        self._connect_to_rabbitmq()
    
    def _init_db_connection_pool(self) -> None:
        """Initialize the PostgreSQL connection pool with retry logic"""
        retry_count = 0
        max_retries = 10
        retry_delay = 5
        
        while retry_count < max_retries:
            try:
                # Create connection pool
                self.db_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=DB_POOL_MIN,
                    maxconn=DB_POOL_MAX,
                    host=POSTGRES_HOST,
                    port=POSTGRES_PORT,
                    user=POSTGRES_USER,
                    password=POSTGRES_PASS,
                    dbname=POSTGRES_DB
                )
                
                # Test connection
                conn = self.db_pool.getconn()
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                self.db_pool.putconn(conn)
                
                DB_CONNECTION_POOL_SIZE.set(DB_POOL_MIN)
                logger.info(f"Connected to PostgreSQL at {POSTGRES_HOST}:{POSTGRES_PORT}")
                return
                
            except psycopg2.Error as error:
                retry_count += 1
                logger.error(f"Database connection attempt {retry_count} failed: {error}")
                
                if retry_count < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.critical("Max retries reached. Could not connect to PostgreSQL.")
                    raise
    
    def _connect_to_rabbitmq(self) -> None:
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
    
    def _validate_weather_data(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate weather data against expected ranges and formats"""
        # Required fields
        required_fields = ['station_id', 'timestamp', 'status']
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Validate timestamp format
        try:
            datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return False, "Invalid timestamp format"
        
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
            if field in data and data[field] is not None:
                try:
                    value = float(data[field])
                    if value < min_val or value > max_val:
                        return False, f"{field} out of range: {value} (expected {min_val}-{max_val})"
                except (ValueError, TypeError):
                    return False, f"Invalid {field} value: {data[field]}"
        
        return True, None
    
    def _store_weather_data(self, data: Dict[str, Any]) -> bool:
        """Store weather data in PostgreSQL"""
        conn = None
        try:
            # Get connection from pool
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            
            # Prepare SQL statement
            sql = """
            INSERT INTO weather_logs (
                station_id,
                timestamp,
                temperature,
                humidity,
                pressure,
                wind_speed,
                wind_direction,
                precipitation,
                solar_radiation,
                battery_level,
                status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Extract values from data
            values = (
                data['station_id'],
                data['timestamp'],
                data.get('temperature'),
                data.get('humidity'),
                data.get('pressure'),
                data.get('wind_speed'),
                data.get('wind_direction'),
                data.get('precipitation'),
                data.get('solar_radiation'),
                data.get('battery_level'),
                data['status']
            )
            
            # Execute SQL
            cursor.execute(sql, values)
            conn.commit()
            cursor.close()
            
            DB_OPERATIONS.labels(operation='insert').inc()
            logger.info(f"Stored data for station {data['station_id']}")
            return True
            
        except psycopg2.Error as error:
            DB_OPERATIONS.labels(operation='error').inc()
            logger.error(f"Database error: {error}")
            
            if conn:
                conn.rollback()
            return False
            
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def _process_message(self, ch, method, properties, body) -> None:
        """Process a message from RabbitMQ"""
        start_time = time.time()
        
        try:
            # Parse JSON message
            data = json.loads(body)
            logger.info(f"Received message from station {data.get('station_id', 'unknown')}")
            
            # Validate data
            is_valid, error_message = self._validate_weather_data(data)
            if not is_valid:
                logger.warning(f"Invalid data: {error_message}")
                MESSAGES_FAILED.labels(reason='validation').inc()
                # Acknowledge the message to remove it from the queue
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Store data in PostgreSQL
            if self._store_weather_data(data):
                # Acknowledge the message
                ch.basic_ack(delivery_tag=method.delivery_tag)
                MESSAGES_PROCESSED.inc()
            else:
                # Negative acknowledge to requeue the message
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                MESSAGES_FAILED.labels(reason='database').inc()
            
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
        """Close connections to RabbitMQ and PostgreSQL"""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("RabbitMQ connection closed")
        
        if self.db_pool:
            self.db_pool.closeall()
            logger.info("PostgreSQL connections closed")
    
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
                    self._init_db_connection_pool()
                    self._connect_to_rabbitmq()
                except Exception as e:
                    logger.error(f"Failed to reconnect: {e}")
                    time.sleep(5)
            else:
                break


def main():
    """Main function to run the weather data consumer"""
    # Start Prometheus metrics server
    start_http_server(8001)
    logger.info("Prometheus metrics server started on port 8001")
    
    # Create and run consumer
    consumer = WeatherDataConsumer()
    try:
        consumer.run()
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
