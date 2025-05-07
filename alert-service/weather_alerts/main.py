#!/usr/bin/env python3
"""
Main module for the Weather Alerts service
"""
import logging
import os
import sys
import time

from prometheus_client import start_http_server

from weather_alerts.alert_manager import AlertManager
from weather_alerts.repositories.postgres_repository import PostgresRepository
from weather_alerts.notifiers.rabbitmq_notifier import RabbitMQNotifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("weather-alerts")

# Environment variables
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 10))


def main():
    """Main function to run the weather alerts service"""
    # Start Prometheus metrics server
    start_http_server(8002)
    logger.info("Prometheus metrics server started on port 8002")
    
    # Create repository
    repository = PostgresRepository()
    
    # Create notifier
    notifier = RabbitMQNotifier()
    
    # Create alert manager
    alert_manager = AlertManager(repository, notifier)
    
    try:
        logger.info(f"Starting alert service with check interval of {CHECK_INTERVAL} seconds")
        
        while True:
            # Check for alerts
            alert_manager.check_alerts()
            
            # Wait before next check
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("Alert service stopped by user")
    finally:
        repository.close()
        notifier.close()
        logger.info("All connections closed")


if __name__ == "__main__":
    main()
