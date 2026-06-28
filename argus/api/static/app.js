/* Argus Environmental Intelligence Platform — dashboard logic */

"use strict";

// ── Map initialisation ────────────────────────────────────────────────────────

const map = L.map("map", { zoomControl: true }).setView([11.15, -61.25], 9);

L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
  attribution: "© OpenStreetMap contributors © CARTO",
  maxZoom: 18,
}).addTo(map);

// Layer groups
const obsLayer        = L.layerGroup().addTo(map);
const trajectoryLayer = L.layerGroup().addTo(map);
const impactLayer     = L.layerGroup().addTo(map);
const wqLayer         = L.layerGroup().addTo(map);

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

// ── Water Quality (D2) ───────────────────────────────────────────────────────

function wqRiskColor(anomalyItems) {
  // Returns a colour based on the highest z_score across anomaly predictions.
  const sigmas = anomalyItems.map(p => Math.abs((p.uncertainty && p.uncertainty.sigma) || 0));
  const max = sigmas.length ? Math.max(...sigmas) : 0;
  if (max >= 3.0) return "#ef4444";   // high risk: red
  if (max >= 2.0) return "#f97316";   // medium risk: orange
  return "#22c55e";                   // low / normal: green
}

async function loadWQReport(targetId) {
  try {
    const res = await fetch(`/waterbody/${targetId}/report`);
    if (!res.ok) return;
    const data = await res.json();
    const panel = document.getElementById("report-panel");
    const textEl = document.getElementById("report-text");
    if (panel && textEl) {
      panel.style.display = "";
      textEl.textContent = data.text || "No report available.";
    }
  } catch (err) {
    console.error("WQ report error:", err);
  }
}

async function loadWQTarget(targetId) {
  try {
    const [obsRes, anomRes] = await Promise.all([
      fetch(`/waterbody/${targetId}/observations?obs_type=chlorophyll_a`),
      fetch(`/waterbody/${targetId}/anomalies`),
    ]);

    const obsData  = obsRes.ok  ? await obsRes.json()  : { items: [] };
    const anomData = anomRes.ok ? await anomRes.json() : { items: [] };

    const color = wqRiskColor(anomData.items);

    // Draw water body polygon if any observation has a polygon geometry
    wqLayer.clearLayers();
    for (const obs of obsData.items) {
      if (obs.geometry && obs.geometry.type === "Polygon") {
        L.geoJSON(obs.geometry, {
          style: { color, weight: 2, opacity: 0.9, fillColor: color, fillOpacity: 0.2 },
        })
          .bindPopup(`<b>Water body: ${targetId}</b><br>Type: ${obs.obs_type}`)
          .addTo(wqLayer);
      }
    }

    // Build trend list (latest 10 obs, newest first)
    const recent = obsData.items.slice(0, 10);
    const wqList = document.getElementById("wq-list");
    if (!wqList) return;

    const statusDot = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};margin-right:6px"></span>`;
    const riskLabel = color === "#ef4444" ? "HIGH RISK" : color === "#f97316" ? "ELEVATED" : "Normal";

    let html = `<div class="stat-row" style="margin-bottom:4px">
      <span>${statusDot}${targetId}</span>
      <span class="stat-value" style="color:${color}">${riskLabel}</span>
    </div>`;

    if (recent.length) {
      html += `<div style="font-size:0.72rem;color:#64748b;margin:6px 0 2px">Recent chl-a (µg/L)</div>`;
      html += `<table style="width:100%;font-size:0.72rem;border-collapse:collapse">`;
      for (const obs of recent) {
        const val = obs.value != null ? Number(obs.value).toFixed(1) : "—";
        const dt  = obs.created_at ? obs.created_at.slice(0, 10) : "—";
        html += `<tr><td style="color:#94a3b8">${dt}</td><td style="text-align:right">${val}</td></tr>`;
      }
      html += "</table>";
    } else {
      html += `<div style="color:#475569;font-size:0.78rem">No observations.</div>`;
    }

    if (anomData.count > 0) {
      html += `<div style="font-size:0.72rem;color:#64748b;margin-top:6px">Anomaly flags: ${anomData.count}</div>`;
    }

    wqList.innerHTML = html;

    const panel = document.getElementById("wq-panel");
    if (panel) panel.style.display = "";

    // Load AI report after populating the WQ panel
    await loadWQReport(targetId);
  } catch (err) {
    console.error("WQ target error:", err);
  }
}

async function loadWaterbodies() {
  try {
    const res = await fetch("/waterbodies");
    if (!res.ok) return;
    const data = await res.json();
    for (const targetId of data.target_ids) {
      await loadWQTarget(targetId);
    }
  } catch (err) {
    console.error("waterbodies error:", err);
  }
}

// ── System status panel (F-039) ───────────────────────────────────────────────

async function loadSystemStatus() {
  try {
    const res = await fetch("/status");
    if (!res.ok) return;
    const s = await res.json();

    const panel = document.getElementById("system-status-panel");
    if (!panel) return;

    const quota = s.quota || {};
    const usedMB = ((quota.cdse_bytes_today || 0) / 1048576).toFixed(1);
    const limitGB = (quota.cdse_daily_limit_gb || 1.0).toFixed(1);
    const remMB   = ((quota.cdse_remaining_bytes || 0) / 1048576).toFixed(0);

    let html = `<div style="font-size:0.7rem;color:#94a3b8;margin-bottom:6px">
      CDSE: ${usedMB} MB used / ${limitGB} GB limit (${remMB} MB remaining)
    </div>`;

    if (s.last_analysis_run_at) {
      html += `<div style="font-size:0.7rem;color:#94a3b8;margin-bottom:6px">
        Last analysis: ${new Date(s.last_analysis_run_at).toLocaleString()}
      </div>`;
    }

    if (s.domain_runs && s.domain_runs.length > 0) {
      html += `<div style="font-size:0.7rem;color:#cbd5e1;margin-bottom:4px">Domain runs:</div>`;
      for (const run of s.domain_runs) {
        const ts = run.last_run_at ? new Date(run.last_run_at).toLocaleString() : "—";
        const dot = run.last_run_status === "complete"
          ? `<span style="color:#22c55e">●</span>`
          : `<span style="color:#ef4444">●</span>`;
        html += `<div style="font-size:0.65rem;color:#94a3b8;padding-left:8px">
          ${dot} ${run.domain_id}/${run.aoi_id} — ${ts}
          (${run.scenes_fetched} scenes, ${run.observations_created} obs)
        </div>`;
      }
    }

    panel.innerHTML = html;
  } catch (err) {
    console.warn("Status panel load failed:", err);
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
      loadWaterbodies(),
      loadSystemStatus(),
    ]);

    updateStatus(`${aoi.name} — ready`);
  } catch (err) {
    updateStatus("Error loading data");
    console.error(err);
  }
}

document.addEventListener("DOMContentLoaded", bootstrap);
