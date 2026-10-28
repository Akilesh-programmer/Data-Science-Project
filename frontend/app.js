/* ═══════════════════════════════════════════════════════════
   EV Infrastructure & Route Optimization — Dashboard JS
   ═══════════════════════════════════════════════════════════ */

const API = '';  // same origin

// ── State ─────────────────────────────────────────────────
let mainMap = null;
let clusterMap = null;
let routeMap = null;
let markerLayer = null;
let heatLayer = null;
let clusterMarkerLayer = null;
let routeLayer = null;
let routeMarkerLayer = null;
let showMarkers = true;
let showHeat = false;
let charts = {};
let currentDataPage = 1;

// ── Color palette ─────────────────────────────────────────
const COLORS = {
  accent: '#06d6a0',
  accent2: '#118ab2',
  accent3: '#073b4c',
  warm1: '#f4a261',
  warm2: '#e76f51',
  purple: '#8b5cf6',
  pink: '#ec4899',
  cyan: '#22d3ee',
  lime: '#84cc16',
  palette: [
    '#06d6a0', '#118ab2', '#f4a261', '#e76f51', '#8b5cf6',
    '#ec4899', '#22d3ee', '#84cc16', '#f59e0b', '#ef4444',
    '#6366f1', '#14b8a6', '#a855f7', '#f97316', '#0ea5e9',
  ],
};

// ── Chart.js Defaults ─────────────────────────────────────
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.pointStyle = 'circle';
Chart.defaults.plugins.legend.labels.padding = 16;

// ═══════════════════════════════════════════════════════════
//  INITIALIZATION
// ═══════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  loadOverview();
  populateCountryDropdowns();
});

// ── Tab Navigation ────────────────────────────────────────
function setupTabs() {
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
      const sectionId = 'section-' + tab.dataset.tab;
      document.getElementById(sectionId).classList.add('active');

      // Lazy-init maps
      if (tab.dataset.tab === 'map' && !mainMap) initMainMap();
      if (tab.dataset.tab === 'clustering' && !clusterMap) initClusterMap();
      if (tab.dataset.tab === 'routes' && !routeMap) initRouteMap();
      if (tab.dataset.tab === 'analytics' && !charts['operators']) loadAnalytics();
      if (tab.dataset.tab === 'data') loadDataTable();
    });
  });
}

// ═══════════════════════════════════════════════════════════
//  OVERVIEW
// ═══════════════════════════════════════════════════════════
async function loadOverview() {
  try {
    const [summary, growth, countries, connectors, power] = await Promise.all([
      fetchJSON('/api/analytics/summary'),
      fetchJSON('/api/analytics/growth'),
      fetchJSON('/api/analytics/top-countries?n=10'),
      fetchJSON('/api/analytics/connectors'),
      fetchJSON('/api/analytics/power-distribution'),
    ]);

    // Update stat cards with animation
    animateValue('stat-total', 0, summary.total_stations, 1500);
    animateValue('stat-countries', 0, summary.total_countries, 1200);
    animateValue('stat-operators', 0, summary.total_operators, 1200);
    document.getElementById('stat-avg-power').innerHTML = `${summary.avg_power_kw}<span class="unit">kW</span>`;
    document.getElementById('stat-operational').innerHTML = `${summary.operational_pct}<span class="unit">%</span>`;
    document.getElementById('stat-fast').innerHTML = `${summary.fast_charge_pct}<span class="unit">%</span>`;

    document.getElementById('status-text').textContent = `${summary.total_stations.toLocaleString()} stations loaded`;

    // Growth chart
    createGrowthChart(growth);
    // Countries chart
    createCountriesChart(countries);
    // Connectors chart
    createConnectorsChart(connectors);
    // Power chart
    createPowerChart(power);

  } catch (err) {
    console.error('Failed to load overview:', err);
    document.getElementById('status-text').textContent = 'Error loading data';
  }
}

function createGrowthChart(data) {
  const ctx = document.getElementById('chart-growth').getContext('2d');
  charts['growth'] = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.map(d => d.year),
      datasets: [
        {
          label: 'Cumulative Stations',
          data: data.map(d => d.cumulative),
          borderColor: COLORS.accent,
          backgroundColor: hexToRgba(COLORS.accent, 0.1),
          fill: true,
          tension: 0.4,
          pointRadius: 3,
          pointHoverRadius: 6,
          borderWidth: 2,
        },
        {
          label: 'New per Year',
          data: data.map(d => d.count),
          borderColor: COLORS.accent2,
          backgroundColor: hexToRgba(COLORS.accent2, 0.1),
          fill: true,
          tension: 0.4,
          pointRadius: 3,
          pointHoverRadius: 6,
          borderWidth: 2,
        }
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'top' },
      },
      scales: {
        y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.04)' } },
        x: { grid: { display: false } },
      },
    },
  });
}

function createCountriesChart(data) {
  const ctx = document.getElementById('chart-countries').getContext('2d');
  charts['countries'] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.map(d => d.country),
      datasets: [{
        label: 'Stations',
        data: data.map(d => d.count),
        backgroundColor: data.map((_, i) => COLORS.palette[i % COLORS.palette.length]),
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: {
        x: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { grid: { display: false } },
      },
    },
  });
}

function createConnectorsChart(data) {
  const ctx = document.getElementById('chart-connectors').getContext('2d');
  charts['connectors'] = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: data.map(d => d.connector_type),
      datasets: [{
        data: data.map(d => d.count),
        backgroundColor: data.map((_, i) => COLORS.palette[i % COLORS.palette.length]),
        borderWidth: 0,
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '55%',
      plugins: {
        legend: { position: 'right', labels: { boxWidth: 12, padding: 12, font: { size: 11 } } },
      },
    },
  });
}

function createPowerChart(data) {
  const ctx = document.getElementById('chart-power').getContext('2d');
  charts['power'] = new Chart(ctx, {
    type: 'polarArea',
    data: {
      labels: data.map(d => d.range_label),
      datasets: [{
        data: data.map(d => d.count),
        backgroundColor: [
          hexToRgba('#22d3ee', 0.6),
          hexToRgba('#06d6a0', 0.6),
          hexToRgba('#f4a261', 0.6),
          hexToRgba('#e76f51', 0.6),
          hexToRgba('#8b5cf6', 0.6),
        ],
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'right', labels: { boxWidth: 12, padding: 10, font: { size: 11 } } },
      },
      scales: { r: { display: false } },
    },
  });
}

// ═══════════════════════════════════════════════════════════
//  ANALYTICS TAB
// ═══════════════════════════════════════════════════════════
async function loadAnalytics() {
  try {
    const [operators, status, countryGrowth] = await Promise.all([
      fetchJSON('/api/analytics/operators?n=10'),
      fetchJSON('/api/analytics/status'),
      fetchJSON('/api/analytics/country-growth?top_n=5'),
    ]);

    // Operators chart
    const ctx1 = document.getElementById('chart-operators').getContext('2d');
    charts['operators'] = new Chart(ctx1, {
      type: 'bar',
      data: {
        labels: operators.map(d => d.operator.length > 25 ? d.operator.slice(0, 22) + '…' : d.operator),
        datasets: [{
          label: 'Stations',
          data: operators.map(d => d.count),
          backgroundColor: operators.map((_, i) => hexToRgba(COLORS.palette[i % COLORS.palette.length], 0.8)),
          borderRadius: 6,
          borderSkipped: false,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.04)' } },
          y: { grid: { display: false }, ticks: { font: { size: 10 } } },
        },
      },
    });

    // Status chart
    const ctx2 = document.getElementById('chart-status').getContext('2d');
    const statusColors = {
      'Operational': '#06d6a0',
      'Temporarily Unavailable': '#f4a261',
      'Planned For Future Date': '#118ab2',
      'Not Operational': '#ef4444',
      'Partly Operational (Mixed)': '#8b5cf6',
    };
    charts['status'] = new Chart(ctx2, {
      type: 'doughnut',
      data: {
        labels: status.map(d => d.status),
        datasets: [{
          data: status.map(d => d.count),
          backgroundColor: status.map(d => statusColors[d.status] || '#64748b'),
          borderWidth: 0,
          hoverOffset: 8,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '60%',
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 12, padding: 10, font: { size: 11 } } },
        },
      },
    });

    // Country growth multi-line chart
    const ctx3 = document.getElementById('chart-country-growth').getContext('2d');
    const countries = Object.keys(countryGrowth);
    const datasets = countries.map((country, i) => ({
      label: country,
      data: countryGrowth[country].map(d => ({ x: d.year, y: d.cumulative })),
      borderColor: COLORS.palette[i],
      backgroundColor: hexToRgba(COLORS.palette[i], 0.05),
      fill: false,
      tension: 0.4,
      borderWidth: 2.5,
      pointRadius: 2,
      pointHoverRadius: 5,
    }));

    charts['country-growth'] = new Chart(ctx3, {
      type: 'line',
      data: { datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: { legend: { position: 'top' } },
        scales: {
          x: { type: 'linear', title: { display: true, text: 'Year' }, grid: { display: false } },
          y: { beginAtZero: true, title: { display: true, text: 'Cumulative Stations' }, grid: { color: 'rgba(255,255,255,0.04)' } },
        },
      },
    });

  } catch (err) {
    console.error('Failed to load analytics:', err);
  }
}

// ═══════════════════════════════════════════════════════════
//  MAIN MAP
// ═══════════════════════════════════════════════════════════
async function initMainMap() {
  mainMap = L.map('main-map', { zoomControl: true }).setView([30, 0], 2);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 18,
    attribution: '© CartoDB © OpenStreetMap',
  }).addTo(mainMap);

  // Load GeoJSON
  try {
    const geo = await fetchJSON('/api/stations/geojson?limit=8000');
    markerLayer = L.layerGroup();

    geo.features.forEach(f => {
      const [lng, lat] = f.geometry.coordinates;
      const p = f.properties;
      const color = p.power_kw > 100 ? '#e76f51' : p.power_kw > 50 ? '#f4a261' : p.power_kw > 22 ? '#06d6a0' : '#118ab2';

      const marker = L.circleMarker([lat, lng], {
        radius: 3,
        fillColor: color,
        color: color,
        weight: 0.5,
        opacity: 0.8,
        fillOpacity: 0.6,
      });

      marker.bindPopup(`
        <strong>${p.name}</strong><br/>
        <b>Operator:</b> ${p.operator}<br/>
        <b>Power:</b> ${p.power_kw} kW<br/>
        <b>Connector:</b> ${p.connector}<br/>
        <b>Status:</b> ${p.status}<br/>
        <b>Country:</b> ${p.country} | <b>Year:</b> ${p.year}
      `);

      markerLayer.addLayer(marker);
    });

    markerLayer.addTo(mainMap);

    // Prepare heatmap data
    const heatData = await fetchJSON('/api/analytics/heatmap?sample_size=10000');
    const heatPoints = heatData.map(d => [d.Latitude, d.Longitude, d.intensity]);
    heatLayer = L.heatLayer(heatPoints, {
      radius: 18,
      blur: 25,
      maxZoom: 10,
      gradient: { 0.2: '#118ab2', 0.4: '#06d6a0', 0.6: '#f4a261', 0.8: '#e76f51', 1.0: '#ef4444' },
    });

  } catch (err) {
    console.error('Map data error:', err);
  }
}

function toggleMapLayer(layer) {
  if (!mainMap) return;
  if (layer === 'markers') {
    showMarkers = !showMarkers;
    document.getElementById('btn-markers').classList.toggle('active', showMarkers);
    if (showMarkers && markerLayer) markerLayer.addTo(mainMap);
    else if (markerLayer) mainMap.removeLayer(markerLayer);
  }
  if (layer === 'heatmap') {
    showHeat = !showHeat;
    document.getElementById('btn-heatmap').classList.toggle('active', showHeat);
    if (showHeat && heatLayer) heatLayer.addTo(mainMap);
    else if (heatLayer) mainMap.removeLayer(heatLayer);
  }
}

// ═══════════════════════════════════════════════════════════
//  CLUSTERING
// ═══════════════════════════════════════════════════════════
function initClusterMap() {
  clusterMap = L.map('cluster-map', { zoomControl: true }).setView([30, 0], 2);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 18,
    attribution: '© CartoDB © OpenStreetMap',
  }).addTo(clusterMap);
  clusterMarkerLayer = L.layerGroup().addTo(clusterMap);
}

// Update K display
document.addEventListener('DOMContentLoaded', () => {
  const slider = document.getElementById('cluster-k');
  if (slider) {
    slider.addEventListener('input', () => {
      document.getElementById('cluster-k-val').textContent = slider.value;
    });
  }
});

async function runClustering() {
  const country = document.getElementById('cluster-country').value;
  const k = document.getElementById('cluster-k').value;

  if (!clusterMap) initClusterMap();

  try {
    const [clusters, gaps, elbow] = await Promise.all([
      fetchJSON(`/api/analytics/clusters?n_clusters=${k}${country ? '&country=' + encodeURIComponent(country) : ''}`),
      fetchJSON(`/api/analytics/coverage-gaps?top_n=10${country ? '&country=' + encodeURIComponent(country) : ''}`),
      fetchJSON(`/api/analytics/elbow?max_k=12${country ? '&country=' + encodeURIComponent(country) : ''}`),
    ]);

    // Clear existing
    clusterMarkerLayer.clearLayers();

    // Add cluster centers to map
    const bounds = [];
    clusters.centers.forEach((c, i) => {
      const color = COLORS.palette[i % COLORS.palette.length];
      const radius = Math.max(8, Math.min(30, Math.sqrt(c.station_count) * 2));
      const marker = L.circleMarker([c.latitude, c.longitude], {
        radius: radius,
        fillColor: color,
        color: '#fff',
        weight: 2,
        fillOpacity: 0.7,
      });
      marker.bindPopup(`
        <strong>Cluster ${c.cluster_id}</strong><br/>
        <b>Stations:</b> ${c.station_count.toLocaleString()}<br/>
        <b>Avg Power:</b> ${c.avg_power_kw} kW<br/>
        <b>Center:</b> ${c.latitude.toFixed(4)}, ${c.longitude.toFixed(4)}
      `);
      clusterMarkerLayer.addLayer(marker);
      bounds.push([c.latitude, c.longitude]);
    });

    // Add gap markers
    gaps.forEach(g => {
      const marker = L.circleMarker([g.latitude, g.longitude], {
        radius: 10,
        fillColor: '#ef4444',
        color: '#fff',
        weight: 2,
        fillOpacity: 0.8,
      });
      marker.bindPopup(`
        <strong>🔴 Coverage Gap</strong><br/>
        <b>Current stations:</b> ${g.current_station_count}<br/>
        <b>Priority:</b> ${g.recommendation}<br/>
        <b>Location:</b> ${g.latitude}, ${g.longitude}
      `);
      clusterMarkerLayer.addLayer(marker);
      bounds.push([g.latitude, g.longitude]);
    });

    if (bounds.length > 0) {
      clusterMap.fitBounds(bounds, { padding: [30, 30] });
    }

    // Update cluster list
    const listEl = document.getElementById('cluster-list');
    listEl.innerHTML = clusters.centers.map((c, i) => `
      <div class="cluster-badge">
        <div class="cluster-id" style="color:${COLORS.palette[i % COLORS.palette.length]}">Cluster ${c.cluster_id}</div>
        <div class="cluster-count">${c.station_count.toLocaleString()} <span style="font-size:0.7rem;color:var(--text-muted)">stations</span></div>
        <div class="cluster-power">Avg ${c.avg_power_kw} kW · ${c.latitude.toFixed(2)}, ${c.longitude.toFixed(2)}</div>
      </div>
    `).join('');

    // Update gap list
    const gapEl = document.getElementById('gap-list');
    if (gaps.length === 0) {
      gapEl.innerHTML = '<p style="color:var(--text-muted);padding:1rem">No coverage gaps detected.</p>';
    } else {
      gapEl.innerHTML = gaps.map(g => `
        <div class="gap-item">
          <div class="${g.recommendation === 'High priority' ? 'priority-high' : 'priority-medium'}">
            ${g.recommendation === 'High priority' ? '🔴' : '🟡'} ${g.recommendation}
          </div>
          <div style="font-size:0.85rem;margin-top:0.35rem;color:var(--text-primary)">
            ${g.latitude.toFixed(4)}, ${g.longitude.toFixed(4)}
          </div>
          <div style="font-size:0.75rem;color:var(--text-secondary)">
            Current: ${g.current_station_count} station(s)
          </div>
        </div>
      `).join('');
    }

    // Elbow chart
    if (charts['elbow']) charts['elbow'].destroy();
    const ctx = document.getElementById('chart-elbow').getContext('2d');
    charts['elbow'] = new Chart(ctx, {
      type: 'line',
      data: {
        labels: elbow.map(d => d.k),
        datasets: [{
          label: 'Inertia',
          data: elbow.map(d => d.inertia),
          borderColor: COLORS.accent,
          backgroundColor: hexToRgba(COLORS.accent, 0.1),
          fill: true,
          tension: 0.3,
          borderWidth: 2.5,
          pointRadius: 4,
          pointHoverRadius: 7,
          pointBackgroundColor: COLORS.accent,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: (items) => `K = ${items[0].label}`,
              label: (item) => `Inertia: ${item.raw.toLocaleString()}`,
            },
          },
        },
        scales: {
          x: { title: { display: true, text: 'Number of Clusters (K)' }, grid: { display: false } },
          y: { title: { display: true, text: 'Inertia' }, grid: { color: 'rgba(255,255,255,0.04)' } },
        },
      },
    });

  } catch (err) {
    console.error('Clustering error:', err);
  }
}

// ═══════════════════════════════════════════════════════════
//  ROUTE OPTIMIZER
// ═══════════════════════════════════════════════════════════
function initRouteMap() {
  routeMap = L.map('route-map', { zoomControl: true }).setView([48, 2], 5);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 18,
    attribution: '© CartoDB © OpenStreetMap',
  }).addTo(routeMap);
  routeLayer = L.layerGroup().addTo(routeMap);
  routeMarkerLayer = L.layerGroup().addTo(routeMap);
}

function setRoutePreset(preset) {
  const presets = {
    'london-paris': { olat: 51.5074, olng: -0.1278, dlat: 48.8566, dlng: 2.3522 },
    'ny-dc': { olat: 40.7128, olng: -74.0060, dlat: 38.9072, dlng: -77.0369 },
    'berlin-munich': { olat: 52.5200, olng: 13.4050, dlat: 48.1351, dlng: 11.5820 },
    'la-sf': { olat: 34.0522, olng: -118.2437, dlat: 37.7749, dlng: -122.4194 },
  };
  const p = presets[preset];
  if (!p) return;
  document.getElementById('route-olat').value = p.olat;
  document.getElementById('route-olng').value = p.olng;
  document.getElementById('route-dlat').value = p.dlat;
  document.getElementById('route-dlng').value = p.dlng;
}

async function optimizeRoute() {
  if (!routeMap) initRouteMap();

  const body = {
    origin_lat: parseFloat(document.getElementById('route-olat').value),
    origin_lng: parseFloat(document.getElementById('route-olng').value),
    dest_lat: parseFloat(document.getElementById('route-dlat').value),
    dest_lng: parseFloat(document.getElementById('route-dlng').value),
    vehicle_range_km: parseFloat(document.getElementById('route-range').value),
    current_soc: parseFloat(document.getElementById('route-soc').value),
    min_soc: parseFloat(document.getElementById('route-min-soc').value),
  };

  const resultDiv = document.getElementById('route-result');
  resultDiv.innerHTML = '<div class="loading-overlay"><div class="spinner"></div> Optimizing route…</div>';

  try {
    const res = await fetch(`${API}/api/routes/optimize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();

    // Clear map layers
    routeLayer.clearLayers();
    routeMarkerLayer.clearLayers();

    // Draw route line
    if (data.waypoints && data.waypoints.length > 1) {
      const latlngs = data.waypoints.map(w => [w.lat, w.lng]);
      const polyline = L.polyline(latlngs, {
        color: COLORS.accent,
        weight: 3,
        opacity: 0.8,
        dashArray: data.feasible ? null : '10, 10',
      });
      routeLayer.addLayer(polyline);

      // Origin marker
      const originIcon = L.divIcon({
        className: '',
        html: '<div style="width:14px;height:14px;background:#06d6a0;border-radius:50%;border:3px solid #fff;box-shadow:0 0 10px rgba(6,214,160,0.5)"></div>',
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      });
      L.marker([data.origin.lat, data.origin.lng], { icon: originIcon })
        .bindPopup('<strong>🟢 Origin</strong>')
        .addTo(routeMarkerLayer);

      // Destination marker
      const destIcon = L.divIcon({
        className: '',
        html: '<div style="width:14px;height:14px;background:#ef4444;border-radius:50%;border:3px solid #fff;box-shadow:0 0 10px rgba(239,68,68,0.5)"></div>',
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      });
      L.marker([data.destination.lat, data.destination.lng], { icon: destIcon })
        .bindPopup('<strong>🔴 Destination</strong>')
        .addTo(routeMarkerLayer);

      // Charging stop markers
      if (data.charging_stops) {
        data.charging_stops.forEach((stop, i) => {
          const stopIcon = L.divIcon({
            className: '',
            html: `<div style="width:12px;height:12px;background:#f4a261;border-radius:50%;border:2px solid #fff;box-shadow:0 0 8px rgba(244,162,97,0.5)"></div>`,
            iconSize: [12, 12],
            iconAnchor: [6, 6],
          });
          L.marker([stop.latitude, stop.longitude], { icon: stopIcon })
            .bindPopup(`
              <strong>⚡ Stop ${i + 1}: ${stop.name}</strong><br/>
              <b>Power:</b> ${stop.power_kw} kW<br/>
              <b>SoC:</b> ${stop.soc_on_arrival}% → ${stop.soc_on_departure}%<br/>
              <b>Charge time:</b> ~${stop.estimated_charge_time_min} min
            `)
            .addTo(routeMarkerLayer);
        });
      }

      routeMap.fitBounds(latlngs, { padding: [40, 40] });
    }

    // Render result panel
    const statusClass = data.feasible ? 'feasible' : 'infeasible';
    let html = `<div class="route-result ${statusClass}">`;
    html += `<p style="margin-bottom:1rem;font-size:0.85rem;color:${data.feasible ? 'var(--accent-1)' : '#ef4444'}">${data.message}</p>`;

    if (data.feasible) {
      html += `
        <div class="route-stats">
          <div class="route-stat"><div class="value">${data.total_distance_km}</div><div class="label">km distance</div></div>
          <div class="route-stat"><div class="value">${data.total_time_hours}</div><div class="label">hours total</div></div>
          <div class="route-stat"><div class="value">${data.charging_stops.length}</div><div class="label">charging stops</div></div>
          <div class="route-stat"><div class="value">${data.energy_consumed_kwh}</div><div class="label">kWh consumed</div></div>
        </div>
      `;

      if (data.charging_stops.length > 0) {
        html += '<div class="stop-timeline">';
        data.charging_stops.forEach((stop, i) => {
          html += `
            <div class="stop-item">
              <div class="stop-name">⚡ Stop ${i + 1}: ${stop.name}</div>
              <div class="stop-details">
                ${stop.power_kw} kW · ${stop.distance_from_prev_km} km from prev · SoC: ${stop.soc_on_arrival}% → ${stop.soc_on_departure}%
              </div>
              <span class="stop-badge charge">~${stop.estimated_charge_time_min} min charge</span>
            </div>
          `;
        });
        html += '</div>';
      }
    }

    html += '</div>';
    resultDiv.innerHTML = html;

  } catch (err) {
    console.error('Route optimization error:', err);
    resultDiv.innerHTML = '<div class="route-result infeasible"><p style="color:#ef4444">Error optimizing route. Check console.</p></div>';
  }
}

// ═══════════════════════════════════════════════════════════
//  DATA EXPLORER
// ═══════════════════════════════════════════════════════════
async function loadDataTable() {
  const country = document.getElementById('data-country').value;
  const status = document.getElementById('data-status').value;
  let url = `/api/stations?page=${currentDataPage}&page_size=50`;
  if (country) url += `&country=${encodeURIComponent(country)}`;
  if (status) url += `&status=${encodeURIComponent(status)}`;

  try {
    const data = await fetchJSON(url);
    const tbody = document.getElementById('data-tbody');
    tbody.innerHTML = data.stations.map(s => `
      <tr>
        <td>${s.StationID}</td>
        <td>${s.AddressTitle}</td>
        <td>${s.Operator}</td>
        <td>${s.Country}</td>
        <td>${s.Town || '—'}</td>
        <td>${s.MaxPowerKW}</td>
        <td>${s.ConnectionTypes}</td>
        <td>${s.StatusType}</td>
        <td>${s.YearCreated}</td>
      </tr>
    `).join('');

    const totalPages = Math.ceil(data.total / data.page_size);
    document.getElementById('data-page-info').textContent = `Page ${data.page} of ${totalPages}`;
    document.getElementById('data-count').textContent = `${data.total.toLocaleString()} stations`;
    document.getElementById('data-prev').disabled = data.page <= 1;
    document.getElementById('data-next').disabled = data.page >= totalPages;

  } catch (err) {
    console.error('Data table error:', err);
  }
}

function dataPage(delta) {
  currentDataPage = Math.max(1, currentDataPage + delta);
  loadDataTable();
}

// ═══════════════════════════════════════════════════════════
//  HELPERS
// ═══════════════════════════════════════════════════════════
async function fetchJSON(url) {
  const res = await fetch(API + url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function animateValue(elementId, start, end, duration) {
  const el = document.getElementById(elementId);
  const range = end - start;
  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Ease out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(start + range * eased);
    el.textContent = current.toLocaleString();
    if (progress < 1) requestAnimationFrame(update);
  }

  requestAnimationFrame(update);
}

function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

async function populateCountryDropdowns() {
  try {
    const countries = await fetchJSON('/api/analytics/top-countries?n=50');
    const selects = [document.getElementById('cluster-country'), document.getElementById('data-country')];
    selects.forEach(sel => {
      if (!sel) return;
      countries.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.country;
        opt.textContent = `${c.country} (${c.count.toLocaleString()})`;
        sel.appendChild(opt);
      });
    });
  } catch (err) {
    console.error('Country dropdown error:', err);
  }
}
