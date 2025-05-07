"""
PostgreSQL repository implementation
"""
import logging
import os
import time
from typing import Dict, Any

import psycopg2
from psycopg2 import pool
from prometheus_client import Counter, Gauge

from weather_consumer.models import WeatherData
from weather_consumer.repositories.data_repository import DataRepository

logger = logging.getLogger("weather-consumer")

# Configure Prometheus metrics
DB_OPERATIONS = Counter('weather_consumer_db_operations_total', 'Total number of database operations', ['operation'])
DB_CONNECTION_POOL_SIZE = Gauge('weather_consumer_db_connection_pool_size', 'Current size of the database connection pool')

# Environment variables
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
POSTGRES_USER = os.getenv('POSTGRES_USER', 'weather_user')
POSTGRES_PASS = os.getenv('POSTGRES_PASS', 'weather_password')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'weather_db')
DB_POOL_MIN = int(os.getenv('DB_POOL_MIN', 1))
DB_POOL_MAX = int(os.getenv('DB_POOL_MAX', 10))


class PostgresRepository(DataRepository):
    """PostgreSQL repository implementation"""
    
    def __init__(self):
        """Initialize the PostgreSQL repository"""
        self.db_pool = None
        self._init_connection_pool()
    
    def _init_connection_pool(self) -> None:
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
    
    def save(self, data: WeatherData) -> bool:
        """Save weather data to PostgreSQL"""
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
            
            # Convert data to database format
            db_data = data.to_db_dict()
            
            # Extract values from data
            values = (
                db_data['station_id'],
                db_data['timestamp'],
                db_data['temperature'],
                db_data['humidity'],
                db_data['pressure'],
                db_data['wind_speed'],
                db_data['wind_direction'],
                db_data['precipitation'],
                db_data['solar_radiation'],
                db_data['battery_level'],
                db_data['status']
            )
            
            # Execute SQL
            cursor.execute(sql, values)
            conn.commit()
            cursor.close()
            
            DB_OPERATIONS.labels(operation='insert').inc()
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
    
    def close(self) -> None:
        """Close the PostgreSQL connection pool"""
        if self.db_pool:
            self.db_pool.closeall()
            logger.info("PostgreSQL connections closed")
