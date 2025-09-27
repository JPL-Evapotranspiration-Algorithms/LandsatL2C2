# Backend System Migration Guide

The LandsatL2C2 package now supports multiple backends for accessing Landsat Collection 2 data:

## Available Backends

### 1. S3 Backend (Recommended)
- **Anonymous access** - No credentials required
- **Cloud Optimized GeoTIFFs** - Direct access to data in the cloud
- **Fast partial reads** - Only download the pixels you need
- **No storage requirements** - Stream data directly from AWS S3

```python
from LandsatL2C2 import LandsatL2C2

# Use S3 backend explicitly
landsat = LandsatL2C2(backend="s3")
```

### 2. M2M Backend (Legacy)
- **Full USGS functionality** - Access to all Earth Explorer features
- **Complete scene downloads** - Traditional file-based workflow
- **Offline processing** - Work with downloaded data
- **Requires credentials** - USGS account needed

```python
from LandsatL2C2 import LandsatL2C2

# Use M2M backend explicitly
landsat = LandsatL2C2(backend="m2m", username="your_username", password="your_password")

# Or use context manager for automatic login/logout
with LandsatL2C2(backend="m2m") as landsat:
    scenes = landsat.scene_search(...)
```

### 3. Auto Backend Selection
- **Intelligent fallback** - Tries S3 first, then M2M
- **Seamless experience** - Works with or without credentials
- **Best of both worlds** - Gets the fastest available backend

```python
from LandsatL2C2 import LandsatL2C2

# Auto-select the best available backend
landsat = LandsatL2C2(backend="auto")  # Default behavior
```

## Installation

### Base Installation
```bash
pip install LandsatL2C2
```

S3 backend dependencies (`boto3` and `pystac-client`) are now included by default.

## Migration from Previous Versions

### Existing Code Compatibility
Your existing code will continue to work without changes:

```python
# This still works exactly as before
from LandsatL2C2 import LandsatL2C2

landsat = LandsatL2C2()  # Now uses auto backend selection
```

### New Recommended Usage
For new projects, explicitly choose your backend:

```python
from LandsatL2C2 import LandsatL2C2

# For most users - no credentials needed
landsat = LandsatL2C2(backend="s3")

# For advanced users who need M2M features
landsat = LandsatL2C2(backend="m2m")
```

## Backend Comparison

| Feature | S3 Backend | M2M Backend |
|---------|------------|-------------|
| **Authentication** | None required | USGS credentials |
| **Data Access** | Stream from cloud | Download to local |
| **Speed** | Fast (partial reads) | Slow (full downloads) |
| **Storage** | None required | Large local storage |
| **Internet** | Required | Optional after download |
| **Coverage** | Collection 2 only | All datasets |
| **Rate Limits** | None | USGS API limits |

## Usage Examples

### Simple Scene Search (S3 Backend)
```python
from datetime import date
from shapely.geometry import Point
from LandsatL2C2 import LandsatL2C2

# Create client with S3 backend
landsat = LandsatL2C2(backend="s3")

# Search for scenes
scenes = landsat.scene_search(
    start=date(2023, 6, 1),
    end=date(2023, 6, 30),
    target_geometry=Point(-118.2437, 34.0522),  # Los Angeles
    cloud_percent_max=20
)

print(f"Found {len(scenes)} scenes")
```

### Load Band Data (S3 Backend)
```python
# Get a granule (no download needed)
granule = landsat.retrieve_granule(
    dataset=scenes.iloc[0]['dataset'],
    date_UTC=scenes.iloc[0]['date_UTC'],
    granule_ID=scenes.iloc[0]['display_ID'],
    entity_ID=scenes.iloc[0]['entity_ID']
)

# Load band data directly from S3
red_band = granule.DN(4)  # Band 4 (red)
nir_band = granule.DN(5)  # Band 5 (NIR)

# Calculate NDVI
ndvi = (nir_band - red_band) / (nir_band + red_band)
```

### Traditional Download Workflow (M2M Backend)
```python
# Use M2M backend for traditional workflow
with LandsatL2C2(backend="m2m") as landsat:
    scenes = landsat.scene_search(
        start=date(2023, 6, 1),
        end=date(2023, 6, 30),
        tiles=["034033"],
        cloud_percent_max=20
    )
    
    # Download complete scene
    granule = landsat.retrieve_granule(
        dataset=scenes.iloc[0]['dataset'],
        date_UTC=scenes.iloc[0]['date_UTC'],
        granule_ID=scenes.iloc[0]['display_ID'],
        entity_ID=scenes.iloc[0]['entity_ID']
    )
    
    # Work with downloaded files
    red_band = granule.DN(4)
```

## Troubleshooting

### S3 Backend Issues
- **STAC catalog connection failed**: Check internet connection
- **Band loading failed**: Verify scene ID format and band name
- **Import errors**: Install S3 dependencies with `pip install LandsatL2C2[s3]`

### M2M Backend Issues
- **Authentication failed**: Check USGS credentials in `M2M_credentials.py`
- **API unavailable**: USGS M2M API may be down for maintenance
- **Rate limit exceeded**: Wait before making more requests

### Auto Backend Issues
- **No backend available**: Both S3 and M2M backends failed
- **Check dependencies**: Ensure either S3 dependencies or M2M credentials are available

## Performance Tips

### For S3 Backend
- Use specific band requests instead of loading all bands
- Consider spatial subsets for large areas
- Cache frequently used data locally if needed

### For M2M Backend
- Use batch downloads for multiple scenes
- Clean up downloaded files to manage storage
- Consider using S3 backend for faster access

## Contributing

The backend system is designed to be extensible. To add a new backend:

1. Create a class that inherits from `LandsatBackend`
2. Implement all abstract methods
3. Add it to the `create_backend()` factory function
4. Add tests and documentation

See `backends.py` for examples of backend implementations.