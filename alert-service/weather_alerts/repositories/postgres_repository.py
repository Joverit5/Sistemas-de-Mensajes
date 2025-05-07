"""
PostgreSQL repository implementation for alerts
"""
import logging
import os
import time
from typing import List, Dict, Any, Optional

import psycopg2
from psycopg2 import pool
from prometheus_client import Counter, Gauge

from weather_alerts.models import Alert, AlertConfiguration
from weather_alerts.repositories.alert_repository import AlertRepository

logger = logging.getLogger("weather-alerts")

# Configure Prometheus metrics
DB_OPERATIONS = Counter('weather_alerts_db_operations_total', 'Total number of database operations', ['operation'])
DB_CONNECTION_POOL_SIZE = Gauge('weather_alerts_db_connection_pool_size', 'Current size of the database connection pool')

# Environment variables
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
POSTGRES_USER = os.getenv('POSTGRES_USER', 'weather_user')
POSTGRES_PASS = os.getenv('POSTGRES_PASS', 'weather_password')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'weather_db')
DB_POOL_MIN = int(os.getenv('DB_POOL_MIN', 1))
DB_POOL_MAX = int(os.getenv('DB_POOL_MAX', 5))


class PostgresRepository(AlertRepository):
    """PostgreSQL repository implementation for alerts"""
    
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
    
    def get_alert_configurations(self) -> List[AlertConfiguration]:
        """Get all enabled alert configurations"""
        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, field_name, operator, threshold_value, severity, enabled
                FROM alert_configurations
                WHERE enabled = TRUE
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
                    enabled=row[6]
                ))
            
            cursor.close()
            DB_OPERATIONS.labels(operation='select').inc()
            
            return configurations
            
        except psycopg2.Error as error:
            DB_OPERATIONS.labels(operation='error').inc()
            logger.error(f"Database error getting alert configurations: {error}")
            return []
            
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def get_threshold_exceeded_readings(self, field_name: str, operator: str, threshold_value: float) -> List[Dict[str, Any]]:
        """Get readings that exceed the threshold"""
        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            
            # Build the query based on the operator
            operator_sql = ""
            if operator == ">":
                operator_sql = ">"
            elif operator == "<":
                operator_sql = "<"
            elif operator == ">=":
                operator_sql = ">="
            elif operator == "<=":
                operator_sql = "<="
            elif operator == "=":
                operator_sql = "="
            else:
                logger.error(f"Unsupported operator: {operator}")
                return []
            
            # Get the latest readings per station that exceed the threshold
            query = f"""
                SELECT * FROM latest_station_readings
                WHERE {field_name} IS NOT NULL
                AND {field_name} {operator_sql} %s
            """
            
            cursor.execute(query, (threshold_value,))
            
            columns = [desc[0] for desc in cursor.description]
            readings = []
            
            for row in cursor.fetchall():
                reading = dict(zip(columns, row))
                readings.append(reading)
            
            cursor.close()
            DB_OPERATIONS.labels(operation='select').inc()
            
            return readings
            
        except psycopg2.Error as error:
            DB_OPERATIONS.labels(operation='error').inc()
            logger.error(f"Database error getting threshold exceeded readings: {error}")
            return []
            
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def get_active_alert(self, station_id: str, alert_type: str) -> Optional[Alert]:
        """Get active alert for a station and alert type"""
        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, station_id, alert_type, alert_message, alert_value, threshold_value, 
                       timestamp, status, created_at, resolved_at
                FROM weather_alerts
                WHERE station_id = %s AND alert_type = %s AND status != 'RESOLVED'
                ORDER BY timestamp DESC
                LIMIT 1
            """, (station_id, alert_type))
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return Alert(
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
                )
            
            return None
            
        except psycopg2.Error as error:
            DB_OPERATIONS.labels(operation='error').inc()
            logger.error(f"Database error getting active alert: {error}")
            return None
            
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def save_alert(self, alert: Alert) -> Optional[int]:
        """Save an alert and return its ID"""
        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO weather_alerts (
                    station_id, alert_type, alert_message, alert_value, 
                    threshold_value, timestamp, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                alert.station_id,
                alert.alert_type,
                alert.alert_message,
                alert.alert_value,
                alert.threshold_value,
                alert.timestamp,
                alert.status
            ))
            
            alert_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            
            DB_OPERATIONS.labels(operation='insert').inc()
            return alert_id
            
        except psycopg2.Error as error:
            DB_OPERATIONS.labels(operation='error').inc()
            logger.error(f"Database error saving alert: {error}")
            
            if conn:
                conn.rollback()
            return None
            
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def close(self) -> None:
        """Close the PostgreSQL connection pool"""
        if self.db_pool:
            self.db_pool.closeall()
            logger.info("PostgreSQL connections closed")
