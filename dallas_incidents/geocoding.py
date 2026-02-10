"""
Geocoding utilities for Active Calls data.

Active Calls datasets don't include coordinates, only street addresses.
This module provides geocoding functionality to convert addresses to lat/lon.
"""

from typing import Dict, List, Optional, Tuple, Any, Union
import json
from pathlib import Path
import time
import logging

logger = logging.getLogger(__name__)


class AddressGeocoder:
    """
    Geocode Dallas street addresses to lat/lon coordinates.
    
    Features:
    - Caching to avoid repeated API calls
    - Rate limiting to respect service limits
    - Intersection handling with LineString geometry
    - Multiple geocoding backends (geopy, etc.)
    
    Example:
        >>> geocoder = AddressGeocoder()
        >>> lat, lon = geocoder.geocode("4300 Wyoming St, Dallas, TX")
        >>> print(f"Location: {lat}, {lon}")
    """
    
    def __init__(
        self,
        cache_file: Optional[str] = None,
        user_agent: str = "dallas_incidents_client"
    ):
        """
        Initialize geocoder with optional cache.
        
        Args:
            cache_file: Path to JSON cache file for geocoded addresses
            user_agent: User agent string for geocoding API
        """
        self.cache_file = cache_file or "geocode_cache.json"
        self.user_agent = user_agent
        self.cache: Dict[str, Union[Tuple[float, float], List[Tuple[float, float]]]] = {}
        self._load_cache()
        
        # Lazy load geopy to avoid requiring it if not using geocoding
        self._geocoder = None
    
    def _get_geocoder(self):
        """Lazy load the geocoding backend."""
        if self._geocoder is None:
            try:
                from geopy.geocoders import Nominatim
                self._geocoder = Nominatim(user_agent=self.user_agent)
            except ImportError:
                raise ImportError(
                    "geopy is required for geocoding Active Calls data. "
                    "Install with: pip install geopy"
                )
        return self._geocoder
    
    def _load_cache(self):
        """Load geocoding cache from file."""
        cache_path = Path(self.cache_file)
        if cache_path.exists():
            try:
                data = json.loads(cache_path.read_text())
                # Convert to appropriate format (tuple or list of tuples)
                self.cache = {}
                for addr, coords in data.items():
                    if isinstance(coords[0], list):
                        # List of coordinates (intersection line)
                        self.cache[addr] = [tuple(c) for c in coords]
                    else:
                        # Single coordinate (point)
                        self.cache[addr] = tuple(coords)
                logger.debug(f"Loaded {len(self.cache)} cached addresses")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                self.cache = {}
    
    def _save_cache(self):
        """Save geocoding cache to file."""
        try:
            # Convert tuples/lists to JSON-serializable format
            data = {}
            for addr, coords in self.cache.items():
                if isinstance(coords, list):
                    # List of tuples (intersection)
                    data[addr] = [list(c) for c in coords]
                else:
                    # Single tuple (point)
                    data[addr] = list(coords)
            Path(self.cache_file).write_text(json.dumps(data, indent=2))
            logger.debug(f"Saved {len(self.cache)} addresses to cache")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def construct_address(self, block: Optional[str], location: str) -> str:
        """
        Construct full Dallas address from Active Calls fields.
        
        Handles both regular addresses and intersections.
        
        Args:
            block: Block number (e.g., "4300")
            location: Street name (e.g., "Wyoming St") or intersection (e.g., "Main St / Elm St")
            
        Returns:
            Full address string (e.g., "4300 Wyoming St, Dallas, TX")
        """
        # Check if this is an intersection (contains / or &)
        if '/' in location or '&' in location:
            # This is an intersection - don't use block number
            # Clean up the intersection format
            intersection = location.replace('/', ' and ').replace('&', ' and ')
            return f"{intersection}, Dallas, TX"
        else:
            # Regular address - use block number if available
            if block:
                return f"{block} {location}, Dallas, TX"
            else:
                return f"{location}, Dallas, TX"
    
    def geocode(self, address: str, use_cache: bool = True) -> Optional[Union[Tuple[float, float], List[Tuple[float, float]]]]:
        """
        Geocode an address to lat/lon coordinates.
        
        Handles both regular addresses and intersections.
        For intersections, returns a list of two coordinate tuples (for drawing a line).
        For regular addresses, returns a single coordinate tuple (for a point).
        
        Args:
            address: Full address string
            use_cache: Whether to use cached results
            
        Returns:
            - For regular addresses: Tuple of (latitude, longitude)
            - For intersections: List of [(lat1, lon1), (lat2, lon2)]
            - None if geocoding failed
        """
        # Check cache first
        if use_cache and address in self.cache:
            logger.debug(f"Cache hit for: {address}")
            return self.cache[address]
        
        # Check if this is an intersection
        if ' and ' in address:
            return self._geocode_intersection(address, use_cache)
        
        # Regular address geocoding
        try:
            geocoder = self._get_geocoder()
            location = geocoder.geocode(address, timeout=10)
            
            if location:
                coords = (location.latitude, location.longitude)
                logger.debug(f"Geocoded: {address} -> {coords}")
                
                # Cache the result
                self.cache[address] = coords
                self._save_cache()
                
                # Rate limiting - be respectful to the service
                time.sleep(1)
                
                return coords
            else:
                logger.warning(f"No results for: {address}")
                return None
                
        except Exception as e:
            logger.error(f"Geocoding failed for {address}: {e}")
            return None
    
    def _geocode_intersection(self, address: str, use_cache: bool) -> Optional[List[Tuple[float, float]]]:
        """
        Geocode an intersection by finding both streets and returning both points.
        
        Returns coordinates for BOTH streets so a line can be drawn between them.
        
        Args:
            address: Intersection address (e.g., "Main St and Elm St, Dallas, TX")
            use_cache: Whether to use cache
            
        Returns:
            List of two coordinate tuples: [(lat1, lon1), (lat2, lon2)]
            This can be used to draw a LineString on the map.
        """
        try:
            # Extract the two streets
            parts = address.split(', Dallas, TX')[0]
            streets = [s.strip() for s in parts.split(' and ')]
            
            if len(streets) != 2:
                logger.warning(f"Cannot parse intersection: {address}")
                return None
            
            geocoder = self._get_geocoder()
            coords_list = []
            
            # Geocode each street
            for street in streets:
                street_address = f"{street}, Dallas, TX"
                
                # Check if this street is already cached
                if use_cache and street_address in self.cache:
                    cached = self.cache[street_address]
                    # Make sure it's a single point, not a line
                    if isinstance(cached, tuple):
                        coords_list.append(cached)
                        logger.debug(f"Cache hit for street: {street_address}")
                    else:
                        logger.warning(f"Cached street has invalid format: {street_address}")
                else:
                    location = geocoder.geocode(street_address, timeout=10)
                    if location:
                        coords = (location.latitude, location.longitude)
                        coords_list.append(coords)
                        # Cache individual street
                        self.cache[street_address] = coords
                        logger.debug(f"Geocoded street: {street_address} -> {coords}")
                        time.sleep(1)
                    else:
                        logger.warning(f"Failed to geocode street: {street_address}")
            
            # Return list of coordinates if we got both streets
            if len(coords_list) == 2:
                logger.info(f"Intersection geocoded: {address} -> line between {coords_list[0]} and {coords_list[1]}")
                
                # Cache the intersection as a LIST (not a single point)
                # Format: [[lat1, lon1], [lat2, lon2]]
                self.cache[address] = coords_list
                self._save_cache()
                
                return coords_list
            elif len(coords_list) == 1:
                # Only got one street, return it as a single point (not a list)
                logger.warning(f"Only one street geocoded for intersection: {address}, using as point")
                single_point = coords_list[0]
                self.cache[address] = single_point
                self._save_cache()
                return single_point
            else:
                logger.warning(f"Failed to geocode intersection: {address}")
                return None
                
        except Exception as e:
            logger.error(f"Error geocoding intersection {address}: {e}")
            return None
    
    def geocode_calls(
        self,
        calls: List[Dict[str, Any]],
        show_progress: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Geocode a list of Active Calls and add coordinates.
        
        For regular addresses, adds 'latitude' and 'longitude' fields.
        For intersections, adds 'is_intersection' and 'intersection_coords' fields.
        
        Args:
            calls: List of Active Call dictionaries
            show_progress: Whether to print progress messages
            
        Returns:
            List of calls with added geographic fields
        """
        geocoded_calls = []
        success_count = 0
        cache_hits = 0
        intersection_count = 0
        
        if show_progress:
            print(f"Geocoding {len(calls)} addresses...")
        
        for i, call in enumerate(calls, 1):
            # Construct address
            block = call.get('block')
            location = call.get('location')
            
            if not location:
                logger.warning(f"Call {i}: No location field")
                geocoded_calls.append(call)
                continue
            
            address = self.construct_address(block, location)
            
            # Check if already in cache before geocoding
            was_cached = address in self.cache
            
            # Geocode
            coords = self.geocode(address, use_cache=True)
            
            # Add to call data
            call_copy = call.copy()
            call_copy['geocoded_address'] = address
            
            if coords:
                # Check if this is an intersection (list of coords) or regular address (single tuple)
                if isinstance(coords, list) and len(coords) == 2:
                    # Intersection - store both points
                    call_copy['is_intersection'] = True
                    call_copy['intersection_coords'] = coords  # List of [(lat1, lon1), (lat2, lon2)]
                    call_copy['latitude'] = None
                    call_copy['longitude'] = None
                    intersection_count += 1
                    success_count += 1
                else:
                    # Regular address - single point
                    call_copy['is_intersection'] = False
                    call_copy['latitude'] = coords[0]
                    call_copy['longitude'] = coords[1]
                    call_copy['intersection_coords'] = None
                    success_count += 1
                
                if was_cached:
                    cache_hits += 1
            else:
                call_copy['is_intersection'] = False
                call_copy['latitude'] = None
                call_copy['longitude'] = None
                call_copy['intersection_coords'] = None
            
            geocoded_calls.append(call_copy)
            
            # Progress updates
            if show_progress and i % 10 == 0:
                print(f"  Processed {i}/{len(calls)} addresses...")
        
        if show_progress:
            print(f"\n✓ Geocoding complete!")
            print(f"  Success: {success_count}/{len(calls)}")
            print(f"  Intersections: {intersection_count}")
            print(f"  Regular addresses: {success_count - intersection_count}")
            print(f"  Cache hits: {cache_hits}")
            print(f"  New geocodes: {success_count - cache_hits}")
        
        return geocoded_calls
    
    def clear_cache(self):
        """Clear the geocoding cache."""
        self.cache = {}
        cache_path = Path(self.cache_file)
        if cache_path.exists():
            cache_path.unlink()
        logger.info("Geocoding cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache."""
        return {
            'size': len(self.cache),
            'file': self.cache_file,
            'addresses': list(self.cache.keys())[:10] + (['...'] if len(self.cache) > 10 else [])
        }


def geocode_active_calls(
    calls: List[Dict[str, Any]],
    cache_file: Optional[str] = None,
    show_progress: bool = True
) -> List[Dict[str, Any]]:
    """
    Convenience function to geocode Active Calls data.
    
    Args:
        calls: List of Active Call dictionaries
        cache_file: Optional path to cache file
        show_progress: Whether to show progress
        
    Returns:
        List of calls with added latitude/longitude fields
    
    Example:
        >>> response = client.get_incidents(IncidentQuery(limit=10))
        >>> geocoded = geocode_active_calls(response.data)
        >>> # Now geocoded calls have 'latitude' and 'longitude' fields
    """
    geocoder = AddressGeocoder(cache_file=cache_file)
    return geocoder.geocode_calls(calls, show_progress=show_progress)
