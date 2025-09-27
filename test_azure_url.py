import requests

url = "https://landsateuwest.blob.core.windows.net/landsat-c2/level-2/standard/oli-tirs/2022/038/036/LC09_L2SP_038036_20220101_20220123_02_T1/LC09_L2SP_038036_20220101_20220123_02_T1_ST_B10.TIF"

print(f"Testing Azure URL: {url}")

try:
    response = requests.head(url)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code != 200:
        print(f"Error response. Let's check if we need authentication...")
        
        # Try to get the response content to see the error
        response = requests.get(url, stream=True)
        print(f"GET Status Code: {response.status_code}")
        if response.status_code == 409:
            print("HTTP 409 - This usually means a conflict or authentication issue")
            print(f"Response text (first 500 chars): {response.text[:500]}")
        
except Exception as e:
    print(f"Error: {e}")

# Let's also check if Planetary Computer provides signed URLs
print("\n" + "="*60)
print("Checking if we need to use Planetary Computer signing...")

try:
    import planetary_computer
    signed_url = planetary_computer.sign(url)
    print(f"Signed URL: {signed_url}")
    
    # Test the signed URL
    response = requests.head(signed_url)
    print(f"Signed URL status: {response.status_code}")
    
except ImportError:
    print("planetary_computer not available - may need to install it")
except Exception as e:
    print(f"Error with planetary computer signing: {e}")