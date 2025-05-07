"""
Alert manager implementation
"""
import logging
from datetime import datetime
from typing import List

from weather_alerts.models import Alert, AlertConfiguration
from weather_alerts.repositories.alert_repository import AlertRepository
from weather_alerts.notifiers.alert_notifier import AlertNotifier

logger = logging.getLogger("weather-alerts")


class AlertManager:
    """Alert manager implementation"""
    
    def __init__(self, repository: AlertRepository, notifier: AlertNotifier):
        """Initialize the alert manager"""
        self.repository = repository
        self.notifier = notifier
    
    def check_alerts(self) -> None:
        """Check for new alerts based on configured thresholds"""
        try:
            # Get alert configurations
            configurations = self.repository.get_alert_configurations()
            
            if not configurations:
                logger.warning("No alert configurations found")
                return
            
            logger.info(f"Checking alerts with {len(configurations)} configurations")
            
            # Process each configuration
            for config in configurations:
                self._process_alert_configuration(config)
                
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    def _process_alert_configuration(self, config: AlertConfiguration) -> None:
        """Process a single alert configuration"""
        try:
            # Get readings that exceed the threshold
            readings = self.repository.get_threshold_exceeded_readings(
                field_name=config.field_name,
                operator=config.operator,
                threshold_value=config.threshold_value
            )
            
            if not readings:
                return
            
            logger.info(f"Found {len(readings)} readings exceeding threshold for {config.name}")
            
            # Create alerts for each reading
            for reading in readings:
                # Check if alert already exists
                existing_alert = self.repository.get_active_alert(
                    station_id=reading['station_id'],
                    alert_type=config.name
                )
                
                if existing_alert:
                    logger.debug(f"Alert already exists for station {reading['station_id']}")
                    continue
                
                # Create new alert
                alert = Alert(
                    station_id=reading['station_id'],
                    alert_type=config.name,
                    alert_message=f"{config.name}: {reading[config.field_name]} {config.operator} {config.threshold_value}",
                    alert_value=reading[config.field_name],
                    threshold_value=config.threshold_value,
                    timestamp=datetime.now(),
                    status="NEW"
                )
                
                # Save alert
                alert_id = self.repository.save_alert(alert)
                
                if alert_id:
                    # Set the ID from the database
                    alert.id = alert_id
                    
                    # Send notification
                    self.notifier.send_alert(alert, config.severity)
                    
                    logger.info(f"Created and sent alert: {alert.alert_message} for station {alert.station_id}")
                
        except Exception as e:
            logger.error(f"Error processing alert configuration {config.name}: {e}")
