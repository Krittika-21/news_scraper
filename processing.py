# processing.py

import logging
from typing import List, Dict, Optional, Tuple, Set
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
import re
import os

# --- Geospatial Imports ---
try:
    import geopandas as gpd
    from shapely.geometry import Point
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False

# --- Config Imports ---
from config import (
    SINGAPORE_LOCATIONS, GEOCODER_USER_AGENT, GEOCODING_CACHE,
    ELECTORAL_BOUNDARIES_FILE, CONSTITUENCY_COLUMN_NAME
)

log = logging.getLogger(__name__)

# --- Global boundary data (Keep loading logic as is) ---
boundaries_gdf = None
boundaries_spatial_index = None

def load_electoral_boundaries():
    # ... (Keep the existing load_electoral_boundaries function exactly as it was) ...
    global boundaries_gdf, boundaries_spatial_index
    if not GEOPANDAS_AVAILABLE:
        log.error("Geopandas library not found. Cannot perform constituency mapping.")
        return False
    if boundaries_gdf is not None: # Already loaded
        return True

    file_path = ELECTORAL_BOUNDARIES_FILE
    if not os.path.exists(file_path):
        log.error(f"Electoral boundaries file not found at: {file_path}")
        return False

    try:
        log.info(f"Loading electoral boundaries from: {file_path}")
        # --- Ensure KML driver is specified if using KMZ ---
        driver = 'KML' if file_path.lower().endswith('.kmz') else None
        temp_gdf = gpd.read_file(file_path, driver=driver)

        if CONSTITUENCY_COLUMN_NAME not in temp_gdf.columns:
             log.error(f"Specified constituency column '{CONSTITUENCY_COLUMN_NAME}' not found in boundary file.")
             log.error(f"Available columns: {list(temp_gdf.columns)}")
             log.error("Please update CONSTITUENCY_COLUMN_NAME in config.py")
             return False

        if temp_gdf.crs is None:
            log.warning("Boundary file has no CRS defined. Assuming EPSG:4326 (WGS84).")
            temp_gdf.set_crs(epsg=4326, inplace=True)
        elif temp_gdf.crs.to_epsg() != 4326:
            log.info(f"Converting boundaries from CRS {temp_gdf.crs} to EPSG:4326")
            temp_gdf = temp_gdf.to_crs(epsg=4326)

        boundaries_gdf = temp_gdf
        boundaries_spatial_index = boundaries_gdf.sindex
        log.info(f"Successfully loaded and indexed {len(boundaries_gdf)} electoral boundaries.")
        return True

    except Exception as e:
        log.error(f"Failed to load or process electoral boundaries file: {e}", exc_info=True)
        boundaries_gdf = None
        boundaries_spatial_index = None
        return False

BOUNDARIES_LOADED_SUCCESSFULLY = load_electoral_boundaries()

# --- Location Extraction (Keep as is) ---
def extract_locations_from_text(text: str, known_locations: List[str]) -> Set[str]:
    # ... (Keep existing function) ...
    found_locations = set()
    for loc in known_locations:
        pattern = r'(?i)(?<!\w)' + re.escape(loc) + r'(?!\w)'
        if re.search(pattern, text):
            found_locations.add(loc)
    if found_locations:
         log.debug(f"Found potential locations in text: {found_locations}")
    return found_locations


# --- Geocoding (Keep as is) ---
def get_geocoder() -> Nominatim:
    # ... (Keep existing function) ...
    return Nominatim(user_agent=GEOCODER_USER_AGENT)

def geocode_location(location_name: str, geolocator: Nominatim, attempt=1, max_attempts=3) -> Optional[Tuple[float, float]]:
    # ... (Keep existing function) ...
    cache_key = location_name.lower()
    if cache_key in GEOCODING_CACHE:
        log.debug(f"Cache hit for geocoding: {location_name}")
        return GEOCODING_CACHE[cache_key]

    query = f"{location_name}, Singapore"
    log.debug(f"Geocoding query: '{query}' (Attempt {attempt})")
    try:
        time.sleep(1) # Respect Nominatim usage policy
        location_data = geolocator.geocode(query, exactly_one=True, timeout=10)
        if location_data:
            coords = (location_data.latitude, location_data.longitude)
            GEOCODING_CACHE[cache_key] = coords
            log.debug(f"Geocoded '{location_name}' to {coords}")
            return coords
        else:
            log.warning(f"Could not geocode location: {location_name}")
            GEOCODING_CACHE[cache_key] = None
            return None
    except GeocoderTimedOut:
        log.warning(f"Geocoder timed out for: {location_name}. Retrying if possible...")
        if attempt < max_attempts:
            time.sleep(attempt * 2)
            return geocode_location(location_name, geolocator, attempt + 1, max_attempts)
        else:
            log.error(f"Geocoder timed out after {max_attempts} attempts for: {location_name}")
            GEOCODING_CACHE[cache_key] = None; return None
    except GeocoderServiceError as e:
        log.error(f"Geocoder service error for {location_name}: {e}"); GEOCODING_CACHE[cache_key] = None; return None
    except Exception as e:
        log.error(f"Unexpected error during geocoding for {location_name}: {e}"); GEOCODING_CACHE[cache_key] = None; return None


# --- Constituency Mapping Function (Keep as is) ---
def find_constituency_for_point(lat, lon):
    # ... (Keep existing function) ...
    if not BOUNDARIES_LOADED_SUCCESSFULLY or boundaries_gdf is None or boundaries_spatial_index is None:
        log.debug("Boundaries not loaded, skipping constituency check.")
        return None
    try:
        point = Point(lon, lat) # Shapely uses (lon, lat) order
        possible_matches_index = list(boundaries_spatial_index.intersection(point.bounds))
        if not possible_matches_index:
            log.debug(f"No candidate boundaries found via spatial index for point ({lat}, {lon})")
            return None
        possible_matches = boundaries_gdf.iloc[possible_matches_index]
        precise_matches = possible_matches[possible_matches.geometry.contains(point)]
        if not precise_matches.empty:
            constituency_name = precise_matches.iloc[0][CONSTITUENCY_COLUMN_NAME]
            log.debug(f"Point ({lat}, {lon}) is in constituency: {constituency_name}")
            return constituency_name
        else:
            log.debug(f"Point ({lat}, {lon}) is not within any candidate boundary geometry.")
            return None
    except Exception as e:
        log.error(f"Error during point-in-polygon check for ({lat}, {lon}): {e}", exc_info=True)
        return None


# --- Article Processing and Grouping (MODIFIED to group by COORDS, enrich with constituency) ---
def process_and_group_articles(articles: List[Dict]) -> List[Dict]: # Return LIST of clusters
    """
    Processes articles to find locations, geocode them, determine constituency (if possible),
    and group them by COORDINATES. Adds constituency info to the cluster.
    """
    geolocator = get_geocoder()
    articles_with_location = []

    log.info(f"Processing {len(articles)} articles for location and constituency enrichment...")

    # 1. Find locations, geocode, and store relevant data
    for article in articles:
        text_to_scan = f"{article['title']} {article['summary']}"
        found_locations = extract_locations_from_text(text_to_scan, SINGAPORE_LOCATIONS)
        log.debug(f"Scanning article '{article['title'][:30]}...'. Found locations: {found_locations}")

        coords = None
        primary_location_name = None

        if found_locations:
            for loc in found_locations:
                log.debug(f"Attempting to geocode location: {loc}")
                coords_result = geocode_location(loc, geolocator)
                if coords_result:
                    log.debug(f"Geocoding SUCCESS for {loc}: {coords_result}")
                    coords = coords_result
                    primary_location_name = loc
                    break # Use first successfully geocoded location
                else:
                    log.debug(f"Geocoding FAILED for {loc}")

        if coords:
            # Add article with coordinate and location name
             articles_with_location.append({
                 **article,
                 'location_name': primary_location_name,
                 'coords': coords
             })
        # else: # Optionally keep track of articles without coordinates
        #     log.debug(f"Article '{article['title'][:30]}...' could not be geocoded.")


    log.info(f"Successfully geocoded {len(articles_with_location)} articles.")

    # 2. Group articles by coordinates (using rounded string key)
    grouped_by_coords = {}
    for article in articles_with_location:
        lat, lon = article['coords']
        # Use rounded coordinates as grouping key
        coord_key = f"{lat:.5f},{lon:.5f}"

        if coord_key not in grouped_by_coords:
            # --- Find constituency for this coordinate cluster (only needs to be done once per cluster) ---
            constituency = find_constituency_for_point(lat, lon)
            grouped_by_coords[coord_key] = {
                'latitude': lat,
                'longitude': lon,
                'location_name': article['location_name'], # Use name from first article in group
                'constituency': constituency, # Store constituency found for this coord
                'articles': []
            }

        # Add article if not already present (basic URL check)
        if not any(a['url'] == article['url'] for a in grouped_by_coords[coord_key]['articles']):
             grouped_by_coords[coord_key]['articles'].append({
                 'title': article['title'],
                 'url': article['url'],
                 'summary': article['summary'],
                 'source': article['source'],
                 # Optionally add 'published_date' if available
             })

    # 3. Format the output list of clusters
    clusters = []
    for data in grouped_by_coords.values():
        clusters.append({
            'latitude': data['latitude'],
            'longitude': data['longitude'],
            'location_name': data['location_name'],
            'constituency': data['constituency'], # Include constituency in output
            'article_count': len(data['articles']),
            'articles': data['articles']
        })

    log.info(f"Grouped articles into {len(clusters)} coordinate clusters.")
    return clusters # Return the LIST of clusters