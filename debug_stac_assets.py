from LandsatL2C2 import LandsatL2C2
from sentinel_tiles import sentinel_tiles
import json

landsat = LandsatL2C2()

geometry = sentinel_tiles.grid("11SPS", 30)

search_results = landsat.scene_search(
    start="2022-01-01",
    end="2022-01-31",
    target_geometry=geometry,
    cloud_percent_max=20
)

# Get the first granule
first_granule = search_results.iloc[0]

print("First granule info:")
print(json.dumps({
    'dataset': first_granule["dataset"],
    'date_UTC': str(first_granule["date_UTC"]),
    'granule_ID': first_granule["granule_ID"],
    'entity_ID': first_granule["entity_ID"],
    'display_ID': first_granule["display_ID"]
}, indent=2))

# Try to access the backend directly to see what STAC data we have
backend = landsat.backend
if hasattr(backend, 'stac_catalog') and backend.stac_catalog:
    try:
        # Let's see if we can get the STAC item directly
        print("\nTrying to get STAC item...")
        search = backend.stac_catalog.search(
            ids=[first_granule["granule_ID"]],
            datetime="2022-01-01/2022-01-31"
        )
        items = list(search.get_items())
        if items:
            item = items[0]
            print(f"STAC Item ID: {item.id}")
            print("Available assets:")
            for asset_key, asset in item.assets.items():
                print(f"  {asset_key}: {asset.href}")
                if 'ST_B10' in asset_key or 'thermal' in asset_key.lower():
                    print(f"    *** This might be our thermal band: {asset.href}")
    except Exception as e:
        print(f"Error getting STAC item: {e}")