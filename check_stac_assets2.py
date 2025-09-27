from pystac_client import Client
import planetary_computer

# Connect to Microsoft Planetary Computer STAC
catalog = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")

# Search for Landsat scenes in our area and date range to see what IDs are available
search = catalog.search(
    collections=["landsat-c2-l2"],
    datetime="2022-01-01/2022-01-02",
    bbox=[-116, 32, -115, 33],
    limit=1
)

items = list(search.items())
if items:
    item = items[0]
    print(f"Found item ID: {item.id}")
    print("Available STAC assets:")
    for asset_name, asset in item.assets.items():
        print(f"  {asset_name}: {asset.href}")
        
    # Look specifically for MTL-related assets
    print("\nLooking for metadata assets:")
    for asset_name, asset in item.assets.items():
        if 'mtl' in asset_name.lower() or 'metadata' in asset_name.lower():
            print(f"  METADATA: {asset_name}: {asset.href}")
else:
    print("No items found")