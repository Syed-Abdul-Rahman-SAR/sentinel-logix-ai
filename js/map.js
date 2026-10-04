// NER-LINK AI - Leaflet Map Integration, Real-Time Fleet Tracking & Predictive Detour Visualization

window.nerMap = null;
window.mapLayers = {
  hubs: [],
  corridors: {},
  incidents: [],
  fleetMarkers: {},
  activeRoute: null,
  routeTruck: null,
  detourRoute: null,
  hazardSegment: null,
  detourBanner: null
};

// Check if Leaflet is loaded
window.initNERMap = function() {
  const mapContainer = document.getElementById("map");
  if (!mapContainer) return;

  // Cleanup if already exists
  if (window.nerMap) {
    window.nerMap.remove();
  }

  try {
    // Initialize map centered on North East India (Jorhat / Nagaon area)
    window.nerMap = L.map("map", {
      center: [25.9, 92.5],
      zoom: 7,
      minZoom: 6,
      maxZoom: 10,
      zoomControl: false,
      attributionControl: false
    });

    // Add zoom control at bottom-right
    L.control.zoom({ position: 'bottomright' }).addTo(window.nerMap);

    // OpenStreetMap tiles (no API key required - public use permitted under ODbL)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors'
    }).addTo(window.nerMap);

    // Hide fallback vector map if Leaflet loads successfully
    const fallbackMap = document.getElementById("map-fallback");
    if (fallbackMap) fallbackMap.classList.add("hidden");

    // Initial render of corridors, hubs, incidents
    window.renderMapAssets();

    // Initialize moving fleet markers
    if (window.updateMapFleetPositions) {
      window.updateMapFleetPositions();
    }
  } catch (error) {
    console.error("Leaflet failed to load or initialize. Activating SVG vector map fallback.", error);
    const fallbackMap = document.getElementById("map-fallback");
    if (fallbackMap) fallbackMap.classList.remove("hidden");
  }
};

window.renderMapAssets = function() {
  if (!window.nerMap) return;

  // 1. Clear previous static layers (keep fleetMarkers to avoid jitter)
  window.mapLayers.hubs.forEach(function(l) { window.nerMap.removeLayer(l); });
  window.mapLayers.hubs = [];

  Object.values(window.mapLayers.corridors).forEach(function(l) { window.nerMap.removeLayer(l); });
  window.mapLayers.corridors = {};

  window.mapLayers.incidents.forEach(function(l) { window.nerMap.removeLayer(l); });
  window.mapLayers.incidents = [];

  // 2. Draw Corridors (Combine base data and graph edges)
  const allCorridors = (window.nerGraph && window.nerGraph.edges) ? window.nerGraph.edges : window.nerData.corridors;

  allCorridors.forEach(function(corr) {
    let color = "#10b981"; // normal
    let weight = 4;
    let dash = null;

    if (corr.status === "minor") {
      color = "#f59e0b"; // yellow
      weight = 4.5;
    } else if (corr.status === "high_risk") {
      color = "#f97316"; // orange
      weight = 5;
    } else if (corr.status === "blocked") {
      color = "#ef4444"; // red
      weight = 6;
      dash = "8, 8";
    }

    // Distinguish alternate bypass routes
    if (corr.id && corr.id.includes("alt")) {
      color = "#06b6d4"; // cyan
      dash = "4, 6";
      weight = 3.5;
    }

    const line = L.polyline(corr.path, {
      color: color,
      weight: weight,
      opacity: 0.85,
      dashArray: dash,
      className: "corridor-line-" + corr.id
    }).addTo(window.nerMap);

    const tooltipContent = `
      <div class="p-2 text-xs bg-slate-900 border border-slate-700 rounded-md">
        <h4 class="font-bold text-white">${corr.name}</h4>
        <div class="mt-1 flex justify-between gap-4">
          <span>Status: <span class="capitalize font-semibold" style="color:${color}">${corr.status || corr.statusText || 'Operational'}</span></span>
          <span>Risk: <span class="font-semibold text-slate-200">${corr.riskScore}/100</span></span>
        </div>
        <div class="mt-0.5">Delay Penalty: <span class="font-semibold text-amber-400">${corr.delay || 'None'}</span></div>
      </div>
    `;
    line.bindTooltip(tooltipContent, { sticky: true, opacity: 0.95 });

    line.on('click', function() {
      if (window.showCorridorDetails) window.showCorridorDetails(corr.id);
    });

    window.mapLayers.corridors[corr.id] = line;
  });

  // 3. Draw Hubs
  window.nerData.hubs.forEach(function(hub) {
    let pulseColor = "green";
    if (hub.risk === "Medium") pulseColor = "yellow";
    else if (hub.risk === "High") pulseColor = "red";

    const customIcon = L.divIcon({
      className: 'custom-leaflet-marker',
      html: `
        <div class="relative w-8 h-8 flex items-center justify-center">
          <div class="marker-pulse ${pulseColor} w-6 h-6"></div>
          <div class="marker-dot ${pulseColor}"></div>
        </div>
      `,
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    });

    const marker = L.marker([hub.lat, hub.lng], { icon: customIcon }).addTo(window.nerMap);
    
    const popupContent = `
      <div class="p-1 text-slate-200 max-w-xs">
        <h3 class="font-bold text-white text-sm mb-1">${hub.name}</h3>
        <p class="text-xs text-slate-400 mb-2">${hub.state} Logistics Hub</p>
        <div class="grid grid-cols-2 gap-x-2 gap-y-1 text-xs border-t border-slate-700/50 pt-2">
          <div><span class="text-slate-400">Inbound:</span> <b class="text-white">${hub.inbound}</b></div>
          <div><span class="text-slate-400">Outbound:</span> <b class="text-white">${hub.outbound}</b></div>
          <div><span class="text-slate-400">Capacity:</span> <b class="text-white">${hub.capacity}</b></div>
          <div><span class="text-slate-400">Risk Level:</span> <b class="${pulseColor === 'red' ? 'text-red-400' : pulseColor === 'yellow' ? 'text-yellow-400' : 'text-emerald-400'}">${hub.risk}</b></div>
        </div>
        <button onclick="window.viewHubDetails('${hub.id}')" class="mt-3 w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-1 px-2 rounded text-xs transition duration-150">
          Open Analytics Depot
        </button>
      </div>
    `;
    marker.bindPopup(popupContent);
    window.mapLayers.hubs.push(marker);
  });

  // 4. Draw Incidents
  window.nerData.incidents.forEach(function(inc) {
    if (inc.status === "Resolved") return;

    let lat = 25.5;
    let lng = 92.5;

    if (inc.location.includes("NH-10") || inc.location.includes("Rangpo") || inc.location.includes("Sevoke") || inc.location.includes("Teesta")) {
      lat = 27.1770; lng = 88.5303;
    } else if (inc.location.includes("Dhemaji")) {
      lat = 27.48; lng = 94.57;
    } else if (inc.location.includes("Churachandpur")) {
      lat = 24.33; lng = 93.68;
    } else if (inc.location.includes("NH-2") || inc.location.includes("Kohima") || inc.location.includes("Dimapur")) {
      lat = 25.6751; lng = 94.1086;
    } else if (inc.location.includes("Silchar") || inc.location.includes("Jowai") || inc.location.includes("NH-6")) {
      lat = 25.3524; lng = 92.3687;
    }

    const customIcon = L.divIcon({
      className: 'custom-leaflet-marker',
      html: `
        <div class="relative w-8 h-8 flex items-center justify-center cursor-pointer">
          <div class="absolute w-8 h-8 rounded-full border-2 border-red-500/40 animate-ping"></div>
          <div class="w-6 h-6 rounded-md bg-red-600 border border-white flex items-center justify-center text-white text-xs font-bold shadow-lg">
            ⚠️
          </div>
        </div>
      `,
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    });

    const marker = L.marker([lat, lng], { icon: customIcon }).addTo(window.nerMap);
    
    const popupContent = `
      <div class="p-1 max-w-xs text-slate-200">
        <div class="flex items-center gap-1.5 mb-1 text-red-400 font-bold text-sm">
          <span>⚠️</span>
          <span>${inc.type} [${inc.severity}]</span>
        </div>
        <p class="text-xs text-slate-300 font-medium mb-1">${inc.location}</p>
        <p class="text-xs text-slate-400 mb-2">${inc.description}</p>
        <div class="text-xs border-t border-slate-700/50 pt-2 flex justify-between text-slate-400">
          <span>Detected: ${inc.detected}</span>
          <button onclick="if(window.nerMap) window.nerMap.closePopup(); window.viewIncidentDetails('${inc.id}')" class="text-blue-400 hover:text-blue-300 font-bold">Details &rarr;</button>
        </div>
      </div>
    `;
    marker.bindPopup(popupContent);
    window.mapLayers.incidents.push(marker);
  });
};

// 5. REAL-TIME FLEET MARKERS (Animates All Active Delivery Trucks on the Map)
window.updateMapFleetPositions = function() {
  if (!window.nerMap || !window.nerData || !window.nerData.shipments) return;

  window.nerData.shipments.forEach(function(ship) {
    if (!ship.currentPos) return;

    const isRerouted = ship.status === "Rerouted";
    const isDelayed = ship.status === "Delayed";
    const isHighRisk = ship.risk === "High";

    let bgBadge = "bg-blue-600";
    let borderBadge = "border-blue-400";
    let iconEmoji = "🚚";

    if (isRerouted) {
      bgBadge = "bg-emerald-600";
      borderBadge = "border-emerald-300";
      iconEmoji = "🤖";
    } else if (isDelayed || isHighRisk) {
      bgBadge = "bg-amber-600";
      borderBadge = "border-amber-300";
      iconEmoji = "⚠️";
    }

    const htmlContent = `
      <div class="relative flex flex-col items-center cursor-pointer group">
        <div class="absolute -top-4 whitespace-nowrap px-1.5 py-0.5 rounded text-[9px] font-mono font-black text-white ${bgBadge} border ${borderBadge} shadow-lg opacity-90 group-hover:opacity-100 transition">
          ${ship.id} ${isRerouted ? '• Rerouted' : ''}
        </div>
        <div class="w-7 h-7 rounded-full ${bgBadge} border-2 border-white shadow-xl flex items-center justify-center text-xs text-white">
          ${iconEmoji}
        </div>
      </div>
    `;

    if (window.mapLayers.fleetMarkers[ship.id]) {
      // Smoothly update existing marker coordinate
      window.mapLayers.fleetMarkers[ship.id].setLatLng(ship.currentPos);
      window.mapLayers.fleetMarkers[ship.id].setIcon(L.divIcon({
        className: 'custom-fleet-marker',
        html: htmlContent,
        iconSize: [28, 28],
        iconAnchor: [14, 14]
      }));
    } else {
      // Create new marker
      const customIcon = L.divIcon({
        className: 'custom-fleet-marker',
        html: htmlContent,
        iconSize: [28, 28],
        iconAnchor: [14, 14]
      });

      const marker = L.marker(ship.currentPos, { icon: customIcon }).addTo(window.nerMap);

      marker.on('click', function() {
        window.openVehicleTelemetryModal(ship.id);
      });

      window.mapLayers.fleetMarkers[ship.id] = marker;
    }
  });
};

// 6. RICH VEHICLE TELEMETRY MODAL / POPUP
window.openVehicleTelemetryModal = function(shipmentId) {
  const ship = window.nerData.shipments.find(function(s) { return s.id === shipmentId; });
  if (!ship) return;

  const drawer = document.getElementById("detail-drawer");
  const body = document.getElementById("drawer-body");
  if (!drawer || !body) return;

  const t = ship.telemetry || {
    progress: 0.45,
    speedKmh: 52,
    fuelLevel: "74%",
    vehicleNumber: "AS-01-BK-9182",
    temperature: "21°C"
  };

  const progressPct = Math.round(t.progress * 100);

  body.innerHTML = `
    <div class="space-y-4 text-slate-200">
      <div class="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <span class="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Live Vehicle Telemetry</span>
          <h2 class="text-lg font-black text-white font-mono">${ship.id}</h2>
        </div>
        <span class="px-2 py-0.5 rounded text-xs font-bold ${
          ship.status === 'Rerouted' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/30' :
          ship.status === 'Delayed' ? 'bg-red-950 text-red-400 border border-red-500/30' :
          'bg-blue-950 text-blue-400 border border-blue-500/30'
        }">${ship.status}</span>
      </div>

      <!-- Live Speed & Progress Gauges -->
      <div class="grid grid-cols-3 gap-2 text-center text-xs">
        <div class="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
          <span class="text-[9px] text-slate-400 block">Telemetry Speed</span>
          <b class="text-white font-mono text-base">${t.speedKmh} km/h</b>
        </div>
        <div class="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
          <span class="text-[9px] text-slate-400 block">Fuel Tank</span>
          <b class="text-emerald-400 font-mono text-base">${t.fuelLevel}</b>
        </div>
        <div class="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
          <span class="text-[9px] text-slate-400 block">Route Risk</span>
          <b class="${ship.risk === 'High' ? 'text-red-400' : ship.risk === 'Medium' ? 'text-amber-400' : 'text-emerald-400'} font-mono text-base">${ship.risk}</b>
        </div>
      </div>

      <!-- Route Progress Bar -->
      <div class="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs">
        <div class="flex justify-between text-slate-400 mb-1 text-[10px]">
          <span>${ship.origin}</span>
          <span>${progressPct}% Completed</span>
          <span>${ship.destination}</span>
        </div>
        <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
          <div class="bg-gradient-to-r from-blue-500 to-emerald-400 h-full rounded-full transition-all duration-300" style="width: ${progressPct}%"></div>
        </div>
      </div>

      <!-- Shipment Details -->
      <div class="space-y-2 text-xs bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
        <div class="flex justify-between"><span class="text-slate-400">Cargo Type:</span> <b class="text-white">${ship.cargo} (${ship.weight})</b></div>
        <div class="flex justify-between"><span class="text-slate-400">Priority:</span> <b class="text-white">${ship.priority}</b></div>
        <div class="flex justify-between"><span class="text-slate-400">Projected ETA:</span> <b class="text-amber-300">${ship.eta}</b></div>
        <div class="flex justify-between"><span class="text-slate-400">Registration:</span> <b class="text-slate-300 font-mono">${t.vehicleNumber}</b></div>
        <div class="flex justify-between"><span class="text-slate-400">Cargo Climate:</span> <b class="text-slate-300">${t.temperature}</b></div>
      </div>

      <!-- Timeline Logs -->
      <div class="space-y-2 pt-2">
        <h4 class="font-bold text-white text-xs uppercase tracking-wider">Telemetry Decision Log</h4>
        <div class="space-y-2 max-h-48 overflow-y-auto pr-1">
          ${ship.timeline.map(function(t) {
            return `
              <div class="p-2 rounded bg-slate-950 text-[11px] border border-slate-850">
                <span class="text-slate-400 text-[10px] block font-mono">${t.time}</span>
                <span class="text-slate-200">${t.act}</span>
              </div>
            `;
          }).join("")}
        </div>
      </div>

      <!-- Manual Predictive Reroute Action -->
      <div class="pt-2">
        <button onclick="window.triggerManualRerouteForShipment('${ship.id}')" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-3 rounded-lg text-xs transition duration-150 shadow-md shadow-blue-500/20">
          🤖 Run Predictive Reroute Evaluation
        </button>
      </div>
    </div>
  `;

  drawer.classList.remove("translate-x-full");
};

window.triggerManualRerouteForShipment = function(shipmentId) {
  const ship = window.nerData.shipments.find(function(s) { return s.id === shipmentId; });
  if (!ship) return;

  const corr = window.nerData.corridors.find(function(c) { return c.id === ship.routeId; }) || window.nerData.corridors[0];
  
  if (window.showToast) {
    window.showToast("Computing dynamic alternative for " + ship.id + "...", "info");
  }

  // Force predictive evaluation for this vehicle
  const originNode = window.cityToNodeId(ship.origin);
  const destNode = window.cityToNodeId(ship.destination);

  const altRoute = window.calculateDynamicRoute(originNode, destNode, {
    avoidCorridorIds: [corr.id],
    priority: ship.priority
  });

  if (altRoute && altRoute.success) {
    const proposal = {
      shipmentId: ship.id,
      cargo: ship.cargo,
      origin: ship.origin,
      destination: ship.destination,
      hazardLocation: corr.name,
      hazardReason: "Operator-Initiated Optimization",
      avoidedCorridorId: corr.id,
      newCorridorIds: altRoute.corridorIds,
      newPath: altRoute.coordinates,
      newEta: altRoute.etaString,
      timeSaved: "38m",
      riskBefore: corr.riskScore,
      riskAfter: altRoute.avgRiskScore,
      primaryAlternate: altRoute.primaryCorridor,
      summary: "Dynamic reroute around " + corr.name.split(" ")[0] + " optimizes safety and transit time."
    };

    window.executePredictiveReroute(proposal);
    window.openVehicleTelemetryModal(ship.id);
  }
};

// 7. PREDICTIVE DETOUR VISUALIZATION ON MAP (Draws Hazard + Detour Polyline)
window.drawPredictiveDetourOnMap = function(proposal) {
  if (!window.nerMap) return;

  // Clear previous detour overlay
  if (window.mapLayers.detourRoute) {
    window.nerMap.removeLayer(window.mapLayers.detourRoute);
    window.mapLayers.detourRoute = null;
  }
  if (window.mapLayers.hazardSegment) {
    window.nerMap.removeLayer(window.mapLayers.hazardSegment);
    window.mapLayers.hazardSegment = null;
  }

  // 1. Draw glowing cyan detour path
  window.mapLayers.detourRoute = L.polyline(proposal.newPath, {
    color: "#06b6d4", // Cyan
    weight: 5.5,
    opacity: 0.95,
    dashArray: "10, 6"
  }).addTo(window.nerMap);

  // 2. Identify avoided corridor and draw pulsing warning polyline
  const avoidedCorr = window.nerData.corridors.find(function(c) { return c.id === proposal.avoidedCorridorId; });
  if (avoidedCorr) {
    window.mapLayers.hazardSegment = L.polyline(avoidedCorr.path, {
      color: "#ef4444",
      weight: 6,
      opacity: 0.9,
      dashArray: "6, 6"
    }).addTo(window.nerMap);
  }

  // 3. Zoom map to encompass detour
  window.nerMap.fitBounds(window.mapLayers.detourRoute.getBounds(), {
    padding: [60, 60]
  });

  // 4. Render floating on-map HUD notification
  renderMapDetourHUD(proposal);
};

// Track whether the user manually dismissed the current HUD notification
window._hudDismissedForEvent = null;

function renderMapDetourHUD(proposal) {
  // Don't re-show if the user already dismissed this exact reroute event
  const eventKey = proposal.shipmentId + ':' + proposal.primaryAlternate;
  if (window._hudDismissedForEvent === eventKey) return;

  let hud = document.getElementById("map-detour-hud");
  if (!hud) {
    const mapEl = document.getElementById("map");
    const mapContainer = mapEl ? mapEl.parentElement : document.body;
    hud = document.createElement("div");
    hud.id = "map-detour-hud";
    hud.className = "absolute top-4 left-6 z-[1000] bg-slate-900/95 border-2 border-cyan-500/80 rounded-xl p-3.5 shadow-2xl backdrop-blur-md max-w-sm text-xs text-slate-200 animate-fade-in pointer-events-auto";
    mapContainer.appendChild(hud);
  }

  hud.innerHTML = `
    <div class="flex items-center justify-between mb-1.5">
      <div class="flex items-center gap-1.5 text-cyan-400 font-extrabold">
        <span class="text-base">🤖</span>
        <span>ACTIVE PREDICTIVE REROUTE</span>
      </div>
      <button onclick="window._hudDismissedForEvent='${eventKey}'; document.getElementById('map-detour-hud').classList.add('hidden')" class="text-slate-400 hover:text-white font-bold text-sm leading-none">&times;</button>
    </div>
    <div class="text-[11px] text-white font-bold mb-1">
      Shipment ${proposal.shipmentId} &rarr; ${proposal.primaryAlternate}
    </div>
    <div class="text-[10px] text-slate-300 leading-relaxed mb-2">
      Avoided <b class="text-red-400">${proposal.hazardLocation.split(" ")[0]}</b> (${proposal.hazardReason}).
    </div>
    <div class="grid grid-cols-2 gap-2 text-[10px] bg-slate-950/80 p-2 rounded border border-slate-800 text-center mb-2">
      <div><span class="text-slate-400 block">Delay Saved</span><b class="text-emerald-400 font-bold">+${proposal.timeSaved}</b></div>
      <div><span class="text-slate-400 block">Risk Reduction</span><b class="text-cyan-300 font-bold">${proposal.riskBefore}% &rarr; ${proposal.riskAfter}%</b></div>
    </div>
    <button onclick="window.openVehicleTelemetryModal('${proposal.shipmentId}')" class="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-bold py-1 px-2 rounded text-[10px] transition">
      Inspect Vehicle Telemetry
    </button>
  `;
  hud.classList.remove("hidden");
}

// 8. ROUTE HIGHLIGHTING (from Route Planner)
window.highlightRouteOnMap = function(pathCoords) {
  if (!window.nerMap) return;

  if (window.mapLayers.activeRoute) {
    window.nerMap.removeLayer(window.mapLayers.activeRoute);
  }

  window.mapLayers.activeRoute = L.polyline(pathCoords, {
    color: "#3b82f6",
    weight: 6,
    opacity: 0.95
  }).addTo(window.nerMap);

  window.nerMap.fitBounds(window.mapLayers.activeRoute.getBounds(), {
    padding: [50, 50]
  });
};

window.resetMapZoom = function() {
  if (window.nerMap) {
    window.nerMap.setView([25.9, 92.5], 7);
  }
};

// =========================================================================
// 9. DIGITAL TWIN MAP INTEGRATION LAYER (Phase 9D)
// =========================================================================
window.digitalTwinMapState = {
  activeScenarioId: null,
  highlightedDepotMarker: null,
  disruptedCorridorPolyline: null,
  shipmentMarkers: [],
  hudElement: null,
  legendElement: null
};

window.updateDigitalTwinMapOverlay = function(result) {
  if (!result || typeof result !== "object") {
    window.clearDigitalTwinMapOverlay();
    return;
  }

  // 1. Clear any existing Digital Twin map overlays first (no duplicate/accumulated overlays)
  window.clearDigitalTwinMapOverlay();

  window.digitalTwinMapState.activeScenarioId = result.scenario_id || "ACTIVE";

  if (!window.nerMap) return;

  const depotId = (result.affected_depot_id || "").toUpperCase();
  const depotName = result.affected_depot_name || result.affected_depot_id || "Depot";
  const routeId = (result.affected_route_id || "").toUpperCase();

  let targetLat = null;
  let targetLng = null;
  let targetHubName = depotName;

  // Resolve Depot Coordinates strictly from existing frontend data / hubs
  if (window.nerData && window.nerData.hubs) {
    const hubMatch = window.nerData.hubs.find(function(h) {
      const hId = (h.id || "").toUpperCase();
      const hName = (h.name || "").toUpperCase();
      return depotId.includes(hId) || hId.includes(depotId) || hName.includes(depotName.toUpperCase()) || depotName.toUpperCase().includes(hName);
    });

    if (hubMatch) {
      targetLat = hubMatch.lat;
      targetLng = hubMatch.lng;
      targetHubName = hubMatch.name;
    }
  }

  // Fallback to known depot coordinates if not matched in mock hubs (without inventing coordinates)
  if (!targetLat) {
    if (depotId.includes("IMP")) { targetLat = 24.8170; targetLng = 93.9368; }
    else if (depotId.includes("TWA")) { targetLat = 27.5800; targetLng = 91.8600; }
    else if (depotId.includes("GHY")) { targetLat = 26.1445; targetLng = 91.7363; }
    else if (depotId.includes("SHL")) { targetLat = 25.5788; targetLng = 91.8931; }
    else if (depotId.includes("SIL")) { targetLat = 24.8333; targetLng = 92.7789; }
  }

  const boundsPoints = [];

  // 2. Render Affected Depot Highlight Marker
  if (targetLat && targetLng) {
    boundsPoints.push([targetLat, targetLng]);

    const depotIcon = L.divIcon({
      className: 'custom-leaflet-marker dt-depot-marker',
      html: `
        <div class="relative w-10 h-10 flex items-center justify-center cursor-pointer">
          <div class="absolute inset-0 rounded-full bg-red-500/50 animate-ping"></div>
          <div class="w-8 h-8 rounded-full bg-red-950 border-2 border-red-500 flex items-center justify-center text-white text-xs font-black shadow-2xl">
            📦
          </div>
        </div>
      `,
      iconSize: [40, 40],
      iconAnchor: [20, 20]
    });

    const marker = L.marker([targetLat, targetLng], { icon: depotIcon, zIndexOffset: 1000 }).addTo(window.nerMap);
    
    const popupHtml = `
      <div class="p-2 text-slate-200 max-w-xs space-y-1">
        <div class="flex items-center gap-1.5 text-red-400 font-extrabold text-xs">
          <span>⚠️</span>
          <span>DIGITAL TWIN DISRUPTION TARGET</span>
        </div>
        <div class="font-black text-white text-sm">${targetHubName}</div>
        <div class="text-[10px] text-slate-400 font-mono">Depot ID: ${depotId}</div>
        <div class="text-[11px] text-amber-300 font-semibold mt-1">Severity: ${result.simulated_risk_level || result.severity || 'HIGH'}</div>
        <div class="text-[10px] text-slate-300 mt-1">${result.human_summary ? result.human_summary.substring(0, 120) + '...' : ''}</div>
      </div>
    `;
    marker.bindPopup(popupHtml);
    window.digitalTwinMapState.highlightedDepotMarker = marker;
  }

  // 3. Render Affected Route / Corridor Overlay
  let corridorMatched = false;
  if (routeId && window.nerData && window.nerData.corridors) {
    const corrMatch = window.nerData.corridors.find(function(c) {
      const cId = (c.id || "").toUpperCase();
      const cName = (c.name || "").toUpperCase();
      return routeId.includes(cId) || cId.includes(routeId) ||
             (routeId === "SIL-IMP" && (cId === "nh37" || cId === "nh2_dim")) ||
             (routeId === "GHY-SHL" && cId === "nh6") ||
             (routeId === "SIL-GHY" && cId === "nh27") ||
             (routeId === "GHY-IMP" && cId === "nh2_dim") ||
             (routeId === "TEZ-TWA" && cName.includes("TAWANG"));
    });

    if (corrMatch && corrMatch.path && corrMatch.path.length > 0) {
      corridorMatched = true;
      corrMatch.path.forEach(function(pt) { boundsPoints.push(pt); });

      const polyline = L.polyline(corrMatch.path, {
        color: "#ef4444",
        weight: 7,
        opacity: 0.95,
        dashArray: "8, 8",
        className: "dt-corridor-disruption"
      }).addTo(window.nerMap);

      const tooltipContent = `
        <div class="p-2 text-xs bg-red-950 border border-red-500/50 rounded-md text-white">
          <div class="font-extrabold flex items-center gap-1 text-red-400"><span>🚨</span> SIMULATED DISRUPTED CORRIDOR</div>
          <div class="font-bold mt-1">${corrMatch.name} (${routeId})</div>
          <div class="text-[10px] text-slate-300 mt-0.5">Disruption Duration: ${result.disruption_duration_days || 5} days</div>
        </div>
      `;
      polyline.bindTooltip(tooltipContent, { sticky: true, opacity: 0.95 });
      window.digitalTwinMapState.disruptedCorridorPolyline = polyline;
    }
  }

  // 4. Render Affected Shipment Markers (Only if actual coordinates exist in frontend data)
  const affectedShipments = result.affected_shipments || [];
  affectedShipments.forEach(function(s) {
    if (!window.nerData || !window.nerData.shipments) return;
    const matchShip = window.nerData.shipments.find(function(ms) { return ms.id === s.shipment_id; });
    if (matchShip && matchShip.currentPos) {
      boundsPoints.push(matchShip.currentPos);
      const shipIcon = L.divIcon({
        className: 'custom-fleet-marker dt-shipment-marker',
        html: `
          <div class="relative flex flex-col items-center cursor-pointer">
            <div class="absolute -top-4 whitespace-nowrap px-1.5 py-0.5 rounded text-[9px] font-mono font-black text-white bg-red-600 border border-red-400 shadow-lg">
              ${s.shipment_id} • Delayed +${s.delay_days}d
            </div>
            <div class="w-7 h-7 rounded-full bg-red-600 border-2 border-white shadow-xl flex items-center justify-center text-xs text-white animate-bounce">
              🚚
            </div>
          </div>
        `,
        iconSize: [28, 28],
        iconAnchor: [14, 14]
      });

      const sMarker = L.marker(matchShip.currentPos, { icon: shipIcon, zIndexOffset: 900 }).addTo(window.nerMap);
      sMarker.bindPopup(`
        <div class="p-2 text-xs text-slate-200">
          <div class="font-bold text-red-400">SIMULATED SHIPMENT DELAY</div>
          <div class="font-mono text-white text-sm font-black">${s.shipment_id}</div>
          <div class="text-slate-300 mt-1">Cargo: ${s.cargo_item_id || 'Supplies'} (${s.quantity || 0} qty)</div>
          <div class="text-amber-300 font-bold mt-1">Delay: +${s.delay_days} days</div>
          <div class="text-slate-400 text-[10px]">Expected Day D+${s.expected_arrival_day} &rarr; Simulated Day D+${s.simulated_arrival_day}</div>
        </div>
      `);
      window.digitalTwinMapState.shipmentMarkers.push(sMarker);
    }
  });

  // 5. Fit Map Bounds
  if (boundsPoints.length > 0) {
    try {
      window.nerMap.fitBounds(boundsPoints, { padding: [50, 50] });
    } catch(e) {}
  }

  // 6. Render Map HUD Status & Map Legend
  renderDigitalTwinMapHUD(result, corridorMatched);
};

window.clearDigitalTwinMapOverlay = function() {
  if (window.digitalTwinMapState.highlightedDepotMarker && window.nerMap) {
    window.nerMap.removeLayer(window.digitalTwinMapState.highlightedDepotMarker);
  }
  if (window.digitalTwinMapState.disruptedCorridorPolyline && window.nerMap) {
    window.nerMap.removeLayer(window.digitalTwinMapState.disruptedCorridorPolyline);
  }
  window.digitalTwinMapState.shipmentMarkers.forEach(function(m) {
    if (window.nerMap) window.nerMap.removeLayer(m);
  });

  window.digitalTwinMapState.highlightedDepotMarker = null;
  window.digitalTwinMapState.disruptedCorridorPolyline = null;
  window.digitalTwinMapState.shipmentMarkers = [];
  window.digitalTwinMapState.activeScenarioId = null;

  // Remove HUD & Legend
  const hud = document.getElementById("digital-twin-map-hud");
  if (hud) hud.remove();
  const legend = document.getElementById("digital-twin-map-legend");
  if (legend) legend.remove();

  var dtBadge = document.getElementById("sidebar-digital-twin-badge");
  if (dtBadge) { dtBadge.innerText = "READY"; dtBadge.className = "text-[8px] bg-slate-800 text-slate-300 border border-slate-700 px-1.5 py-0.5 rounded font-mono"; }
};

function renderDigitalTwinMapHUD(result, corridorMatched) {
  const mapContainer = document.getElementById("map") ? document.getElementById("map").parentElement : null;
  if (!mapContainer) return;

  let hud = document.getElementById("digital-twin-map-hud");
  if (!hud) {
    hud = document.createElement("div");
    hud.id = "digital-twin-map-hud";
    hud.className = "absolute top-4 left-6 z-[1000] bg-slate-950/95 border-2 border-red-500/80 rounded-xl p-3.5 shadow-2xl backdrop-blur-md max-w-sm text-xs text-slate-200";
    mapContainer.appendChild(hud);
  }

  var geomWarning = !corridorMatched && result.affected_route_id ? '<div class="text-[10px] text-amber-400 bg-amber-950/40 border border-amber-500/30 p-1.5 rounded mt-1.5 font-mono">⚠️ ROUTE GEOMETRY UNAVAILABLE (' + result.affected_route_id + ')</div>' : '';

  hud.innerHTML = `
    <div class="flex items-center justify-between mb-1.5">
      <div class="flex items-center gap-1.5 text-red-400 font-black text-xs uppercase tracking-wider">
        <span class="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
        <span>DIGITAL TWIN &bull; SCENARIO ACTIVE</span>
      </div>
      <button onclick="window.clearDigitalTwinMapOverlay()" class="text-slate-400 hover:text-white font-bold text-sm" title="Clear Digital Twin Map Overlay">&times;</button>
    </div>
    <div class="text-xs text-white font-bold mb-0.5">
      Target: ${result.affected_depot_name || result.affected_depot_id}
    </div>
    <div class="text-[10px] text-slate-400 font-mono mb-2">
      ${(result.scenario_type || "ROUTE_DISRUPTION").replace(/_/g, " ")} &middot; Duration: ${result.disruption_duration_days || 5}d
    </div>
    ${geomWarning}
    <div class="mt-2 flex gap-2">
      <button onclick="window.switchTab('digital-twin')" class="flex-1 bg-cyan-950 hover:bg-cyan-900 border border-cyan-500/40 text-cyan-300 font-bold py-1 px-2 rounded text-[10px] transition text-center">
        Open Results Dashboard
      </button>
      <button onclick="window.clearDigitalTwinMapOverlay()" class="bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 font-bold py-1 px-2 rounded text-[10px] transition">
        Clear Layer
      </button>
    </div>
  `;
  hud.classList.remove("hidden");

  // Render Map Legend
  let legend = document.getElementById("digital-twin-map-legend");
  if (!legend) {
    legend = document.createElement("div");
    legend.id = "digital-twin-map-legend";
    legend.className = "absolute bottom-6 left-6 z-[1000] bg-slate-950/95 border border-slate-800 rounded-lg p-2.5 shadow-xl text-[10px] text-slate-300 space-y-1.5";
    mapContainer.appendChild(legend);
  }

  legend.innerHTML = `
    <div class="font-bold text-white text-[9px] uppercase tracking-wider mb-1 border-b border-slate-800 pb-1">Digital Twin Layers</div>
    <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-full bg-red-600 border border-white shrink-0"></span><span>Affected Depot (${result.affected_depot_id})</span></div>
    <div class="flex items-center gap-2"><span class="w-4 h-1 bg-red-500 border-dashed border-red-300 shrink-0"></span><span>Disrupted Transit Corridor</span></div>
    <div class="flex items-center gap-2"><span class="text-xs">🚚</span><span>Delayed Replenishment Shipment</span></div>
  `;
}

