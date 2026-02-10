"""
Main client for Dallas Incidents API using sodapy.

Provides a high-level interface for querying Dallas Police incident data.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Iterator, Union
from datetime import date
import logging

from sodapy import Socrata

from dallas_incidents.models import (
    ClientConfig,
    IncidentQuery,
    IncidentResponse,
    OutputFormat,
    DateRange,
    GeoQuery,
)

logger = logging.getLogger(__name__)


class DallasIncidentsClient:
    """
    Client for Dallas Open Data Incidents API.
    
    Uses sodapy library for efficient interaction with Socrata API.
    Supports multiple output formats including GeoJSON for mapping.
    
    Example:
        >>> from dallas_incidents import DallasIncidentsClient, IncidentQuery, DateRange
        >>> from datetime import date
        >>> 
        >>> client = DallasIncidentsClient(app_token="your_token_here")
        >>> 
        >>> query = IncidentQuery(
        ...     beats=["241", "242"],
        ...     date_range=DateRange(start=date(2024, 1, 1), end=date(2024, 12, 31)),
        ...     limit=500
        ... )
        >>> 
        >>> response = client.get_incidents(query)
        >>> df = response.to_df()
    """
    
    def __init__(
        self,
        config: Optional[ClientConfig] = None,
        app_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        preset: Optional[str] = None,
    ):
        """
        Initialize the Dallas Incidents client.
        
        Args:
            config: ClientConfig object with full configuration
            app_token: Socrata app token (can also use SOCRATA_APP_TOKEN env var)
            username: Username for write operations (optional)
            password: Password for write operations (optional)
            preset: Quick setup using a dataset preset ('police_incidents', 'active_calls_northeast', etc.)
        
        Examples:
            # Use preset for Police Incidents (historical data)
            >>> client = DallasIncidentsClient(preset='police_incidents', app_token='your_token')
            
            # Use preset for Active Calls Northeast (real-time)
            >>> client = DallasIncidentsClient(preset='active_calls_northeast', app_token='your_token')
            
            # Use custom config
            >>> config = ClientConfig(dataset_id='custom-id', datetime_field='date_field')
            >>> client = DallasIncidentsClient(config=config, app_token='your_token')
        """
        # Handle preset configuration
        if preset:
            self.config = ClientConfig.from_preset(preset, app_token=app_token)
        else:
            self.config = config or ClientConfig()
        
        # Override config with explicit parameters
        if app_token and not preset:  # Don't override if preset was used
            self.config.app_token = app_token
        if username:
            self.config.username = username
        if password:
            self.config.password = password
        
        # Try to get app token from environment if not provided
        if not self.config.app_token:
            self.config.app_token = os.getenv("SOCRATA_APP_TOKEN")
        
        # Initialize sodapy client
        self.client = Socrata(
            self.config.domain,
            self.config.app_token,
            username=self.config.username,
            password=self.config.password,
            timeout=self.config.timeout,
        )
        
        logger.info(
            f"Initialized Dallas Incidents client for dataset {self.config.dataset_id}"
        )
    
    def get_incidents(
        self,
        query: Optional[IncidentQuery] = None,
        **kwargs,
    ) -> IncidentResponse:
        """
        Query incidents with flexible filtering.
        
        Args:
            query: IncidentQuery object with filters
            **kwargs: Additional keyword arguments to pass to sodapy
        
        Returns:
            IncidentResponse with results
        """
        if query is None:
            query = IncidentQuery()
        
        # Convert query to SoQL parameters, passing config for field mapping
        params = query.to_soql_params(config=self.config)
        params.update(kwargs)
        
        logger.debug(f"Querying with params: {params}")
        
        # Determine content type based on format
        content_type = query.format.value
        
        # Execute query using sodapy
        results = self.client.get(
            self.config.dataset_id,
            content_type=content_type,
            **params,
        )
        
        # Handle GeoJSON FeatureCollection format
        if query.format == OutputFormat.GEOJSON and isinstance(results, dict):
            if 'features' in results:
                # Extract features array from FeatureCollection
                results = results['features']
        
        logger.info(f"Retrieved {len(results)} incidents")
        
        return IncidentResponse(
            data=results,
            query=query,
            format=query.format,
        )
    
    def get_all_incidents(
        self,
        query: Optional[IncidentQuery] = None,
        **kwargs,
    ) -> Iterator[Dict[str, Any]]:
        """
        Get all incidents matching query, handling pagination automatically.
        
        Returns a generator that yields incidents one at a time.
        Useful for large result sets that don't fit in memory.
        
        Args:
            query: IncidentQuery object with filters
            **kwargs: Additional keyword arguments
        
        Yields:
            Individual incident dictionaries
        """
        if query is None:
            query = IncidentQuery()
        
        params = query.to_soql_params()
        params.update(kwargs)
        
        # Remove limit/offset as get_all handles pagination
        params.pop("limit", None)
        params.pop("offset", None)
        
        content_type = query.format.value
        
        logger.info("Starting paginated query for all incidents")
        
        for incident in self.client.get_all(
            self.config.dataset_id,
            content_type=content_type,
            **params,
        ):
            yield incident
    
    def get_geojson(
        self,
        query: Optional[IncidentQuery] = None,
        **kwargs,
    ) -> IncidentResponse:
        """
        Get incidents in GeoJSON format for mapping.
        
        Convenience method that sets format to GEOJSON.
        
        Args:
            query: IncidentQuery object with filters
            **kwargs: Additional keyword arguments
        
        Returns:
            IncidentResponse with GeoJSON data
        """
        if query is None:
            query = IncidentQuery()
        
        query.format = OutputFormat.GEOJSON
        return self.get_incidents(query, **kwargs)
    
    def get_by_beat(
        self,
        beats: List[str],
        start_date: Optional[Union[date, str]] = None,
        end_date: Optional[Union[date, str]] = None,
        limit: int = 1000,
        **kwargs,
    ) -> IncidentResponse:
        """
        Get incidents for specific police beats.
        
        Args:
            beats: List of beat identifiers
            start_date: Start date (date object or ISO string like '2024-01-01')
            end_date: End date (date object or ISO string like '2024-01-01')
            limit: Maximum number of results
            **kwargs: Additional filters
        
        Returns:
            IncidentResponse with results
        """
        # Build date_range if dates provided
        date_range = None
        if start_date or end_date:
            date_range = DateRange(start=start_date, end=end_date)
        
        query = IncidentQuery(beats=beats, date_range=date_range, limit=limit, **kwargs)
        return self.get_incidents(query)
    
    def get_by_date_range(
        self,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        limit: int = 1000,
        **kwargs,
    ) -> IncidentResponse:
        """
        Get incidents within a date range.
        
        Args:
            start_date: Start date (date, datetime, or ISO string)
            end_date: End date (date, datetime, or ISO string)
            limit: Maximum number of results
            **kwargs: Additional filters
        
        Returns:
            IncidentResponse with results
        """
        date_range = DateRange(start=start_date, end=end_date)
        query = IncidentQuery(date_range=date_range, limit=limit, **kwargs)
        return self.get_incidents(query)
    
    def get_by_location(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float = 1000,
        limit: int = 1000,
        **kwargs,
    ) -> IncidentResponse:
        """
        Get incidents near a geographic location.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            radius_meters: Search radius in meters (default 1000m = 1km)
            limit: Maximum number of results
            **kwargs: Additional filters
        
        Returns:
            IncidentResponse with results
        """
        geo_query = GeoQuery(
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
        )
        query = IncidentQuery(
            geo_query=geo_query,
            limit=limit,
            format=OutputFormat.GEOJSON,
            **kwargs,
        )
        return self.get_incidents(query)
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the dataset.
        
        Returns:
            Dictionary with dataset metadata
        """
        return self.client.get_metadata(self.config.dataset_id)
    
    def get_field_names(self) -> List[str]:
        """
        Get list of available field names in the dataset.
        
        Returns:
            List of field names
        """
        metadata = self.get_metadata()
        return [col["fieldName"] for col in metadata.get("columns", [])]
    
    def search(
        self,
        search_text: str,
        limit: int = 1000,
        **kwargs,
    ) -> IncidentResponse:
        """
        Full-text search across incident data.
        
        Args:
            search_text: Text to search for
            limit: Maximum number of results
            **kwargs: Additional filters
        
        Returns:
            IncidentResponse with matching results
        """
        query = IncidentQuery(limit=limit, **kwargs)
        return self.get_incidents(query, q=search_text)
    
    def search_by_category(
        self,
        category: str,
        beats: Optional[List[str]] = None,
        start_date: Optional[Union[date, str]] = None,
        end_date: Optional[Union[date, str]] = None,
        limit: int = 1000,
        **kwargs,
    ) -> IncidentResponse:
        """
        Search incidents by offense category.
        
        Args:
            category: Offense category ('weapon', 'drug', 'violent', 'theft', etc.)
            beats: Optional list of beat identifiers
            start_date: Start date (date object or ISO string like '2024-01-01')
            end_date: End date (date object or ISO string like '2024-01-01')
            limit: Maximum number of results
            **kwargs: Additional filters (division, etc.)
        
        Returns:
            IncidentResponse with matching results
        
        Examples:
            >>> # Get all weapon-related crimes
            >>> response = client.search_by_category('weapon', limit=500)
            
            >>> # Get drug crimes in specific beats
            >>> response = client.search_by_category('drug', beats=['241', '242'])
            
            >>> # Get violent crimes in last 30 days (using string dates)
            >>> response = client.search_by_category(
            ...     'violent',
            ...     start_date='2024-10-01',
            ...     end_date='2024-10-31'
            ... )
            
            >>> # Using date objects
            >>> from datetime import date, timedelta
            >>> response = client.search_by_category(
            ...     'weapon',
            ...     start_date=date.today() - timedelta(days=30)
            ... )
        """
        # Build date_range if dates provided
        date_range = None
        if start_date or end_date:
            date_range = DateRange(start=start_date, end=end_date)
        
        query = IncidentQuery(
            offense_category=category,
            beats=beats,
            date_range=date_range,
            limit=limit,
            **kwargs
        )
        return self.get_incidents(query)
    
    def search_by_keyword(
        self,
        keyword: str,
        beats: Optional[List[str]] = None,
        start_date: Optional[Union[date, str]] = None,
        end_date: Optional[Union[date, str]] = None,
        limit: int = 1000,
        **kwargs,
    ) -> IncidentResponse:
        """
        Search incidents by keyword in offense descriptions.
        
        Args:
            keyword: Keyword to search for ('gun', 'sex', 'theft', etc.)
            beats: Optional list of beat identifiers
            start_date: Start date (date object or ISO string like '2024-01-01')
            end_date: End date (date object or ISO string like '2024-01-01')
            limit: Maximum number of results
            **kwargs: Additional filters (division, etc.)
        
        Returns:
            IncidentResponse with matching results
        
        Examples:
            >>> # Find all gun-related incidents
            >>> response = client.search_by_keyword('gun', limit=500)
            
            >>> # Find sex crimes in specific area and date range
            >>> response = client.search_by_keyword(
            ...     'sex',
            ...     beats=['241'],
            ...     start_date='2024-01-01',
            ...     end_date='2024-01-31'
            ... )
            
            >>> # Find fraud cases in last week
            >>> from datetime import date, timedelta
            >>> response = client.search_by_keyword(
            ...     'fraud',
            ...     start_date=date.today() - timedelta(days=7)
            ... )
        """
        # Build date_range if dates provided
        date_range = None
        if start_date or end_date:
            date_range = DateRange(start=start_date, end=end_date)
        
        query = IncidentQuery(
            offense_keyword=keyword,
            beats=beats,
            date_range=date_range,
            limit=limit,
            **kwargs
        )
        return self.get_incidents(query)
    
    def close(self):
        """Close the underlying sodapy client connection."""
        self.client.close()
        logger.info("Closed Dallas Incidents client")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __repr__(self) -> str:
        return (
            f"DallasIncidentsClient("
            f"dataset={self.config.dataset_id}, "
            f"domain={self.config.domain})"
        )
