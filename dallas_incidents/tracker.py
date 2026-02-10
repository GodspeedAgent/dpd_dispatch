"""
Call tracking utilities for following active calls into historical incidents.

This module provides convenient APIs for:
1. Capturing active calls of interest
2. Building queries to find them later in historical data
3. Tracking calls over time with snapshots
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path


@dataclass
class TrackedCall:
    """Represents an active call being tracked for follow-up."""
    
    # Core identification
    nature_of_call: str
    location: str
    beat: str
    block: Optional[str] = None
    unit_number: Optional[str] = None
    
    # Tracking metadata
    captured_at: datetime = field(default_factory=datetime.now)
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with datetime serialization."""
        data = asdict(self)
        data['captured_at'] = self.captured_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrackedCall':
        """Create from dictionary with datetime parsing."""
        data = data.copy()
        if isinstance(data.get('captured_at'), str):
            data['captured_at'] = datetime.fromisoformat(data['captured_at'])
        return cls(**data)
    
    def get_search_window(self, days_after: int = 3) -> tuple[date, date]:
        """
        Get date range for searching this call in historical data.
        
        Args:
            days_after: Number of days after capture to search
            
        Returns:
            Tuple of (start_date, end_date) for searching
        """
        capture_date = self.captured_at.date()
        # Search from day of capture through N days after
        return (capture_date, capture_date + timedelta(days=days_after))


class CallTracker:
    """
    Convenient API for tracking active calls and following up in historical data.
    
    Workflow:
        1. Query active calls and mark interesting ones
        2. Save tracked calls to file
        3. Later, generate queries to find them in Police Incidents
    
    Example:
        >>> # Step 1: Track interesting active calls
        >>> tracker = CallTracker()
        >>> 
        >>> # Query active calls
        >>> active_client = DallasIncidentsClient(preset='active_calls_northeast')
        >>> response = active_client.get_incidents(IncidentQuery(limit=100))
        >>> 
        >>> # Mark calls of interest
        >>> for call in response.data:
        >>>     if call['nature_of_call'] == 'BURGLARY':
        >>>         tracker.track_call(call, notes="Residential burglary", tags=['property_crime'])
        >>> 
        >>> # Save for later
        >>> tracker.save('tracked_calls.json')
        >>> 
        >>> # Step 2: Follow up later (next day)
        >>> tracker = CallTracker.load('tracked_calls.json')
        >>> 
        >>> # Generate search criteria for historical data
        >>> incidents_client = DallasIncidentsClient(preset='police_incidents')
        >>> for query in tracker.generate_queries():
        >>>     results = incidents_client.get_incidents(query)
        >>>     # Process results...
    """
    
    def __init__(self):
        """Initialize an empty call tracker."""
        self.tracked_calls: List[TrackedCall] = []
    
    def track_call(
        self,
        call: Dict[str, Any],
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> TrackedCall:
        """
        Track an active call for follow-up.
        
        Args:
            call: Active call data dictionary
            notes: Optional notes about why tracking this call
            tags: Optional tags for categorization
            
        Returns:
            TrackedCall object
        """
        tracked = TrackedCall(
            nature_of_call=call.get('nature_of_call', ''),
            location=call.get('location', ''),
            beat=call.get('beat', ''),
            block=call.get('block'),
            unit_number=call.get('unit_number'),
            notes=notes,
            tags=tags or []
        )
        self.tracked_calls.append(tracked)
        return tracked
    
    def track_multiple(
        self,
        calls: List[Dict[str, Any]],
        filter_func: Optional[callable] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[TrackedCall]:
        """
        Track multiple calls at once, optionally filtering.
        
        Args:
            calls: List of active call dictionaries
            filter_func: Optional function to filter calls (returns True to track)
            notes: Notes to apply to all tracked calls
            tags: Tags to apply to all tracked calls
            
        Returns:
            List of TrackedCall objects
        """
        tracked = []
        for call in calls:
            if filter_func is None or filter_func(call):
                tracked.append(self.track_call(call, notes, tags))
        return tracked
    
    def generate_queries(
        self,
        days_after: int = 3,
        limit_per_query: int = 100
    ):
        """
        Generate IncidentQuery objects to search for tracked calls in historical data.
        
        Args:
            days_after: Number of days after capture to search
            limit_per_query: Max results per query
            
        Yields:
            IncidentQuery objects configured to find tracked calls
        """
        from dallas_incidents.models import IncidentQuery, DateRange
        
        # Group calls by beat and date range for efficient querying
        beat_groups: Dict[str, List[TrackedCall]] = {}
        
        for call in self.tracked_calls:
            if call.beat not in beat_groups:
                beat_groups[call.beat] = []
            beat_groups[call.beat].append(call)
        
        # Generate queries per beat
        for beat, calls in beat_groups.items():
            # Find earliest and latest capture times
            min_date = min(call.captured_at.date() for call in calls)
            max_date = max(call.captured_at.date() for call in calls)
            
            # Extend range by days_after
            end_date = max_date + timedelta(days=days_after)
            
            yield IncidentQuery(
                beats=[beat],
                date_range=DateRange(start=min_date, end=end_date),
                limit=limit_per_query
            )
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about tracked calls.
        
        Returns:
            Dictionary with summary information
        """
        if not self.tracked_calls:
            return {
                'total_tracked': 0,
                'beats': [],
                'call_types': [],
                'tags': []
            }
        
        from collections import Counter
        
        return {
            'total_tracked': len(self.tracked_calls),
            'beats': list(Counter(c.beat for c in self.tracked_calls).items()),
            'call_types': list(Counter(c.nature_of_call for c in self.tracked_calls).items()),
            'tags': list(Counter(tag for c in self.tracked_calls for tag in c.tags).items()),
            'earliest_capture': min(c.captured_at for c in self.tracked_calls).isoformat(),
            'latest_capture': max(c.captured_at for c in self.tracked_calls).isoformat(),
        }
    
    def filter_by_tag(self, tag: str) -> List[TrackedCall]:
        """Get all tracked calls with a specific tag."""
        return [call for call in self.tracked_calls if tag in call.tags]
    
    def filter_by_beat(self, beat: str) -> List[TrackedCall]:
        """Get all tracked calls in a specific beat."""
        return [call for call in self.tracked_calls if call.beat == beat]
    
    def save(self, filepath: str):
        """
        Save tracked calls to JSON file.
        
        Args:
            filepath: Path to save file
        """
        data = {
            'version': '1.0',
            'saved_at': datetime.now().isoformat(),
            'tracked_calls': [call.to_dict() for call in self.tracked_calls]
        }
        
        Path(filepath).write_text(json.dumps(data, indent=2))
    
    @classmethod
    def load(cls, filepath: str) -> 'CallTracker':
        """
        Load tracked calls from JSON file.
        
        Args:
            filepath: Path to load from
            
        Returns:
            CallTracker instance
        """
        data = json.loads(Path(filepath).read_text())
        
        tracker = cls()
        tracker.tracked_calls = [
            TrackedCall.from_dict(call_data)
            for call_data in data['tracked_calls']
        ]
        
        return tracker
    
    def __len__(self) -> int:
        """Return number of tracked calls."""
        return len(self.tracked_calls)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"CallTracker(tracked={len(self.tracked_calls)} calls)"


class SnapshotTracker:
    """
    Track active calls over time with timestamped snapshots.
    
    Useful for monitoring patterns, response times, and call volume.
    
    Example:
        >>> tracker = SnapshotTracker()
        >>> 
        >>> # Take snapshots every 5 minutes
        >>> client = DallasIncidentsClient(preset='active_calls_northeast')
        >>> for _ in range(12):  # 1 hour of monitoring
        >>>     response = client.get_incidents(IncidentQuery(limit=500))
        >>>     tracker.take_snapshot(response.data)
        >>>     time.sleep(300)
        >>> 
        >>> # Analyze
        >>> tracker.save('snapshots.json')
        >>> print(f"Average active calls: {tracker.get_average_count()}")
        >>> print(f"Peak calls: {tracker.get_peak_count()}")
    """
    
    def __init__(self):
        """Initialize an empty snapshot tracker."""
        self.snapshots: List[Dict[str, Any]] = []
    
    def take_snapshot(self, calls: List[Dict[str, Any]], metadata: Optional[Dict] = None):
        """
        Record a snapshot of current active calls.
        
        Args:
            calls: List of active call dictionaries
            metadata: Optional metadata to attach to snapshot
        """
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'count': len(calls),
            'calls': calls,
            'metadata': metadata or {}
        }
        self.snapshots.append(snapshot)
    
    def get_average_count(self) -> float:
        """Calculate average number of active calls across snapshots."""
        if not self.snapshots:
            return 0.0
        return sum(s['count'] for s in self.snapshots) / len(self.snapshots)
    
    def get_peak_count(self) -> int:
        """Get maximum number of active calls in any snapshot."""
        if not self.snapshots:
            return 0
        return max(s['count'] for s in self.snapshots)
    
    def get_call_duration_estimates(self) -> Dict[str, timedelta]:
        """
        Estimate how long calls stayed active by tracking their presence across snapshots.
        
        Returns:
            Dictionary mapping call identifiers to estimated duration
        """
        # Track when each unique call appears
        call_appearances: Dict[str, List[datetime]] = {}
        
        for snapshot in self.snapshots:
            timestamp = datetime.fromisoformat(snapshot['timestamp'])
            for call in snapshot['calls']:
                # Create unique identifier from call details
                call_id = f"{call.get('beat')}_{call.get('location')}_{call.get('nature_of_call')}"
                
                if call_id not in call_appearances:
                    call_appearances[call_id] = []
                call_appearances[call_id].append(timestamp)
        
        # Calculate duration estimates
        durations = {}
        for call_id, appearances in call_appearances.items():
            if len(appearances) > 1:
                duration = max(appearances) - min(appearances)
                durations[call_id] = duration
        
        return durations
    
    def save(self, filepath: str):
        """Save snapshots to JSON file."""
        data = {
            'version': '1.0',
            'snapshots': self.snapshots
        }
        Path(filepath).write_text(json.dumps(data, indent=2))
    
    @classmethod
    def load(cls, filepath: str) -> 'SnapshotTracker':
        """Load snapshots from JSON file."""
        data = json.loads(Path(filepath).read_text())
        tracker = cls()
        tracker.snapshots = data['snapshots']
        return tracker
    
    def __len__(self) -> int:
        """Return number of snapshots."""
        return len(self.snapshots)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"SnapshotTracker(snapshots={len(self.snapshots)})"
