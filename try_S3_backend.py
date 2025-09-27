from LandsatL2C2 import LandsatL2C2
from sentinel_tiles import sentinel_tiles

landsat = LandsatL2C2()

geometry = sentinel_tiles.grid("11SPS", 30)

search_results = landsat.scene_search(
    start="2022-01-01",
    end="2022-01-31",
    target_geometry=geometry,
    cloud_percent_max=20
)

print(search_results)

# Retrieve the first granule from the search results
first_granule = search_results.iloc[0]

# Download the granule as a wrapper object
granule = landsat.retrieve_granule(
    dataset=first_granule["dataset"],
    date_UTC=first_granule["date_UTC"],
    granule_ID=first_granule["granule_ID"],
    entity_ID=first_granule["entity_ID"]
)

print(granule)

ST = granule.ST

print(ST)
