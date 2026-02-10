"""
Data models for Dallas Incidents API.

Defines dataclasses and types for working with incident data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class OutputFormat(str, Enum):
    """Supported output formats from Socrata API."""
    JSON = "json"
    GEOJSON = "geojson"
    CSV = "csv"


class DatasetPreset(str, Enum):
    """Predefined dataset configurations for common Dallas Open Data datasets."""
    POLICE_INCIDENTS = "qv6i-rri7"  # Historical police incidents (2014-present, 86 columns)
    ACTIVE_CALLS_NORTHEAST = "juse-v5tw"  # Active calls for Northeast Division (5 columns, real-time)
    ACTIVE_CALLS_ALL = "9fxf-t2tr"  # All Dallas Police Active Calls (parent dataset)


@dataclass
class DateRange:
    """Date range filter for incident queries."""
    start: Optional[Union[date, str]] = None
    end: Optional[Union[date, str]] = None
    
    def __post_init__(self):
        """Parse string dates to date objects."""
        if isinstance(self.start, str):
            self.start = datetime.fromisoformat(self.start).date()
        if isinstance(self.end, str):
            self.end = datetime.fromisoformat(self.end).date()

    def to_soql(self, field_name: str = "date1") -> Optional[str]:
        """Convert to SoQL WHERE clause."""
        if not field_name:  # Skip if no datetime field exists
            return None
            
        clauses = []
        
        if self.start:
            start_iso = f"{self.start.isoformat()}T00:00:00.000"
            clauses.append(f"{field_name} >= '{start_iso}'")
        
        if self.end:
            end_iso = f"{self.end.isoformat()}T23:59:59.999"
            clauses.append(f"{field_name} <= '{end_iso}'")
        
        return " AND ".join(clauses) if clauses else None


@dataclass
class GeoQuery:
    """Geographic query parameters."""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_meters: Optional[float] = None
    
    def to_soql(self, location_field: str = "geocoded_column") -> Optional[str]:
        """Convert to SoQL WHERE clause using within_circle."""
        if all([self.latitude, self.longitude, self.radius_meters]):
            return (
                f"within_circle({location_field}, "
                f"{self.latitude}, {self.longitude}, {self.radius_meters})"
            )
        return None


@dataclass
class IncidentQuery:
    """
    Query parameters for fetching incidents.
    
    Provides a fluent interface for building complex queries with semantic search support.
    """
    # Filters
    beats: Optional[List[str]] = None
    division: Optional[str] = None
    date_range: Optional[DateRange] = None
    nibrs_codes: Optional[List[str]] = None
    nibrs_type: Optional[str] = None
    nibrs_crime: Optional[str] = None
    nibrs_crime_category: Optional[str] = None
    nibrs_code: Optional[str] = None
    ucr_offense: Optional[str] = None
    geo_query: Optional[GeoQuery] = None
    
    # Semantic offense category search
    offense_category: Optional[str] = None  # e.g., 'weapon', 'drug', 'violent'
    offense_keyword: Optional[str] = None  # e.g., 'gun', 'sex', 'theft'
    
    # Query options
    limit: int = 1000
    offset: int = 0
    order_by: Optional[str] = None
    select_fields: Optional[List[str]] = None
    
    # Output format
    format: OutputFormat = OutputFormat.JSON
    
    # Additional filters
    extra_where: Optional[str] = None
    
    def to_soql_params(self, config: Optional['ClientConfig'] = None) -> Dict[str, Any]:
        """
        Convert query to SoQL parameters.
        
        Args:
            config: Optional ClientConfig to use for field mapping
        """
        where_clauses = []
        
        # Beat filter
        if self.beats:
            beat_field = config.beat_field if config else "beat"
            beat_list = ", ".join(f"'{b}'" for b in self.beats)
            where_clauses.append(f"{beat_field} IN ({beat_list})")
        
        # Division filter
        if self.division:
            division_field = config.division_field if config else "division"
            if division_field:  # Only add if dataset has division field
                where_clauses.append(f"{division_field} = '{self.division}'")
        
        # Date range - only add if datetime field exists
        if self.date_range and config:
            if config.datetime_field:
                date_clause = self.date_range.to_soql(config.datetime_field)
                if date_clause:
                    where_clauses.append(date_clause)
        
        # NIBRS codes
        if self.nibrs_codes:
            codes_list = ", ".join(f"'{c}'" for c in self.nibrs_codes)
            where_clauses.append(f"nibrs IN ({codes_list})")
        
        # NIBRS type
        if self.nibrs_type:
            where_clauses.append(f"nibrs_type = '{self.nibrs_type}'")
        
        # NIBRS crime (specific offense)
        if self.nibrs_crime:
            where_clauses.append(f"nibrs_crime = '{self.nibrs_crime}'")
        
        # NIBRS crime category
        if self.nibrs_crime_category:
            where_clauses.append(f"nibrs_crime_category = '{self.nibrs_crime_category}'")
        
        # NIBRS code (single code)
        if self.nibrs_code:
            where_clauses.append(f"nibrs_code = '{self.nibrs_code}'")
        
        # UCR offense
        if self.ucr_offense:
            where_clauses.append(f"ucr_offense = '{self.ucr_offense}'")
        
        # Offense category search
        if self.offense_category:
            offense_clause = self._build_offense_category_clause()
            if offense_clause:
                where_clauses.append(offense_clause)
        
        # Offense keyword search
        if self.offense_keyword:
            offense_clause = self._build_offense_keyword_clause()
            if offense_clause:
                where_clauses.append(offense_clause)
        
        # Geographic query
        if self.geo_query:
            location_field = config.location_field if config else "geocoded_column"
            geo_clause = self.geo_query.to_soql(location_field)
            if geo_clause:
                where_clauses.append(geo_clause)
        
        # Extra where clause
        if self.extra_where:
            where_clauses.append(f"({self.extra_where})")
        
        params = {
            "limit": self.limit,
            "offset": self.offset,
        }
        
        if where_clauses:
            params["where"] = " AND ".join(where_clauses)
        
        if self.order_by:
            params["order"] = self.order_by
        
        if self.select_fields:
            params["select"] = ",".join(self.select_fields)
        
        return params
    
    def _build_offense_category_clause(self) -> Optional[str]:
        """Build SoQL WHERE clause for offense category search."""
        try:
            from dallas_incidents.offense_categories import (
                OffenseCategory,
                search_offenses_by_category,
                OFFENSE_TYPE_MAP
            )
        except ImportError:
            return None
        
        # Convert string to enum if needed
        if isinstance(self.offense_category, str):
            try:
                category = OffenseCategory(self.offense_category.lower())
            except ValueError:
                return None
        else:
            category = self.offense_category
        
        # Get offense types for this category
        offenses = OFFENSE_TYPE_MAP.get(category, [])
        
        if not offenses:
            return None
        
        # Build OR clause for offincident field
        offense_conditions = [f"offincident = '{off}'" for off in offenses]
        return f"({' OR '.join(offense_conditions)})"
    
    def _build_offense_keyword_clause(self) -> Optional[str]:
        """Build SoQL WHERE clause for keyword search in offense fields."""
        keyword = self.offense_keyword.upper()
        
        # Search in both offincident and ucr_offense fields
        return (
            f"(upper(offincident) LIKE '%{keyword}%' OR "
            f"upper(ucr_offense) LIKE '%{keyword}%')"
        )


@dataclass
class IncidentResponse:
    """
    Response wrapper for incident data.
    
    Provides convenient access to results and metadata.
    """
    data: List[Dict[str, Any]]
    query: IncidentQuery
    total_returned: int = field(init=False)
    format: OutputFormat = OutputFormat.JSON
    
    def __post_init__(self):
        self.total_returned = len(self.data)
    
    def to_df(self):
        """Convert to pandas DataFrame."""
        try:
            import pandas as pd
            return pd.DataFrame(self.data)
        except ImportError:
            raise ImportError(
                "pandas is required for to_df(). "
                "Install with: pip install pandas"
            )
    
    def to_geopandas(self):
        """Convert to GeoPandas GeoDataFrame (for GeoJSON data)."""
        try:
            import geopandas as gpd
            
            if self.format != OutputFormat.GEOJSON:
                raise ValueError(
                    "to_geopandas() requires GeoJSON format. "
                    "Set format=OutputFormat.GEOJSON in your query."
                )
            
            return gpd.GeoDataFrame.from_features(self.data)
        except ImportError:
            raise ImportError(
                "geopandas is required for to_geopandas(). "
                "Install with: pip install geopandas"
            )
    
    def filter_by_offense(self, offense: str) -> IncidentResponse:
        """Filter results by UCR offense description."""
        filtered = [
            item for item in self.data
            if item.get("ucr_offense", "").lower() == offense.lower()
        ]
        return IncidentResponse(
            data=filtered,
            query=self.query,
            format=self.format
        )
    
    def get_unique_values(self, field: str) -> List[Any]:
        """Get unique values for a specific field."""
        values = set()
        for item in self.data:
            if field in item:
                values.add(item[field])
        return sorted(list(values))
    
    @property
    def has_geometry(self) -> bool:
        """Check if response contains geographic data."""
        if not self.data:
            return False
        return "geometry" in self.data[0] or "geocoded_column" in self.data[0]
    
    def to_map(
        self,
        cluster: bool = True,
        heatmap: bool = False,
        color_by: Optional[str] = None,
        popup_fields: Optional[List[str]] = None,
        popup_profile: Optional[Union[str, List[str]]] = None,
        tiles: str = "OpenStreetMap",
        zoom_start: int = 11,
    ):
        """
        Create an interactive Folium map from the incident data.
        
        This is a convenience method that automatically handles the geographic data
        conversion and creates a map without needing to use IncidentMapper separately.
        
        Args:
            cluster: If True, use marker clustering for better performance
            heatmap: If True, create a heatmap instead of markers
            color_by: Field name to color-code markers (e.g., 'nibrstype', 'ucr_offense')
            popup_fields: List of field names to include in marker popups
            popup_profile: PopupProfile name for predefined field sets:
                - 'essential': Basic info (date, offense, beat, address)
                - 'demographic': Demographic fields (race, ethnicity, sex, victimtype)
                - 'crime_details': Crime classification (UCR, NIBRS, weapon, premise)
                - 'location': Geographic details (beat, division, sector, address)
                - 'temporal': Time-related fields (dates, times, watch)
                - 'investigation': Case details (officers, status, follow-ups)
                - 'comprehensive': Most important fields combined
                Can pass a list like ['essential', 'demographic'] to combine profiles.
            tiles: Map tile style ('OpenStreetMap', 'CartoDB positron', etc.)
            zoom_start: Initial zoom level
        
        Returns:
            folium.Map object
        
        Examples:
            >>> # Simple clustered map with comprehensive popup
            >>> response = client.get_incidents(IncidentQuery(beats=['241'], limit=500))
            >>> map_obj = response.to_map()
            >>> map_obj.save('incidents.html')
            
            >>> # Demographic analysis map
            >>> map_obj = response.to_map(popup_profile='demographic', cluster=False)
            
            >>> # Combine essential and demographic fields
            >>> map_obj = response.to_map(popup_profile=['essential', 'demographic'])
            
            >>> # Crime details with color coding by offense type
            >>> map_obj = response.to_map(
            ...     popup_profile='crime_details',
            ...     color_by='nibrs_type'
            ... )
            
            >>> # Heatmap
            >>> map_obj = response.to_map(heatmap=True, tiles='CartoDB dark_matter')
        """
        try:
            from dallas_incidents.visualization import IncidentMapper
        except ImportError:
            raise ImportError(
                "Folium is required for to_map(). "
                "Install with: pip install folium"
            )
        
        # Check if we have geographic data
        if not self.has_geometry:
            # Try to convert to GeoJSON format if we have geocoded_column
            if self.data and 'geocoded_column' in self.data[0]:
                # Convert data to GeoJSON format
                geojson_data = self._convert_to_geojson()
                # Create a temporary response with GeoJSON format
                geo_response = IncidentResponse(
                    data=geojson_data,
                    query=self.query,
                    format=OutputFormat.GEOJSON
                )
                mapper = IncidentMapper(geo_response)
            # Check if this is Active Calls data (has block/location but no coords)
            elif self.data and 'location' in self.data[0]:
                # Geocode Active Calls addresses
                geojson_data = self._geocode_active_calls()
                if not geojson_data:
                    raise ValueError(
                        "Failed to geocode Active Calls addresses. "
                        "Install geopy with: pip install geopy"
                    )
                # Create a temporary response with GeoJSON format
                geo_response = IncidentResponse(
                    data=geojson_data,
                    query=self.query,
                    format=OutputFormat.GEOJSON
                )
                mapper = IncidentMapper(geo_response)
            else:
                raise ValueError(
                    "No geographic data found in response. "
                    "Ensure the data includes 'geocoded_column', 'geometry', or 'location' fields."
                )
        else:
            mapper = IncidentMapper(self)
        
        # Create and return the map
        return mapper.create_map(
            cluster=cluster,
            heatmap=heatmap,
            color_by=color_by,
            popup_fields=popup_fields,
            popup_profile=popup_profile,
            tiles=tiles,
            zoom_start=zoom_start,
        )
    
    def _convert_to_geojson(self) -> List[Dict[str, Any]]:
        """
        Convert data with geocoded_column to GeoJSON format.
        
        Internal method to handle Police Incidents dataset format where
        geocoded_column contains: {'latitude': 'XX.XXX', 'longitude': '-XX.XXX', 'human_address': '...'}
        """
        features = []
        
        for incident in self.data:
            geo_col = incident.get('geocoded_column')
            if not geo_col:
                continue
            
            # Extract coordinates
            try:
                if isinstance(geo_col, dict):
                    lat = float(geo_col.get('latitude', 0))
                    lon = float(geo_col.get('longitude', 0))
                elif isinstance(geo_col, str):
                    # Handle if it's a JSON string
                    import json
                    geo_data = json.loads(geo_col)
                    lat = float(geo_data.get('latitude', 0))
                    lon = float(geo_data.get('longitude', 0))
                else:
                    continue
                
                # Skip if coordinates are invalid
                if lat == 0 and lon == 0:
                    continue
                
                # Create GeoJSON feature
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]  # GeoJSON is [lon, lat]
                    },
                    "properties": {k: v for k, v in incident.items() if k != 'geocoded_column'}
                }
                features.append(feature)
                
            except (ValueError, TypeError, KeyError, AttributeError):
                # Skip incidents with invalid coordinates
                continue
        
        return features
    
    def _geocode_active_calls(self) -> List[Dict[str, Any]]:
        """
        Geocode Active Calls data using block + location fields.
        
        Active Calls datasets don't have coordinates, only street addresses.
        This method constructs full addresses and geocodes them to lat/lon.
        
        Returns:
            List of GeoJSON features with geocoded coordinates
        """
        try:
            from dallas_incidents.geocoding import geocode_active_calls
        except ImportError:
            raise ImportError(
                "geopy is required for geocoding Active Calls data. "
                "Install with: pip install geopy"
            )
        
        # Geocode all calls
        print(f"Geocoding {len(self.data)} Active Calls addresses...")
        geocoded_calls = geocode_active_calls(self.data, show_progress=True)
        
        # Convert to GeoJSON format
        features = []
        for call in geocoded_calls:
            # Check if this is an intersection (has LineString geometry)
            if call.get('is_intersection') and call.get('intersection_coords'):
                # Create LineString feature for intersection
                coords_list = call['intersection_coords']  # [(lat1, lon1), (lat2, lon2)]
                
                # Convert to GeoJSON format [lon, lat]
                line_coords = [[lon, lat] for lat, lon in coords_list]
                
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": line_coords
                    },
                    "properties": {
                        k: v for k, v in call.items()
                        if k not in ('latitude', 'longitude', 'intersection_coords', 'is_intersection')
                    }
                }
                features.append(feature)
            else:
                # Regular point feature
                lat = call.get('latitude')
                lon = call.get('longitude')
                
                # Skip if geocoding failed
                if lat is None or lon is None:
                    continue
                
                # Create GeoJSON feature
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]  # GeoJSON is [lon, lat]
                    },
                    "properties": {
                        k: v for k, v in call.items()
                        if k not in ('latitude', 'longitude', 'intersection_coords', 'is_intersection')
                    }
                }
                features.append(feature)
        
        return features


@dataclass
class ClientConfig:
    """
    Configuration for DallasIncidentsClient.
    
    Supports multiple datasets with different schemas through preset configurations.
    Use from_preset() to quickly configure for common datasets.
    
    Examples:
        # Use Police Incidents (historical data with timestamps)
        config = ClientConfig.from_preset('police_incidents', app_token='your_token')
        
        # Use Active Calls for Northeast Division (real-time, no timestamps)
        config = ClientConfig.from_preset('active_calls_northeast', app_token='your_token')
        
        # Custom configuration
        config = ClientConfig(
            dataset_id='custom-id',
            datetime_field='custom_date_field',
            app_token='your_token'
        )
    """
    domain: str = "www.dallasopendata.com"
    dataset_id: str = "juse-v5tw"  # Default: Active Calls Northeast
    app_token: Optional[str] = None
    timeout: int = 30
    username: Optional[str] = None
    password: Optional[str] = None
    
    # Field mapping - varies by dataset schema
    datetime_field: Optional[str] = None  # Set to None for datasets without timestamps
    location_field: str = "location"
    beat_field: str = "beat"
    division_field: str = "division"
    
    # Dataset metadata
    dataset_name: Optional[str] = None
    dataset_description: Optional[str] = None
    
    @classmethod
    def from_preset(cls, preset: Union[str, DatasetPreset], app_token: Optional[str] = None) -> 'ClientConfig':
        """
        Create configuration from a predefined dataset preset.
        
        Args:
            preset: Dataset preset name or DatasetPreset enum value
            app_token: Optional Socrata app token
            
        Returns:
            Configured ClientConfig instance
            
        Available presets:
            - 'police_incidents' or DatasetPreset.POLICE_INCIDENTS:
                Historical police incidents (June 2014-present)
                86 columns including timestamps, NIBRS codes, UCR offenses
                
            - 'active_calls_northeast' or DatasetPreset.ACTIVE_CALLS_NORTHEAST:
                Real-time active calls for Northeast Division
                5 columns: nature_of_call, unit_number, block, location, beat
                Updated every few minutes, no historical timestamps
                
            - 'active_calls_all' or DatasetPreset.ACTIVE_CALLS_ALL:
                Real-time active calls for all Dallas divisions
                Parent dataset for regional filtered views
        
        Examples:
            >>> config = ClientConfig.from_preset('police_incidents', app_token='token123')
            >>> config = ClientConfig.from_preset(DatasetPreset.ACTIVE_CALLS_NORTHEAST)
        """
        # Convert string to enum if needed
        original_preset = preset
        if isinstance(preset, DatasetPreset):
            # Already an enum, use as-is
            pass
        elif isinstance(preset, str):
            preset_str = preset.lower()
            preset_map = {
                'police_incidents': DatasetPreset.POLICE_INCIDENTS,
                'active_calls_northeast': DatasetPreset.ACTIVE_CALLS_NORTHEAST,
                'active_calls_all': DatasetPreset.ACTIVE_CALLS_ALL,
            }
            if preset_str not in preset_map:
                raise ValueError(
                    f"Unknown preset '{original_preset}'. Available presets: "
                    f"{', '.join(preset_map.keys())}"
                )
            preset = preset_map[preset_str]
        else:
            raise ValueError(
                f"preset must be a string or DatasetPreset enum, got {type(preset)}"
            )
        
        # Configure based on preset
        if preset == DatasetPreset.POLICE_INCIDENTS:
            return cls(
                dataset_id="qv6i-rri7",
                app_token=app_token,
                datetime_field="date1",  # Has timestamp fields
                location_field="geocoded_column",
                beat_field="beat",
                division_field="division",
                dataset_name="Police Incidents",
                dataset_description="Historical police incidents from June 2014 to present (86 columns)"
            )
        
        elif preset == DatasetPreset.ACTIVE_CALLS_NORTHEAST:
            return cls(
                dataset_id="juse-v5tw",
                app_token=app_token,
                datetime_field=None,  # No timestamp fields
                location_field="location",
                beat_field="beat",
                division_field=None,  # Not available in this dataset
                dataset_name="Active Calls - Northeast Division",
                dataset_description="Real-time active police calls for Northeast Division (5 columns, updated every few minutes)"
            )
        
        elif preset == DatasetPreset.ACTIVE_CALLS_ALL:
            return cls(
                dataset_id="9fxf-t2tr",
                app_token=app_token,
                datetime_field=None,  # No timestamp fields
                location_field="location",
                beat_field="beat",
                division_field=None,
                dataset_name="Dallas Police Active Calls",
                dataset_description="Real-time active police calls for all Dallas divisions"
            )
        
        else:
            raise ValueError(f"Unsupported preset: {preset}")
    
    @property
    def endpoint_url(self) -> str:
        """Get the full endpoint URL."""
        return f"https://{self.domain}/resource/{self.dataset_id}"
    
    @property
    def supports_timestamps(self) -> bool:
        """Check if this dataset has timestamp fields."""
        return self.datetime_field is not None
    
    def get_info(self) -> str:
        """Get human-readable configuration info."""
        info = [
            f"Dataset: {self.dataset_name or self.dataset_id}",
            f"Description: {self.dataset_description or 'N/A'}",
            f"Endpoint: {self.endpoint_url}",
            f"Timestamp Support: {'Yes' if self.supports_timestamps else 'No'}",
        ]
        if self.datetime_field:
            info.append(f"Datetime Field: {self.datetime_field}")
        return "\n".join(info)
