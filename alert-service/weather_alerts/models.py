"""
Data models for the Weather Alerts service
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertStatus(Enum):
    """Alert status values"""
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class AlertConfiguration(BaseModel):
    """Alert configuration model"""
    id: int
    name: str
    field_name: str
    operator: str
    threshold_value: float
    severity: str
    enabled: bool


class Alert(BaseModel):
    """Alert model"""
    id: Optional[int] = None
    station_id: str
    alert_type: str
    alert_message: str
    alert_value: float
    threshold_value: float
    timestamp: datetime
    status: str = AlertStatus.NEW.value
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class AlertNotification(BaseModel):
    """Alert notification model"""
    alert_id: int
    station_id: str
    alert_type: str
    alert_message: str
    alert_value: float
    threshold_value: float
    timestamp: str
    severity: str
