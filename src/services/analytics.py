from typing import Dict
import statistics
from .base import BaseService


class AggregationService(BaseService):
    """Generic service for aggregating numeric measurements across Digital Replicas"""

    def execute(
        self,
        data: Dict,
        dr_type: str = None,
        attribute: str = None,
        measurements_key: str = "measurements",
        type_key: str = "measure_type",
        value_key: str = "value",
        **kwargs,
    ) -> Dict:
        """
        Execute statistical aggregation on measurements from specified DRs.

        Args:
            data: Dictionary containing the DT data including all DRs
            dr_type: Optional Digital Replica type filter
            attribute: Optional measurement type filter
            measurements_key: Key inside dr['data'] containing the measurements list
            type_key: Key identifying the measurement type in each entry
            value_key: Key identifying the numeric value in each entry
        """
        if not data or "digital_replicas" not in data:
            raise ValueError("Invalid data: missing digital replicas")

        drs = [
            dr
            for dr in data["digital_replicas"]
            if dr_type is None or dr.get("type") == dr_type
        ]

        if not drs:
            return {"error": f"No digital replicas found of type {dr_type}"}

        all_measurements = []
        for dr in drs:
            measurements = dr.get("data", {}).get(measurements_key, [])
            if attribute:
                measurements = [
                    m for m in measurements if m.get(type_key) == attribute
                ]
            all_measurements.extend(measurements)

        if not all_measurements:
            return {"error": f"No measurements found for attribute {attribute}"}

        grouped_measurements = {}
        for measure in all_measurements:
            measure_type = measure.get(type_key)
            if measure_type is None or value_key not in measure:
                continue
            grouped_measurements.setdefault(measure_type, []).append(
                float(measure[value_key])
            )

        stats = {}
        for measure_type, values in grouped_measurements.items():
            try:
                stats[measure_type] = {
                    "count": len(values),
                    "mean": statistics.mean(values),
                    "min": min(values),
                    "max": max(values),
                    "stddev": statistics.stdev(values) if len(values) > 1 else 0,
                }
            except (statistics.StatisticsError, ValueError) as e:
                stats[measure_type] = {"error": str(e), "count": len(values)}

        return stats