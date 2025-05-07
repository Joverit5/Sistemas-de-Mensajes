"""
RabbitMQ notifier implementation
"""
import json
import logging
import os
import time
from datetime import datetime

import pika
from prometheus_client import Counter

from weather_alerts.models import Alert, AlertNotification
from weather_alerts.notifiers.alert_notifier import AlertNotifier

logger = logging.getLogger("weather-alerts")

# Configure Prometheus metrics
NOTIFICATIONS_SENT = Counter('weather_alerts_notifications_sent_total', 'Total number of alert notifications sent', ['severity'])
NOTIFICATION_ERRORS = Counter('weather_alerts_notification_errors_total', 'Total number of notification errors', ['type'])

# Environment variables
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'weather_user')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'weather_password')
EXCHANGE_NAME = os.getenv('EXCHANGE_NAME', 'weather_exchange')
ROUTING_KEY = os.getenv('ROUTING_KEY', 'weather.alerts')


class RabbitMQNotifier(AlertNotifier):
    """RabbitMQ notifier implementation"""
    
    def __init__(self):
        """Initialize the RabbitMQ notifier"""
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
                
                logger.info(f"Connected to RabbitMQ at {RABBITMQ_HOST}:{RABBITMQ_PORT}")
                return
                
            except pika.exceptions.AMQPConnectionError as error:
                retry_count += 1
                NOTIFICATION_ERRORS.labels(type='connection').inc()
                logger.error(f"Connection attempt {retry_count} failed: {error}")
                
                if retry_count < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.critical("Max retries reached. Could not connect to RabbitMQ.")
                    raise
    
    def send_alert(self, alert: Alert, severity: str) -> bool:
        """Send an alert notification"""
        try:
            # Check if connection is closed and reconnect if necessary
            if not self.connection or self.connection.is_closed:
                logger.warning("Connection closed. Reconnecting...")
                self.connect()
            
            # Create notification
            notification = AlertNotification(
                alert_id=alert.id,
                station_id=alert.station_id,
                alert_type=alert.alert_type,
                alert_message=alert.alert_message,
                alert_value=alert.alert_value,
                threshold_value=alert.threshold_value,
                timestamp=alert.timestamp.isoformat(),
                severity=severity
            )
            
            # Convert to JSON
            message = json.dumps(notification.model_dump())
            
            # Send message with persistent delivery mode
            self.channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=f"{ROUTING_KEY}.{severity.lower()}",
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            # Update metrics
            NOTIFICATIONS_SENT.labels(severity=severity).inc()
            
            logger.info(f"Sent alert notification: {alert.alert_message}")
            return True
            
        except (pika.exceptions.AMQPError, ConnectionError) as error:
            NOTIFICATION_ERRORS.labels(type='publish').inc()
            logger.error(f"Error sending alert notification: {error}")
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
            logger.info("RabbitMQ connection closed")
