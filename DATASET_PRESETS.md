# Dataset Presets Reference

The `dallas_incidents` package supports three Dallas Open Data datasets with different schemas and capabilities through configuration presets.

## Available Presets

### 1. Police Incidents (Historical Data)

**Preset**: `'police_incidents'` | **Dataset ID**: `qv6i-rri7`

```python
client = DallasIncidentsClient(preset='police_incidents', app_token='token')
response = client.get_by_beat(['241'], start_date='2024-01-01', limit=500)
```

- **Columns**: 86 fields
- **Date Range**: June 2014 - Present  
- **Update Frequency**: Daily
- **Best For**: Historical analysis, trend identification, research

**Key Features:**
- ✅ Full timestamps (`date1`)
- ✅ NIBRS codes and classification
- ✅ UCR offense descriptions
- ✅ Demographics (race, ethnicity, sex)
- ✅ Geographic fields (beat, division, sector, coordinates)
- ✅ Investigation details (officers, status, case numbers)

---

### 2. Active Calls - Northeast Division (Real-time)

**Preset**: `'active_calls_northeast'` | **Dataset ID**: `juse-v5tw`

```python
client = DallasIncidentsClient(preset='active_calls_northeast', app_token='token')
response = client.get_by_beat(['241'], limit=100)
```

- **Columns**: 5 fields
- **Date Range**: Current active calls only
- **Update Frequency**: Every few minutes
- **Best For**: Real-time Northeast monitoring, current incident awareness

**Available Fields:**
- `nature_of_call`: Type (e.g., "BURGLARY", "TRAFFIC STOP")
- `unit_number`: Responding officer's unit ID
- `block`: Block number
- `location`: Street name or intersection
- `beat`: Police beat number

**Limitations:**
- ❌ No timestamps
- ❌ No historical data
- ❌ No NIBRS/UCR codes
- ❌ No coordinates (requires geocoding for maps)

---

### 3. Active Calls - All Divisions (Real-time)

**Preset**: `'active_calls_all'` | **Dataset ID**: `9fxf-t2tr`

```python
client = DallasIncidentsClient(preset='active_calls_all', app_token='token')
response = client.get_incidents(IncidentQuery(limit=500))
```

- **Columns**: ~5 fields (similar to Northeast)
- **Date Range**: Current active calls only
- **Update Frequency**: Every few minutes
- **Best For**: Citywide real-time monitoring

---

## Dataset Comparison

| Feature | Police Incidents | Active Calls NE | Active Calls All |
|---------|-----------------|-----------------|------------------|
| **Preset** | `police_incidents` | `active_calls_northeast` | `active_calls_all` |
| **Dataset ID** | qv6i-rri7 | juse-v5tw | 9fxf-t2tr |
| **Columns** | 86 | 5 | 5 |
| **Timestamps** | ✅ Yes | ❌ No | ❌ No |
| **Historical** | ✅ 2014-Present | ❌ Current only | ❌ Current only |
| **NIBRS Codes** | ✅ Yes | ❌ No | ❌ No |
| **Demographics** | ✅ Yes | ❌ No | ❌ No |
| **Coordinates** | ✅ Yes | ❌ No (addresses only) | ❌ No (addresses only) |
| **Division** | ✅ All | Northeast only | All |
| **Update Freq** | Daily | Every few min | Every few min |

---

## Police Incidents - Field Reference

### Core Fields (Most Used)

| Field | Type | Description |
|-------|------|-------------|
| `date1` | timestamp | Incident date/time |
| `incidentnum` | string | Unique incident number |
| `offincident` | string | Offense description |
| `ucr_offense` | string | UCR offense classification |
| `beat` | string | Police beat identifier |
| `division` | string | Police division name |
| `incident_address` | string | Street address |
| `geocoded_column` | location | Lat/lon coordinates + address |

### NIBRS Classification (8 fields)

| Field | Description | Example Values |
|-------|-------------|----------------|
| `nibrs` | NIBRS code | 13A, 220, 35A |
| `nibrs_type` | Crime classification | Crime Against Person, Crime Against Property |
| `nibrs_crime` | Crime name | Aggravated Assault, Burglary/Breaking & Entering |
| `nibrs_crime_category` | Category | Assault Offenses, Larceny/Theft Offenses |
| `nibrs_crimeagainst` | Target | Person, Property, Society |
| `nibrs_group` | Group | Group A, Group B |
| `nibrs_offense_code` | Offense code | 13A, 220 |

### Demographics (3 fields)

| Field | Description | Values |
|-------|-------------|--------|
| `comprace` | Race | B=Black, W=White, H=Hispanic, A=Asian, I=American Indian, U=Unknown |
| `compethnicity` | Ethnicity | H=Hispanic, N=Non-Hispanic, U=Unknown |
| `compsex` | Sex | M=Male, F=Female, U=Unknown |

### Location Fields (9 fields)

`incident_address`, `beat`, `division`, `sector`, `district`, `ra` (reporting area), `zip_code`, `city`, `geocoded_column`

### Temporal Fields (8 fields)

`date1`, `time1`, `date2_of_occurrence_2`, `reporteddate`, `edate`, `watch`, `servyr`, `mo`, `year1`

### Investigation Fields (9 fields)

`servnumid`, `ro1name`, `ro2name`, `status`, `ucr_disp`, `followup1`, `followup2`, `elenum`

### Crime Details (6 fields)

`weaponused`, `premise`, `gang`, `objattack`, `victimtype`, `involvement`

**Total**: 86 fields. See dataset documentation for complete schema.

---

## Query Capabilities by Dataset

| Query Type | Police Incidents | Active Calls |
|------------|-----------------|--------------|
| **By Beat** | ✅ Yes | ✅ Yes |
| **By Date Range** | ✅ Yes | ❌ No |
| **By Category** | ✅ Yes | ❌ No |
| **By Keyword** | ✅ Yes | ❌ No |
| **By NIBRS** | ✅ Yes | ❌ No |
| **By Demographics** | ✅ Yes | ❌ No |
| **By Division** | ✅ Yes | ✅ Limited |
| **Geographic** | ✅ Yes | ❌ No |

---

## Custom Configuration

For datasets not covered by presets:

```python
from dallas_incidents import ClientConfig

config = ClientConfig(
    dataset_id="your-dataset-id",
    datetime_field="date_field_name",  # or None if no timestamps
    location_field="location",
    beat_field="beat",
    division_field="division",  # or None if not available
    dataset_name="Custom Dataset"
)

client = DallasIncidentsClient(config=config, app_token='token')
```

---

## Troubleshooting

### Issue: Date queries don't work
**Cause**: Dataset lacks timestamps  
**Solution**: Use Police Incidents preset for date-based queries
```python
if not client.config.supports_timestamps:
    print("Use 'police_incidents' preset for date queries")
```

### Issue: Field not found errors
**Cause**: Field unavailable in current dataset  
**Solution**: Check available fields
```python
fields = client.get_field_names()
print(f"Available: {fields}")
```

### Issue: Empty results from Active Calls
**Cause**: Shows only current active calls  
**Solution**: Active Calls are ephemeral - query frequently for real-time monitoring

### Issue: Map shows no markers for Active Calls
**Cause**: No coordinates in data  
**Solution**: Use geocoding
```python
from dallas_incidents import geocode_active_calls
geocoded = geocode_active_calls(response.data, cache_file='cache.json')
```

---

## Finding Other Datasets

Browse: https://www.dallasopendata.com/browse?category=Public+Safety

To add a new dataset:
1. Note the dataset ID (last part of URL)
2. Check the columns/schema  
3. Create a custom `ClientConfig`

---

**For complete API documentation, see [README.md](README.md)**
