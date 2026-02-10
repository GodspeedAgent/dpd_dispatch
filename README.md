# Dallas Open Data - Police Incidents Package

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive Python package for accessing, analyzing, and visualizing Dallas Police data from the [Dallas Open Data portal](https://www.dallasopendata.com/). Supports both historical Police Incidents (2014-present, 86 fields) and real-time Active Calls (5 fields) with intelligent query handling for different dataset schemas.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Datasets Overview](#datasets-overview)
- [Query Methods Reference](#query-methods-reference)
- [Visualization Reference](#visualization-reference)
- [Advanced Features](#advanced-features)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Resources](#resources)

## Features

### Core Capabilities
- 🚀 **Multi-Dataset Support**: Seamless switching between Police Incidents and Active Calls datasets
- 🔍 **Intelligent Querying**: Automatic query adaptation based on dataset capabilities
- 📊 **Data Analysis**: Built-in utilities for counting, grouping, and summarizing
- 🗺️ **Interactive Mapping**: Folium-based visualizations with clustering, heatmaps, and custom styling
- 📦 **Multiple Export Formats**: JSON, GeoJSON, CSV, and pandas DataFrames
- 🎯 **Type Safety**: Complete type hints for IDE support and code quality

### Advanced Features (v1.2.0)
- 🏷️ **Semantic Crime Search**: Query by category (`'weapon'`, `'drug'`, `'violent'`) instead of exact offense names
- 🔎 **Keyword Search**: Find incidents by keyword (`'gun'`, `'sex'`, `'theft'`) across offense fields
- 👥 **Demographic Analysis**: Filter and analyze incidents by race, ethnicity, and sex
- 🗺️ **Smart Popup Profiles**: Pre-configured field sets for map popups (8 profiles including combined support)
- 🔴 **Murder Highlighting**: Automatic visual distinction for homicides with skull icons
- 🎨 **NIBRS Support**: Query and visualize using National Incident-Based Reporting System fields
- 📅 **Simplified Date API**: Accept both date objects and ISO strings without DateRange wrapper
- 📋 **Auto-Categorization**: 300+ offense types mapped to 15 semantic categories

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/dallas_incidents.git
cd dallas_incidents

# Install dependencies
pip install -r requirements.txt

# Development installation (editable mode)
pip install -e .
```

**Optional Dependencies:**
```bash
pip install jupyter matplotlib seaborn geopandas  # For analysis and notebooks
```

## Quick Start

```python
from dallas_incidents import DallasIncidentsClient
from datetime import date, timedelta

# Initialize with Police Incidents dataset
client = DallasIncidentsClient(
    preset='police_incidents',
    app_token='your_token_here'  # Get free token at dev.socrata.com
)

# Query recent incidents - simplified API!
response = client.get_by_beat(
    beats=['241', '242'],
    start_date=date.today() - timedelta(days=30),
    limit=500
)

# Convert to DataFrame and analyze
df = response.to_df()
print(f"Retrieved {len(df)} incidents")

# Create interactive map
map_obj = response.to_map(cluster=True, popup_profile='essential')
map_obj.save('incidents_map.html')
```

**See [examples/](examples/) for complete working examples and notebooks.**

## Datasets Overview

The package supports three Dallas Open Data datasets with different schemas and capabilities:

| Feature | Police Incidents | Active Calls NE | Active Calls All |
|---------|-----------------|-----------------|------------------|
| **Preset** | `'police_incidents'` | `'active_calls_northeast'` | `'active_calls_all'` |
| **Dataset ID** | qv6i-rri7 | juse-v5tw | 9fxf-t2tr |
| **Columns** | 86 | 5 | 5 |
| **Date Range** | 2014-Present | Current only | Current only |
| **Update Freq** | Daily | Every few min | Every few min |
| **Timestamps** | ✅ Yes | ❌ No | ❌ No |
| **NIBRS Codes** | ✅ Yes | ❌ No | ❌ No |
| **Demographics** | ✅ Yes | ❌ No | ❌ No |
| **Best For** | Historical analysis, trends | Real-time NE monitoring | Citywide monitoring |

**📖 For complete field listings and dataset details, see [DATASET_PRESETS.md](DATASET_PRESETS.md)**

## Query Methods Reference

### Primary Query Methods

| Method | Description | Datasets | Example |
|--------|-------------|----------|---------|
| `get_incidents(query)` | Execute IncidentQuery with flexible filters | All | `client.get_incidents(IncidentQuery(beats=['241']))` |
| `search_by_category(category, ...)` | Search by semantic category (15 available) | Police Incidents | `client.search_by_category('weapon', start_date='2024-01-01')` |
| `search_by_keyword(keyword, ...)` | Search offense descriptions by keyword | Police Incidents | `client.search_by_keyword('gun', beats=['241'])` |
| `get_by_beat(beats, ...)` | Query specific police beats | All | `client.get_by_beat(['241', '242'], limit=500)` |
| `get_by_date_range(start, end, ...)` | Query date range (accepts date or string) | Police Incidents | `client.get_by_date_range('2024-01-01', '2024-12-31')` |
| `get_by_location(lat, lon, radius, ...)` | Geographic query within radius | Police Incidents | `client.get_by_location(32.7767, -96.7970, 2000)` |

### Utility Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `get_all_incidents(query)` | Generator for paginated results | Iterator[Dict] |
| `get_metadata()` | Get dataset schema and metadata | Dict |
| `get_field_names()` | List all available field names | List[str] |
| `search(text, limit)` | Full-text search across all fields | IncidentResponse |

### IncidentQuery Parameters

| Parameter | Type | Description | Availability |
|-----------|------|-------------|--------------|
| `beats` | List[str] | Police beat identifiers | All datasets |
| `date_range` | DateRange | Start and end dates | Police Incidents only |
| `nibrs_codes` | List[str] | NIBRS codes (e.g., ['13A', '13B']) | Police Incidents only |
| `nibrs_type` | str | Crime type: 'Crime Against Person', 'Crime Against Property', 'Crime Against Society' | Police Incidents only |
| `nibrs_crime` | str | Specific NIBRS crime name | Police Incidents only |
| `nibrs_crime_category` | str | NIBRS crime category | Police Incidents only |
| `nibrs_code` | str | Single NIBRS code | Police Incidents only |
| `ucr_offense` | str | UCR offense description | Police Incidents only |
| `division` | str | Police division name | Police Incidents only |
| `offense_category` | str | Semantic category (see table below) | Police Incidents only |
| `offense_keyword` | str | Keyword in offense description | Police Incidents only |
| `geo_query` | GeoQuery | Geographic filter (lat, lon, radius) | Police Incidents only |
| `limit` | int | Maximum results (default: 1000) | All datasets |
| `offset` | int | Pagination offset | All datasets |
| `order_by` | str | Sort field | All datasets |
| `select_fields` | List[str] | Specific fields to return | All datasets |
| `format` | OutputFormat | JSON, GEOJSON, or CSV | All datasets |

**Simplified Date API:**  
Methods like `search_by_category()`, `search_by_keyword()`, and `get_by_beat()` accept direct `start_date` and `end_date` parameters (date objects or ISO strings) without requiring DateRange wrapper.

```python
# All three formats work:
client.search_by_category('weapon', start_date=date(2024, 1, 1))
client.search_by_category('weapon', start_date='2024-01-01')
client.search_by_category('weapon', start_date=date.today() - timedelta(days=7))
```

### Semantic Categories (15 Available)

| Category | Offense Types Included |
|----------|------------------------|
| `'violent'` | Murder, aggravated assault, kidnapping, arson |
| `'assault'` | Simple assault, aggravated assault, family violence |
| `'robbery'` | Robbery of business, individual, residence |
| `'theft'` | Shoplifting, theft from person/building/vehicle |
| `'burglary'` | Burglary of habitation, building, vehicle (BMV) |
| `'vehicle'` | Auto theft, unauthorized use of motor vehicle |
| `'drug'` | Drug possession, delivery, manufacturing |
| `'weapon'` | Firearm offenses, deadly conduct, prohibited weapons |
| `'fraud'` | Fraud, forgery, identity theft, credit card abuse |
| `'traffic'` | DWI, traffic violations, hit and run |
| `'property'` | Criminal mischief, vandalism, graffiti |
| `'public_order'` | Trespassing, harassment, disorderly conduct |
| `'death'` | Death investigations, suspicious deaths |
| `'animal'` | Animal cruelty, dangerous dog |
| `'other'` | All other offense types |

**Example:**
```python
# Get all weapon-related incidents
weapon_crimes = client.search_by_category('weapon', limit=500)
```

## Visualization Reference

### Map Creation Methods

**Quick Method (from IncidentResponse):**
```python
map_obj = response.to_map(cluster=True, popup_profile='essential')
map_obj.save('map.html')
```

**Advanced Method (using IncidentMapper):**
```python
from dallas_incidents import IncidentMapper
mapper = IncidentMapper(response)
map_obj = mapper.create_map(cluster=True, color_by='ucr_offense')
```

### to_map() Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cluster` | bool | True | Enable marker clustering for performance |
| `heatmap` | bool | False | Create density heatmap instead of markers |
| `color_by` | str | None | Field to color-code markers by |
| `popup_fields` | List[str] | None | Manual field selection for popups |
| `popup_profile` | str \| List[str] | 'comprehensive' | Pre-configured field set(s) |
| `tiles` | str | 'OpenStreetMap' | Map tile provider |
| `zoom_start` | int | 11 | Initial zoom level |

### Popup Profiles (8 Available)

| Profile | Fields Included | Use Case |
|---------|-----------------|----------|
| `'essential'` | date1, offincident, beat, incident_address, incidentnum | Minimal information, clean popups |
| `'demographic'` | date1, offincident, involvement, victimtype, comprace, compethnicity, compsex, objattack | Population analysis, victim demographics |
| `'crime_details'` | date1, offincident, ucr_offense, nibrs_crime, nibrs_type, nibrs_crime_category, premise, weaponused, gang | Crime classification and details |
| `'location'` | incident_address, beat, division, sector, district, zip_code, city, ra | Geographic analysis |
| `'temporal'` | date1, time1, date2_of_occurrence_2, reporteddate, edate, watch, servyr | Time-based analysis |
| `'investigation'` | incidentnum, servnumid, ro1name, ro2name, status, ucr_disp, followup1, followup2, elenum | Case management |
| `'nibrs'` | date1, offincident, nibrs_crime, nibrs_crime_category, nibrs_crimeagainst, nibrs_code, nibrs_group, nibrs_type | NIBRS-specific analysis |
| `'comprehensive'` | date1, incidentnum, offincident, ucr_offense, nibrs_type, incident_address, beat, division, comprace, compsex, weaponused, premise, status | General purpose (default) |

**Combined Profiles (v1.2.0):**  
Pass a list to combine multiple profiles:
```python
map_obj = response.to_map(popup_profile=['essential', 'demographic', 'location'])
```

### Special Visualization Features

**Murder Highlighting:**  
Incidents with "HOMICIDE" or "MURDER" in `nibrs_crime_category` automatically display with red skull icon markers using BeautifyIcon plugin.

**Color Coding:**  
Color markers by any field to visualize patterns:
```python
map_obj = response.to_map(color_by='ucr_offense')  # By offense type
map_obj = response.to_map(color_by='nibrs_type')   # By NIBRS category
map_obj = response.to_map(color_by='comprace')     # By demographics
map_obj = response.to_map(color_by='beat')         # By police beat
```

19 distinct colors available, automatically assigned to unique field values.

**Heatmap:**  
```python
map_obj = response.to_map(heatmap=True, tiles='CartoDB dark_matter')
```

**Tile Providers:**
- `'OpenStreetMap'` (default)
- `'CartoDB positron'` (light, clean)
- `'CartoDB dark_matter'` (dark theme, good for heatmaps)
- `'Stamen Terrain'`, `'Stamen Toner'`
- And more via Folium

### Geocoding for Active Calls

Active Calls datasets lack coordinates. Use geocoding for mapping:

```python
from dallas_incidents import geocode_active_calls

# Geocode addresses with caching
geocoded_data = geocode_active_calls(
    response.data,
    cache_file='geocode_cache.json',
    show_progress=True
)

# Or use to_map() which automatically geocodes
map_obj = response.to_map(cluster=True)  # Auto-geocoding happens
```

## Advanced Features

### Demographic Analysis

**Available Functions:**

| Function | Description | Returns |
|----------|-------------|---------|
| `demographic_summary(incidents)` | Text summary of race, ethnicity, sex breakdown | str |
| `filter_by_demographics(incidents, race, ethnicity, sex)` | Filter incidents by demographic criteria | List[Dict] |
| `count_by_demographics(incidents, field)` | Count incidents by demographic field | Dict[str, int] |
| `demographic_breakdown(incidents)` | Complete breakdown by all demographic fields | Dict[str, Dict[str, int]] |

**Example:**
```python
from dallas_incidents import demographic_summary, filter_by_demographics

print(demographic_summary(response.data))

# Output:
# Demographic Analysis (500 incidents):
# RACE:
#   Black: 250 (50.0%)
#   White: 150 (30.0%)
#   Hispanic: 75 (15.0%)
# ...

# Filter to specific demographics
black_male = filter_by_demographics(response.data, race='Black', sex='Male')
```

**Demographic Fields (Police Incidents):**
- `comprace`: Race (B=Black, W=White, H=Hispanic, A=Asian, I=American Indian, U=Unknown)
- `compethnicity`: Ethnicity (H=Hispanic, N=Non-Hispanic, U=Unknown)
- `compsex`: Sex (M=Male, F=Female, U=Unknown)

### NIBRS Filtering

National Incident-Based Reporting System classification and querying.

**NIBRS Query Fields:**

| Field | Description | Example Values |
|-------|-------------|----------------|
| `nibrs_type` | Crime classification | 'Crime Against Person', 'Crime Against Property', 'Crime Against Society' |
| `nibrs_codes` | List of NIBRS codes | ['13A', '13B', '13C'] (assault codes) |
| `nibrs_crime` | Specific crime name | 'Aggravated Assault', 'Simple Assault' |
| `nibrs_crime_category` | Crime category | 'Assault Offenses', 'Larceny/Theft Offenses' |
| `nibrs_code` | Single NIBRS code | '13A' |

**Example:**
```python
# All crimes against persons
query = IncidentQuery(nibrs_type='Crime Against Person', limit=1000)

# Specific assault codes
query = IncidentQuery(nibrs_codes=['13A', '13B'], beats=['241'])
```

**Common NIBRS Codes:**
- 13A, 13B, 13C: Assault offenses
- 120: Robbery
- 220: Burglary
- 23A-23H: Larceny/theft offenses
- 240: Motor vehicle theft
- 35A, 35B: Drug/narcotic offenses
- 09A: Murder/manslaughter

### Offense Auto-Categorization

Map 300+ offense types to 15 semantic categories.

```python
from dallas_incidents import categorize_offense, OffenseCategory

offense = "ASSAULT (AGG) -DEADLY WEAPON"
category = categorize_offense(offense)  # Returns: OffenseCategory.ASSAULT

# Add to DataFrame
df = response.to_df()
df['category'] = df['offincident'].apply(categorize_offense)
category_counts = df['category'].value_counts()
```

### Call Tracking (Active Calls → Police Incidents)

Track active calls and find their historical incident records.

```python
from dallas_incidents import CallTracker

# Initialize tracker
tracker = CallTracker()

# Track interesting active calls
active_client = DallasIncidentsClient(preset='active_calls_northeast')
response = active_client.get_incidents(IncidentQuery(limit=100))

for call in response.data:
    if call['nature_of_call'] == 'BURGLARY':
        tracker.track_call(call, notes="Residential burglary", tags=['property'])

tracker.save('tracked_calls.json')

# Later: Query historical data for tracked calls
incidents_client = DallasIncidentsClient(preset='police_incidents')
for query in tracker.generate_queries(days_after=3):
    results = incidents_client.get_incidents(query)
    # Process results...
```

## API Reference

### Classes

#### DallasIncidentsClient

Main API client for querying Dallas Open Data.

**Initialization:**
```python
# Using preset (recommended)
client = DallasIncidentsClient(preset='police_incidents', app_token='token')

# Using custom config
config = ClientConfig(dataset_id='custom-id', ...)
client = DallasIncidentsClient(config=config, app_token='token')
```

**Methods:** See [Query Methods Reference](#query-methods-reference) table above.

#### IncidentQuery

Fluent query builder for filtering incidents.

```python
query = IncidentQuery(
    beats=['241'],
    date_range=DateRange(start=date(2024, 1, 1)),
    nibrs_type='Crime Against Person',
    limit=500
)
```

**All Parameters:** See [IncidentQuery Parameters](#incidentquery-parameters) table above.

#### IncidentResponse

Response wrapper with utilities for data manipulation.

**Properties:**
- `data`: List[Dict] - Raw incident data
- `total_returned`: int - Number of incidents returned
- `query`: IncidentQuery - Original query
- `format`: OutputFormat - Response format
- `has_geometry`: bool - Whether data includes coordinates

**Methods:**
- `to_df()`: Convert to pandas DataFrame
- `to_map(...)`: Create Folium map (see [Visualization Reference](#visualization-reference))
- `to_geojson()`: Convert to GeoJSON format
- `get_unique_values(field)`: Get unique values for a field
- `filter(condition)`: Filter incidents by condition

#### DateRange

Date filtering helper.

```python
# Using date objects
DateRange(start=date(2024, 1, 1), end=date(2024, 12, 31))

# Using ISO strings
DateRange(start='2024-01-01', end='2024-12-31')
```

#### GeoQuery

Geographic query builder.

```python
GeoQuery(latitude=32.7767, longitude=-96.7970, radius_meters=2000)
```

#### ClientConfig

Configuration dataclass for custom datasets.

```python
config = ClientConfig(
    dataset_id='custom-id',
    datetime_field='date_field',  # or None
    location_field='location',
    beat_field='beat',
    division_field='division',  # or None
    domain='www.dallasopendata.com',
    timeout=30
)
```

### Enums

#### OutputFormat
- `JSON`: Standard JSON response
- `GEOJSON`: GeoJSON with geometry
- `CSV`: Comma-separated values

#### PopupProfile
- `ESSENTIAL`, `DEMOGRAPHIC`, `CRIME_DETAILS`, `LOCATION`, `TEMPORAL`, `INVESTIGATION`, `NIBRS`, `COMPREHENSIVE`

#### OffenseCategory
- `VIOLENT`, `ASSAULT`, `ROBBERY`, `THEFT`, `BURGLARY`, `VEHICLE`, `DRUG`, `WEAPON`, `FRAUD`, `TRAFFIC`, `PROPERTY`, `PUBLIC_ORDER`, `DEATH`, `ANIMAL`, `OTHER`

#### DemographicField
- `RACE`, `ETHNICITY`, `SEX`

### Utility Functions

| Function | Module | Description |
|----------|--------|-------------|
| `summarize_incidents(incidents)` | utils | Generate summary statistics |
| `count_by_field(incidents, field)` | utils | Count occurrences by field |
| `get_top_n(counts, n)` | utils | Get top N items from counts |
| `to_dataframe(incidents)` | utils | Convert to pandas DataFrame |
| `export_to_csv(incidents, filepath)` | utils | Export to CSV file |
| `export_to_geojson(incidents, filepath)` | utils | Export to GeoJSON file |
| `filter_by_date(incidents, start, end)` | utils | Filter by date range |
| `incidents_near_point(incidents, lat, lon, radius_m)` | utils | Filter by distance |
| `demographic_summary(incidents)` | demographics | Print demographic breakdown |
| `filter_by_demographics(incidents, race, ethnicity, sex)` | demographics | Filter by demographics |
| `count_by_demographics(incidents, field)` | demographics | Count by demographic field |
| `demographic_breakdown(incidents)` | demographics | Complete demographic breakdown |
| `categorize_offense(offense)` | offense_categories | Map offense to category |
| `search_offenses_by_keyword(keyword)` | offense_categories | Find offenses by keyword |
| `geocode_active_calls(calls, cache_file, show_progress)` | geocoding | Geocode Active Calls addresses |

## Configuration

### App Token

**Required for production use** to avoid rate limiting.

1. Get free token: https://dev.socrata.com/
2. Set in code:
   ```python
   client = DallasIncidentsClient(app_token='YOUR_TOKEN')
   ```
3. Or environment variable:
   ```bash
   export SOCRATA_APP_TOKEN='YOUR_TOKEN'
   ```

### Custom Dataset Configuration

```python
from dallas_incidents import ClientConfig, DallasIncidentsClient

config = ClientConfig(
    dataset_id='your-dataset-id',
    datetime_field='date_field_name',  # or None if no timestamps
    location_field='location',
    beat_field='beat',
    division_field='division',  # or None if not available
    dataset_name='Custom Dataset',
    domain='www.dallasopendata.com',
    timeout=30
)

client = DallasIncidentsClient(config=config, app_token='token')
```

### Check Dataset Capabilities

```python
# Get configuration info
print(client.config.get_info())

# Check timestamp support
if client.config.supports_timestamps:
    print("Can query by date range")
else:
    print("Real-time data only")
```

## Examples

The `examples/` directory contains comprehensive working examples:

| File | Description | What You'll Learn |
|------|-------------|-------------------|
| `simple_example.py` | Basic usage patterns | Client initialization, queries, maps, exports |
| `geocoding_example.py` | Active Calls geocoding | Address geocoding, caching, intersection handling |
| `multi_dataset_example.py` | Multiple dataset usage | Switching presets, dataset comparison |
| `example_usage.ipynb` | Comprehensive notebook | All features with visualizations |
| `tracking_example.ipynb` | Call tracking workflow | Active Calls → Police Incidents correlation |

**Run examples:**
```bash
python examples/simple_example.py
python examples/multi_dataset_example.py
jupyter notebook examples/example_usage.ipynb
```

**📖 See [examples/README.md](examples/README.md) for detailed example documentation.**

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Date queries return empty | Active Calls dataset lacks timestamps | Use Police Incidents preset: `preset='police_incidents'` |
| Field not found errors | Field unavailable in current dataset | Check available fields: `client.get_field_names()` |
| Rate limiting errors | No app token | Get free token at dev.socrata.com |
| Import errors | Missing dependencies | `pip install -r requirements.txt` |
| Geocoding fails | Invalid addresses | Use geocoding cache, check address format |
| Map shows no markers | No coordinates in data | Check `response.has_geometry`, use geocoding for Active Calls |
| Empty results | Filters too restrictive | Simplify query, check dataset capabilities |

### Dataset-Specific Issues

**Police Incidents:**
- Historical data may have 24-48 hour delay
- Some fields may be null/empty for older records
- Coordinates available via `geocoded_column`

**Active Calls:**
- Shows only current active calls (no history)
- No timestamps or NIBRS codes available
- Requires geocoding for mapping (addresses only)
- Updates every few minutes

### Getting Help

1. Check [DATASET_PRESETS.md](DATASET_PRESETS.md) for field availability
2. Review [examples/](examples/) for working code
3. Check dataset metadata: `client.get_metadata()`
4. Verify installation: `python verify_install.py`

## Resources

### Documentation
- [DATASET_PRESETS.md](DATASET_PRESETS.md) - Dataset reference and field listings
- [CHANGELOG.md](CHANGELOG.md) - Version history and changes
- [examples/README.md](examples/README.md) - Example documentation

### External Resources
- [Dallas Open Data Portal](https://www.dallasopendata.com/)
- [Police Incidents Dataset](https://www.dallasopendata.com/Public-Safety/Police-Incidents/qv6i-rri7)
- [Active Calls Northeast Dataset](https://www.dallasopendata.com/Public-Safety/Police-Calls-for-Service-Northeast/juse-v5tw)
- [Socrata API Documentation](https://dev.socrata.com/)
- [sodapy Library](https://github.com/xmunoz/sodapy)
- [Folium Documentation](https://python-visualization.github.io/folium/)

### Development
- **Repository**: GitHub (TBD)
- **License**: MIT
- **Python Version**: 3.8+
- **Dependencies**: sodapy, pandas, folium, requests

## Contributing

Contributions welcome! Areas for enhancement:
- Additional dataset presets
- New visualization types
- Performance optimizations
- Additional analysis utilities
- Documentation improvements
- Test coverage

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

**Current Version**: 1.2.0

**Major Features by Version:**
- **v1.2.0**: Semantic search, demographic analysis, smart popups, murder highlighting, NIBRS support, simplified date API
- **v1.1.0**: Multi-dataset support with presets, Active Calls datasets
- **v1.0.0**: Initial release with Police Incidents support, Folium maps, analysis utilities

---

**License**: MIT  
**Maintained by**: Dallas Open Data Community

For questions, issues, or contributions, please open an issue on GitHub.
