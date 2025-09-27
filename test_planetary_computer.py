import pystac_client

# Try Microsoft Planetary Computer STAC catalog
try:
    catalog = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    print("Microsoft Planetary Computer collections:")
    
    collections = list(catalog.get_collections())
    landsat_collections = [c for c in collections if 'landsat' in c.id.lower()]
    
    for collection in landsat_collections:
        print(f"  {collection.id}: {collection.title}")
    
    print("\n" + "="*60)
    
    # Test search for thermal data
    if landsat_collections:
        print("Testing search for thermal data...")
        
        # Try different collection IDs
        test_collections = ['landsat-c2-l2']
        
        for collection_id in test_collections:
            print(f"\nTesting collection: {collection_id}")
            try:
                search = catalog.search(
                    collections=[collection_id],
                    datetime="2022-01-01/2022-01-01",
                    limit=2
                )
                items = list(search.items())
                print(f"  Found {len(items)} items")
                
                if items:
                    item = items[0]
                    print(f"  Sample item: {item.id}")
                    print(f"  Assets: {list(item.assets.keys())}")
                    
                    # Check if any assets look like thermal bands
                    thermal_assets = [key for key in item.assets.keys() if any(term in key.lower() for term in ['thermal', 'lwir', 'st_', 'temp'])]
                    if thermal_assets:
                        print(f"  Thermal-like assets: {thermal_assets}")
                        # Show URL of first thermal asset
                        thermal_asset = item.assets[thermal_assets[0]]
                        print(f"  Sample thermal URL: {thermal_asset.href}")
                    else:
                        print("  No thermal assets found")
                        
            except Exception as e:
                print(f"  Error: {e}")
                
except Exception as e:
    print(f"Error connecting to Planetary Computer: {e}")