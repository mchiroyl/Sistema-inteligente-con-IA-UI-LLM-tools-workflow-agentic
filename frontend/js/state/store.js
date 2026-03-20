/**
 * Support Intake AI — State Store
 * Manages the global application state.
 */

// Private state
let historyData = [];
let globalFilter = 'all'; // 'all', 'success', 'needs_review', 'error', 'ai_direct', 'human'
let currentSearch = '';

// Subscribers for reactivity
const listeners = [];

function notifyListeners() {
  for (const listener of listeners) {
    listener();
  }
}

export const store = {
  subscribe(callback) {
    listeners.push(callback);
    // return unsubscribe function
    return () => {
      const idx = listeners.indexOf(callback);
      if (idx > -1) listeners.splice(idx, 1);
    };
  },

  setHistory(data) {
    historyData = Array.isArray(data) ? data : [];
    notifyListeners();
  },

  getHistory() {
    return historyData;
  },

  setFilter(filter) {
    globalFilter = filter;
    notifyListeners();
  },

  getFilter() {
    return globalFilter;
  },

  setSearch(term) {
    currentSearch = (term || '').toLowerCase();
    notifyListeners();
  },

  getSearch() {
    return currentSearch;
  },

  /**
   * Returns history filtered by current tab and search term
   */
  getFilteredHistory() {
    return historyData.map((item, originalIndex) => ({ item, originalIndex }))
      .filter(({ item }) => {
        // Dropdown state filter
        let stateMatch = false;
        if (globalFilter === 'all') stateMatch = true;
        else if (globalFilter === 'success' && item.status === 'success') stateMatch = true;
        else if (globalFilter === 'needs_review' && item.status === 'needs_review') stateMatch = true;
        else if (globalFilter === 'error' && item.status === 'error') stateMatch = true;
        else if (globalFilter === 'ai_direct' && item.status === 'success' && !item.edited_by_human) stateMatch = true;
        else if (globalFilter === 'human' && item.edited_by_human) stateMatch = true;

        if (!stateMatch) return false;

        // Search text filter
        if (!currentSearch) return true;

        const textToSearch = [
          item.filename,
          item.summary,
          item.extracted_data?.reporter_name,
          item.extracted_data?.problem_description,
          item.status
        ].join(" ").toLowerCase();

        return textToSearch.includes(currentSearch);
      });
  },

  /**
   * Calculates metrics for the Dashboard KPIs
   */
  getMetrics() {
    let completed = 0;
    let review = 0;
    let errors = 0;
    let aiDirect = 0;
    let humanCorrected = 0;

    // Prioridades: Crítica, Alta, Media, Baja, Sin Asignar
    const priorities = { "Crítica": 0, "Alta": 0, "Media": 0, "Baja": 0, "Sin Asignar": 0 };

    historyData.forEach(item => {
      if (item.status === "success") completed++;
      else if (item.status === "needs_review") review++;
      else if (item.status === "error") errors++;

      if (item.status === "success" && !item.edited_by_human) aiDirect++;
      if (item.edited_by_human) humanCorrected++;

      // Conteo para el semáforo
      if (item.status === "success" && item.extracted_data?.priority) {
        const p = item.extracted_data.priority;
        if (priorities[p] !== undefined) priorities[p]++;
      } else if (item.status === "success") {
        priorities["Sin Asignar"]++;
      }
    });

    return {
      total: historyData.length,
      completed,
      review,
      errors,
      aiDirect,
      humanCorrected,
      priorities
    };
  }
};
