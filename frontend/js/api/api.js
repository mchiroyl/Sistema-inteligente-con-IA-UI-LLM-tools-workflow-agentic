/**
 * Support Intake AI — API Layer
 * Handles all HTTP communication with the FastAPI backend.
 */

// API URL — relative when served by FastAPI, absolute as fallback
const API_URL = (window.location.port === "8000")
  ? window.location.origin + "/api/analyze"
  : "http://127.0.0.1:8000/api/analyze";

const HISTORY_URL = (window.location.port === "8000")
  ? window.location.origin + "/api/history"
  : "http://127.0.0.1:8000/api/history";


/**
 * Sends a file to the analyze endpoint.
 * @param {File} file 
 * @returns {Promise<Object>} Analysis response data
 */
export async function analyzeFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(API_URL, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetches the ticket history.
 * @returns {Promise<Array>} List of historical tickets
 */
export async function fetchHistory() {
  const response = await fetch(HISTORY_URL);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Updates a specific ticket in the history.
 * @param {number} index Index of the ticket
 * @param {Object} updatedData Fields to update
 * @returns {Promise<Object>} Success or error message
 */
export async function updateHistoryItem(index, updatedData) {
  const response = await fetch(`${HISTORY_URL}/${index}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updatedData)
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  
  return response.json();
}
