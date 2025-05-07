"""
Alert notifier interface
"""
from abc import ABC, abstractmethod

from weather_alerts.models import Alert


class AlertNotifier(ABC):
    """Interface for alert notifiers"""
    
    @abstractmethod
    def send_alert(self, alert: Alert, severity: str) -> bool:
        """Send an alert notification"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the notifier connection"""
        pass
