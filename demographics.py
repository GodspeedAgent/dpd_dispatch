"""
Demographic analysis utilities for Dallas Police incidents.

Provides tools for filtering, analyzing, and visualizing incidents by
demographic characteristics (race, ethnicity, sex, etc.).
"""

from typing import Dict, List, Any, Optional, Tuple
from collections import Counter
from enum import Enum


class DemographicField(str, Enum):
    """Demographic fields available in Police Incidents dataset."""
    RACE = "comprace"
    ETHNICITY = "compethnicity"
    SEX = "compsex"


# Standard demographic values (based on common police reporting)
RACE_VALUES = {
    'W': 'White',
    'B': 'Black',
    'H': 'Hispanic',
    'A': 'Asian',
    'I': 'American Indian/Alaska Native',
    'U': 'Unknown',
    'O': 'Other',
}

ETHNICITY_VALUES = {
    'H': 'Hispanic',
    'N': 'Non-Hispanic',
    'U': 'Unknown',
}

SEX_VALUES = {
    'M': 'Male',
    'F': 'Female',
    'U': 'Unknown',
}


def normalize_demographic_value(field: str, value: Any) -> Optional[str]:
    """
    Normalize demographic field values to readable format.
    
    Args:
        field: Demographic field name ('comprace', 'compethnicity', 'compsex')
        value: Raw value from dataset
    
    Returns:
        Normalized string value or None
    """
    if not value:
        return None
    
    value_str = str(value).upper().strip()
    
    if field == DemographicField.RACE:
        return RACE_VALUES.get(value_str, value_str)
    elif field == DemographicField.ETHNICITY:
        return ETHNICITY_VALUES.get(value_str, value_str)
    elif field == DemographicField.SEX:
        return SEX_VALUES.get(value_str, value_str)
    
    return value_str


def filter_by_demographics(
    incidents: List[Dict[str, Any]],
    race: Optional[str] = None,
    ethnicity: Optional[str] = None,
    sex: Optional[str] = None,
    properties: bool = False
) -> List[Dict[str, Any]]:
    """
    Filter incidents by demographic criteria.
    
    Args:
        incidents: List of incident dictionaries
        race: Filter by race (e.g., 'W', 'B', 'H', 'A', 'White', 'Black', etc.)
        ethnicity: Filter by ethnicity (e.g., 'H', 'N', 'Hispanic', 'Non-Hispanic')
        sex: Filter by sex (e.g., 'M', 'F', 'Male', 'Female')
        properties: If True, look in properties dict (for GeoJSON)
    
    Returns:
        Filtered list of incidents
    """
    filtered = incidents
    
    def get_field(incident: Dict[str, Any], field: str) -> Any:
        data = incident.get("properties", incident) if properties else incident
        return data.get(field)
    
    # Normalize filter values
    if race:
        race_upper = race.upper().strip()
        # Convert full names to codes if needed
        race_code = race_upper[0] if len(race_upper) > 1 else race_upper
        filtered = [
            inc for inc in filtered
            if get_field(inc, DemographicField.RACE) 
            and str(get_field(inc, DemographicField.RACE)).upper().startswith(race_code)
        ]
    
    if ethnicity:
        ethnicity_upper = ethnicity.upper().strip()
        ethnicity_code = ethnicity_upper[0] if len(ethnicity_upper) > 1 else ethnicity_upper
        filtered = [
            inc for inc in filtered
            if get_field(inc, DemographicField.ETHNICITY)
            and str(get_field(inc, DemographicField.ETHNICITY)).upper().startswith(ethnicity_code)
        ]
    
    if sex:
        sex_upper = sex.upper().strip()
        sex_code = sex_upper[0] if len(sex_upper) > 1 else sex_upper
        filtered = [
            inc for inc in filtered
            if get_field(inc, DemographicField.SEX)
            and str(get_field(inc, DemographicField.SEX)).upper().startswith(sex_code)
        ]
    
    return filtered


def count_by_demographics(
    incidents: List[Dict[str, Any]],
    field: DemographicField,
    properties: bool = False,
    normalize: bool = True
) -> Dict[str, int]:
    """
    Count incidents by demographic field.
    
    Args:
        incidents: List of incident dictionaries
        field: Demographic field to count by
        properties: If True, look in properties dict (for GeoJSON)
        normalize: If True, convert codes to readable names
    
    Returns:
        Dictionary mapping demographic values to counts
    """
    counts = Counter()
    
    for incident in incidents:
        data = incident.get("properties", incident) if properties else incident
        value = data.get(field.value)
        
        if value is not None:
            if normalize:
                value = normalize_demographic_value(field.value, value)
            counts[value] += 1
    
    return dict(counts)


def demographic_breakdown(
    incidents: List[Dict[str, Any]],
    properties: bool = False
) -> Dict[str, Dict[str, int]]:
    """
    Get full demographic breakdown of incidents.
    
    Args:
        incidents: List of incident dictionaries
        properties: If True, look in properties dict (for GeoJSON)
    
    Returns:
        Dictionary with counts by race, ethnicity, and sex
    """
    return {
        'race': count_by_demographics(incidents, DemographicField.RACE, properties),
        'ethnicity': count_by_demographics(incidents, DemographicField.ETHNICITY, properties),
        'sex': count_by_demographics(incidents, DemographicField.SEX, properties),
    }


def demographic_summary(
    incidents: List[Dict[str, Any]],
    properties: bool = False
) -> str:
    """
    Generate human-readable demographic summary.
    
    Args:
        incidents: List of incident dictionaries
        properties: If True, look in properties dict (for GeoJSON)
    
    Returns:
        Formatted summary string
    """
    breakdown = demographic_breakdown(incidents, properties)
    
    lines = [f"Demographic Analysis ({len(incidents)} incidents):", ""]
    
    for category, counts in breakdown.items():
        lines.append(f"{category.upper()}:")
        total = sum(counts.values())
        for value, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total * 100) if total > 0 else 0
            lines.append(f"  {value}: {count} ({pct:.1f}%)")
        lines.append("")
    
    return "\n".join(lines)


def cross_tabulate_demographics(
    incidents: List[Dict[str, Any]],
    field1: DemographicField,
    field2: DemographicField,
    properties: bool = False
) -> Dict[Tuple[str, str], int]:
    """
    Cross-tabulate two demographic fields.
    
    Args:
        incidents: List of incident dictionaries
        field1: First demographic field
        field2: Second demographic field
        properties: If True, look in properties dict (for GeoJSON)
    
    Returns:
        Dictionary mapping (value1, value2) tuples to counts
    """
    counts = Counter()
    
    for incident in incidents:
        data = incident.get("properties", incident) if properties else incident
        
        val1 = data.get(field1.value)
        val2 = data.get(field2.value)
        
        if val1 is not None and val2 is not None:
            val1_norm = normalize_demographic_value(field1.value, val1)
            val2_norm = normalize_demographic_value(field2.value, val2)
            counts[(val1_norm, val2_norm)] += 1
    
    return dict(counts)


def get_demographic_percentages(
    incidents: List[Dict[str, Any]],
    field: DemographicField,
    properties: bool = False
) -> Dict[str, float]:
    """
    Get percentage distribution for a demographic field.
    
    Args:
        incidents: List of incident dictionaries
        field: Demographic field to analyze
        properties: If True, look in properties dict (for GeoJSON)
    
    Returns:
        Dictionary mapping values to percentages
    """
    counts = count_by_demographics(incidents, field, properties)
    total = sum(counts.values())
    
    if total == 0:
        return {}
    
    return {value: (count / total * 100) for value, count in counts.items()}


def compare_demographics_by_offense(
    incidents: List[Dict[str, Any]],
    offense_field: str = "offincident",
    demographic_field: DemographicField = DemographicField.RACE,
    properties: bool = False,
    top_n: int = 10
) -> Dict[str, Dict[str, int]]:
    """
    Compare demographic breakdown across different offense types.
    
    Args:
        incidents: List of incident dictionaries
        offense_field: Field containing offense type
        demographic_field: Demographic field to analyze
        properties: If True, look in properties dict (for GeoJSON)
        top_n: Number of top offenses to include
    
    Returns:
        Dictionary mapping offense types to demographic breakdowns
    """
    # Group incidents by offense
    offense_groups = {}
    for incident in incidents:
        data = incident.get("properties", incident) if properties else incident
        offense = data.get(offense_field)
        
        if offense:
            if offense not in offense_groups:
                offense_groups[offense] = []
            offense_groups[offense].append(incident)
    
    # Get top N offenses by count
    offense_counts = [(o, len(incs)) for o, incs in offense_groups.items()]
    offense_counts.sort(key=lambda x: x[1], reverse=True)
    top_offenses = [o for o, _ in offense_counts[:top_n]]
    
    # Get demographic breakdown for each top offense
    result = {}
    for offense in top_offenses:
        result[offense] = count_by_demographics(
            offense_groups[offense],
            demographic_field,
            properties
        )
    
    return result


def create_demographic_df(
    incidents: List[Dict[str, Any]],
    properties: bool = False
):
    """
    Create a pandas DataFrame with demographic information.
    
    Args:
        incidents: List of incident dictionaries
        properties: If True, extract from properties dict (for GeoJSON)
    
    Returns:
        pandas DataFrame with demographic columns
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(
            "pandas is required. Install with: pip install pandas"
        )
    
    data = []
    for incident in incidents:
        item = incident.get("properties", incident) if properties else incident
        
        row = {
            'race': normalize_demographic_value(
                DemographicField.RACE,
                item.get(DemographicField.RACE)
            ),
            'ethnicity': normalize_demographic_value(
                DemographicField.ETHNICITY,
                item.get(DemographicField.ETHNICITY)
            ),
            'sex': normalize_demographic_value(
                DemographicField.SEX,
                item.get(DemographicField.SEX)
            ),
        }
        
        # Include other useful fields
        for field in ['offincident', 'ucr_offense', 'beat', 'division', 'date1']:
            if field in item:
                row[field] = item[field]
        
        data.append(row)
    
    return pd.DataFrame(data)


def visualize_demographics(
    incidents: List[Dict[str, Any]],
    field: DemographicField = DemographicField.RACE,
    properties: bool = False,
    kind: str = 'bar'
):
    """
    Create a visualization of demographic distribution.
    
    Args:
        incidents: List of incident dictionaries
        field: Demographic field to visualize
        properties: If True, look in properties dict (for GeoJSON)
        kind: Chart type ('bar', 'pie', 'barh')
    
    Returns:
        matplotlib figure
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError(
            "matplotlib is required. Install with: pip install matplotlib"
        )
    
    counts = count_by_demographics(incidents, field, properties)
    
    # Remove 'Unknown' if present for cleaner viz
    counts_clean = {k: v for k, v in counts.items() if k != 'Unknown'}
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    if kind == 'pie':
        ax.pie(
            counts_clean.values(),
            labels=counts_clean.keys(),
            autopct='%1.1f%%',
            startangle=90
        )
        ax.axis('equal')
    else:
        # Bar chart
        values = list(counts_clean.values())
        labels = list(counts_clean.keys())
        
        if kind == 'barh':
            ax.barh(labels, values)
            ax.set_xlabel('Count')
        else:
            ax.bar(labels, values)
            ax.set_ylabel('Count')
        
        ax.set_title(f'Incidents by {field.value.replace("comp", "").title()}')
    
    plt.tight_layout()
    return fig
