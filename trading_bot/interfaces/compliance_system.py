"""Compliance System interface for audit and regulatory compliance."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from datetime import datetime


class AuditEntry:
    """Audit trail entry."""
    
    def __init__(self, timestamp: datetime, action: str, parameters: Dict[str, Any], result: str):
        self.timestamp = timestamp
        self.action = action
        self.parameters = parameters
        self.result = result


class IComplianceSystem(ABC):
    """Interface for compliance and audit system."""

    @abstractmethod
    def create_audit_entry(self, action: str, parameters: Dict[str, Any], result: str) -> None:
        """Create audit trail entry.
        
        Args:
            action: Action performed
            parameters: Action parameters
            result: Action result
        """
        pass

    @abstractmethod
    def get_audit_trail(self, start_date: datetime, end_date: datetime) -> List[AuditEntry]:
        """Get audit trail for date range.
        
        Args:
            start_date: Start date for audit trail
            end_date: End date for audit trail
            
        Returns:
            List of audit entries
        """
        pass

    @abstractmethod
    def generate_compliance_report(self, period: str) -> Dict[str, Any]:
        """Generate compliance report.
        
        Args:
            period: Reporting period
            
        Returns:
            Compliance report dictionary
        """
        pass

    @abstractmethod
    def track_algo_id(self, trade_id: str, algo_id: str) -> None:
        """Track algorithmic trading ID for compliance.
        
        Args:
            trade_id: Trade identifier
            algo_id: Algorithm identifier
        """
        pass