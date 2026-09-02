"""Base interface for JARVIS modules and agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseModule(ABC):
    """Abstract base class for all pluggable JARVIS modules (email, voice, calendar, scrapers, etc.)."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.is_initialized = False

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize connections, credentials, or resources needed by the module.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        pass

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """Main execution method for the module.
        
        Args:
            **kwargs: Module-specific arguments.
            
        Returns:
            Any: Module-specific execution output.
        """
        pass

    def shutdown(self) -> None:
        """Cleanup resources, close sockets, or terminate subprocesses."""
        self.is_initialized = False

    def get_status(self) -> Dict[str, Any]:
        """Return module health status and metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "initialized": self.is_initialized,
        }
