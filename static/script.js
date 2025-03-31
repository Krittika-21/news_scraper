// static/script.js

document.addEventListener('DOMContentLoaded', () => {
    const mapContainerId = 'map-container';
    const loadingIndicator = document.getElementById('loading-indicator');
    // Use relative URL if served by Flask, absolute if using CORS
    const backendApiUrl = '/api/news/clusters';

    // --- 1. Initialize Leaflet Map (Brought back) ---
    function initializeMap() {
        console.log("Initializing map...");
        const singaporeCenter = [1.3521, 103.8198];
        const initialZoom = 11;

        // Check if map container exists
        const mapElement = document.getElementById(mapContainerId);
        if (!mapElement) {
            console.error(`Map container element with ID '${mapContainerId}' not found.`);
            return null;
        }

        const map = L.map(mapContainerId).setView(singaporeCenter, initialZoom);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        console.log("Map initialized.");
        return map;
    }

    // --- 2. Fetch News Data (Keep as is - expects a LIST now) ---
    async function fetchNewsData() {
        console.log(`Fetching news data from ${backendApiUrl}...`);
        if (loadingIndicator) loadingIndicator.style.display = 'block';

        try {
            const response = await fetch(backendApiUrl);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const data = await response.json(); // Should be a list of clusters
            console.log("News data received:", data);
            if (!Array.isArray(data)) {
                 console.warn("Received data is not an array, processing might fail.", data);
                 // Optionally try to handle if it's the old constituency format by mistake
                 // return []; // Or return empty to prevent errors later
            }
            return data;
        } catch (error) {
            console.error("Error fetching news data:", error);
            alert(`Failed to fetch news data: ${error.message}\nIs the backend server running?`);
            return null;
        } finally {
             if (loadingIndicator) loadingIndicator.style.display = 'none';
        }
    }

    // --- 3. Create Popup Content (Updated to include constituency) ---
    function createPopupHtml(cluster) {
        if (!cluster || !cluster.articles || cluster.articles.length === 0) {
            return "No articles found for this location.";
        }

        // Basic sanitization helper
        const sanitize = (str) => (str || "").replace(/</g, "<").replace(/>/g, ">");

        // Start building the HTML string
        let html = `<strong>${sanitize(cluster.location_name) || 'Location'} (${cluster.article_count})</strong>`;

        // Add constituency info if available
        if (cluster.constituency) {
             html += `<br><small>Constituency: ${sanitize(cluster.constituency)}</small>`;
        } else if (cluster.constituency === null) { // Explicitly null means checked but not found
             html += `<br><small>Constituency: Outside Boundaries</small>`;
        } // If undefined, maybe boundaries weren't loaded - don't show anything

        html += '<ul>'; // Start list

        cluster.articles.forEach(article => {
            html += `
                <li>
                    <a href="${sanitize(article.url)}" target="_blank" rel="noopener noreferrer">
                        ${sanitize(article.title)}
                    </a>
                    <span class="popup-source">Source: ${sanitize(article.source)}</span>
                </li>
            `;
        });

        html += '</ul>';
        return html;
    }


    // --- 4. Add Markers to Map (Brought back) ---
    function addMarkersToMap(map, clusters) {
        if (!map) {
             console.error("Map object is invalid, cannot add markers.");
             return;
        }
        if (!clusters || !Array.isArray(clusters)) {
            console.error("Invalid or non-array cluster data for adding markers.");
            return;
        }
        console.log(`Adding ${clusters.length} cluster markers to the map...`);

        // Clear existing markers if needed (e.g., for refresh) - requires storing marker layer group

        clusters.forEach(cluster => {
            if (typeof cluster.latitude === 'number' && typeof cluster.longitude === 'number') {
                const marker = L.marker([cluster.latitude, cluster.longitude]);
                const popupContent = createPopupHtml(cluster);

                marker.bindPopup(popupContent, {
                    maxWidth: 350,
                });

                marker.addTo(map);
            } else {
                console.warn("Skipping cluster due to missing/invalid coordinates:", cluster);
            }
        });
        console.log("Markers added.");
    }

    // --- Main Execution ---
    async function main() {
        const map = initializeMap(); // Initialize the map first
        if (!map) {
             console.error("Map initialization failed. Aborting.");
             if (loadingIndicator) loadingIndicator.style.display = 'none'; // Hide loading indicator
             return;
        }

        const newsClusters = await fetchNewsData(); // Fetch data (expects a list)

        if (newsClusters) { // Check if fetch was successful (returned array or null)
             if (newsClusters.length > 0) {
                 addMarkersToMap(map, newsClusters); // Add markers if data exists
             } else {
                  console.log("No news clusters to display.");
                  // Optionally display a message on the map or page
             }
        }
        // Error case is handled within fetchNewsData with an alert
    }

    main(); // Run the main function
});