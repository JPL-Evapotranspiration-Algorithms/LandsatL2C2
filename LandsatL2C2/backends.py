"""
Backend interfaces for Landsat data access.

This module provides both M2M API and S3 anonymous backends for Landsat Collection 2 data.
"""

import logging
import json
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Union, Optional, Dict, Any
from urllib.parse import urljoin

# Standard library imports
import pandas as pd
import geopandas as gpd
from dateutil import parser
from shapely.geometry import Point, Polygon, shape

# Optional imports for S3 backend
try:
    import boto3
    import pystac_client
    import rasterio
    from botocore import UNSIGNED
    from botocore.config import Config
    from rasterio.session import AWSSession
    HAS_S3_DEPS = True
except ImportError:
    HAS_S3_DEPS = False
    boto3 = None
    pystac_client = None
    rasterio = None

from .EEAPI import EEAPI

logger = logging.getLogger(__name__)


class LandsatBackend(ABC):
    """Abstract base class for Landsat data backends"""
    
    @abstractmethod
    def scene_search(
        self,
        start_date: Union[date, datetime, str],
        end_date: Union[date, datetime, str] = None,
        target_geometry: Union[Point, Polygon] = None,
        cloud_percent_max: float = 100,
        collections: List[str] = None,
        max_results: int = None
    ) -> pd.DataFrame:
        """Search for Landsat scenes"""
        pass
    
    @abstractmethod
    def download_options(self, scene_ids: List[str]) -> Dict[str, Any]:
        """Get download options for scenes"""
        pass
    
    @abstractmethod
    def download_granule(self, scene_id: str, download_directory: str) -> str:
        """Download a complete granule"""
        pass
    
    @abstractmethod
    def get_band_data(self, scene_id: str, band_name: str) -> Any:
        """Get band data (either file path or rasterio dataset)"""
        pass


class M2MBackend(LandsatBackend):
    """M2M API backend using EEAPI"""
    
    def __init__(self, username: str = None, password: str = None, **kwargs):
        # Store credentials but don't initialize EEAPI until needed
        self.username = username
        self.password = password
        self.kwargs = kwargs
        self.eeapi = None
        self._logged_in = False
    
    def _ensure_eeapi(self):
        """Initialize EEAPI if not already done"""
        if self.eeapi is None:
            # If no credentials provided, get them now (not during __init__)
            username = self.username
            password = self.password
            
            if username is None or password is None:
                from .M2M_credentials import get_M2M_credentials
                credentials = get_M2M_credentials()
                username = credentials["username"]
                password = credentials["password"]
            
            self.eeapi = EEAPI(username=username, password=password, **self.kwargs)
    
    def __enter__(self):
        self.login()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logout()
    
    def login(self):
        """Login to M2M API"""
        if not self._logged_in:
            self._ensure_eeapi()
            self.eeapi.login()
            self._logged_in = True
    
    def logout(self):
        """Logout from M2M API"""
        if self._logged_in and self.eeapi:
            self.eeapi.logout()
            self._logged_in = False
    
    def scene_search(
        self,
        start_date: Union[date, datetime, str],
        end_date: Union[date, datetime, str] = None,
        target_geometry: Union[Point, Polygon] = None,
        cloud_percent_max: float = 100,
        collections: List[str] = None,
        max_results: int = None
    ) -> pd.DataFrame:
        """Search using M2M API"""
        
        if not self._logged_in:
            self.login()
        
        # Convert collections to M2M dataset names
        if collections is None:
            datasets = ["landsat_tm_c2_l2", "landsat_etm_c2_l2", "landsat_ot_c2_l2"]
        else:
            # Map STAC collection names to M2M dataset names
            collection_mapping = {
                "landsat-c2l2-sr": ["landsat_tm_c2_l2", "landsat_etm_c2_l2", "landsat_ot_c2_l2"],
                "landsat-c2l2-st": ["landsat_tm_c2_l2", "landsat_etm_c2_l2", "landsat_ot_c2_l2"]
            }
            datasets = []
            for collection in collections:
                if collection in collection_mapping:
                    datasets.extend(collection_mapping[collection])
                else:
                    datasets.append(collection)
        
        results = []
        for dataset in datasets:
            try:
                df = self.eeapi.scene_search(
                    start=start_date,
                    end=end_date,
                    dataset=dataset,
                    target_geometry=target_geometry,
                    cloud_percent_max=cloud_percent_max,
                    max_results=max_results
                )
                if not df.empty:
                    results.append(df)
            except Exception as e:
                logger.warning(f"Search failed for dataset {dataset}: {e}")
        
        if results:
            return pd.concat(results, ignore_index=True)
        else:
            return pd.DataFrame()
    
    def download_options(self, scene_ids: List[str]) -> Dict[str, Any]:
        """Get download options using M2M API"""
        if not self._logged_in:
            self.login()
        return self.eeapi.download_options(scene_ids)
    
    def download_granule(self, scene_id: str, download_directory: str) -> str:
        """Download granule using M2M API"""
        if not self._logged_in:
            self.login()
        return self.eeapi.download_granule(scene_id, download_directory)
    
    def get_band_data(self, scene_id: str, band_name: str) -> str:
        """Get local file path for band (assumes already downloaded)"""
        # This would return the local file path after download
        # Implementation depends on how files are organized locally
        raise NotImplementedError("M2M backend requires local file access implementation")


class S3Backend(LandsatBackend):
    """S3 anonymous access backend for Landsat Collection 2"""
    
    def __init__(self):
        if not HAS_S3_DEPS:
            raise ImportError(
                "S3 backend requires additional dependencies. Install with: "
                "pip install LandsatL2C2[s3]"
            )
        
        # Anonymous S3 client
        self.s3_client = boto3.client('s3', config=Config(signature_version=UNSIGNED))
        self.bucket = 'usgs-landsat'
        
        # STAC catalog for metadata search
        try:
            self.stac_catalog = pystac_client.Client.open(
                "https://landsatlook.usgs.gov/stac-server"
            )
        except Exception as e:
            logger.warning(f"Could not connect to STAC catalog: {e}")
            # Fallback to Microsoft Planetary Computer
            try:
                self.stac_catalog = pystac_client.Client.open(
                    "https://planetarycomputer.microsoft.com/api/stac/v1"
                )
            except Exception as e2:
                logger.error(f"Could not connect to any STAC catalog: {e2}")
                self.stac_catalog = None
        
        # AWS session for rasterio
        self.aws_session = AWSSession(boto3.Session(), requester_pays=False)
    
    def scene_search(
        self,
        start_date: Union[date, datetime, str],
        end_date: Union[date, datetime, str] = None,
        target_geometry: Union[Point, Polygon] = None,
        cloud_percent_max: float = 100,
        collections: List[str] = None,
        max_results: int = None
    ) -> pd.DataFrame:
        """Search using STAC catalog"""
        
        if self.stac_catalog is None:
            raise RuntimeError("No STAC catalog available for search")
        
        # Parse dates
        if isinstance(start_date, str):
            start_date = parser.parse(start_date).date()
        if end_date is None:
            end_date = start_date
        if isinstance(end_date, str):
            end_date = parser.parse(end_date).date()
        
        # Default to Landsat Collection 2
        if collections is None:
            collections = ["landsat-c2l2-sr"]
        
        # Build search parameters
        search_params = {
            "collections": collections,
            "datetime": f"{start_date}/{end_date}",
            "limit": max_results or 1000
        }
        
        # Add spatial filter if provided
        if target_geometry is not None:
            if isinstance(target_geometry, (Point, Polygon)):
                search_params["intersects"] = target_geometry
        
        try:
            # Search STAC catalog
            search = self.stac_catalog.search(**search_params)
            items = list(search.get_items())
            
            # Convert to DataFrame
            results = []
            for item in items:
                # Extract cloud cover from properties
                cloud_cover = item.properties.get('eo:cloud_cover', 0)
                
                if cloud_cover <= cloud_percent_max:
                    results.append({
                        'date_UTC': parser.parse(item.datetime).date(),
                        'display_ID': item.id,
                        'entity_ID': item.id,
                        'cloud': cloud_cover,
                        'dataset': item.collection_id,
                        'granule_ID': item.id,
                        'geometry': item.geometry,
                        'assets': item.assets
                    })
            
            if not results:
                return pd.DataFrame()
            
            df = pd.DataFrame(results)
            
            # Convert geometry column to proper GeoDataFrame
            geometries = []
            for geom in df['geometry']:
                if isinstance(geom, dict):
                    geometries.append(shape(geom))
                else:
                    geometries.append(geom)
            
            df = gpd.GeoDataFrame(
                df.drop('geometry', axis=1), 
                geometry=geometries, 
                crs="EPSG:4326"
            )
            
            return df.sort_values(['date_UTC', 'display_ID'])
            
        except Exception as e:
            logger.error(f"STAC search failed: {e}")
            return pd.DataFrame()
    
    def download_options(self, scene_ids: List[str]) -> Dict[str, Any]:
        """Get S3 URLs for scenes (no actual download needed)"""
        options = {}
        for scene_id in scene_ids:
            options[scene_id] = {
                'available': True,
                'access_method': 's3_anonymous',
                'base_url': f"https://{self.bucket}.s3.amazonaws.com/"
            }
        return options
    
    def download_granule(self, scene_id: str, download_directory: str) -> str:
        """For S3 backend, return S3 path (no actual download)"""
        # Return the S3 path pattern for the scene
        return self._get_s3_scene_path(scene_id)
    
    def get_band_data(self, scene_id: str, band_name: str):
        """Get band data as rasterio dataset from S3"""
        url = self.get_band_url(scene_id, band_name)
        
        # Use rasterio with AWS session for anonymous access
        with rasterio.Env(self.aws_session):
            return rasterio.open(url)
    
    def get_band_url(self, scene_id: str, band_name: str) -> str:
        """Get S3 URL for a specific band"""
        s3_path = self._get_s3_band_path(scene_id, band_name)
        return f"https://{self.bucket}.s3.amazonaws.com/{s3_path}"
    
    def _get_s3_scene_path(self, scene_id: str) -> str:
        """Get S3 path for a scene directory"""
        parts = scene_id.split('_')
        if len(parts) < 4:
            raise ValueError(f"Invalid scene ID format: {scene_id}")
        
        sensor = parts[0]
        pathrow = parts[2]
        date_str = parts[3]
        
        # Convert date
        date_obj = parser.parse(date_str)
        year = date_obj.year
        path = pathrow[:3]
        row = pathrow[3:]
        
        # Build S3 path
        return f"collection02/level-2/standard/oli-tirs/{year}/{path}/{row}/{scene_id}/"
    
    def _get_s3_band_path(self, scene_id: str, band_name: str) -> str:
        """Get S3 path for a specific band file"""
        scene_path = self._get_s3_scene_path(scene_id)
        return f"{scene_path}{scene_id}_{band_name}.TIF"
    
    def list_scene_bands(self, scene_id: str) -> List[str]:
        """List available bands for a scene"""
        # Common Landsat Collection 2 bands
        return [
            'SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7',
            'ST_B10', 'QA_PIXEL', 'QA_RADSAT', 'SR_QA_AEROSOL'
        ]


def create_backend(backend_type: str = "auto", **kwargs) -> LandsatBackend:
    """
    Factory function to create the appropriate backend
    
    Args:
        backend_type: "m2m", "s3", or "auto"
        **kwargs: Backend-specific arguments
    
    Returns:
        Configured backend instance
    """
    
    if backend_type == "m2m":
        return M2MBackend(**kwargs)
    elif backend_type == "s3":
        if not HAS_S3_DEPS:
            raise ImportError(
                "S3 backend requires additional dependencies. Install with: "
                "pip install LandsatL2C2[s3]"
            )
        return S3Backend()
    elif backend_type == "auto":
        # Try S3 first (no credentials required)
        if HAS_S3_DEPS:
            try:
                backend = S3Backend()
                # Test connection
                if backend.stac_catalog is not None:
                    logger.info("Using S3 backend")
                    return backend
            except Exception as e:
                logger.warning(f"S3 backend failed: {e}")
        else:
            logger.info("S3 dependencies not available, skipping S3 backend")
        
        # Fall back to M2M
        try:
            backend = M2MBackend(**kwargs)
            logger.info("Using M2M backend")
            return backend
        except Exception as e:
            logger.error(f"M2M backend failed: {e}")
            raise RuntimeError("No backend available")
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")