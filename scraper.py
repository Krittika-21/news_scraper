# scraper.py

import requests
from bs4 import BeautifulSoup
import feedparser
import logging
from typing import List, Dict, Optional
import time 
import re

# Use module-specific logger
log = logging.getLogger(__name__)

# --- Import locations from config ---
try:
    from config import SINGAPORE_LOCATIONS
except ImportError:
    # Define a minimal fallback list if config import fails (optional)
    SINGAPORE_LOCATIONS = ['Singapore']
    logging.warning("Could not import SINGAPORE_LOCATIONS from config. Using fallback list.")

# --- HTML Scraping Helper Functions (Keep as is) ---
def fetch_html(url: str) -> Optional[str]:
    # ... (no changes needed here) ...
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        log.error(f"Error fetching HTML URL {url}: {e}")
        return None

def parse_articles_from_html(html_content: str, config: Dict) -> List[Dict]:
    # ... (no changes needed here, but ensure it's only called for HTML type) ...
    articles = []
    if not html_content:
        return articles
    try:
        soup = BeautifulSoup(html_content, 'html.parser') # Keep html.parser for actual HTML pages
        selectors = config['selectors'] # This line causes error if called for RSS
        base_url = config.get('base_url', config['url'])
        article_elements = soup.select(selectors['article_container'])
        log.info(f"Found {len(article_elements)} potential HTML article elements using selector '{selectors['article_container']}' for {config['name']}")
        for element in article_elements:
            title_element = element.select_one(selectors['title'])
            link_element = element.select_one(selectors['link'])
            summary_element = element.select_one(selectors.get('summary'))
            title = title_element.get_text(strip=True) if title_element else None
            raw_link = link_element['href'] if link_element and link_element.has_attr('href') else None
            summary = summary_element.get_text(strip=True) if summary_element else ""
            if title and raw_link:
                link = requests.compat.urljoin(base_url, raw_link)
                articles.append({'title': title, 'url': link, 'summary': summary, 'source': config['name']})
            else:
                 log.warning(f"Skipping HTML element, missing title or link. Element: {str(element)[:100]}...")
    except KeyError as e:
         log.error(f"Missing key '{e}' in selectors config for HTML source '{config['name']}'. Check config.py.")
    except Exception as e:
        log.error(f"Error parsing HTML for {config['name']}: {e}", exc_info=True)
    return articles


# --- RSS Parsing Helper Function (MODIFIED for better summary parsing) ---
def parse_rss_feed(feed_url: str, source_name: str) -> List[Dict]:
    """Parses articles from an RSS feed URL, filtering by keywords."""
    articles = []
    filtered_out_count = 0
    log.info(f"Fetching and parsing RSS feed: {feed_url}")
    try:
        feed_data = feedparser.parse(feed_url)
        if feed_data.bozo:
            log.warning(f"Feedparser reported potential issues (bozo=1) for {feed_url}. Error: {feed_data.get('bozo_exception', 'Unknown')}")

        log.info(f"Found {len(feed_data.entries)} total entries in RSS feed for {source_name}. Filtering...")

        for entry in feed_data.entries:
            title = entry.get('title', '') # Default to empty string
            link = entry.get('link')
            summary_html = entry.get('summary', entry.get('description', ''))
            published_parsed = entry.get('published_parsed')
            published_date = time.strftime('%Y-%m-%dT%H:%M:%SZ', published_parsed) if published_parsed else None

            # --- Keyword Filtering Step ---
            text_to_check = f"{title} {summary_html}" # Check raw summary HTML too
            found_keyword = False
            # Use a simple check or reuse extract_locations_from_text logic
            # Simple check for any location mention:
            for loc in SINGAPORE_LOCATIONS:
                 # Case-insensitive check, maybe add word boundaries if needed
                 if re.search(r'(?i)\b' + re.escape(loc) + r'\b', text_to_check):
                      found_keyword = True
                      break # Found one keyword, no need to check others

            if not found_keyword:
                filtered_out_count += 1
                log.debug(f"Filtering out RSS entry (no SG keywords): '{title[:50]}...'")
                continue # Skip this entry if no keywords found
            # --- End Keyword Filtering ---


            # --- Proceed if keywords were found ---
            cleaned_summary = ""
            if summary_html:
                try:
                    summary_soup = BeautifulSoup(summary_html, 'lxml')
                    cleaned_summary = summary_soup.get_text(strip=True, separator=' ')
                except Exception as parse_err:
                    log.warning(f"Could not parse summary HTML for entry '{title}' using lxml: {parse_err}. Using raw summary.")
                    cleaned_summary = re.sub('<[^<]+?>', '', summary_html).strip()

            if title and link:
                articles.append({
                    'title': title.strip(),
                    'url': link.strip(),
                    'summary': cleaned_summary,
                    'source': source_name,
                    'published_date': published_date
                })
            # else: # No need for this log if we filter above
            #    log.warning(f"Skipping RSS entry, missing title or link. Entry: {entry.get('id', 'N/A')}")

    except Exception as e:
        log.error(f"Error parsing RSS feed {feed_url} for {source_name}: {e}", exc_info=True)

    log.info(f"Finished parsing RSS for {source_name}. Kept {len(articles)} articles, filtered out {filtered_out_count}.")
    return articles



# --- Main Scraping Function (VERIFY LOGIC) ---
def scrape_news_sources(sources_config: List[Dict]) -> List[Dict]:
    """Scrapes news articles from a list of configured sources (HTML or RSS)."""
    all_articles = []
    log.info(f"Starting scraping process for {len(sources_config)} sources...")

    for source in sources_config:
        # --- Defensive check for source validity ---
        if not isinstance(source, dict) or 'name' not in source or 'url' not in source:
             log.warning(f"Skipping invalid source configuration: {source}")
             continue

        source_name = source['name']
        source_type = source.get('type', 'html').lower() # Default to html if type not specified
        source_url = source['url']
        parsed_articles = [] # Initialize for this source

        log.info(f"Processing source: {source_name} ({source_type.upper()}) - {source_url}")

        # --- Ensure correct branching based on type ---
        if source_type == 'rss':
            parsed_articles = parse_rss_feed(source_url, source_name)
        elif source_type == 'html':
            # Check if selectors are provided for HTML type
            if 'selectors' not in source:
                 log.error(f"Source '{source_name}' is type 'html' but missing 'selectors' in config.py. Skipping.")
                 continue # Skip this source if selectors are missing

            html = fetch_html(source_url)
            if html:
                # This should ONLY be called if type is 'html' AND selectors exist
                parsed_articles = parse_articles_from_html(html, source)
            else:
                log.warning(f"Could not fetch HTML content for {source_name}")
        else:
            log.warning(f"Unsupported source type '{source_type}' for {source_name}. Skipping.")

        # --- Log results for this specific source ---
        log.info(f"Parsed {len(parsed_articles)} articles from {source_name}")
        all_articles.extend(parsed_articles)

    log.info(f"Scraping finished. Total articles collected: {len(all_articles)}")
    return all_articles