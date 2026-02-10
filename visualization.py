"""
Visualization module for Dallas Incidents.

Provides tools for creating interactive maps and visualizations using Folium.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import logging
from enum import Enum

from dallas_incidents.models import IncidentResponse, OutputFormat

logger = logging.getLogger(__name__)


class PopupProfile(str, Enum):
    """Predefined popup field profiles for easy map customization."""
    ESSENTIAL = "essential"
    DEMOGRAPHIC = "demographic"
    CRIME_DETAILS = "crime_details"
    LOCATION = "location"
    TEMPORAL = "temporal"
    INVESTIGATION = "investigation"
    NIBRS = "nibrs"
    COMPREHENSIVE = "comprehensive"


# Predefined field sets for different use cases
POPUP_FIELD_PROFILES = {
    PopupProfile.ESSENTIAL: [
        'date1',
        'offincident',
        'beat',
        'incident_address',
        'incidentnum'
    ],
    
    PopupProfile.DEMOGRAPHIC: [
        'date1',
        'offincident',
        'involvement',
        'victimtype',
        'comprace',
        'compethnicity',
        'compsex',
        'objattack',
    ],
    
    PopupProfile.CRIME_DETAILS: [
        'date1',
        'offincident',
        'ucr_offense',
        'nibrs_crime',
        'nibrs_type',
        'nibrs_crime_category',
        'premise',
        'weaponused',
        'gang',
    ],
    
    PopupProfile.LOCATION: [
        'incident_address',
        'beat',
        'division',
        'sector',
        'district',
        'zip_code',
        'city',
        'ra',
    ],
    
    PopupProfile.TEMPORAL: [
        'date1',
        'time1',
        'date2_of_occurrence_2',
        'reporteddate',
        'edate',
        'watch',
        'servyr',
    ],
    
    PopupProfile.INVESTIGATION: [
        'incidentnum',
        'servnumid',
        'ro1name',
        'ro2name',
        'status',
        'ucr_disp',
        'followup1',
        'followup2',
        'elenum',
    ],
    
    PopupProfile.NIBRS: [
        'date1',
        'offincident',
        'nibrs_crime',
        'nibrs_crime_category',
        'nibrs_crimeagainst',
        'nibrs_code',
        'nibrs_group',
        'nibrs_type',
    ],
    
    PopupProfile.COMPREHENSIVE: [
        'date1',
        'incidentnum',
        'offincident',
        'ucr_offense',
        'nibrs_type',
        'incident_address',
        'beat',
        'division',
        'comprace',
        'compsex',
        'weaponused',
        'premise',
        'status',
    ],
}


def get_popup_fields(profile: Union[PopupProfile, str, List[Union[PopupProfile, str]]]) -> List[str]:
    """
    Get popup fields for a predefined profile or combine multiple profiles.
    
    Args:
        profile: PopupProfile enum value, string, or list of profiles to combine
    
    Returns:
        List of field names (with duplicates removed if combining profiles)
        
    Examples:
        >>> get_popup_fields('essential')
        ['date1', 'offincident', 'beat', 'incident_address']
        
        >>> get_popup_fields(['essential', 'demographic'])
        ['date1', 'offincident', 'beat', 'incident_address', 'comprace', 'compethnicity', 'compsex', 'victimtype', 'involvement']
    """
    # Handle list of profiles - combine with ordered union
    if isinstance(profile, list):
        combined_fields = []
        seen = set()
        for p in profile:
            # Convert string to enum if needed
            if isinstance(p, str):
                p = PopupProfile(p)
            # Add fields from this profile
            for field in POPUP_FIELD_PROFILES.get(p, POPUP_FIELD_PROFILES[PopupProfile.ESSENTIAL]):
                if field not in seen:
                    combined_fields.append(field)
                    seen.add(field)
        return combined_fields
    
    # Handle single profile
    if isinstance(profile, str):
        profile = PopupProfile(profile)
    
    return POPUP_FIELD_PROFILES.get(profile, POPUP_FIELD_PROFILES[PopupProfile.ESSENTIAL])


class IncidentMapper:
    """
    Create interactive Folium maps from incident data.
    
    Supports clustering, heatmaps, and custom marker styling.
    
    Example:
        >>> from dallas_incidents import DallasIncidentsClient, IncidentMapper
        >>> 
        >>> client = DallasIncidentsClient()
        >>> response = client.get_geojson(limit=500)
        >>> 
        >>> mapper = IncidentMapper(response)
        >>> map_obj = mapper.create_map(cluster=True)
        >>> map_obj.save("incidents_map.html")
    """
    
    # Default Dallas coordinates
    DEFAULT_CENTER = (32.7767, -96.7970)
    DEFAULT_ZOOM = 11
    
    def __init__(
        self,
        response: Optional[IncidentResponse] = None,
        center: Optional[Tuple[float, float]] = None,
        zoom_start: int = DEFAULT_ZOOM,
    ):
        """
        Initialize the mapper.
        
        Args:
            response: IncidentResponse with data to map
            center: Map center coordinates (lat, lon)
            zoom_start: Initial zoom level
        """
        self.response = response
        self.center = center or self.DEFAULT_CENTER
        self.zoom_start = zoom_start
        
        # Import folium here to make it optional
        try:
            import folium
            self.folium = folium
        except ImportError:
            raise ImportError(
                "folium is required for visualization. "
                "Install with: pip install folium"
            )
    
    def create_map(
        self,
        cluster: bool = False,
        heatmap: bool = False,
        color_by: Optional[str] = None,
        popup_fields: Optional[List[str]] = None,
        popup_profile: Optional[Union[PopupProfile, str, List[Union[PopupProfile, str]]]] = None,
        style_function: Optional[Callable] = None,
        tiles: str = "OpenStreetMap",
        zoom_start: Optional[int] = None,
        **map_kwargs,
    ):
        """
        Create an interactive Folium map.
        
        Args:
            cluster: Use marker clustering for better performance
            heatmap: Create a heatmap instead of markers
            color_by: Field to use for color coding markers
            popup_fields: List of fields to show in popups (overrides popup_profile)
            popup_profile: PopupProfile enum, string, or list of profiles to combine ('essential', 'demographic', etc.)
            style_function: Custom styling function for markers
            tiles: Map tile provider (OpenStreetMap, CartoDB, Stamen, etc.)
            zoom_start: Initial zoom level (overrides default if provided)
            **map_kwargs: Additional arguments for folium.Map
        
        Returns:
            folium.Map object
        
        Examples:
            # Use single profile
            >>> mapper.create_map(popup_profile='demographic')
            
            # Combine multiple profiles
            >>> mapper.create_map(popup_profile=['essential', 'demographic'])
            
            # Custom fields still work
            >>> mapper.create_map(popup_fields=['date1', 'offincident', 'beat'])
        """
        if self.response is None:
            raise ValueError("No response data provided")
        
        # Determine popup fields to use
        if popup_fields is None and popup_profile is not None:
            popup_fields = get_popup_fields(popup_profile)
        
        # Auto-calculate center if not provided
        if self.center == self.DEFAULT_CENTER and self.response.data:
            calculated_center = self._calculate_center()
            if calculated_center:
                self.center = calculated_center
        
        # Use provided zoom_start or fall back to instance default
        zoom = zoom_start if zoom_start is not None else self.zoom_start
        
        # Create base map
        m = self.folium.Map(
            location=self.center,
            zoom_start=zoom,
            tiles=tiles,
            **map_kwargs,
        )
        
        if heatmap:
            self._add_heatmap(m)
        elif cluster:
            self._add_clustered_markers(m, popup_fields, color_by, style_function)
        else:
            self._add_markers(m, popup_fields, color_by, style_function)
        
        # Add LineString features (intersections) on top
        self._add_linestrings(m, popup_fields, color_by)
        
        # Add layer control if multiple layers
        self.folium.LayerControl().add_to(m)
        
        logger.info(f"Created map with {len(self.response.data)} incidents")
        
        return m
    
    def _calculate_center(self) -> Optional[Tuple[float, float]]:
        """Calculate map center from incident locations."""
        lats, lons = [], []
        
        for incident in self.response.data:
            # Handle LineString geometry (intersections)
            if "geometry" in incident and incident["geometry"]["type"] == "LineString":
                coords = incident["geometry"]["coordinates"]
                # Add all points in the line
                for lon, lat in coords:
                    lats.append(lat)
                    lons.append(lon)
            else:
                # Handle Point geometry
                lat, lon = self._extract_coordinates(incident)
                if lat and lon:
                    lats.append(lat)
                    lons.append(lon)
        
        if lats and lons:
            return (sum(lats) / len(lats), sum(lons) / len(lons))
        
        return None
    
    def _extract_coordinates(
        self, incident: Dict[str, Any]
    ) -> Tuple[Optional[float], Optional[float]]:
        """Extract lat/lon from various incident formats."""
        # GeoJSON format
        if "geometry" in incident:
            geom = incident["geometry"]
            if geom["type"] == "Point":
                lon, lat = geom["coordinates"]
                return lat, lon
            elif geom["type"] == "LineString":
                # For LineString, return None to skip in point-based methods
                return None, None
        
        # Direct location fields
        if "geocoded_column" in incident:
            loc = incident["geocoded_column"]
            if "coordinates" in loc:
                lon, lat = loc["coordinates"]
                return lat, lon
            if "latitude" in loc and "longitude" in loc:
                return float(loc["latitude"]), float(loc["longitude"])
        
        # Separate lat/lon fields
        if "latitude" in incident and "longitude" in incident:
            return float(incident["latitude"]), float(incident["longitude"])
        
        return None, None
    
    def _add_markers(
        self,
        m,
        popup_fields: Optional[List[str]] = None,
        color_by: Optional[str] = None,
        style_function: Optional[Callable] = None,
    ):
        """Add individual markers to map."""
        # Try to import BeautifyIcon for better murder markers
        try:
            from folium.plugins import BeautifyIcon
            has_beautify = True
        except ImportError:
            has_beautify = False
        
        color_map = self._create_color_map(color_by) if color_by else {}
        
        for incident in self.response.data:
            lat, lon = self._extract_coordinates(incident)
            if not (lat and lon):
                continue
            
            # Extract data from properties if GeoJSON
            data = incident.get("properties", incident)
            
            # Check if this is a murder/homicide for special highlighting
            is_murder = False
            if "nibrs_crime_category" in data:
                category = str(data["nibrs_crime_category"]).upper()
                if "HOMICIDE" in category or "MURDER" in category:
                    is_murder = True
            
            # Create popup content
            popup_html = self._create_popup_html(incident, popup_fields)
            
            # Create marker with special styling for murders
            if is_murder and has_beautify:
                # Use star marker with skull icon for murders - very obvious!
                icon = BeautifyIcon(
                    icon='skull',
                    icon_shape='marker',
                    number=None,
                    border_color='darkred',
                    background_color='red',
                    text_color='white',
                    inner_icon_style='font-size:20px;padding-top:1px;'
                )
                self.folium.Marker(
                    location=[lat, lon],
                    popup=self.folium.Popup(popup_html, max_width=300),
                    icon=icon,
                ).add_to(m)
            else:
                # Determine marker color for non-murders
                if is_murder:
                    color = "red"
                    icon = "remove-sign"  # X icon as fallback
                elif color_by and color_by in data:
                    color = color_map.get(data[color_by], "blue")
                    icon = "info-sign"
                else:
                    color = "blue"
                    icon = "info-sign"
                
                # Standard folium marker
                self.folium.Marker(
                    location=[lat, lon],
                    popup=self.folium.Popup(popup_html, max_width=300),
                    icon=self.folium.Icon(color=color, icon=icon),
                ).add_to(m)
    
    def _add_clustered_markers(
        self,
        m,
        popup_fields: Optional[List[str]] = None,
        color_by: Optional[str] = None,
        style_function: Optional[Callable] = None,
    ):
        """Add markers with clustering for better performance."""
        try:
            from folium.plugins import MarkerCluster
        except ImportError:
            logger.warning("MarkerCluster not available, falling back to regular markers")
            return self._add_markers(m, popup_fields, color_by, style_function)
        
        # Try to import BeautifyIcon for better murder markers
        try:
            from folium.plugins import BeautifyIcon
            has_beautify = True
        except ImportError:
            has_beautify = False
        
        marker_cluster = MarkerCluster().add_to(m)
        color_map = self._create_color_map(color_by) if color_by else {}
        
        for incident in self.response.data:
            lat, lon = self._extract_coordinates(incident)
            if not (lat and lon):
                continue
            
            # Extract data from properties if GeoJSON
            data = incident.get("properties", incident)
            
            # Check if this is a murder/homicide for special highlighting
            is_murder = False
            if "nibrs_crime_category" in data:
                category = str(data["nibrs_crime_category"]).upper()
                if "HOMICIDE" in category or "MURDER" in category:
                    is_murder = True
            
            # Create popup content
            popup_html = self._create_popup_html(incident, popup_fields)
            
            # Create marker with special styling for murders
            if is_murder and has_beautify:
                # Use star marker with skull icon for murders - very obvious!
                icon = BeautifyIcon(
                    icon='skull',
                    icon_shape='marker',
                    number=None,
                    border_color='darkred',
                    background_color='red',
                    text_color='white',
                    inner_icon_style='font-size:20px;padding-top:1px;'
                )
                self.folium.Marker(
                    location=[lat, lon],
                    popup=self.folium.Popup(popup_html, max_width=300),
                    icon=icon,
                ).add_to(marker_cluster)
            else:
                # Determine marker color for non-murders
                if is_murder:
                    color = "red"
                    icon = "remove-sign"  # X icon as fallback
                elif color_by and color_by in data:
                    color = color_map.get(data[color_by], "blue")
                    icon = "info-sign"
                else:
                    color = "blue"
                    icon = "info-sign"
                
                # Standard folium marker
                self.folium.Marker(
                    location=[lat, lon],
                    popup=self.folium.Popup(popup_html, max_width=300),
                    icon=self.folium.Icon(color=color, icon=icon),
                ).add_to(marker_cluster)
    
    def _add_heatmap(self, m):
        """Add heatmap layer to map."""
        try:
            from folium.plugins import HeatMap
        except ImportError:
            raise ImportError(
                "HeatMap plugin not available. "
                "Install with: pip install folium"
            )
        
        # Extract coordinates
        heat_data = []
        for incident in self.response.data:
            lat, lon = self._extract_coordinates(incident)
            if lat and lon:
                heat_data.append([lat, lon])
        
        if heat_data:
            HeatMap(heat_data).add_to(m)
            logger.info(f"Added heatmap with {len(heat_data)} points")
    
    def _create_popup_html(
        self,
        incident: Dict[str, Any],
        fields: Optional[List[str]] = None,
    ) -> str:
        """Create HTML content for marker popup."""
        # Default fields if not specified - use most useful fields
        if fields is None:
            # Get properties if GeoJSON
            if "properties" in incident:
                # Use comprehensive profile as default
                fields = POPUP_FIELD_PROFILES[PopupProfile.COMPREHENSIVE]
            else:
                # Fallback to comprehensive
                fields = POPUP_FIELD_PROFILES[PopupProfile.COMPREHENSIVE]
        
        html_parts = ["<div style='font-family: Arial; font-size: 12px;'>"]
        
        # Extract data from properties if GeoJSON
        data = incident.get("properties", incident)
        
        for field in fields:
            if field in data and data[field] is not None:
                value = data[field]
                # Format dates nicely
                if "date" in field.lower() or "time" in field.lower():
                    value = str(value)[:19]  # Truncate to datetime
                
                # Make field names more readable
                field_display = field.replace('_', ' ').replace('comp', '').title()
                
                html_parts.append(
                    f"<b>{field_display}:</b> {value}<br/>"
                )
        
        html_parts.append("</div>")
        return "".join(html_parts)
    
    def _create_color_map(self, field: str) -> Dict[Any, str]:
        """Create a color mapping for unique field values."""
        # Get unique values
        data = self.response.data
        values = set()
        
        for incident in data:
            # Handle GeoJSON format
            item = incident.get("properties", incident)
            if field in item:
                values.add(item[field])
        
        # Assign colors
        colors = [
            "red", "blue", "green", "purple", "orange",
            "darkred", "lightred", "beige", "darkblue", "darkgreen",
            "cadetblue", "darkpurple", "white", "pink", "lightblue",
            "lightgreen", "gray", "black", "lightgray"
        ]
        
        return {val: colors[i % len(colors)] for i, val in enumerate(sorted(values))}
    
    def _add_linestrings(
        self,
        m,
        popup_fields: Optional[List[str]] = None,
        color_by: Optional[str] = None,
    ):
        """Add LineString features (intersections) to the map."""
        color_map = self._create_color_map(color_by) if color_by else {}
        
        for incident in self.response.data:
            # Check if this is a LineString feature
            if "geometry" in incident and incident["geometry"]["type"] == "LineString":
                coords = incident["geometry"]["coordinates"]
                # Convert from [lon, lat] to [lat, lon] for folium
                locations = [[lat, lon] for lon, lat in coords]
                
                # Determine line color
                if color_by and "properties" in incident and color_by in incident["properties"]:
                    color = color_map.get(incident["properties"][color_by], "blue")
                else:
                    color = "blue"
                
                # Create popup content
                props = incident.get("properties", incident)
                popup_html = self._create_popup_html(props, popup_fields)
                
                # Draw the line
                self.folium.PolyLine(
                    locations=locations,
                    color=color,
                    weight=3,
                    opacity=0.8,
                    popup=self.folium.Popup(popup_html, max_width=300),
                    tooltip="Intersection"
                ).add_to(m)
    
    @staticmethod
    def create_choropleth(
        geojson_data: Dict[str, Any],
        data_field: str,
        key_on: str = "feature.properties.beat",
        fill_color: str = "YlOrRd",
        legend_name: str = "Incident Count",
    ):
        """
        Create a choropleth map from GeoJSON data.
        
        Useful for showing incident density by geographic area.
        
        Args:
            geojson_data: GeoJSON data with geometry
            data_field: Field containing numeric data
            key_on: Property to join on
            fill_color: Color scheme
            legend_name: Legend title
        
        Returns:
            folium.Map with choropleth layer
        """
        try:
            import folium
        except ImportError:
            raise ImportError(
                "folium is required. Install with: pip install folium"
            )
        
        m = folium.Map(
            location=IncidentMapper.DEFAULT_CENTER,
            zoom_start=IncidentMapper.DEFAULT_ZOOM,
        )
        
        folium.Choropleth(
            geo_data=geojson_data,
            name="choropleth",
            data=geojson_data,
            columns=[key_on, data_field],
            key_on=key_on,
            fill_color=fill_color,
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name=legend_name,
        ).add_to(m)
        
        folium.LayerControl().add_to(m)
        
        return m
    
    @classmethod
    def from_geojson(
        cls,
        geojson_data: Dict[str, Any],
        **kwargs,
    ) -> IncidentMapper:
        """
        Create mapper from raw GeoJSON data.
        
        Args:
            geojson_data: GeoJSON FeatureCollection
            **kwargs: Additional arguments for IncidentMapper
        
        Returns:
            IncidentMapper instance
        """
        from dallas_incidents.models import IncidentQuery
        
        # Extract features
        features = geojson_data.get("features", [])
        
        # Create fake response
        response = IncidentResponse(
            data=features,
            query=IncidentQuery(format=OutputFormat.GEOJSON),
            format=OutputFormat.GEOJSON,
        )
        
        return cls(response=response, **kwargs)
