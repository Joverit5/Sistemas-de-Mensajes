"""
Alert repository interface
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from weather_alerts.models import Alert, AlertConfiguration


class AlertRepository(ABC):
    """Interface for alert repositories"""
    
    @abstractmethod
    def get_alert_configurations(self) -> List[AlertConfiguration]:
        """Get all enabled alert configurations"""
        pass
    
    @abstractmethod
    def get_threshold_exceeded_readings(self, field_name: str, operator: str, threshold_value: float) -> List[Dict[str, Any]]:
        """Get readings that exceed the threshold"""
        pass
    
    @abstractmethod
    def get_active_alert(self, station_id: str, alert_type: str) -> Optional[Alert]:
        """Get active alert for a station and alert type"""
        pass
    
    @abstractmethod
    def save_alert(self, alert: Alert) -> Optional[int]:
        """Save an alert and return its ID"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the repository connection"""
        pass
