# config_streamlit.py (Ensure these are set correctly)
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

NEWS_SOURCES = [
    {
        'name': 'Google News (Search: Singapore)',
        'type': 'rss',
        'url': 'https://news.google.com/rss/search?q=Singapore&hl=en-SG&gl=SG&ceid=SG:en',
    }
]

_general_locations = [
    "Orchard Road", "Marina Bay", "Sentosa", "Changi Airport", "Jurong East", "Jurong West",
    "Tampines", "Pasir Ris", "Woodlands", "Yishun", "Ang Mo Kio", "Bishan", "Toa Payoh",
    "Bukit Merah", "Queenstown", "Clementi", "Bukit Timah", "Novena", "Geylang", "Bedok",
    "Punggol", "Sengkang", "Hougang", "Serangoon", "Bukit Panjang", "Choa Chu Kang", "Tuas",
    "Pulau Ubin", "Tekong", "Raffles Place", "Tanjong Pagar", "City Hall", "Dhoby Ghaut",
    "Somerset", "Newton", "Stevens", "Botanic Gardens", "Holland Village", "Buona Vista",
    "Commonwealth", "Dover", "Outram Park", "HarbourFront", "Telok Blangah", "Labrador Park",
    "Pasir Panjang", "Haw Par Villa", "Kent Ridge", "one-north", "Singapore"
]
_electoral_districts_2025 = [
    "Aljunied", "Ang Mo Kio", "Bishan-Toa Payoh", "Chua Chu Kang", "East Coast",
    "Holland-Bukit Timah", "Jalan Besar", "Jurong-Clementi", "Marine Parade",
    "Marsiling-Yew Tee", "Nee Soon", "Pasir Ris-Punggol", "Sembawang", "Tampines",
    "Tanjong Pagar", "West Coast", "Bukit Batok", "Bukit Panjang", "Hong Kah North",
    "Hougang", "Kebun Baru", "MacPherson", "Marymount", "Mountbatten", "Pioneer",
    "Potong Pasir", "Punggol West", "Radin Mas", "Sengkang Central", "Yio Chu Kang",
    "Yuhua", "Jurong", "Clementi", "Marsiling", "Yew Tee", "Pasir Ris", "Sengkang"
]
SINGAPORE_LOCATIONS = list(set(_general_locations + _electoral_districts_2025))

ELECTORAL_BOUNDARIES_FILE = os.path.join(BASE_DIR, 'data', 'doc.kml')
CONSTITUENCY_COLUMN_NAME = 'Name'

GEOCODER_USER_AGENT = "singapore_news_mapper_streamlit_v0.1"