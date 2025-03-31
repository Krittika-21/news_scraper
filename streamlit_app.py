import streamlit as st
import pandas as pd
import logging
import time
import re
import os
from typing import List, Dict, Optional, Tuple, Set

# Geospatial and Mapping
import geopandas as gpd
from shapely.geometry import Point
import folium
# Import GeoJsonTooltip for hover info on boundaries
from folium.features import GeoJsonTooltip
from streamlit_folium import st_folium

# Web/Parsing
import feedparser
from bs4 import BeautifulSoup
import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Import config
try:
    import config
except ModuleNotFoundError:
    st.error("Error: config.py not found. Please ensure it's in the same directory.")
    st.stop()

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# --- Constants from Config ---
NEWS_SOURCES = config.NEWS_SOURCES
SINGAPORE_LOCATIONS = config.SINGAPORE_LOCATIONS
ELECTORAL_BOUNDARIES_FILE = config.ELECTORAL_BOUNDARIES_FILE
CONSTITUENCY_COLUMN_NAME = config.CONSTITUENCY_COLUMN_NAME
GEOCODER_USER_AGENT = config.GEOCODER_USER_AGENT

# --- Caching Functions ---
@st.cache_resource
def load_boundaries_data(file_path):
    # ... (Keep this function exactly as is) ...
    if not os.path.exists(file_path):
        log.error(f"Electoral boundaries file not found at: {file_path}")
        st.error(f"Error: Boundary file not found at {file_path}. Cannot map constituencies.")
        return None, None
    log.info(f"Loading electoral boundaries from: {file_path}")
    try:
        driver = 'KML' if file_path.lower().endswith(('.kml', '.kmz')) else None
        gdf = gpd.read_file(file_path, driver=driver)
        if CONSTITUENCY_COLUMN_NAME not in gdf.columns:
            log.error(f"Constituency column '{CONSTITUENCY_COLUMN_NAME}' not found in boundary file.")
            st.error(f"Config Error: Column '{CONSTITUENCY_COLUMN_NAME}' not in boundary file. Available: {list(gdf.columns)}")
            return None, None
        if gdf.crs is None:
            log.warning("Boundary file CRS not defined. Assuming EPSG:4326.")
            gdf.set_crs(epsg=4326, inplace=True)
        elif gdf.crs.to_epsg() != 4326:
            log.info(f"Converting boundaries CRS from {gdf.crs} to EPSG:4326")
            gdf = gdf.to_crs(epsg=4326)
        spatial_index = gdf.sindex
        log.info(f"Successfully loaded and indexed {len(gdf)} electoral boundaries.")
        return gdf, spatial_index # Return both gdf and index
    except ImportError:
        log.error("Geopandas/Shapely not installed correctly.")
        st.error("Geospatial libraries not found. Please check installation.")
        return None, None
    except Exception as e:
        log.error(f"Failed to load or process boundaries file: {e}", exc_info=True)
        st.error(f"Error loading boundary file: {e}")
        return None, None

@st.cache_resource
def get_geocoder_instance():
    # ... (Keep this function as is) ...
    log.info("Initializing geocoder...")
    return Nominatim(user_agent=GEOCODER_USER_AGENT)

@st.cache_data(ttl="30m")
def fetch_and_process_news(_news_sources_config: List[Dict]):
    # ... (Keep this function exactly as is - it uses load_boundaries_data) ...
    log.info("Fetching and processing news data...")
    all_articles = []
    geocoder = get_geocoder_instance()
    # Make sure boundary data is loaded here for constituency mapping
    boundaries_gdf, boundaries_spatial_index = load_boundaries_data(ELECTORAL_BOUNDARIES_FILE)

    # --- 1. Fetch Articles ---
    for source in _news_sources_config:
        source_name = source['name']
        source_type = source.get('type', 'html').lower()
        source_url = source['url']
        parsed_articles = []
        filtered_out_count = 0
        log.info(f"Processing source: {source_name} ({source_type.upper()})")
        if source_type == 'rss':
            try:
                feed_data = feedparser.parse(source_url)
                if feed_data.bozo: log.warning(f"Feedparser issue for {source_url}: {feed_data.get('bozo_exception')}")
                log.info(f"Found {len(feed_data.entries)} total entries. Filtering...")
                for entry in feed_data.entries:
                    title = entry.get('title', '')
                    link = entry.get('link')
                    summary_html = entry.get('summary', entry.get('description', ''))
                    text_to_check = f"{title} {summary_html}"
                    found_keyword = any(re.search(r'(?i)\b' + re.escape(loc) + r'\b', text_to_check) for loc in SINGAPORE_LOCATIONS)
                    if not found_keyword: filtered_out_count += 1; continue
                    cleaned_summary = ""
                    if summary_html:
                        try:
                            summary_soup = BeautifulSoup(summary_html, 'lxml')
                            cleaned_summary = summary_soup.get_text(strip=True, separator=' ')
                        except Exception: cleaned_summary = re.sub('<[^<]+?>', '', summary_html).strip()
                    if title and link: parsed_articles.append({'title': title.strip(), 'url': link.strip(), 'summary': cleaned_summary, 'source': source_name})
                log.info(f"Kept {len(parsed_articles)} articles from {source_name}, filtered out {filtered_out_count}.")
                all_articles.extend(parsed_articles)
            except Exception as e: log.error(f"Error parsing RSS feed {source_url}: {e}", exc_info=True); st.warning(f"Could not process RSS feed: {source_name}")
        else: log.warning(f"Unsupported source type '{source_type}' for {source_name}.")
    log.info(f"Total articles after fetching & initial filtering: {len(all_articles)}")

    # --- 2. Process Articles (Geocode, Constituency Map) ---
    articles_with_location = []
    geocoding_cache = {}
    for article in all_articles:
        text_to_scan = f"{article['title']} {article['summary']}"
        found_locations = set(loc for loc in SINGAPORE_LOCATIONS if re.search(r'(?i)\b' + re.escape(loc) + r'\b', text_to_scan))
        if not found_locations: continue
        coords = None; primary_location_name = None
        for loc in found_locations:
            cache_key = loc.lower()
            if cache_key in geocoding_cache: coords_result = geocoding_cache[cache_key]
            else:
                try:
                    time.sleep(0.5); location_data = geocoder.geocode(f"{loc}, Singapore", exactly_one=True, timeout=10)
                    coords_result = (location_data.latitude, location_data.longitude) if location_data else None; geocoding_cache[cache_key] = coords_result
                except (GeocoderTimedOut, GeocoderServiceError, Exception) as e: log.warning(f"Geocoding error for '{loc}': {e}"); coords_result = None; geocoding_cache[cache_key] = None
            if coords_result: coords = coords_result; primary_location_name = loc; break
        if coords: articles_with_location.append({**article, 'location_name': primary_location_name, 'coords': coords})
    log.info(f"Successfully geocoded {len(articles_with_location)} articles.")

    # --- 3. Group by Coordinates & Find Constituency ---
    grouped_by_coords = {}
    for article in articles_with_location:
        lat, lon = article['coords']
        coord_key = f"{lat:.5f},{lon:.5f}"
        if coord_key not in grouped_by_coords:
            constituency = None
            if boundaries_gdf is not None and boundaries_spatial_index is not None: # Check if boundaries loaded
                try:
                    point = Point(lon, lat)
                    possible_matches_index = list(boundaries_spatial_index.intersection(point.bounds))
                    if possible_matches_index:
                        possible_matches = boundaries_gdf.iloc[possible_matches_index]
                        precise_matches = possible_matches[possible_matches.geometry.contains(point)]
                        if not precise_matches.empty: constituency = precise_matches.iloc[0][CONSTITUENCY_COLUMN_NAME]
                except Exception as e: log.error(f"Error during point-in-polygon check for ({lat}, {lon}): {e}")
            grouped_by_coords[coord_key] = {'latitude': lat, 'longitude': lon, 'location_name': article['location_name'], 'constituency': constituency, 'articles': []}
        if not any(a['url'] == article['url'] for a in grouped_by_coords[coord_key]['articles']):
             grouped_by_coords[coord_key]['articles'].append({'title': article['title'], 'url': article['url'], 'summary': article['summary'], 'source': article['source']})

    # --- 4. Format final cluster list ---
    final_clusters = []
    for data in grouped_by_coords.values():
        final_clusters.append({'latitude': data['latitude'], 'longitude': data['longitude'], 'location_name': data['location_name'], 'constituency': data['constituency'], 'article_count': len(data['articles']), 'articles': data['articles']})
    log.info(f"Grouped articles into {len(final_clusters)} coordinate clusters.")
    return final_clusters


# --- Streamlit App Layout ---

st.set_page_config(page_title="Singapore News Map", layout="wide")
st.title("🇸🇬 News Map")
st.write("Recent news articles clustered by location, overlaid on 2020 Electoral Boundaries.")

# --- Load Data ---
boundaries_gdf, _ = load_boundaries_data(ELECTORAL_BOUNDARIES_FILE)
clusters = fetch_and_process_news(config.NEWS_SOURCES)

# --- Create and Display Map ---
map_center = [1.3521, 103.8198]
map_zoom = 11

# Create base map
m = folium.Map(location=map_center, zoom_start=map_zoom, tiles="OpenStreetMap")

# --- Add Boundary Layer (MODIFIED with highlight_function) ---
if boundaries_gdf is not None:
    log.info("Adding electoral boundary layer to the map...")
    try:
        # Define a style function for the default boundary appearance
        style_function = lambda x: {
            'fillColor': '#add8e6', # Light blue fill
            'color': '#00008b',     # Dark blue border
            'weight': 1.5,          # Border thickness
            'fillOpacity': 0.2,     # Semi-transparent fill
        }
        # --- Define a highlight function for hover effect ---
        highlight_function = lambda x: {
            'fillColor': '#add8e6',  # Keep same fill color (or change if desired, e.g., '#87cefa')
            'color': '#00008b',      # Keep same border color (or change, e.g., 'black')
            'weight': 3,             # Make border thicker on hover
            'fillOpacity': 0.5       # Make fill more opaque on hover
        }
        # Define tooltip to show constituency name on hover
        tooltip = GeoJsonTooltip(
            fields=[CONSTITUENCY_COLUMN_NAME],
            aliases=['Constituency:'],
            sticky=True,
            style=("background-color: white; color: black; font-family: sans-serif; font-size: 12px; padding: 5px;")
        )

        # Add GeoJson layer to the map, including the highlight_function
        folium.GeoJson(
            boundaries_gdf,
            name='2020 Electoral Boundaries',
            style_function=style_function,
            highlight_function=highlight_function, # <-- ADD THIS PARAMETER
            tooltip=tooltip,
            show=True
        ).add_to(m)
        log.info("Boundary layer added with hover highlighting.")
    except Exception as e:
        log.error(f"Error adding boundary layer: {e}", exc_info=True)
        st.warning("Could not display electoral boundaries on the map.")
else:
    st.warning("Boundary data not loaded, cannot display boundary layer.")


# --- Add News Cluster Markers (Keep as is) ---
if clusters is None:
    st.error("Failed to load or process news data. Check logs.")
elif not clusters:
    st.warning("No relevant news articles found or processed.")
else:
    log.info(f"Adding {len(clusters)} news clusters to the map...")
    for cluster in clusters:
        # ... (Keep marker creation logic exactly the same) ...
        lat = cluster['latitude']
        lon = cluster['longitude']
        count = cluster['article_count']
        loc_name = cluster.get('location_name', 'Location')
        constituency = cluster.get('constituency', None)
        tooltip_text = f"{loc_name} ({count} articles)"
        if constituency: tooltip_text += f"<br>Constituency: {constituency}"
        elif constituency is None and boundaries_gdf is not None: tooltip_text += f"<br>Constituency: Outside Boundaries"
        popup_html = f"<b>{loc_name} ({count})</b>"
        if constituency: popup_html += f"<br><small>Constituency: {constituency}</small>"
        elif constituency is None and boundaries_gdf is not None: popup_html += f"<br><small>Constituency: Outside Boundaries</small>"
        popup_html += "<hr style='margin: 3px 0;'>"
        popup_html += "<ul style='padding-left: 15px; margin-top: 5px; max-height: 150px; overflow-y: auto;'>"
        for article in cluster['articles']:
             safe_title = article['title'].replace('<', '<').replace('>', '>')
             popup_html += f"<li style='margin-bottom: 5px;'><a href='{article['url']}' target='_blank'>{safe_title}</a><br><small>({article['source']})</small></li>"
        popup_html += "</ul>"
        popup = folium.Popup(popup_html, max_width=350)
        folium.Marker(location=[lat, lon], tooltip=tooltip_text, popup=popup, icon=folium.Icon(color='red', icon='info-sign')).add_to(m)
    log.info("News cluster markers added.")

# --- Add Layer Control (Keep as is) ---
if boundaries_gdf is not None:
    folium.LayerControl().add_to(m)

# --- Display Map (Keep as is) ---
log.info("Rendering map...")
st_folium(m, width='100%', height=600, returned_objects=[])
log.info("Map rendered.")

st.caption("Map data © OpenStreetMap contributors | Boundary data © Elections Department Singapore (via data.gov.sg) | News sourced from Google News RSS")