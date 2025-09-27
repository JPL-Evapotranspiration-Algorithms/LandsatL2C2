#!/usr/bin/env python3
"""
Example usage of LandsatL2C2 with both S3 and M2M backends

This script demonstrates how to use the LandsatL2C2 package with:
1. S3 backend (anonymous access, no credentials required)
2. M2M backend (requires USGS credentials)
"""

from datetime import date
from shapely.geometry import Point
from LandsatL2C2 import LandsatL2C2

def example_s3_backend():
    """Example using S3 backend (no credentials required)"""
    print("=== S3 Backend Example ===")
    
    # Create LandsatL2C2 instance with S3 backend
    landsat = LandsatL2C2(backend="s3")
    
    # Define search parameters
    start_date = date(2023, 6, 1)
    end_date = date(2023, 6, 30)
    location = Point(-118.2437, 34.0522)  # Los Angeles
    
    try:
        # Search for scenes
        print(f"Searching for scenes near LA from {start_date} to {end_date}")
        scenes = landsat.scene_search(
            start=start_date,
            end=end_date,
            target_geometry=location,
            cloud_percent_max=20,
            max_results=5
        )
        
        print(f"Found {len(scenes)} scenes")
        if not scenes.empty:
            print(scenes[['date_UTC', 'display_ID', 'cloud']].head())
            
            # Retrieve a granule (S3 access)
            scene_id = scenes.iloc[0]['display_ID']
            granule = landsat.retrieve_granule(
                dataset=scenes.iloc[0]['dataset'],
                date_UTC=scenes.iloc[0]['date_UTC'],
                granule_ID=scene_id,
                entity_ID=scene_id
            )
            
            if granule:
                print(f"Retrieved granule: {scene_id}")
                # Load a band from S3 
                try:
                    red_band = granule.DN(4)  # Band 4 (red)
                    print(f"Loaded red band with shape: {red_band.shape}")
                except Exception as e:
                    print(f"Band loading failed: {e}")
    
    except Exception as e:
        print(f"S3 backend example failed: {e}")


def example_m2m_backend():
    """Example using M2M backend (requires credentials)"""
    print("\n=== M2M Backend Example ===")
    
    try:
        # Create LandsatL2C2 instance with M2M backend
        # This will use credentials from M2M_credentials.py
        landsat = LandsatL2C2(backend="m2m")
        
        # Use context manager for automatic login/logout
        with landsat:
            # Define search parameters
            start_date = date(2023, 6, 1)
            end_date = date(2023, 6, 30)
            location = Point(-118.2437, 34.0522)  # Los Angeles
            
            # Search for scenes
            print(f"Searching for scenes near LA from {start_date} to {end_date}")
            scenes = landsat.scene_search(
                start=start_date,
                end=end_date,
                target_geometry=location,
                cloud_percent_max=20,
                max_results=5
            )
            
            print(f"Found {len(scenes)} scenes")
            if not scenes.empty:
                print(scenes[['date_UTC', 'display_ID', 'cloud']].head())
    
    except Exception as e:
        print(f"M2M backend example failed: {e}")
        print("Note: M2M backend requires valid USGS credentials")


def example_auto_backend():
    """Example using auto backend selection"""
    print("\n=== Auto Backend Example ===")
    
    # Create LandsatL2C2 instance with auto backend selection
    # This will try S3 first, then fall back to M2M if S3 fails
    landsat = LandsatL2C2(backend="auto")
    
    print(f"Selected backend type: {landsat._backend_type}")
    
    # Define search parameters
    start_date = date(2023, 6, 1)
    end_date = date(2023, 6, 30)
    tiles = ["034033"]  # WRS2 tile covering Los Angeles
    
    try:
        # Search for scenes
        print(f"Searching for scenes in tile {tiles[0]} from {start_date} to {end_date}")
        scenes = landsat.scene_search(
            start=start_date,
            end=end_date,
            tiles=tiles,
            cloud_percent_max=50,
            max_results=3
        )
        
        print(f"Found {len(scenes)} scenes")
        if not scenes.empty:
            print(scenes[['date_UTC', 'display_ID', 'cloud', 'sensor']].head())
    
    except Exception as e:
        print(f"Auto backend example failed: {e}")


if __name__ == "__main__":
    # Run examples
    example_s3_backend()
    example_m2m_backend()
    example_auto_backend()
    
    print("\n=== Backend Comparison ===")
    print("S3 Backend:")
    print("  + No credentials required (anonymous access)")
    print("  + Direct access to Cloud Optimized GeoTIFFs")
    print("  + Fast partial data reads")
    print("  + No download required")
    print("  - Requires internet connection")
    print("  - Limited to Collection 2 data")
    
    print("\nM2M Backend:")
    print("  + Full USGS Earth Explorer functionality")
    print("  + Access to all available datasets")
    print("  + Can download complete scenes")
    print("  + Works offline after download")
    print("  - Requires USGS account and credentials")
    print("  - Downloads can be large and slow")
    print("  - Subject to API rate limits")