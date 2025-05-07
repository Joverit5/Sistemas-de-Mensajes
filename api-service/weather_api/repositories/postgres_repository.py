"""
PostgreSQL repository implementation for the Weather API service
"""
import logging
import os
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

import psycopg2
from psycopg2 import pool
from prometheus_client import Counter, Gauge

from weather_api.models import WeatherReading, Station, Alert, AlertConfiguration

logger = logging.getLogger("weather-api")

# Configure Prometheus metrics
DB_OPERATIONS = Counter('weather_api_db_operations_total', 'Total number of database operations', ['operation'])
DB_CONNECTION_POOL_SIZE = Gauge('weather_api_db_connection_pool_size', 'Current size of the database connection pool')

# Environment variables
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
POSTGRES_USER = os.getenv('POSTGRES_USER', 'weather_user')
POSTGRES_PASS = os.getenv('POSTGRES_PASS', 'weather_password')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'weather_db')
DB_POOL_MIN = int(os.getenv('DB_POOL_MIN', 1))
DB_POOL_MAX = int(os.getenv('DB_POOL_MAX', 10))


class PostgresRepository:
    """PostgreSQL repository implementation for the Weather API service"""
    
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
    
    def get_stations(self) -> List[Station]:
        """Get all weather stations"""
        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, latitude, longitude, elevation, type, status, created_at, updated_at
                FROM stations
                ORDER BY id
            """)
            
            stations = []
            for row in cursor.fetchall():
                stations.append(Station(
                    id=row[0],
                    name=row[1],
                    latitude=row[2],
                    longitude=row[3],
                    elevation=row[4],
                    type=row[5],
                    status=row[6],
                    created_at=row[7],
                    updated_at=row[8]
                ))
            
            cursor.close()
            DB_OPERATIONS.labels(operation='select').inc()
            
            return stations
            
        except psycopg2.Error as error:
            DB_OPERATIONS.labels(operation='error').inc()
            logger.error(f"Database error getting stations: {error}")
            raise
            
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def get_station(self, station_id: str) -> Optional[Station]:
        """Get a specific weather station"""
        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, latitude, longitude, elevation, type, status, created_at, updated_at
                FROM stations
                WHERE id = %s
            """, (station_id,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return Station(
                    id=row[0],
                    name=row[1],
                    latitude=row[2],
                    longitude=row[3],
                    elevation=row[4],
                    type=row[5],
                    status=row[6],
                    created_at=row[7],
                    updated_at=row[8]
                )
            
            return None
            
        except psycopg2.Error as error:
            DB_OPERATIONS.labels(operation='error').inc()
            logger.error(f"Database error getting station {station_id}: {error}")
            raise
            
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def get_readings(
        self,
        station_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[WeatherReading]:
        """Get weather readings with optional filters"""
        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            
            # Build query with filters
            query = """
                SELECT id, station_id, timestamp, temperature, humidity, pressure,
                       wind_speed, wind_direction, precipitation, solar_radiation,
                       battery_level, status
                FROM weather_logs
                WHERE 1=1
            """
            params = []
            
            if station_id:
                query += " AND station_id = %s"
                params.append(station_id)
            
            if start_date:
                query += " AND timestamp >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= %s"
                params.append(end_date)
            
            query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            
            readings = []
            for row in cursor.fetchall():
                readings.append(WeatherReading(
                    id=row[0],
                    station_id=row[1],
                    timestamp=row[2],
                    temperature=row[3],
                    humidity=row[4],
                    pressure=row[5],
                    wind_speed=row[6],
                    wind_direction=row[7],
                    precipitation=row[8],
                    solar_radiation=row[9],
                    battery_level=row[10],
                    status=row[11]
                ))
            
            cursor.close()
            DB_OPERATIONS.labels(operation='select').inc()
            
            return readings
            
        except psycopg2.Error as error:
            DB_OPERATIONS.labels(operation='error').inc()
            logger.error(f"Database error getting readings: {error}")
            raise
            
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def get_latest_readings(self) -> List[WeatherReading]:
        """Get the latest reading from each station"""
        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, station_id, timestamp, temperature, humidity, pressure,
                       wind_speed, wind_direction, precipitation, solar_radiation,
                       battery_level, status
                FROM latest_station_readings
                ORDER BY station_id
            """)
            
            readings = []
            for row in cursor.fetchall():
                readings.append(WeatherReading(
                    id=row[0],
                    station_id=row[1],
                    timestamp=row[2],
                    temperature=row[3],
                    humidity=row[4],
                    pressure=row[5],
                    wind_speed=row[6],
                    wind_direction=row[7],
                    precipitation=row[8],
                    solar_radiation=row[9],
                    battery_level=row[10],
                    status=row[11]
                ))
            
            cursor.close()
            DB_OPERATIONS.labels(operation='select').inc()
            
            return readings
            
        except psycopg2.Error as error:
            DB_OPERATIONS.labels(operation='error').inc()
            logger.error(f"Database error getting latest readings: {error}")
            raise
            
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def get_alerts(
        self,
        station_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Alert]:
        """Get alerts with optional filters"""
        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            
            # Build query with filters
            query = """
                SELECT id, station_id, alert_type, alert_message, alert_value,
                       threshold_value, timestamp, status, created_at, resolved_at
                FROM weather_alerts
                WHERE 1=1
            """
            params = []
            
            if station_id:
                query += " AND station_id = %s"
                params.append(station_id)
            
            if status:
                query += " AND status = %s"
                params.append(status)
            
            if start_date:
                query += " AND timestamp >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= %s"
                params.append(end_date)
            
            query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            
            alerts = []
            for row in cursor.fetchall():
                alerts.append(Alert(
                    id=row[0],
                    station_id=row[1],
                    alert_type=row[2],
                    alert_message=row[3],
                    alert_value=row[4],
                    threshold_value=row[5],
                    timestamp=row[6],
                    status=row[7],
                    created_at=row[8],
                    resolved_at=row[9]
                ))
            
            cursor.close()
            DB_OPERATIONS.labels(operation='select').inc()
            
            return alerts
            
        except psycopg2.Error as error:
            DB_OPERATIONS.labels(operation='error').inc()
            logger.error(f"Database error getting alerts: {error}")
            raise
            
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def get_alert_configurations(self) -> List[AlertConfiguration]:
        """Get all alert configurations"""
        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, field_name, operator, threshold_value, severity,
                       enabled, created_at, updated_at
                FROM alert_configurations
                ORDER BY id
            """)
            
            configurations = []
            for row in cursor.fetchall():
                configurations.append(AlertConfiguration(
                    id=row[0],
                    name=row[1],
                    field_name=row[2],
                    operator=row[3],
                    threshold_value=row[4],
                    severity=row[5],
                    enabled=row[6],
                    created_at=row[7],
                    updated_at=row[8]
                ))
            
            cursor.close()
            DB_OPERATIONS.labels(operation='select').inc()
            
            return configurations
            
        except psycopg2.Error as error:
            DB_OPERATIONS.labels(operation='error').inc()
            logger.error(f"Database error getting alert configurations: {error}")
            raise
            
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def close(self) -> None:
        """Close the PostgreSQL connection pool"""
        if self.db_pool:
            self.db_pool.closeall()
            logger.info("PostgreSQL connections closed")
