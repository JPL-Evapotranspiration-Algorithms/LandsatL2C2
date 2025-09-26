#!/usr/bin/env python3
"""
Test script to compare M2M API vs earthaccess functionality.
This script helps verify that the migration works correctly.
"""

import logging
from datetime import date
from shapely.geometry import box
from LandsatL2C2 import LandsatL2C2
import sys

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_search_comparison():
    """Test search functionality with both APIs."""
    print("=== Testing Search Functionality ===")
    
    # Test parameters
    start_date = date(2023, 6, 1)
    end_date = date(2023, 6, 2)
    # California test area
    test_geometry = box(-120.0, 35.0, -119.0, 36.0)
    
    # Test with earthaccess (default)
    print("\n--- Testing earthaccess (Default) ---")
    try:
        landsat_ea = LandsatL2C2()  # Now defaults to earthaccess with netrc
        
        scenes_ea = landsat_ea.scene_search(
            start=start_date,
            end=end_date,
            target_geometry=test_geometry,
            max_results=5
        )
        
        print(f"earthaccess found {len(scenes_ea)} scenes")
        if len(scenes_ea) > 0:
            print(f"Sample earthaccess scene: {scenes_ea.iloc[0]['display_ID']}")
            
    except Exception as e:
        print(f"earthaccess error: {e}")
        scenes_ea = None
    
    # Test with M2M API (legacy)
    print("\n--- Testing M2M API (Legacy) ---")
    try:
        landsat_m2m = LandsatL2C2(use_m2m_legacy=True)
        
        scenes_m2m = landsat_m2m.scene_search(
            start=start_date,
            end=end_date,
            target_geometry=test_geometry,
            max_results=5
        )
        
        print(f"M2M API found {len(scenes_m2m)} scenes")
        if len(scenes_m2m) > 0:
            print(f"Sample M2M scene: {scenes_m2m.iloc[0]['display_ID']}")
            
    except Exception as e:
        print(f"M2M API error: {e}")
        scenes_m2m = None
    
    # Compare results
    print(f"\n--- Comparison ---")
    if scenes_m2m is not None and scenes_ea is not None:
        print(f"M2M scenes: {len(scenes_m2m)}")
        print(f"earthaccess scenes: {len(scenes_ea)}")
        
        if len(scenes_m2m) > 0 and len(scenes_ea) > 0:
            print("Both APIs returned results!")
        elif len(scenes_ea) > 0:
            print("Only earthaccess returned results")
        elif len(scenes_m2m) > 0:
            print("Only M2M API returned results")
        else:
            print("Neither API returned results")
    else:
        print("Could not compare - one or both APIs failed")

def test_authentication():
    """Test different authentication methods."""
    print("\n=== Testing Authentication ===")
    
    auth_methods = [
        ("netrc", "Uses ~/.netrc file"),
        ("environment", "Uses EARTHDATA_USERNAME/EARTHDATA_PASSWORD env vars"),
        ("interactive", "Prompts for credentials")
    ]
    
    for method, description in auth_methods:
        print(f"\n--- Testing {method} authentication ---")
        print(f"Description: {description}")
        
        try:
            landsat = LandsatL2C2(
                earthaccess_auth_strategy=method  # earthaccess is now default
            )
            
            # Try a simple search to test auth
            scenes = landsat.scene_search(
                start=date(2023, 6, 1),
                end=date(2023, 6, 1),
                target_geometry=box(-120.0, 35.0, -119.0, 36.0),
                max_results=1
            )
            
            print(f"✓ {method} authentication successful")
            
        except Exception as e:
            print(f"✗ {method} authentication failed: {e}")

def test_download_small():
    """Test download functionality with a very small request."""
    print("\n=== Testing Download (Small Test) ===")
    
    try:
        landsat = LandsatL2C2()  # Uses earthaccess with netrc by default
        
        # Very small test area and time range
        downloads = landsat.download(
            start_date=date(2023, 6, 1),
            end_date=date(2023, 6, 1),
            target_geometry=box(-120.0, 35.0, -119.5, 35.5),
            max_results=1
        )
        
        print(f"Download test completed. Results: {len(downloads)} items")
        
        if len(downloads) > 0:
            successful_downloads = downloads[downloads['download'].notna()]
            print(f"Successful downloads: {len(successful_downloads)}")
            
    except Exception as e:
        print(f"Download test failed: {e}")

def main():
    """Main test function."""
    print("LandsatL2C2 earthaccess Migration Test")
    print("=====================================")
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "auth":
            test_authentication()
        elif test_type == "search":
            test_search_comparison()
        elif test_type == "download":
            test_download_small()
        else:
            print(f"Unknown test type: {test_type}")
            print("Usage: python test_earthaccess_migration.py [auth|search|download]")
            
    else:
        # Run all tests
        test_authentication()
        test_search_comparison()
        
        # Only run download test if user confirms
        response = input("\nRun download test? This will attempt to download data (y/N): ")
        if response.lower() in ['y', 'yes']:
            test_download_small()
        else:
            print("Skipping download test")
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()