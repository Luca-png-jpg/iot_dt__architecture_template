from typing import Dict, List, Any



class DigitalTwin:
    """Core Digital Twin class that manages DRs and services"""

    def __init__(self):
        self.digital_replicas: List = []  # List of DR objects
        self.active_services: Dict = {}  # service_name -> service_instance

    def add_digital_replica(self, dr_instance: Any) -> None:
        """Adds a Digital Replica to the Digital Twin"""
        self.digital_replicas.append(dr_instance)

    def add_service(self, service):
        """Adds a service to the DT"""
        if isinstance(service, type):
            # If a class is passed, instantiate it
            service = service()
        self.active_services[service.name] = service

    def list_services(self):
        """List all services"""
        return list(self.active_services.keys())

    def remove_service(self, service_name: str) -> None:
        """Removes an active service"""
        if service_name in self.active_services:
            del self.active_services[service_name]

    def get_dt_data(self):
        """Get all DT data including DRs"""
        return {"digital_replicas": self.digital_replicas}

    def execute_service(self, service_name: str, **kwargs):
        """Execute a named service with parameters"""
        if service_name not in self.active_services:
            raise ValueError(f"Service {service_name} not found")

        service = self.active_services[service_name]

        # Prepare data for service
        data = {"digital_replicas": self.digital_replicas}

        # Execute service with data and additional parameters
        return service.execute(data, **kwargs)