from LandsatL2C2 import LandsatL2C2
from sentinel_tiles import sentinel_tiles
import json

landsat = LandsatL2C2()
backend = landsat.backend

# Check what collections are available in the STAC catalog
try:
    collections = list(backend.stac_catalog.get_collections())
    print("Available collections:")
    for collection in collections:
        print(f"  {collection.id}: {collection.title}")
        
    print("\n" + "="*50)
    
    # Try searching for thermal products specifically
    geometry = sentinel_tiles.grid("11SPS", 30)
    
    # Test different collection combinations
    test_collections = [
        ["landsat-c2l2-sr"],
        ["landsat-c2l2-st"], 
        ["landsat-c2l2-sr", "landsat-c2l2-st"],
        ["landsat-c2-l2"],
    ]
    
    for collections in test_collections:
        print(f"\nTesting collections: {collections}")
        try:
            search_params = {
                "collections": collections,
                "datetime": "2022-01-01/2022-01-01",
                "limit": 5
            }
            # Skip geometry for now to avoid format issues
            # if geometry:
            #     search_params["intersects"] = geometry
                
            search = backend.stac_catalog.search(**search_params)
            items = list(search.items())
            print(f"  Found {len(items)} items")
            
            if items:
                item = items[0]
                print(f"  Sample item: {item.id}")
                print(f"  Collection: {item.collection_id}")
                print(f"  Assets: {list(item.assets.keys())}")
                
                # Look for thermal-related assets
                thermal_assets = [key for key in item.assets.keys() if 'thermal' in key.lower() or 'lwir' in key.lower() or 'st_' in key.lower()]
                if thermal_assets:
                    print(f"  Thermal assets found: {thermal_assets}")
                else:
                    print("  No thermal assets found")
        except Exception as e:
            print(f"  Error searching: {e}")
            
except Exception as e:
    print(f"Error accessing STAC catalog: {e}")