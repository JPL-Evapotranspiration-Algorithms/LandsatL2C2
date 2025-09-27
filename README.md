# LandsatL2C2
Landsat Level 2 Collection 2 Search & Download Utility

## New Backend System! 🚀

LandsatL2C2 now supports multiple backends for accessing Landsat data:

- **S3 Backend** (Recommended): Anonymous access to cloud-optimized data, no credentials required
- **M2M Backend** (Legacy): Traditional USGS API access with full download functionality  
- **Auto Backend**: Intelligent selection between S3 and M2M

## Quick Start

### S3 Backend (No Credentials Needed)
```python
from LandsatL2C2 import LandsatL2C2
from datetime import date
from shapely.geometry import Point

# Create client with S3 backend
landsat = LandsatL2C2(backend="s3")

# Search for scenes
scenes = landsat.scene_search(
    start=date(2023, 6, 1),
    end=date(2023, 6, 30),
    target_geometry=Point(-118.2437, 34.0522),  # Los Angeles
    cloud_percent_max=20
)

# Load data directly from cloud
granule = landsat.retrieve_granule(
    dataset=scenes.iloc[0]['dataset'],
    date_UTC=scenes.iloc[0]['date_UTC'],
    granule_ID=scenes.iloc[0]['display_ID'],
    entity_ID=scenes.iloc[0]['entity_ID']
)

# Access bands without downloading
red_band = granule.DN(4)  # Stream from S3
```

### Installation

Base installation:
```bash
pip install LandsatL2C2
```

```bash
pip install LandsatL2C2
```

S3 backend dependencies are included by default.

See [BACKEND_MIGRATION.md](BACKEND_MIGRATION.md) for detailed migration guide and examples.
