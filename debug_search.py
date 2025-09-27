from LandsatL2C2 import LandsatL2C2
from sentinel_tiles import sentinel_tiles
import pystac_client

# Test the search directly
landsat = LandsatL2C2()
backend = landsat.backend

geometry = sentinel_tiles.grid("11SPS", 30)
print(f"Geometry type: {type(geometry)}")
print(f"Geometry: {geometry}")

# Test direct STAC search
catalog = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")

try:
    # Test without geometry first
    print("\nTesting search without geometry...")
    search = catalog.search(
        collections=["landsat-c2-l2"],
        datetime="2022-01-01/2022-01-31",
        limit=5
    )
    items = list(search.items())
    print(f"Found {len(items)} items without geometry filter")
    
    if items:
        item = items[0]
        print(f"Sample: {item.id}, geometry: {item.geometry}")
    
    # Test with geometry
    print("\nTesting search with geometry...")
    if hasattr(geometry, '__geo_interface__'):
        geom_dict = geometry.__geo_interface__
    else:
        geom_dict = geometry
        
    print(f"Geometry dict: {geom_dict}")
    
    search = catalog.search(
        collections=["landsat-c2-l2"],
        datetime="2022-01-01/2022-01-31",
        intersects=geom_dict,
        limit=5
    )
    items = list(search.items())
    print(f"Found {len(items)} items with geometry filter")
    
except Exception as e:
    print(f"Error in direct search: {e}")