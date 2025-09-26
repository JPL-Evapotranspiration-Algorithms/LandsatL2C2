# Migration Guide: M2M API to earthaccess

## Overview

This package now uses `earthaccess` as the **default** method for accessing Landsat data, with the traditional M2M API available as a legacy option. The `earthaccess` approach offers several advantages:

- **Simplified Authentication**: Uses NASA Earthdata Login with `.netrc` by default
- **Cloud-Native Access**: Direct access to cloud-hosted data
- **Better Performance**: Streaming capabilities and optimized downloads
- **Modern API**: More intuitive and well-documented interface
- **Future-Proof**: Actively maintained by NASA

## Usage

### Using earthaccess (Default)

```python
from LandsatL2C2 import LandsatL2C2
from datetime import date

# Initialize with earthaccess (default behavior)
landsat = LandsatL2C2()  # Uses earthaccess with netrc auth by default

# OR explicitly specify earthaccess options
landsat = LandsatL2C2(
    use_earthaccess=True,  # This is now the default
    earthaccess_auth_strategy="netrc"  # This is now the default
)

# Search for scenes (same API as before)
scenes = landsat.scene_search(
    start=date(2023, 6, 1),
    end=date(2023, 6, 30),
    target_geometry=your_geometry,
    max_results=10
)

# Download scenes (same API as before)
downloads = landsat.download(
    start_date=date(2023, 6, 1),
    end_date=date(2023, 6, 30),
    target_geometry=your_geometry
)
```

### Using M2M API (Legacy)

```python
from LandsatL2C2 import LandsatL2C2

# Initialize with legacy M2M API
landsat = LandsatL2C2(
    use_m2m_legacy=True  # Explicitly use legacy M2M
)

# Same API as before
scenes = landsat.scene_search(...)
downloads = landsat.download(...)
```

## Authentication

### earthaccess Authentication

earthaccess supports multiple authentication strategies:

1. **`.netrc` file** (default): Store credentials in `~/.netrc`
```python
landsat = LandsatL2C2()  # Uses netrc by default
# OR explicitly
landsat = LandsatL2C2(earthaccess_auth_strategy="netrc")
```

2. **Environment Variables**: Set `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD`
```python
landsat = LandsatL2C2(earthaccess_auth_strategy="environment")
```

3. **Interactive**: Prompts for username/password
```python
landsat = LandsatL2C2(earthaccess_auth_strategy="interactive")
```

### Setting up `.netrc` (Recommended)

Create a file `~/.netrc` with the following content:

```
machine urs.earthdata.nasa.gov
login your_username
password your_password
```

Then set appropriate permissions:
```bash
chmod 600 ~/.netrc
```

## Dataset Mapping

The M2M dataset names are automatically mapped to earthaccess collections:

| M2M Dataset | earthaccess Collection | Description |
|-------------|----------------------|-------------|
| `landsat_tm_c2_l2` | Surface Reflectance Collection 2 | Landsat 4-5 TM |
| `landsat_etm_c2_l2` | Surface Reflectance Collection 2 | Landsat 7 ETM+ |
| `landsat_ot_c2_l2` | Surface Reflectance Collection 2 | Landsat 8-9 OLI/TIRS |

## Migration Steps

1. **Install earthaccess** (now included by default):
```bash
pip install earthaccess
```

2. **Set up `.netrc` authentication** (recommended):
```bash
# Create ~/.netrc file with your NASA Earthdata credentials
echo "machine urs.earthdata.nasa.gov login YOUR_USERNAME password YOUR_PASSWORD" > ~/.netrc
chmod 600 ~/.netrc
```

3. **Update your code** (minimal changes needed):
```python
# Before (still works, but now uses earthaccess by default)
landsat = LandsatL2C2()

# After (same code, now uses earthaccess automatically)
landsat = LandsatL2C2()  # Now defaults to earthaccess with netrc auth

# If you need legacy M2M API
landsat = LandsatL2C2(use_m2m_legacy=True)
```

4. **Test your workflow** - the API remains the same, but now uses modern earthaccess by default

## Compatibility Notes

- All existing API methods work the same way
- Granule metadata structure may be slightly different
- Download directory structure is preserved
- Performance characteristics may differ (generally better with earthaccess)

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Ensure your NASA Earthdata credentials are correct
2. **No Data Found**: Some collections may have different availability in earthaccess vs M2M
3. **Network Issues**: earthaccess requires reliable internet connection

### Getting Help

If you encounter issues:
1. Check the earthaccess documentation: https://earthaccess.readthedocs.io/
2. Verify your NASA Earthdata account is active
3. Try the M2M API as a fallback by setting `use_earthaccess=False`

## Future Plans

- The M2M API support will be maintained for backward compatibility
- New features will be developed primarily for the earthaccess backend
- Performance optimizations will focus on the earthaccess implementation