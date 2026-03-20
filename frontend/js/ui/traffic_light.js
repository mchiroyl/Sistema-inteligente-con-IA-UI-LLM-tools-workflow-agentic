/**
 * Support Intake AI — Traffic Light UI
 * Replaces the donut chart with a 3-light animated Semáforo.
 */

import { store } from "../state/store.js";

/**
 * Renders the traffic light based on current metrics.
 */
export function updateTrafficLight() {
  const container = document.getElementById("headerChartArea");
  if (!container) return;

  const metrics = store.getMetrics();
  const p = metrics.priorities;

  // Group priorities
  const countRed = (p["Crítica"] || 0) + (p["Alta"] || 0);
  const countYellow = (p["Media"] || 0);
  const countGreen = (p["Baja"] || 0);

  // Status for CSS animations
  const isActiveRed = countRed > 0;
  const isActiveYellow = countYellow > 0;
  const isActiveGreen = countGreen > 0;

  // Default state when 0 tickets to avoid a completely dead UI
  const noData = !isActiveRed && !isActiveYellow && !isActiveGreen;

  container.innerHTML = `
    <div class="traffic-light-container">
      <div class="traffic-light-body">
        <div class="bulb-wrapper">
          <div class="bulb red-bulb ${isActiveRed ? 'active animate-pulse' : (noData ? 'dim' : 'off')}"></div>
          <span class="bulb-count red-text">${countRed}</span>
          <span class="bulb-label">Urgente</span>
        </div>
        <div class="bulb-wrapper">
          <div class="bulb yellow-bulb ${isActiveYellow ? 'active animate-pulse' : (noData ? 'dim' : 'off')}"></div>
          <span class="bulb-count yellow-text">${countYellow}</span>
          <span class="bulb-label">Normal</span>
        </div>
        <div class="bulb-wrapper">
          <div class="bulb green-bulb ${isActiveGreen ? 'active animate-pulse' : (noData ? 'dim' : 'off')}"></div>
          <span class="bulb-count green-text">${countGreen}</span>
          <span class="bulb-label">Tranquilo</span>
        </div>
      </div>
    </div>
  `;
}
