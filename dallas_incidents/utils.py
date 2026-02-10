"""
Utility functions for Dallas Incidents data processing.

Provides helpers for data transformation, analysis, and common operations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from collections import Counter
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


def parse_datetime(dt_string: str) -> Optional[datetime]:
    """
    Parse various datetime string formats from Socrata.
    
    Args:
        dt_string: Datetime string from API
    
    Returns:
        datetime object or None if parsing fails
    """
    if not dt_string:
        return None
    
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(dt_string, fmt)
        except (ValueError, TypeError):
            continue
    
    # Use debug instead of warning to avoid spam
    logger.debug(f"Could not parse datetime: {dt_string}")
    return None


def extract_date(dt_string: str) -> Optional[date]:
    """
    Extract date from datetime string.
    
    Args:
        dt_string: Datetime string from API
    
    Returns:
        date object or None
    """
    dt = parse_datetime(dt_string)
    return dt.date() if dt else None


def group_by_field(
    incidents: List[Dict[str, Any]],
    field: str,
    properties: bool = False,
) -> Dict[Any, List[Dict[str, Any]]]:
    """
    Group incidents by a specific field.
    
    Args:
        incidents: List of incident dictionaries
        field: Field name to group by
        properties: If True, look in properties dict (for GeoJSON)
    
    Returns:
        Dictionary mapping field values to lists of incidents
    """
    grouped = {}
    
    for incident in incidents:
        data = incident.get("properties", incident) if properties else incident
        value = data.get(field)
        
        if value not in grouped:
            grouped[value] = []
        grouped[value].append(incident)
    
    return grouped


def count_by_field(
    incidents: List[Dict[str, Any]],
    field: str,
    properties: bool = False,
) -> Dict[Any, int]:
    """
    Count incidents by field value.
    
    Args:
        incidents: List of incident dictionaries
        field: Field name to count by
        properties: If True, look in properties dict (for GeoJSON)
    
    Returns:
        Dictionary mapping field values to counts
    """
    counts = Counter()
    
    for incident in incidents:
        data = incident.get("properties", incident) if properties else incident
        value = data.get(field)
        if value is not None:
            counts[value] += 1
    
    return dict(counts)


def get_top_n(
    counts: Dict[Any, int],
    n: int = 10,
    reverse: bool = True,
) -> List[Tuple[Any, int]]:
    """
    Get top N items from a counts dictionary.
    
    Args:
        counts: Dictionary of counts
        n: Number of items to return
        reverse: If True, return highest counts first
    
    Returns:
        List of (value, count) tuples
    """
    return sorted(counts.items(), key=lambda x: x[1], reverse=reverse)[:n]


def filter_by_date(
    incidents: List[Dict[str, Any]],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    date_field: str = "date1",
    properties: bool = False,
) -> List[Dict[str, Any]]:
    """
    Filter incidents by date range (client-side).
    
    Args:
        incidents: List of incident dictionaries
        start_date: Minimum date (inclusive)
        end_date: Maximum date (inclusive)
        date_field: Field containing date
        properties: If True, look in properties dict (for GeoJSON)
    
    Returns:
        Filtered list of incidents
    """
    filtered = []
    
    for incident in incidents:
        data = incident.get("properties", incident) if properties else incident
        dt_string = data.get(date_field)
        
        if not dt_string:
            continue
        
        incident_date = extract_date(dt_string)
        if not incident_date:
            continue
        
        if start_date and incident_date < start_date:
            continue
        if end_date and incident_date > end_date:
            continue
        
        filtered.append(incident)
    
    return filtered


def extract_coordinates(
    incident: Dict[str, Any]
) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract latitude and longitude from various incident formats.
    
    Args:
        incident: Incident dictionary
    
    Returns:
        Tuple of (latitude, longitude) or (None, None)
    """
    # GeoJSON format
    if "geometry" in incident:
        geom = incident["geometry"]
        if geom and geom.get("type") == "Point":
            coords = geom.get("coordinates", [])
            if len(coords) >= 2:
                return coords[1], coords[0]  # lat, lon
    
    # Check properties
    props = incident.get("properties", incident)
    
    # geocoded_column format
    if "geocoded_column" in props:
        loc = props["geocoded_column"]
        if isinstance(loc, dict):
            if "coordinates" in loc:
                coords = loc["coordinates"]
                return coords[1], coords[0]  # lat, lon
            if "latitude" in loc and "longitude" in loc:
                return float(loc["latitude"]), float(loc["longitude"])
    
    # Direct lat/lon fields
    if "latitude" in props and "longitude" in props:
        try:
            return float(props["latitude"]), float(props["longitude"])
        except (ValueError, TypeError):
            pass
    
    return None, None


def calculate_bounding_box(
    incidents: List[Dict[str, Any]]
) -> Optional[Tuple[float, float, float, float]]:
    """
    Calculate bounding box for incidents.
    
    Args:
        incidents: List of incident dictionaries
    
    Returns:
        Tuple of (min_lat, min_lon, max_lat, max_lon) or None
    """
    lats, lons = [], []
    
    for incident in incidents:
        lat, lon = extract_coordinates(incident)
        if lat and lon:
            lats.append(lat)
            lons.append(lon)
    
    if not lats or not lons:
        return None
    
    return min(lats), min(lons), max(lats), max(lons)


def distance_meters(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate distance between two coordinates using Haversine formula.
    
    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point
    
    Returns:
        Distance in meters
    """
    from math import radians, sin, cos, sqrt, atan2
    
    # Earth radius in meters
    R = 6371000
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    
    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c


def incidents_near_point(
    incidents: List[Dict[str, Any]],
    latitude: float,
    longitude: float,
    radius_meters: float = 1000,
) -> List[Dict[str, Any]]:
    """
    Filter incidents within radius of a point (client-side).
    
    Args:
        incidents: List of incident dictionaries
        latitude: Center point latitude
        longitude: Center point longitude
        radius_meters: Search radius in meters
    
    Returns:
        Filtered list of incidents
    """
    nearby = []
    
    for incident in incidents:
        inc_lat, inc_lon = extract_coordinates(incident)
        if inc_lat and inc_lon:
            dist = distance_meters(latitude, longitude, inc_lat, inc_lon)
            if dist <= radius_meters:
                nearby.append(incident)
    
    return nearby


def summarize_incidents(
    incidents: List[Dict[str, Any]],
    properties: bool = False,
) -> Dict[str, Any]:
    """
    Generate summary statistics for incidents.
    
    Args:
        incidents: List of incident dictionaries
        properties: If True, look in properties dict (for GeoJSON)
    
    Returns:
        Dictionary with summary statistics
    """
    if not incidents:
        return {"total": 0}
    
    # Count by various fields
    beats = count_by_field(incidents, "beat", properties)
    divisions = count_by_field(incidents, "division", properties)
    offenses = count_by_field(incidents, "ucr_offense", properties)
    nibrs_types = count_by_field(incidents, "nibrstype", properties)
    
    # Date range
    dates = []
    for incident in incidents:
        data = incident.get("properties", incident) if properties else incident
        dt_string = data.get("date1")
        if dt_string:
            dt = extract_date(dt_string)
            if dt:
                dates.append(dt)
    
    summary = {
        "total": len(incidents),
        "unique_beats": len(beats),
        "unique_divisions": len(divisions),
        "unique_offenses": len(offenses),
        "top_beats": get_top_n(beats, 5),
        "top_divisions": get_top_n(divisions, 5),
        "top_offenses": get_top_n(offenses, 10),
        "top_nibrs_types": get_top_n(nibrs_types, 5),
    }
    
    if dates:
        summary["date_range"] = {
            "earliest": min(dates).isoformat(),
            "latest": max(dates).isoformat(),
        }
    
    # Geographic info
    bbox = calculate_bounding_box(incidents)
    if bbox:
        summary["bounding_box"] = {
            "min_lat": bbox[0],
            "min_lon": bbox[1],
            "max_lat": bbox[2],
            "max_lon": bbox[3],
        }
    
    return summary


def to_dataframe(incidents: List[Dict[str, Any]], flatten_geojson: bool = True):
    """
    Convert incidents to pandas DataFrame.
    
    Args:
        incidents: List of incident dictionaries
        flatten_geojson: If True, flatten GeoJSON properties
    
    Returns:
        pandas DataFrame
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(
            "pandas is required for to_dataframe(). "
            "Install with: pip install pandas"
        )
    
    if not incidents:
        return pd.DataFrame()
    
    # Handle GeoJSON format
    if flatten_geojson and "properties" in incidents[0]:
        data = []
        for incident in incidents:
            row = incident.get("properties", {}).copy()
            
            # Add coordinates if available
            lat, lon = extract_coordinates(incident)
            if lat and lon:
                row["latitude"] = lat
                row["longitude"] = lon
            
            data.append(row)
        return pd.DataFrame(data)
    
    return pd.DataFrame(incidents)


def export_to_geojson(
    incidents: List[Dict[str, Any]],
    output_file: str,
):
    """
    Export incidents to GeoJSON file.
    
    Args:
        incidents: List of incident dictionaries (should be GeoJSON format)
        output_file: Path to output file
    """
    import json
    
    geojson = {
        "type": "FeatureCollection",
        "features": incidents,
    }
    
    with open(output_file, "w") as f:
        json.dump(geojson, f, indent=2)
    
    logger.info(f"Exported {len(incidents)} incidents to {output_file}")


def export_to_csv(
    incidents: List[Dict[str, Any]],
    output_file: str,
    flatten_geojson: bool = True,
):
    """
    Export incidents to CSV file.
    
    Args:
        incidents: List of incident dictionaries
        output_file: Path to output file
        flatten_geojson: If True, flatten GeoJSON properties
    """
    df = to_dataframe(incidents, flatten_geojson)
    df.to_csv(output_file, index=False)
    
    logger.info(f"Exported {len(incidents)} incidents to {output_file}")
