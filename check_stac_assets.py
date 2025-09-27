from pystac_client import Client
import planetary_computer

# Connect to Microsoft Planetary Computer STAC
catalog = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")

# Search for a specific Landsat scene
search = catalog.search(
    collections=["landsat-c2-l2"],
    ids=["LC09_L2SP_038036_20220101_20220123_02_T1"]
)

items = list(search.items())
if items:
    item = items[0]
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