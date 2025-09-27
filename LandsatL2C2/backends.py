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

# S3 backend imports (required dependencies)
try:
    import boto3
    import pystac_client
    import rasterio
    from botocore import UNSIGNED
    from botocore.config import Config
    from rasterio.session import AWSSession
    import planetary_computer
    HAS_S3_DEPS = True
except ImportError as e:
    # This should not happen with proper installation
    raise ImportError(
        f"S3 backend dependencies missing: {e}. "
        "Please reinstall LandsatL2C2 or install missing dependencies: "
        "pip install boto3 pystac-client rasterio planetary-computer"
    )

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
        
        # Anonymous S3 client
        self.s3_client = boto3.client('s3', config=Config(signature_version=UNSIGNED))
        self.bucket = 'usgs-landsat'
        
        # STAC catalog for metadata search - use Microsoft Planetary Computer for public access
        try:
            self.stac_catalog = pystac_client.Client.open(
                "https://planetarycomputer.microsoft.com/api/stac/v1"
            )
            logger.info("Connected to Microsoft Planetary Computer STAC catalog")
        except Exception as e:
            logger.warning(f"Could not connect to Planetary Computer STAC catalog: {e}")
            # Fallback to USGS (requires authentication)
            try:
                self.stac_catalog = pystac_client.Client.open(
                    "https://landsatlook.usgs.gov/stac-server"
                )
                logger.warning("Using USGS STAC catalog - data access may require authentication")
            except Exception as e2:
                logger.error(f"Could not connect to any STAC catalog: {e2}")
                self.stac_catalog = None
        
        # AWS session for rasterio
        self.aws_session = AWSSession(boto3.Session(), requester_pays=False)
        
        # Cache for STAC assets
        self._stac_assets_cache = {}
    
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
        
        # Parse dates and ensure proper formatting
        if isinstance(start_date, str):
            start_date = parser.parse(start_date).date()
        elif isinstance(start_date, datetime):
            start_date = start_date.date()
            
        if end_date is None:
            end_date = start_date
        elif isinstance(end_date, str):
            end_date = parser.parse(end_date).date()
        elif isinstance(end_date, datetime):
            end_date = end_date.date()
        
        # Default to Landsat Collection 2 - Planetary Computer has combined collection
        if collections is None:
            collections = ["landsat-c2-l2"]
        
        # Format dates as ISO strings for STAC
        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()
        
        # Build search parameters
        search_params = {
            "collections": collections,
            "datetime": f"{start_iso}/{end_iso}",
            "limit": max_results or 1000
        }
        
        # Add spatial filter if provided
        if target_geometry is not None:
            try:
                if hasattr(target_geometry, '__geo_interface__'):
                    search_params["intersects"] = target_geometry.__geo_interface__
                elif isinstance(target_geometry, dict):
                    search_params["intersects"] = target_geometry
                elif isinstance(target_geometry, (Point, Polygon)):
                    # Convert to GeoJSON-like dict
                    search_params["intersects"] = target_geometry.__geo_interface__
                else:
                    logger.warning(f"Unknown geometry type: {type(target_geometry)}")
            except Exception as e:
                logger.warning(f"Could not convert geometry for STAC search: {e}")
                # Continue without spatial filter
        
        try:
            # Search STAC catalog
            logger.info(f"STAC search params: {search_params}")
            search = self.stac_catalog.search(**search_params)
            
            # Use a reasonable limit to avoid hanging
            items = []
            count = 0
            max_items = search_params.get("limit", 1000)
            
            for item in search.items():
                items.append(item)
                count += 1
                if count >= max_items:
                    break
                    
            logger.info(f"Retrieved {len(items)} items from STAC catalog")
            
            # Convert to DataFrame
            results = []
            for item in items:
                # Extract cloud cover from properties
                cloud_cover = item.properties.get('eo:cloud_cover', 0)
                
                if cloud_cover <= cloud_percent_max:
                    # Handle datetime parsing - item.datetime might be string or datetime
                    try:
                        if isinstance(item.datetime, str):
                            date_utc = parser.parse(item.datetime).date()
                        else:
                            # Assume it's already a datetime-like object
                            date_utc = item.datetime.date()
                    except Exception as e:
                        logger.warning(f"Could not parse datetime for item {item.id}: {e}")
                        continue
                        
                    # Cache the assets for this scene
                    self._stac_assets_cache[item.id] = item.assets
                    
                    results.append({
                        'date_UTC': date_utc,
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
        """Get band data as rasterio dataset using STAC assets"""
        # First try to get URL from STAC assets
        url = self._get_band_url_from_stac(scene_id, band_name)
        
        if not url:
            # Fallback to constructed S3 URL
            url = self.get_band_url(scene_id, band_name)
            logger.info(f"Using constructed S3 URL: {url}")
        else:
            logger.info(f"Using STAC asset URL: {url}")
            
            # Sign URL if it's from Microsoft Planetary Computer
            if "blob.core.windows.net" in url and planetary_computer is not None:
                try:
                    signed_url = planetary_computer.sign(url)
                    logger.info(f"Signed URL for Planetary Computer access")
                    url = signed_url
                except Exception as e:
                    logger.warning(f"Could not sign URL: {e}")
        
        # Use rasterio with AWS session for anonymous access
        try:
            with rasterio.Env(self.aws_session):
                return rasterio.open(url)
        except Exception as e:
            logger.error(f"Failed to load band {band_name} from URL {url}: {e}")
            raise
    
    def _get_band_url_from_stac(self, scene_id: str, band_name: str) -> Optional[str]:
        """Get band URL from cached STAC assets"""
        logger.info(f"Searching STAC assets for scene {scene_id}, band {band_name}")
        
        # Map band names to STAC asset keys (Planetary Computer format)
        band_mapping = {
            'SR_B1': 'coastal',   # Coastal/aerosol band
            'SR_B2': 'blue', 
            'SR_B3': 'green',
            'SR_B4': 'red',
            'SR_B5': 'nir08',
            'SR_B6': 'swir16',
            'SR_B7': 'swir22',
            'ST_B10': 'lwir11',   # Thermal band in Planetary Computer (corrected)
            'QA_PIXEL': 'qa_pixel',
            'QA_RADSAT': 'qa_radsat',
            'SR_QA_AEROSOL': 'qa_aerosol',  # Corrected name in Planetary Computer
            'mtl.txt': 'mtl.txt',   # MTL metadata file
            'mtl.xml': 'mtl.xml',   # MTL metadata file (XML format)
            'mtl.json': 'mtl.json'  # MTL metadata file (JSON format)
        }
        
        asset_key = band_mapping.get(band_name)
        if not asset_key:
            logger.warning(f"No STAC asset mapping for band {band_name}")
            return None
        
        # Check if we have the scene cached and if it has the specific asset
        assets = self._stac_assets_cache.get(scene_id, {})
        
        if asset_key in assets:
            logger.info(f"Found STAC asset {asset_key} for scene {scene_id}")
            return assets[asset_key].href
        else:
            logger.warning(f"Asset {asset_key} not found for scene {scene_id}")
            logger.info(f"Available assets for {scene_id}: {list(assets.keys())}")
            return None
        
    def _search_and_cache_st_product(self, scene_id: str):
        """Search for and cache ST product assets for a given scene"""
        if self.stac_catalog is None:
            logger.warning("No STAC catalog available")
            return
            
        try:
            # Convert scene ID to ST product ID (replace _SR with _ST)
            st_scene_id = scene_id.replace('_SR', '_ST')
            logger.info(f"Searching for ST product: {st_scene_id}")
            
            # Search for the ST product
            search = self.stac_catalog.search(
                collections=["landsat-c2l2-st"],
                ids=[st_scene_id],
                limit=1
            )
            items = list(search.items())
            
            if items:
                item = items[0]
                logger.info(f"Found ST product: {item.id}, assets: {list(item.assets.keys())}")
                # Merge ST assets with existing cached assets (if any)
                if scene_id in self._stac_assets_cache:
                    # Update existing assets with ST assets
                    for key, asset in item.assets.items():
                        self._stac_assets_cache[scene_id][key] = asset
                else:
                    # Cache ST assets under the original scene_id
                    self._stac_assets_cache[scene_id] = item.assets
                    
                logger.info(f"Cached ST product assets for scene {scene_id}")
            else:
                logger.warning(f"No ST product found for scene ID: {st_scene_id}")
                
        except Exception as e:
            logger.warning(f"Could not find ST product for scene {scene_id}: {e}")

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
        return S3Backend()
    elif backend_type == "auto":
        # Use S3 backend by default (no credentials required)
        try:
            backend = S3Backend()
            logger.info("Using S3 backend")
            return backend
        except Exception as e:
            logger.error(f"S3 backend failed: {e}")
            # Only fall back to M2M if explicitly needed or if S3 fails
            logger.warning("Falling back to M2M backend (requires credentials)")
            try:
                backend = M2MBackend(**kwargs)
                logger.info("Using M2M backend")
                return backend
            except Exception as e:
                logger.error(f"M2M backend failed: {e}")
                raise RuntimeError("No backend available")
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")