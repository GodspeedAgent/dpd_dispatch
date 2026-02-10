# Changelog

All notable changes to the dallas_incidents package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-11-11

### Added - Multi-Dataset Support

#### New Features
- **DatasetPreset**: Enum for predefined dataset configurations
  - `POLICE_INCIDENTS`: Historical incidents (2014-present, 86 columns)
  - `ACTIVE_CALLS_NORTHEAST`: Real-time Northeast Division calls (5 columns)
  - `ACTIVE_CALLS_ALL`: Real-time citywide active calls

- **ClientConfig Enhancements**:
  - `from_preset()`: Factory method for quick configuration
  - Field mapping properties: `datetime_field`, `location_field`, `beat_field`, `division_field`
  - `supports_timestamps`: Property to check timestamp availability
  - `get_info()`: Human-readable configuration information
  - `dataset_name` and `dataset_description`: Metadata fields

- **DallasIncidentsClient**:
  - `preset` parameter for easy initialization
  - Automatic field mapping based on dataset configuration

- **IncidentQuery**:
  - Config-aware query building
  - Graceful handling of unavailable fields
  - Conditional filter application based on dataset capabilities

#### Documentation
- **DATASET_PRESETS.md**: Complete dataset reference guide
- **docs/archive/MULTI_DATASET_IMPLEMENTATION.md**: Technical implementation details (archived)
- **multi_dataset_example.py**: Working examples for all datasets
- **verify_presets.py**: Automated preset verification script

#### Examples
- Updated `simple_example.py` to use presets
- Updated `README.md` with dataset comparison table and comprehensive reference tables

### Changed
- **ClientConfig**: Default `datetime_field` is now `None` to support datasets without timestamps
- **IncidentQuery.to_soql_params()**: Now accepts `config` parameter for field mapping
- **Client initialization**: Now supports `preset` parameter alongside traditional `config`
- **Documentation**: Updated all examples to show explicit preset usage

### Improved
- Query flexibility: Automatically adapts to available dataset fields
- Error handling: Better messages when using unavailable fields
- Type safety: Enhanced with DatasetPreset enum
- Code clarity: Explicit dataset selection via presets

### Fixed
- Date-based queries now skip gracefully when dataset has no timestamp fields
- Division filtering skips when field not available in dataset
- Geographic queries adapt to different location field names

### Backward Compatibility
- ✅ All existing code continues to work
- Default configuration maintained for compatibility
- Convenience methods (`get_by_beat`, `get_by_date_range`, etc.) still functional
- No breaking changes to existing API

---

## [1.0.0] - 2025-11-08

### Added - Initial Release

#### Core Features
- **DallasIncidentsClient**: Main API client built on sodapy
  - Context manager support for automatic cleanup
  - Multiple convenience methods (get_by_beat, get_by_date_range, get_by_location)
  - Automatic pagination with get_all_incidents()
  - GeoJSON format support
  - Metadata access and field inspection
  - Full-text search capability

#### Data Models
- **ClientConfig**: Configuration dataclass for client settings
- **IncidentQuery**: Fluent query builder with comprehensive filters
- **IncidentResponse**: Response wrapper with utility methods
- **DateRange**: Helper for date-based filtering
- **GeoQuery**: Geographic query builder
- **OutputFormat**: Enum for response formats (JSON, GeoJSON, CSV)

#### Visualization
- **IncidentMapper**: Folium-based map creator
  - Clustered markers for performance
  - Heatmap visualization
  - Color-coded markers by attribute
  - Customizable popup fields
  - Multiple tile provider support
  - Choropleth map support
  - Automatic center and bounds calculation

#### Utilities
- DateTime parsing and conversion functions
- Data grouping and counting helpers
- Geographic calculations (distance, bounding box)
- Coordinate extraction from various formats
- Summary statistics generation
- Export to CSV and GeoJSON
- DataFrame conversion utilities
- Client-side filtering functions

#### Documentation
- Comprehensive README.md with full API documentation
- QUICKSTART.md for rapid onboarding
- PROJECT_OVERVIEW.md detailing architecture and design
- Detailed docstrings throughout the codebase
- Multiple example scripts and notebooks

#### Examples
- example_usage.ipynb: Comprehensive Jupyter notebook tutorial
- simple_example.py: Basic usage script
- Examples README with common use cases

#### Testing
- Unit tests for all major components
- Mock-based testing for API interactions
- Installation verification script
- Test coverage ~85%

#### Development Tools
- requirements.txt: Core dependencies
- requirements-dev.txt: Development dependencies
- setup.py: Package installation configuration
- .env.example: Environment variable template
- .gitignore: Git ignore configuration
- verify_install.py: Installation verification

### Dependencies
- sodapy >= 2.2.0
- requests >= 2.31.0
- pandas >= 2.0.0
- folium >= 0.14.0

### Optional Dependencies
- geopandas >= 0.14.0 (for advanced geospatial analysis)
- matplotlib >= 3.7.0 (for plotting)
- seaborn >= 0.12.0 (for statistical visualization)

### Development Dependencies
- pytest >= 7.4.0
- pytest-cov >= 4.1.0
- black >= 23.0.0
- flake8 >= 6.0.0
- mypy >= 1.4.0
- jupyter >= 1.0.0

### Dataset Information
- Source: Dallas Open Data Portal (www.dallasopendata.com)
- Dataset ID: juse-v5tw
- API: Socrata Open Data API (SODA)
- Format Support: JSON, GeoJSON, CSV

### Known Limitations
- Some incidents may not have geographic coordinates
- API rate limiting applies without app token
- Large datasets require pagination for complete retrieval

### Breaking Changes
- N/A (Initial release)

### Migration Guide
- N/A (Initial release)

---

## [Unreleased]

### Planned Features
- [ ] Async API support for concurrent requests
- [ ] CLI interface for command-line usage
- [ ] Additional visualization templates
- [ ] Integration with other Dallas Open Data datasets
- [ ] Real-time data streaming support
- [ ] Machine learning model integration
- [ ] Dashboard templates
- [ ] Automated report generation
- [ ] Data caching layer
- [ ] Advanced spatial analysis functions

### Under Consideration
- Web API wrapper
- Docker containerization
- Cloud deployment templates
- Automated data updates
- Custom alert system
- Time series forecasting
- Anomaly detection

---

## Version History

- **1.0.0** (2025-11-08): Initial release with full functionality

---

## Contributing

When contributing to this project:

1. Update this CHANGELOG.md with your changes
2. Follow [Semantic Versioning](https://semver.org/)
3. Add entries under the [Unreleased] section
4. Move entries to a new version section upon release

### Changelog Sections

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes

---

## Links

- [Dallas Open Data Portal](https://www.dallasopendata.com/)
- [Police Incidents Dataset](https://dev.socrata.com/foundry/www.dallasopendata.com/juse-v5tw)
- [Socrata API Documentation](https://dev.socrata.com/)
- [sodapy GitHub](https://github.com/afeld/sodapy)
- [Folium Documentation](https://python-visualization.github.io/folium/)

---

**Note**: This project follows [Semantic Versioning](https://semver.org/):
- MAJOR version for incompatible API changes
- MINOR version for backwards-compatible functionality additions
- PATCH version for backwards-compatible bug fixes
