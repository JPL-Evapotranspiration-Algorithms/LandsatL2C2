import pytest

# List of dependencies
dependencies = [
    "colored_logging",
    "dateutil",
    "geopandas",
    "matplotlib",
    "pandas",
    "pyproj",
    "rasterio",
    "rasters",
    "requests",
    "shapely"
]

# Generate individual test functions for each dependency
@pytest.mark.parametrize("dependency", dependencies)
def test_dependency_import(dependency):
    __import__(dependency)
