# LandsatL2C2

**Modern Landsat Level 2 Collection 2 Search & Download Utility**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A Python library for searching and downloading Landsat Collection 2 Level-2 data using NASA's modern **earthaccess** library by default, with legacy M2M API support.

## 🚀 Key Features

- **Modern earthaccess Integration**: Uses NASA's official earthaccess library by default
- **Simplified Authentication**: Secure `.netrc` authentication with NASA Earthdata Login
- **Cloud-Native Access**: Direct access to NASA Earthdata Cloud
- **Backward Compatible**: Legacy M2M API support for existing workflows
- **High-Level API**: Same simple interface for both backends
- **Advanced Processing**: Built-in support for mosaicking, compositing, and product generation

## 📦 Installation

```bash
pip install LandsatL2C2
```

## 🔧 Quick Start

### 1. Set up Authentication (One-time setup)

Create a `.netrc` file with your [NASA Earthdata](https://urs.earthdata.nasa.gov/) credentials:

```bash
echo "machine urs.earthdata.nasa.gov login YOUR_USERNAME password YOUR_PASSWORD" > ~/.netrc
chmod 600 ~/.netrc
```

### 2. Basic Usage

```python
from LandsatL2C2 import LandsatL2C2
from datetime import date
from shapely.geometry import box

# Initialize (uses earthaccess with netrc by default)
landsat = LandsatL2C2()

# Define area of interest (California example)
geometry = box(-120.0, 35.0, -119.0, 36.0)

# Search for scenes
scenes = landsat.scene_search(
    start=date(2023, 6, 1),
    end=date(2023, 6, 30),
    target_geometry=geometry,
    max_results=10,
    cloud_percent_max=20
)

print(f"Found {len(scenes)} scenes")

# Download data
downloads = landsat.download(
    start_date=date(2023, 6, 1),
    end_date=date(2023, 6, 30),
    target_geometry=geometry,
    max_results=5
)
```

### 3. Advanced Processing

```python
# Generate processed products
with LandsatL2C2() as landsat:
    results = landsat.process(
        start=date(2023, 6, 1),
        products=["NDVI", "albedo", "ST_C"],
        geometry=geometry,
        target="my_study_area"
    )
```

## Authentication

### earthaccess Authentication

Set up NASA Earthdata Login credentials using one of these methods:

1. **`.netrc` file (recommended)**:
   ```bash
   # Create ~/.netrc file
   echo "machine urs.earthdata.nasa.gov login YOUR_USERNAME password YOUR_PASSWORD" > ~/.netrc
   chmod 600 ~/.netrc
   ```

2. **Environment variables**:
   ```bash
   export EARTHDATA_USERNAME=your_username
   export EARTHDATA_PASSWORD=your_password
   ```

3. **Interactive login**: The package will prompt for credentials when needed.

### M2M API Authentication

For M2M API, set up EROS Registration System credentials in `~/.M2M_credentials`.

## Features

- Search Landsat Collection 2 Level-2 data by:
  - Date range
  - Geographic area (bounding box, polygon, point)
  - Cloud cover percentage
  - Sensor type (Landsat 4, 5, 7, 8, 9)
- Download data with automatic organization
- Process downloaded data into analysis-ready products
- Support for both cloud-hosted and on-premises data access

## Migration from M2M to earthaccess

See [EARTHACCESS_MIGRATION.md](EARTHACCESS_MIGRATION.md) for detailed migration guidance.

## Documentation

- [API Documentation](docs/api.md)
- [Migration Guide](EARTHACCESS_MIGRATION.md)
- [Examples](examples/)

## Requirements

- Python >= 3.10
- NASA Earthdata Login account (for earthaccess)
- EROS Registration System account (for M2M API)

## License

This project is licensed under the terms specified in the LICENSE file.

## Contributing

Contributions are welcome! Please see the contributing guidelines for details.

## Acknowledgments

Developed by Gregory H. Halverson at the Jet Propulsion Laboratory, California Institute of Technology.
