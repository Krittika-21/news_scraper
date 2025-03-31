# Singapore News Map Backend

This project is a Python Flask backend application that scrapes news articles related to Singapore, identifies locations mentioned, maps these locations to electoral constituencies (using 2020 boundaries as 2025 is not released yet), and provides an API endpoint serving this data, intended for use with a map-based frontend (like Leaflet).

## Features

*   **News Aggregation:** Scrapes news from configured RSS feeds (e.g., Google News search for "Singapore").
*   **Location Extraction:** Identifies mentions of known Singapore locations (including general places and 2025 electoral districts) within article titles and summaries.
*   **Geocoding:** Converts identified location names into latitude/longitude coordinates using `geopy` (Nominatim/OpenStreetMap).
*   **Constituency Mapping:** Determines which 2020 electoral constituency a geocoded point falls into using `geopandas` and an official boundary file (see Data Sources).
*   **Coordinate Clustering:** Groups articles based on their geocoded coordinates.
*   **API Endpoint:** Provides a `/api/news/clusters` endpoint returning a JSON list of clusters, each containing coordinates, location name, constituency name (if found), and associated articles.
*   **Basic Caching:** Implements simple in-memory caching for the API results and geocoding lookups (Note: Not suitable for multi-instance production).

## Tech Stack

*   **Backend:** Python 3.x, Flask
*   **Data Processing:**
    *   GeoPandas (for geospatial operations)
    *   Shapely (for geometric objects, dependency of GeoPandas)
    *   Geopy (for geocoding)
*   **Web Scraping/Parsing:**
    *   Requests (for HTTP calls)
    *   BeautifulSoup4 (for HTML parsing)
    *   Feedparser (for RSS parsing)
    *   lxml (for robust XML/HTML parsing)
*   **Deployment (Recommended):** Gunicorn (WSGI Server)
*   **Frontend (Assumed):** HTML, CSS, JavaScript, Leaflet.js

## Project Structure
├── app.py # Main Flask application, API routes
├── scraper.py # Functions for fetching and parsing news (RSS/HTML)
├── processing.py # Functions for location extraction, geocoding, constituency mapping, grouping
├── config.py # Configuration (news sources, file paths, API settings, location lists)
├── requirements.txt # Python dependencies
├── data/ # Folder for data files
│ └── doc.kml # Electoral boundary file (or GeoJSON/KMZ) - See Data Sources
├── templates/ # HTML templates (e.g., index.html if served by Flask)
│ └── index.html
└── static/ # Static files (CSS, JavaScript for frontend)
├── script.js
└── style.css

## Setup and Installation (Local)

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```

2.  **Create and Activate Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *   **Note:** Installing `geopandas` via pip can be tricky due to system dependencies. If you encounter issues, try installing it using Conda: `conda install geopandas`.

4.  **Download Boundary Data:**
    *   Obtain the electoral boundary file (e.g., the 2020 KML/GeoJSON from data.gov.sg - see Data Sources section below).
    *   Place the file inside the `data/` directory.
    *   Ensure the filename matches the `ELECTORAL_BOUNDARIES_FILE` path in `config.py` (e.g., `data/doc.kml`).

5.  **Configure `config.py`:**
    *   Verify `ELECTORAL_BOUNDARIES_FILE` points to your downloaded boundary file.
    *   **Crucially:** Verify `CONSTITUENCY_COLUMN_NAME` matches the actual column name containing constituency identifiers in your boundary file (use the `test_kmz_reader.py` script or inspect the file if unsure - it might be `'Name'`, `'ED_DESC'`, etc.).
    *   Review `NEWS_SOURCES` if you want to add/change feeds.

6.  **Run the Application:**
    ```bash
    python app.py
    ```
    The Flask development server will start (usually on `http://127.0.0.1:5000`).

7.  **Access Frontend/API:**
    *   If Flask serves the frontend, navigate to `http://127.0.0.1:5000/`.
    *   Access the API directly at `http://127.0.0.1:5000/api/news/clusters`.

## API Endpoint

*   **URL:** `/api/news/clusters`
*   **Method:** `GET`
*   **Response:** A JSON list of cluster objects. Each object has the following structure:
    ```json
    [
      {
        "latitude": 1.3xxxx,
        "longitude": 103.8xxxx,
        "location_name": "Found Location Name", // e.g., "Bishan"
        "constituency": "Constituency Name", // e.g., "Bishan-Toa Payoh", or null
        "article_count": 2,
        "articles": [
          {
            "title": "Article Title 1",
            "url": "http://...",
            "summary": "Article summary...",
            "source": "News Source Name"
          },
          {
            "title": "Article Title 2",
            // ...
          }
        ]
      },
      // ... more clusters
    ]
    ```

## Acknowledgements and Data Sources

*   **Electoral Boundaries:** This application uses the 2020 Electoral Boundary dataset provided by the Elections Department Singapore via data.gov.sg.
    *   **Citation:** Elections Department, 2024, "Electoral Boundary Dataset", data.gov.sg. Accessed: March 31, 2025. [Online]. Available: https://data.gov.sg/datasets/d_4e7981c19ae3c1e3b7ce3d9842415c8d/view
*   **Geocoding:** Location name to coordinate conversion uses the Nominatim service via the `geopy` library, which relies on OpenStreetMap data. Please respect their usage policies.
*   **News Feeds:** News articles are sourced from publicly available RSS feeds (e.g., Google News).

## Deployment Notes

*   **WSGI Server:** Use a production WSGI server like Gunicorn. Add `gunicorn` to `requirements.txt` and configure your hosting platform (e.g., Azure Web Apps, PythonAnywhere, Render) to use it (e.g., `gunicorn --workers=4 app:app`).
*   **Background Tasks:** For production, the scraping and processing logic should be moved to background tasks (e.g., Azure Functions Timer Trigger, Celery, APScheduler) running on a schedule. This prevents API timeouts and keeps the API responsive.
*   **Persistent Caching/State:** Replace in-memory caches (`API_CACHE`, `GEOCODING_CACHE`) with a persistent, shared cache like Redis (e.g., Azure Cache for Redis) when deploying multiple instances. The background task should write results to this cache, and the API should read from it.
*   **`geopandas` Dependencies:** Ensure the deployment environment can install `geopandas` and its underlying C libraries (GDAL, GEOS, PROJ). This might require custom build steps or using Docker-based deployments on some platforms.
*   **Environment Variables:** Use environment variables (e.g., Azure App Settings) for configuration like API keys, database/cache connection strings, and `FLASK_DEBUG=False`.

