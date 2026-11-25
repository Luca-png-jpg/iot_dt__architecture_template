from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseService(ABC):
    """Base class for all services in the pool"""

    def __init__(self):
        self.name = self.__class__.__name__

    @abstractmethod
    def execute(self, data: Dict, **kwargs) -> Any:
        """
        Execute the service on provided data.

        Args:
            data: Input data dictionary provided by the Digital Twin
            **kwargs: Optional service-specific parameters

        Returns:
            Processed data in any format
        """
        pass