"""
Message publisher interface
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class MessagePublisher(ABC):
    """Interface for message publishers"""
    
    @abstractmethod
    def send_message(self, data: Dict[str, Any]) -> bool:
        """Send a message to the messaging system"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the connection to the messaging system"""
        pass
