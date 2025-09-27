import boto3
from botocore import UNSIGNED
from botocore.config import Config

# Create anonymous S3 client
s3_client = boto3.client('s3', config=Config(signature_version=UNSIGNED))
bucket = 'usgs-landsat'

# Test scene ID from our error
scene_id = "LC09_L2SP_038036_20220101_20230503_02_T1_SR"

# Try different path patterns
test_paths = [
    "collection02/level-2/standard/oli-tirs/2022/038/036/",
    "collection02/level-2/standard/oli-tirs/2022/038/036/" + scene_id + "/",
    "collection02/level-2/standard/oli-tirs/2022/038/036/" + scene_id,
    "collection02/level-2/standard/oli-tirs/038/036/2022/",
    "collection02/level-2/standard/oli-tirs/038/036/2022/" + scene_id + "/",
]

for path in test_paths:
    try:
        print(f"\nTesting path: {path}")
        result = s3_client.list_objects_v2(Bucket=bucket, Prefix=path, MaxKeys=10)
        if 'Contents' in result:
            print(f"  Found {len(result['Contents'])} objects:")
            for obj in result['Contents'][:5]:  # Show first 5
                print(f"    {obj['Key']}")
            if len(result['Contents']) > 5:
                print(f"    ... and {len(result['Contents']) - 5} more")
        else:
            print("  No objects found")
    except Exception as e:
        print(f"  Error: {e}")