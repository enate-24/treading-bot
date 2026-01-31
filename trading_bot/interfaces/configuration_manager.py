"""Configuration Manager interface for system configuration."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class IConfigurationManager(ABC):
    """Interface for configuration management component."""

    @abstractmethod
    def load_configuration(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        pass

    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate configuration parameters.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if configuration is valid
        """
        pass

    @abstractmethod
    def update_configuration(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values.
        
        Args:
            updates: Dictionary of configuration updates
        """
        pass

    @abstractmethod
    def get_configuration_history(self) -> List[Dict[str, Any]]:
        """Get configuration change history.
        
        Returns:
            List of historical configurations
        """
        pass

    @abstractmethod
    def rollback_configuration(self, version: int) -> None:
        """Rollback to previous configuration version.
        
        Args:
            version: Configuration version to rollback to
        """
        pass