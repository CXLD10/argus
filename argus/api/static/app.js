/* Argus Environmental Intelligence Platform — dashboard logic */

"use strict";

// ── Map initialisation ────────────────────────────────────────────────────────

const map = L.map("map", { zoomControl: true }).setView([11.15, -61.25], 9);

L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
  attribution: "© OpenStreetMap contributors © CARTO",
  maxZoom: 18,
}).addTo(map);

// Layer groups
const obsLayer       = L.layerGroup().addTo(map);
const trajectoryLayer = L.layerGroup().addTo(map);
const impactLayer    = L.layerGroup().addTo(map);

// ── Helpers ───────────────────────────────────────────────────────────────────

function updateStatus(msg) {
  const el = document.getElementById("status-bar");
  if (el) el.textContent = msg;
}

function confidenceColor(conf) {
  if (conf >= 0.8) return "#ef4444";  // red
  if (conf >= 0.5) return "#f97316";  // orange
  return "#facc15";                   // yellow
}

// ── Load observations ─────────────────────────────────────────────────────────

async function loadObservations(aoiId) {
  try {
    const res = await fetch(`/aois/${aoiId}/observations`);
    if (!res.ok) return;
    const data = await res.json();
    obsLayer.clearLayers();

    for (const obs of data.items) {
      const color = confidenceColor(obs.confidence);
      const poly = L.geoJSON(obs.geometry, {
        style: {
          color,
          weight: 2,
          opacity: 0.9,
          fillColor: color,
          fillOpacity: 0.25,
        },
      });
      poly.bindPopup(
        `<b>${obs.obs_type}</b><br>` +
        `Confidence: ${(obs.confidence * 100).toFixed(0)}%<br>` +
        `Area: ${obs.area_km2.toFixed(1)} km²<br>` +
        `Status: <span class="badge badge-${obs.status}">${obs.status}</span>`
      );
      poly.addTo(obsLayer);
    }

    document.getElementById("obs-count").textContent  = data.count;
    document.getElementById("obs-confirmed").textContent =
      data.items.filter(o => o.status === "confirmed").length;
  } catch (err) {
    console.error("observations error:", err);
  }
}

// ── Load predictions + frames ─────────────────────────────────────────────────

async function loadPredictions(aoiId) {
  try {
    const res = await fetch(`/aois/${aoiId}/predictions`);
    if (!res.ok) return;
    const data = await res.json();
    trajectoryLayer.clearLayers();

    let frameCount = 0;
    for (const pred of data.items) {
      for (let i = 0; i < pred.frames.length; i++) {
        const frame = pred.frames[i];
        const opacity = 0.08 + 0.3 * (i / Math.max(pred.frames.length - 1, 1));
        L.geoJSON(frame.footprint, {
          style: {
            color: "#38bdf8",
            weight: 1,
            opacity: 0.6,
            fillColor: "#38bdf8",
            fillOpacity: opacity,
          },
        })
          .bindPopup(
            `<b>Trajectory frame</b><br>` +
            `Valid at: ${frame.valid_at}<br>` +
            `Particles: ${frame.particle_count}`
          )
          .addTo(trajectoryLayer);
        frameCount++;
      }
    }

    document.getElementById("pred-count").textContent  = data.count;
    document.getElementById("frame-count").textContent = frameCount;
  } catch (err) {
    console.error("predictions error:", err);
  }
}

// ── Load impact assessments ───────────────────────────────────────────────────

async function loadImpact(aoiId) {
  try {
    const res = await fetch(`/aois/${aoiId}/impact`);
    if (!res.ok) return;
    const data = await res.json();
    impactLayer.clearLayers();

    const etaPanel = document.getElementById("eta-items");
    etaPanel.innerHTML = "";

    for (const ia of data.items) {
      // ETA card in sidebar
      const card = document.createElement("div");
      card.className = "eta-item";
      const metricKey = Object.keys(ia.metrics)[0] || "";
      const metricVal = ia.metrics[metricKey];
      const metricStr = metricVal !== undefined
        ? `${metricKey}: ${Number(metricVal).toFixed(1)}`
        : "";
      card.innerHTML =
        `<div class="eta-label">${ia.exposure_layer_id}</div>` +
        `<div class="eta-value">ETA ${ia.eta_hours.toFixed(1)} h</div>` +
        (metricStr ? `<div class="eta-metric">${metricStr}</div>` : "");
      etaPanel.appendChild(card);
    }

    if (data.count === 0) {
      etaPanel.innerHTML = '<div style="color:#475569;font-size:0.78rem">No impacts detected.</div>';
    }
  } catch (err) {
    console.error("impact error:", err);
  }
}

// ── AOI discovery + bootstrap ─────────────────────────────────────────────────

async function bootstrap() {
  updateStatus("Loading…");
  try {
    const res = await fetch("/aois");
    if (!res.ok) { updateStatus("API unavailable"); return; }
    const data = await res.json();

    if (data.count === 0) { updateStatus("No AOIs configured"); return; }

    // Use the first active AOI
    const aoi = data.items.find(a => a.active) || data.items[0];
    document.getElementById("aoi-name").textContent = aoi.name;
    updateStatus(`AOI: ${aoi.name}`);

    await Promise.all([
      loadObservations(aoi.id),
      loadPredictions(aoi.id),
      loadImpact(aoi.id),
    ]);

    updateStatus(`${aoi.name} — ready`);
  } catch (err) {
    updateStatus("Error loading data");
    console.error(err);
  }
}

document.addEventListener("DOMContentLoaded", bootstrap);
