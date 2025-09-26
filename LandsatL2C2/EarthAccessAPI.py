"""
This module handles searching and downloading Landsat data using NASA's earthaccess library.

Developed by Gregory Halverson at the Jet Propulsion Laboratory.
"""
import logging
import os
from datetime import datetime, date
from os.path import join, dirname, expanduser, splitext, exists, abspath
from typing import List, Union, Optional
from pathlib import Path

import earthaccess
import geopandas as gpd
import pandas as pd
from dateutil import parser
from shapely.geometry import Point, Polygon, shape

import colored_logging
from rasters import RasterGrid

logger = logging.getLogger(__name__)


class EarthAccessUnavailableError(Exception):
    pass


class EarthAccessAPI:
    """
    Earth Access API client for NASA Earthdata using earthaccess library.
    This replaces the M2M API functionality with modern NASA Earthdata access.
    """
    
    logger = logging.getLogger(__name__)

    # Landsat Collection 2 concept IDs in NASA CMR
    _LANDSAT_COLLECTION_2_CONCEPT_IDS = {
        "surface_reflectance": "C3442503899-USGS_EROS",
        "surface_temperature": "C3442506077-USGS_EROS",
        "hls_landsat": "HLSL30"  # HLS uses short_name instead of concept_id
    }
    
    # Map old M2M dataset names to new earthaccess collections
    _M2M_TO_EARTHACCESS_MAPPING = {
        "landsat_tm_c2_l2": "surface_reflectance",
        "landsat_etm_c2_l2": "surface_reflectance", 
        "landsat_ot_c2_l2": "surface_reflectance"
    }
    
    _DEFAULT_DOWNLOAD_DIRECTORY = "earthaccess_download"

    def __init__(
            self,
            download_directory: str = None,
            authentication_strategy: str = "interactive"):
        """
        Initialize EarthAccess API client.
        
        Args:
            download_directory: Directory for downloaded files
            authentication_strategy: How to authenticate ('interactive', 'netrc', 'environment')
        """
        
        if download_directory is None:
            download_directory = self._DEFAULT_DOWNLOAD_DIRECTORY

        self.download_directory = expanduser(download_directory)
        self.authentication_strategy = authentication_strategy
        self._authenticated = False

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, type, value, tb):
        # earthaccess doesn't require explicit logout
        pass

    def login(self):
        """Authenticate with NASA Earthdata Login."""
        try:
            if self.authentication_strategy == "interactive":
                earthaccess.login()
            elif self.authentication_strategy == "netrc":
                earthaccess.login(strategy="netrc")
            elif self.authentication_strategy == "environment":
                earthaccess.login(strategy="environment")
            else:
                earthaccess.login()  # Default to interactive
                
            self._authenticated = earthaccess.__auth__.authenticated
            if not self._authenticated:
                raise EarthAccessUnavailableError("Failed to authenticate with NASA Earthdata")
                
        except Exception as e:
            raise EarthAccessUnavailableError(f"Authentication failed: {e}")

    def _map_m2m_dataset(self, dataset_name: str) -> dict:
        """
        Map M2M dataset names to earthaccess parameters.
        
        Args:
            dataset_name: M2M dataset name (e.g., 'landsat_tm_c2_l2')
            
        Returns:
            dict with search parameters for earthaccess
        """
        if dataset_name in self._M2M_TO_EARTHACCESS_MAPPING:
            collection_type = self._M2M_TO_EARTHACCESS_MAPPING[dataset_name]
            
            if collection_type == "surface_reflectance":
                return {
                    "concept_id": self._LANDSAT_COLLECTION_2_CONCEPT_IDS["surface_reflectance"]
                }
            elif collection_type == "surface_temperature":
                return {
                    "concept_id": self._LANDSAT_COLLECTION_2_CONCEPT_IDS["surface_temperature"]
                }
            elif collection_type == "hls_landsat":
                return {
                    "short_name": self._LANDSAT_COLLECTION_2_CONCEPT_IDS["hls_landsat"]
                }
        
        # If no mapping found, try to use as concept_id or short_name directly
        return {"short_name": dataset_name}

    def scene_search(
            self,
            start_date: Union[date, datetime, str],
            target_geometry: Union[Point, Polygon, RasterGrid],
            datasets: Union[str, list],
            end_date: Union[date, datetime, str] = None,
            max_results: int = None,
            cloud_percent_min: float = 0,
            cloud_percent_max: float = 100,
            ascending: bool = True) -> gpd.GeoDataFrame:
        """
        Search for Landsat scenes using earthaccess.
        
        Args:
            start_date: Start date for temporal filter
            target_geometry: Spatial geometry for search
            datasets: Dataset name(s) to search
            end_date: End date for temporal filter
            max_results: Maximum number of results
            cloud_percent_min: Minimum cloud cover percentage
            cloud_percent_max: Maximum cloud cover percentage
            ascending: Sort order
            
        Returns:
            GeoDataFrame with search results
        """
        if not self._authenticated:
            self.login()
            
        if isinstance(start_date, str):
            start_date = parser.parse(start_date).date()

        if end_date is None:
            end_date = start_date
        elif isinstance(end_date, str):
            end_date = parser.parse(end_date).date()

        if isinstance(datasets, str):
            datasets = [datasets]

        # Convert geometry to bounding box for earthaccess
        if isinstance(target_geometry, Point):
            lon, lat = target_geometry.x, target_geometry.y
            bounding_box = (lon, lat, lon, lat)
        elif isinstance(target_geometry, Polygon):
            bounds = target_geometry.bounds
            bounding_box = (bounds[0], bounds[1], bounds[2], bounds[3])  # (west, south, east, north)
        elif isinstance(target_geometry, RasterGrid):
            x_min, y_min, x_max, y_max = target_geometry.bbox_latlon
            bounding_box = (x_min, y_min, x_max, y_max)
        else:
            raise ValueError("Unsupported geometry type for earthaccess search")

        results_list = []

        for dataset in datasets:
            self.logger.info(f"Searching dataset {colored_logging.val(dataset)} from {start_date} to {end_date}")
            
            # Map M2M dataset name to earthaccess parameters
            search_params = self._map_m2m_dataset(dataset)
            
            # Build search parameters
            search_kwargs = {
                **search_params,
                "temporal": (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")),
                "bounding_box": bounding_box,
                "count": max_results if max_results else -1
            }
            
            # Add cloud cover filter if supported
            if cloud_percent_max < 100 or cloud_percent_min > 0:
                search_kwargs["cloud_cover"] = (cloud_percent_min, cloud_percent_max)

            try:
                granules = earthaccess.search_data(**search_kwargs)
                self.logger.info(f"Found {len(granules)} granules")
                
                # Convert earthaccess results to pandas DataFrame
                for granule in granules:
                    umm = granule.get('umm', {})
                    granule_ur = umm.get('GranuleUR', '')
                    
                    # Extract date from granule ID or temporal extent
                    temporal_extent = umm.get('TemporalExtent', {})
                    if temporal_extent:
                        range_dt = temporal_extent.get('RangeDateTime', {})
                        begin_time = range_dt.get('BeginningDateTime', '')
                        if begin_time:
                            date_utc = parser.parse(begin_time).date()
                        else:
                            date_utc = start_date
                    else:
                        date_utc = start_date
                    
                    # Extract spatial geometry
                    spatial_extent = umm.get('SpatialExtent', {})
                    geometry = None
                    if spatial_extent:
                        horizontal = spatial_extent.get('HorizontalSpatialDomain', {})
                        geom_data = horizontal.get('Geometry', {})
                        if geom_data:
                            # Try to create geometry from CMR spatial data
                            try:
                                geometry = shape(geom_data)
                            except:
                                geometry = target_geometry  # Fallback to search geometry
                        
                    if geometry is None:
                        geometry = target_geometry
                    
                    # Extract sensor information from granule ID
                    sensor = self._extract_sensor_from_granule_id(granule_ur)
                    
                    # Extract cloud cover if available
                    cloud_cover = 0  # Default, as earthaccess may not always provide this
                    
                    result_row = {
                        "date_UTC": date_utc,
                        "display_ID": granule_ur,
                        "entity_ID": granule_ur,  # Use granule_ur as entity_id
                        "cloud": cloud_cover,
                        "dataset": dataset,
                        "sensor": sensor,
                        "granule_ID": granule_ur,
                        "geometry": geometry,
                        "_earthaccess_granule": granule  # Store original granule for download
                    }
                    
                    results_list.append(result_row)
                    
            except Exception as e:
                self.logger.warning(f"Failed to search dataset {dataset}: {e}")
                continue

        if not results_list:
            raise Exception("No scenes found")

        # Create GeoDataFrame
        df = pd.DataFrame(results_list)
        gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
        
        # Sort results
        if 'date_UTC' in gdf.columns:
            gdf = gdf.sort_values(by=["date_UTC", "display_ID"], ascending=ascending)
            
        return gdf

    def _extract_sensor_from_granule_id(self, granule_id: str) -> str:
        """Extract sensor type from granule ID."""
        if 'L30' in granule_id:  # HLS Landsat
            return 'LC08'  # Default to Landsat 8 for HLS
        elif 'LC08' in granule_id:
            return 'LC08'
        elif 'LC09' in granule_id:
            return 'LC09'
        elif 'LE07' in granule_id:
            return 'LE07'
        elif 'LT05' in granule_id:
            return 'LT05'
        elif 'LT04' in granule_id:
            return 'LT04'
        else:
            return 'Unknown'

    def retrieve_granule(
            self,
            dataset: str,
            date_UTC: Union[date, str],
            granule_ID: str,
            entity_ID: str,
            bands: List[str] = None) -> Optional[str]:
        """
        Download a granule using earthaccess.
        
        Args:
            dataset: Dataset name
            date_UTC: Date of granule
            granule_ID: Granule identifier
            entity_ID: Entity identifier (same as granule_ID for earthaccess)
            bands: List of bands to download (not used in earthaccess)
            
        Returns:
            Path to downloaded granule directory or file
        """
        if not self._authenticated:
            self.login()

        try:
            # Search for the specific granule
            search_params = self._map_m2m_dataset(dataset)
            
            granules = earthaccess.search_data(
                granule_name=granule_ID,
                count=1,
                **search_params
            )
            
            if not granules:
                self.logger.warning(f"Granule {granule_ID} not found")
                return None
                
            granule = granules[0]
            
            # Create download directory
            if isinstance(date_UTC, str):
                date_UTC = parser.parse(date_UTC).date()
                
            download_dir = join(self.download_directory, f"{date_UTC:%Y-%m-%d}")
            os.makedirs(download_dir, exist_ok=True)
            
            # Download granule
            self.logger.info(f"Downloading granule: {granule_ID}")
            downloaded_files = earthaccess.download(granule, local_path=download_dir)
            
            if downloaded_files:
                # Return the directory containing the downloaded files
                return download_dir
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to download granule {granule_ID}: {e}")
            return None

    def download(
            self,
            start: Union[date, datetime, str],
            end: Union[date, datetime, str],
            geometry: Union[Point, Polygon, RasterGrid],
            datasets: Union[str, list] = None,
            sensors: Union[List[str], str] = None,
            bands: Union[List[str], str] = None,
            max_results: int = None,
            cloud_percent_min: float = 0,
            cloud_percent_max: float = 100) -> pd.DataFrame:
        """
        Search and download Landsat data using earthaccess.
        
        Args:
            start: Start date
            end: End date
            geometry: Target geometry
            datasets: Dataset names
            sensors: Sensor names (for filtering)
            bands: Band names (not used in earthaccess)
            max_results: Maximum results
            cloud_percent_min: Minimum cloud cover
            cloud_percent_max: Maximum cloud cover
            
        Returns:
            DataFrame with download results
        """
        self.logger.info(
            "Searching scenes with earthaccess" +
            f" from {colored_logging.time(f'{start:%Y-%m-%d}' if hasattr(start, 'strftime') else str(start))}" +
            f" to {colored_logging.time(f'{end:%Y-%m-%d}' if hasattr(end, 'strftime') else str(end))}"
        )

        # Use default datasets if none provided
        if datasets is None:
            datasets = ["surface_reflectance"]  # Default to surface reflectance

        scenes = self.scene_search(
            start_date=start,
            end_date=end,
            target_geometry=geometry,
            datasets=datasets,
            max_results=max_results,
            cloud_percent_min=cloud_percent_min,
            cloud_percent_max=cloud_percent_max
        )

        self.logger.info(f"Found {len(scenes)} scenes")

        downloads = []

        for i, scene in scenes.iterrows():
            granule_ID = scene.granule_ID
            
            try:
                # Use earthaccess to download directly from the stored granule object
                if '_earthaccess_granule' in scene:
                    granule = scene['_earthaccess_granule']
                    
                    # Create download directory
                    date_UTC = scene.date_UTC
                    download_dir = join(self.download_directory, f"{date_UTC:%Y-%m-%d}")
                    os.makedirs(download_dir, exist_ok=True)
                    
                    self.logger.info(f"Downloading granule: {granule_ID}")
                    downloaded_files = earthaccess.download(granule, local_path=download_dir)
                    
                    if downloaded_files:
                        download = download_dir
                    else:
                        download = None
                        self.logger.warning(f"Failed to download granule: {granule_ID}")
                else:
                    download = None
                    self.logger.warning(f"No earthaccess granule object for: {granule_ID}")
                    
            except Exception as e:
                download = None
                self.logger.exception(e)
                self.logger.warning(f"Failed to download granule: {granule_ID}")

            downloads.append(download)

        scenes["download"] = downloads
        return scenes