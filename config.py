# config.py (Combined Filtering and Updated Locations)
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- News Sources Configuration ---
NEWS_SOURCES = [
    {
        'name': 'Google News (Search: Singapore)', # Use search feed
        'type': 'rss',
        # Use the SEARCH-based RSS feed URL for pre-filtering
        'url': 'https://news.google.com/rss/search?q=Singapore&hl=en-SG&gl=SG&ceid=SG:en',
    }
]

# --- Location Configuration ---
# Original list of general locations
_general_locations = [
    "Orchard Road", "Marina Bay", "Sentosa", "Changi Airport", "Jurong East",
    "Jurong West", "Tampines", "Pasir Ris", "Woodlands", "Yishun", "Ang Mo Kio",
    "Bishan", "Toa Payoh", "Bukit Merah", "Queenstown", "Clementi", "Bukit Timah",
    "Novena", "Geylang", "Bedok", "Punggol", "Sengkang", "Hougang", "Serangoon",
    "Bukit Panjang", "Choa Chu Kang", "Tuas", "Pulau Ubin", "Tekong",
    "Raffles Place", "Tanjong Pagar", "City Hall", "Dhoby Ghaut", "Somerset",
    "Newton", "Stevens", "Botanic Gardens", "Holland Village", "Buona Vista",
    "Commonwealth", "Dover", "Outram Park", "HarbourFront", "Telok Blangah",
    "Labrador Park", "Pasir Panjang", "Haw Par Villa", "Kent Ridge", "one-north",
    # Add Singapore itself for the search feed, although less critical for keyword filter now
    "Singapore"
]

# 2025 Electoral Districts (GRCs and SMCs)
_electoral_districts_2025 = [
    # GRCs
    "Aljunied", "Ang Mo Kio", "Bishan-Toa Payoh", "Chua Chu Kang", "East Coast",
    "Holland-Bukit Timah", "Jalan Besar", "Jurong-Clementi", "Marine Parade",
    "Marsiling-Yew Tee", "Nee Soon", "Pasir Ris-Punggol", "Sembawang", "Tampines",
    "Tanjong Pagar", "West Coast",
    # SMCs
    "Bukit Batok", "Bukit Panjang", "Hong Kah North", "Hougang", "Kebun Baru",
    "MacPherson", "Marymount", "Mountbatten", "Pioneer", "Potong Pasir",
    "Punggol West", "Radin Mas", "Sengkang Central", "Yio Chu Kang", "Yuhua",
    # Add base names that might appear without GRC/SMC suffix
    "Jurong", "Clementi", "Marsiling", "Yew Tee", "Pasir Ris", "Sengkang"
]

# Combine lists and remove duplicates using a set, then convert back to list
SINGAPORE_LOCATIONS = list(set(_general_locations + _electoral_districts_2025))
# Optional: Print the final list length for verification during startup
# print(f"Loaded {len(SINGAPORE_LOCATIONS)} unique Singapore locations/districts for filtering.")


# --- Geospatial Configuration ---
ELECTORAL_BOUNDARIES_FILE = os.path.join(BASE_DIR, 'data', 'doc.kml') # Use the KML file
CONSTITUENCY_COLUMN_NAME = 'Name' # Use the correct column name from KML

# --- Geocoding Configuration ---
GEOCODER_USER_AGENT = "singapore_news_mapper_app_v0.5" # Increment version maybe
GEOCODING_CACHE = {}

# --- API Configuration ---
API_HOST = '0.0.0.0'
API_PORT = 5000
API_DEBUG = True