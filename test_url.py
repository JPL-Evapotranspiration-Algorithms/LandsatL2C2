import requests

url = "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2022/038/036/LC09_L2SP_038036_20220101_20230503_02_T1/LC09_L2SP_038036_20220101_20230503_02_T1_ST_B10.TIF"

print(f"Testing URL: {url}")

try:
    response = requests.head(url)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code != 200:
        # Get the actual content to see what error we're getting
        response = requests.get(url)
        print(f"Response content (first 500 chars): {response.text[:500]}")
        
except Exception as e:
    print(f"Error: {e}")