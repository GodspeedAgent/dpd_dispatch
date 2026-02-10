"""dallas_incidents package.

Convenience re-exports for the primary client and core models.
"""

from .client import DallasIncidentsClient
from .models import (
    ClientConfig,
    IncidentQuery,
    IncidentResponse,
    OutputFormat,
    DateRange,
    GeoQuery,
)

__all__ = [
    "DallasIncidentsClient",
    "ClientConfig",
    "IncidentQuery",
    "IncidentResponse",
    "OutputFormat",
    "DateRange",
    "GeoQuery",
]
