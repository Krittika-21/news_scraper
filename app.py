# app.py

from flask import Flask, jsonify, request
import logging

from config import NEWS_SOURCES, API_HOST, API_PORT, API_DEBUG
from scraper import scrape_news_sources
from processing import process_and_group_articles
from flask import render_template
from flask_cors import CORS
# Configure logging early, before Flask potentially overrides it.
logging.basicConfig(level=logging.DEBUG, # <--- CHANGE THIS TO DEBUG
                    format='%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s') # Added module/line number

app = Flask(__name__, template_folder='templates', static_folder='static')
# CORS might not be strictly needed now, but doesn't hurt to leave it
CORS(app)

# --- Add Route to Serve the Frontend ---
@app.route('/') # Serve index.html at the root URL
def index():
    # Renders the templates/index.html file
    return render_template('index.html')

# --- In-memory Cache for API results (Simple Caching) ---
# In a real app, use Redis, Memcached, or a proper caching library/database.
# Also, implement cache invalidation (e.g., time-based).
API_CACHE = {
    'clustered_news': None,
    'last_updated': None
}
CACHE_TTL_SECONDS = 60 * 30 # Cache results for 30 minutes

# --- API Endpoint ---

@app.route('/api/news/clusters', methods=['GET'])
def get_news_clusters():
    """
    API endpoint to retrieve news articles clustered by location.
    Uses a simple time-based cache.
    """
    import time
    now = time.time()

    # Check cache
    if API_CACHE['clustered_news'] and API_CACHE['last_updated'] and (now - API_CACHE['last_updated'] < CACHE_TTL_SECONDS):
        logging.info("Serving clustered news data from cache.")
        return jsonify(API_CACHE['clustered_news'])

    logging.info("Cache miss or expired. Fetching and processing fresh news data for constituency grouping....")
    try:
        # 1. Scrape Data
        articles = scrape_news_sources(NEWS_SOURCES)
        if not articles:
             # Return potentially stale cache data if scraping fails, or an error
             if API_CACHE['clustered_news']:
                 logging.warning("Scraping failed, returning stale cache data.")
                 return jsonify(API_CACHE['clustered_news'])
             else:
                 return jsonify({"error": "Failed to scrape news sources and no cache available."}), 500


        # 2. Process and Cluster Data
        # clustered_data = process_and_group_articles(articles)
        # # 3. Update Cache
        # API_CACHE['clustered_news'] = clustered_data
        # API_CACHE['last_updated'] = now
        # logging.info("Successfully updated API cache with fresh data.")
        # 4. Return Data
        # return jsonify(clustered_data)

        # 2. Process and Group Data by Constituency
        # This function now returns a dictionary keyed by constituency name
        grouped_data = process_and_group_articles(articles)

        # 3. Update Cache
        API_CACHE['clustered_news'] = grouped_data
        API_CACHE['last_updated'] = now
        logging.info("Successfully updated API cache with constituency-grouped data.")
       
        # 4. Return Data (jsonify handles the dictionary structure)
        return jsonify(grouped_data)

        

    except Exception as e:
        logging.exception("An error occurred while processing the request.")
        # Return potentially stale cache data on error, or a generic error
        if API_CACHE['clustered_news']:
             logging.warning("Processing failed, returning stale cache data.")
             return jsonify(API_CACHE['clustered_news'])
        else:
            return jsonify({"error": "An internal server error occurred."}), 500

# --- Basic Health Check Endpoint ---
@app.route('/health', methods=['GET'])
def health_check():
    """A simple health check endpoint."""
    return jsonify({"status": "ok"}), 200


# --- Main Execution ---
if __name__ == '__main__':
    logging.info(f"Starting Flask server on {API_HOST}:{API_PORT}")
    # Use waitress or gunicorn for production instead of Flask's development server
    app.run(host=API_HOST, port=API_PORT, debug=API_DEBUG)