// NER-LINK AI - Main Application Controller

document.addEventListener("DOMContentLoaded", () => {
  // Initialize navigation & view routers
  window.initAppRouting();
  
  // Initialize Toast notifier
  window.initToast();

  // Populate data tables & dashboards
  window.refreshDashboardUI();

  // Initialize Leaflet map
  if (window.initNERMap) {
    window.initNERMap();
  }

  // Bind forms & search
  window.bindFormEvents();

  // Render Charts
  window.initCharts();

  // Initialize Real-Time Telemetry & Predictive Engine
  if (window.startRealtimeEngine) {
    window.startRealtimeEngine();
  }
});

// View Routing Switcher
window.currentTab = "overview";
window.currentRole = "admin"; // admin, operator, citizen
window.selectedState = "all";

window.switchTab = function(tabId) {
  window.currentTab = tabId;

  // Toggle active sidebar items
  const navItems = document.querySelectorAll(".nav-item");
  navItems.forEach(item => {
    if (item.getAttribute("data-tab") === tabId) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Toggle visible sections
  const sections = document.querySelectorAll(".view-section");
  sections.forEach(sec => {
    if (sec.id === tabId) {
      sec.classList.remove("hidden");
    } else {
      sec.classList.add("hidden");
    }
  });

  // Resize Leaflet Map when switching to Live Map
  if (tabId === "map" && window.nerMap) {
    setTimeout(() => {
      window.nerMap.invalidateSize();
    }, 100);
  }

  // Update specific view components
  if (tabId === "analytics") {
    setTimeout(() => window.initCharts(), 150);
  }
  if (tabId === "sentinel-inventory") {
    setTimeout(() => window.fetchSentinelData(), 100);
  }
  // Refresh overview content every time it's revisited so it stays populated
  if (tabId === "overview") {
    setTimeout(() => {
      window.refreshDashboardUI();
      if (window.fetchSentinelData) window.fetchSentinelData();
    }, 80);
  }
  // Load route vulnerability data when visiting risk tab
  if (tabId === "risk") {
    setTimeout(() => window.fetchRiskCorridors(), 100);
  }
  // Trigger intelligence data fetch for intelligence-heavy tabs
  if (tabId === "forecast" || tabId === "readiness" || tabId === "unified-intel") {
    if (window.fetchIntelligenceDashboard) {
      setTimeout(() => window.fetchIntelligenceDashboard(), 100);
    }
  }
};


window.initAppRouting = function() {
  const navItems = document.querySelectorAll(".nav-item");
  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const tabId = item.getAttribute("data-tab");
      window.switchTab(tabId);
    });
  });

  // Role toggle bindings
  const roleSelect = document.getElementById("role-selector");
  if (roleSelect) {
    roleSelect.addEventListener("change", (e) => {
      window.currentRole = e.target.value;
      window.applyRoleVisibility();
      window.showToast(`User interface switched to ${window.currentRole.toUpperCase()} mode.`, "info");
    });
  }

  // State selector bindings
  const stateSelect = document.getElementById("state-selector");
  if (stateSelect) {
    stateSelect.addEventListener("change", (e) => {
      window.selectedState = e.target.value;
      window.refreshDashboardUI();
      window.showToast(`Dashboard filtered by state: ${e.target.value.toUpperCase()}`, "info");
    });
  }
};

// Role-Based UI Customization
window.applyRoleVisibility = function() {
  const role = window.currentRole;
  
  // Elements that require Admin mode
  const adminElements = document.querySelectorAll(".role-admin-only");
  adminElements.forEach(el => {
    if (role === "admin") el.classList.remove("hidden");
    else el.classList.add("hidden");
  });

  // Elements that require Operator mode
  const operatorElements = document.querySelectorAll(".role-operator-only");
  operatorElements.forEach(el => {
    if (role === "operator" || role === "admin") el.classList.remove("hidden");
    else el.classList.add("hidden");
  });

  // Citizen mode overrides
  const citizenDisclaimer = document.getElementById("citizen-view-disclaimer");
  if (citizenDisclaimer) {
    if (role === "citizen") citizenDisclaimer.classList.remove("hidden");
    else citizenDisclaimer.classList.add("hidden");
  }
};

// Form and Interactivity Bindings
window.bindFormEvents = function() {
  // Route planner form
  const routeForm = document.getElementById("route-planner-form");
  if (routeForm) {
    routeForm.addEventListener("submit", (e) => {
      e.preventDefault();
      window.generateAIRoutes();
    });
  }

  // Incident simulator form
  const simForm = document.getElementById("simulation-form");
  if (simForm) {
    simForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const type = document.getElementById("sim-incident-type").value;
      const corridor = document.getElementById("sim-corridor").value;
      if (window.runImpactSimulation) {
        window.runImpactSimulation(type, corridor);
      }
    });
  }

  // AI Copilot trigger buttons
  const copBtn = document.getElementById("copilot-trigger-btn");
  const copPanel = document.getElementById("copilot-panel");
  const closeCop = document.getElementById("close-copilot-btn");
  if (copBtn && copPanel) {
    copBtn.addEventListener("click", () => {
      copPanel.classList.toggle("translate-x-full");
    });
  }
  if (closeCop && copPanel) {
    closeCop.addEventListener("click", () => {
      copPanel.classList.add("translate-x-full");
    });
  }

  // Copilot message submission
  const copSubmit = document.getElementById("send-copilot-msg-btn");
  const copInput = document.getElementById("copilot-input");
  if (copSubmit && copInput) {
    const sendMsg = () => {
      const val = copInput.value.trim();
      if (val) {
        copInput.value = "";
        window.askAICopilot(val);
      }
    };
    copSubmit.addEventListener("click", sendMsg);
    copInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") sendMsg();
    });
  }

  // Global Search Box
  const searchInput = document.getElementById("global-search-input");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      const query = e.target.value;
      if (window.executeGlobalSearch) {
        window.executeGlobalSearch(query);
      }
    });
    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        const overlay = document.getElementById("search-results-overlay");
        if (overlay) overlay.classList.add("hidden");
      }
    });
  }

  // Citizen Issue Reporter
  const reportForm = document.getElementById("citizen-report-form");
  if (reportForm) {
    reportForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const type = document.getElementById("rep-type").value;
      const loc = document.getElementById("rep-loc").value;
      const desc = document.getElementById("rep-desc").value;

      window.nerData.incidents.unshift({
        id: `rep-${Date.now()}`,
        type: type,
        location: loc,
        state: "Assam", // Default
        severity: "Medium",
        detected: "Just now",
        affectedRoutes: "Local Roads",
        status: "Active",
        description: desc + " [Reported by Public Citizen]"
      });

      window.nerData.alerts.unshift({
        id: `alert-rep-${Date.now()}`,
        severity: "warning",
        text: `Citizen reported issue: ${type} at ${loc}. Checking verification status.`,
        timestamp: "Just now",
        acknowledged: false
      });

      window.showToast("Incident report submitted. AI validating route impact.", "success");
      reportForm.reset();
      window.refreshDashboardUI();
      if (window.renderMapAssets) window.renderMapAssets();
    });
  }
};

// Generate AI route options from planner
window.generateAIRoutes = function() {
  const container = document.getElementById("route-results-container");
  if (!container) return;

  // Show loading skeleton
  container.innerHTML = `
    <div class="space-y-3 p-2 animate-pulse">
      <div class="h-4 bg-slate-800 rounded w-1/3"></div>
      <div class="h-20 bg-slate-800 rounded"></div>
      <div class="h-20 bg-slate-800 rounded"></div>
      <div class="h-20 bg-slate-800 rounded"></div>
    </div>
  `;
  container.classList.remove("hidden");

  const origin = document.getElementById("route-origin").value;
  const destination = document.getElementById("route-destination").value;
  const cargo = document.getElementById("route-cargo").value;
  const priority = document.getElementById("route-priority").value;

  setTimeout(() => {
    const origNode = window.cityToNodeId ? window.cityToNodeId(origin) : "ghy";
    const destNode = window.cityToNodeId ? window.cityToNodeId(destination) : "imp";

    // 1. Calculate Primary AI-Optimal Route
    let r1 = window.calculateDynamicRoute ? window.calculateDynamicRoute(origNode, destNode, { priority }) : null;
    
    // Fallback if same city or null
    if (!r1 || !r1.success || r1.coordinates.length === 0) {
      const fallbackCorr = window.nerData.corridors[0];
      r1 = {
        success: true,
        coordinates: fallbackCorr.path,
        distanceKm: 384,
        etaString: "8h 15m",
        avgRiskScore: 18,
        accessibilityScore: 94,
        primaryCorridor: fallbackCorr.name
      };
    }

    // 2. Calculate Secondary Alternative (bypassing primary corridor)
    const avoidPrimary = (r1.corridorIds && r1.corridorIds[0]) ? [r1.corridorIds[0]] : [];
    let r2 = window.calculateDynamicRoute ? window.calculateDynamicRoute(origNode, destNode, { avoidCorridorIds: avoidPrimary, priority }) : null;
    if (!r2 || !r2.success || r2.coordinates.length === 0) {
      r2 = {
        success: true,
        coordinates: r1.coordinates,
        distanceKm: Math.round(r1.distanceKm * 1.12),
        etaString: "9h 30m",
        avgRiskScore: Math.min(85, r1.avgRiskScore + 18),
        accessibilityScore: Math.max(40, r1.accessibilityScore - 12),
        primaryCorridor: "Alternate Mountain Ridge Segment"
      };
    }

    // 3. Calculate Valley / Low-Risk Alternate
    let r3 = {
      success: true,
      coordinates: r2.coordinates,
      distanceKm: Math.round(r1.distanceKm * 1.25),
      etaString: "10h 45m",
      avgRiskScore: 12,
      accessibilityScore: 97,
      primaryCorridor: "Valley Bypass Route"
    };

    const r1Score = Math.max(70, Math.min(98, Math.round(100 - (r1.avgRiskScore * 0.4))));
    const r2Score = Math.max(50, Math.min(88, Math.round(100 - (r2.avgRiskScore * 0.5))));
    const r3Score = Math.max(65, Math.min(92, Math.round(100 - (r3.avgRiskScore * 0.3) - 10)));

    container.innerHTML = `
      <div class="flex justify-between items-center mb-3">
        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-400">Dynamic AI Paths Generated</h3>
        <span class="text-[10px] text-emerald-400 bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 rounded font-bold">
          ⚡ Live Graph Pathfinding
        </span>
      </div>
      
      <div class="space-y-3">
        <!-- Route 1: AI Recommended -->
        <div class="p-4 rounded-lg bg-blue-950/20 border border-blue-500/40 relative hover:border-blue-500 transition duration-150">
          <div class="absolute top-3 right-3 bg-blue-600 text-white text-[9px] uppercase tracking-widest font-extrabold px-1.5 py-0.5 rounded shadow">AI Recommended</div>
          <div class="text-xs font-bold text-white mb-1">${r1.primaryCorridor}</div>
          <div class="grid grid-cols-4 gap-2 text-center text-[10px] mb-2 border-b border-slate-800/80 pb-2">
            <div><span class="text-slate-400 block">ETA</span><b class="text-white">${r1.etaString}</b></div>
            <div><span class="text-slate-400 block">Distance</span><b class="text-white">${r1.distanceKm} km</b></div>
            <div><span class="text-slate-400 block">Risk</span><b class="${r1.avgRiskScore < 30 ? 'text-emerald-400' : 'text-amber-400'}">${r1.avgRiskScore < 30 ? 'Low' : 'Moderate'} (${r1.avgRiskScore}/100)</b></div>
            <div><span class="text-slate-400 block">Accessibility</span><b class="text-white">${r1.accessibilityScore}%</b></div>
          </div>
          <p class="text-[11px] text-slate-300 leading-normal italic mb-3">
            “Recommended optimal route based on live weather and road stability sensors. Avoids predicted congestion queues.”
          </p>
          <div class="flex items-center justify-between">
            <div class="flex gap-1.5">
              <span class="text-[10px] text-slate-400">AI Score: <b class="text-white">${r1Score}/100</b></span>
              <span class="text-[10px] text-slate-400">Reliability: <b class="text-emerald-400">${r1.accessibilityScore}%</b></span>
            </div>
            <button onclick="window.confirmRouteSelection('${JSON.stringify(r1.coordinates)}', '${r1.primaryCorridor.replace(/'/g, "")}')" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-1.5 px-3 rounded text-[11px] transition shadow-md shadow-blue-500/20">
              Select & Dispatch &rarr;
            </button>
          </div>
        </div>

        <!-- Route 2: Secondary Mountain Path -->
        <div class="p-4 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition duration-150">
          <div class="text-xs font-bold text-slate-300 mb-1">Direct Alternate (${r2.primaryCorridor})</div>
          <div class="grid grid-cols-4 gap-2 text-center text-[10px] mb-2 border-b border-slate-800/80 pb-2">
            <div><span class="text-slate-400 block">ETA</span><b class="text-white">${r2.etaString}</b></div>
            <div><span class="text-slate-400 block">Distance</span><b class="text-white">${r2.distanceKm} km</b></div>
            <div><span class="text-slate-400 block">Risk</span><b class="text-amber-400">${r2.avgRiskScore}/100</b></div>
            <div><span class="text-slate-400 block">Accessibility</span><b class="text-white">${r2.accessibilityScore}%</b></div>
          </div>
          <p class="text-[11px] text-slate-400 leading-normal mb-3">
            Secondary transit corridor. May encounter localized rainfall or moisture elevation along ridgelines.
          </p>
          <div class="flex items-center justify-between">
            <div class="flex gap-1.5">
              <span class="text-[10px] text-slate-400">AI Score: <b class="text-white">${r2Score}/100</b></span>
              <span class="text-[10px] text-slate-400">Reliability: <b class="text-white">${r2.accessibilityScore}%</b></span>
            </div>
            <button onclick="window.confirmRouteSelection('${JSON.stringify(r2.coordinates)}', 'Route 2')" class="bg-slate-800 hover:bg-slate-700 text-white font-bold py-1 px-3 rounded text-[11px] transition">
              Select Route
            </button>
          </div>
        </div>

        <!-- Route 3: Valley Bypass -->
        <div class="p-4 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition duration-150">
          <div class="text-xs font-bold text-slate-300 mb-1">Low-Risk Flatland Bypass (${r3.primaryCorridor})</div>
          <div class="grid grid-cols-4 gap-2 text-center text-[10px] mb-2 border-b border-slate-800/80 pb-2">
            <div><span class="text-slate-400 block">ETA</span><b class="text-white">${r3.etaString}</b></div>
            <div><span class="text-slate-400 block">Distance</span><b class="text-white">${r3.distanceKm} km</b></div>
            <div><span class="text-slate-400 block">Risk</span><b class="text-emerald-400 font-bold">Ultra Low (${r3.avgRiskScore}/100)</b></div>
            <div><span class="text-slate-400 block">Accessibility</span><b class="text-white">${r3.accessibilityScore}%</b></div>
          </div>
          <p class="text-[11px] text-slate-400 leading-normal mb-3">
            Maximum safety corridor. Bypasses mountain passes entirely but incurs additional travel distance.
          </p>
          <div class="flex items-center justify-between">
            <div class="flex gap-1.5">
              <span class="text-[10px] text-slate-400">AI Score: <b class="text-white">${r3Score}/100</b></span>
              <span class="text-[10px] text-slate-400">Reliability: <b class="text-white">${r3.accessibilityScore}%</b></span>
            </div>
            <button onclick="window.confirmRouteSelection('${JSON.stringify(r3.coordinates)}', 'Route 3')" class="bg-slate-800 hover:bg-slate-700 text-white font-bold py-1 px-3 rounded text-[11px] transition">
              Select Route
            </button>
          </div>
        </div>
      </div>

      <!-- Explainable Scoring Card -->
      <div class="mt-4 p-4 rounded-lg bg-slate-900/80 border border-slate-800 text-xs">
        <h4 class="font-bold text-white mb-2 flex items-center gap-1.5">
          <span>🧠</span>
          <span>Explainable AI Route Score Model (Live Factors)</span>
        </h4>
        <div class="space-y-2">
          <div>
            <div class="flex justify-between text-slate-400 text-[10px] mb-0.5">
              <span>Road Accessibility Weight (30%)</span>
              <span class="text-white">${r1.accessibilityScore}/100</span>
            </div>
            <div class="w-full bg-slate-800 h-1 rounded-full overflow-hidden">
              <div class="bg-emerald-500 h-full" style="width: ${r1.accessibilityScore}%"></div>
            </div>
          </div>
          <div>
            <div class="flex justify-between text-slate-400 text-[10px] mb-0.5">
              <span>Safety & Slope Stability (25%)</span>
              <span class="text-white">${100 - r1.avgRiskScore}/100</span>
            </div>
            <div class="w-full bg-slate-800 h-1 rounded-full overflow-hidden">
              <div class="bg-blue-500 h-full" style="width: ${100 - r1.avgRiskScore}%"></div>
            </div>
          </div>
          <div>
            <div class="flex justify-between text-slate-400 text-[10px] mb-0.5">
              <span>Weather Saturation Index (20%)</span>
              <span class="text-white">89/100</span>
            </div>
            <div class="w-full bg-slate-800 h-1 rounded-full overflow-hidden">
              <div class="bg-yellow-500 h-full" style="width: 89%"></div>
            </div>
          </div>
          <div>
            <div class="flex justify-between text-slate-400 text-[10px] mb-0.5">
              <span>Travel Time Efficiency (15%)</span>
              <span class="text-white">92/100</span>
            </div>
            <div class="w-full bg-slate-800 h-1 rounded-full overflow-hidden">
              <div class="bg-emerald-400 h-full" style="width: 92%"></div>
            </div>
          </div>
          <div>
            <div class="flex justify-between text-slate-400 text-[10px] mb-0.5">
              <span>Transit Margin & Fuel (10%)</span>
              <span class="text-white">85/100</span>
            </div>
            <div class="w-full bg-slate-800 h-1 rounded-full overflow-hidden">
              <div class="bg-amber-600 h-full" style="width: 85%"></div>
            </div>
          </div>
        </div>
        <div class="mt-3 pt-2.5 border-t border-slate-800 flex justify-between font-bold text-white text-xs">
          <span>Overall AI Route Score</span>
          <span class="text-emerald-400">${r1Score}/100</span>
        </div>
      </div>
    `;
  }, 700);
};

window.confirmRouteSelection = function(coordsString, name) {
  const coords = JSON.parse(coordsString);
  window.switchTab("map");
  if (window.highlightRouteOnMap) {
    window.highlightRouteOnMap(coords);
  }
  window.showToast(`${name} selected and mapped. Delivery vehicle initiated.`, "success");
};

// UI Reactive Refresh (Re-renders tables, KPI metrics based on mock data changes)
window.refreshDashboardUI = function() {
  const data = window.nerData;

  // Filter calculations based on state selector
  let filteredShipments = data.shipments;
  let filteredIncidents = data.incidents;
  let avgEta = "8h 42m";
  let activeShipmentsCount = 1284;
  let accessiblePct = "87%";
  let criticalCount = 12;
  let highRiskCount = 7;
  let optimizedCount = 436;

  if (window.selectedState !== "all") {
    const sName = data.states.find(s => s.id === window.selectedState)?.name || "";
    filteredShipments = data.shipments.filter(s => s.origin.includes(sName) || s.destination.includes(sName));
    filteredIncidents = data.incidents.filter(i => i.state === sName);
    
    // Scaling metrics down for individual states
    activeShipmentsCount = Math.floor(Math.random() * 200) + 50;
    const stateObj = data.states.find(s => s.id === window.selectedState);
    accessiblePct = stateObj ? `${stateObj.score}%` : "87%";
    criticalCount = filteredIncidents.filter(i => i.severity === "Critical" || i.severity === "High").length;
    highRiskCount = Math.max(0, criticalCount - 1);
    optimizedCount = Math.floor(activeShipmentsCount * 0.45);
    avgEta = "6h 15m";
  } else {
    // Standard baseline overview values, updated if simulation runs
    const blockedCount = data.corridors.filter(c => c.status === "blocked").length;
    if (blockedCount > 0) {
      accessiblePct = "75%";
      criticalCount = 13;
      highRiskCount = 8;
      avgEta = "9h 38m";
    }
  }

  // Update Overview KPIs
  const elActive = document.getElementById("kpi-active-shipments");
  const elAccess = document.getElementById("kpi-accessible-routes");
  const elDisrupt = document.getElementById("kpi-critical-disruptions");
  const elRisk = document.getElementById("kpi-high-risk");
  const elEta = document.getElementById("kpi-avg-eta");
  const elOpt = document.getElementById("kpi-ai-optimized");

  if (elActive) elActive.innerText = activeShipmentsCount.toLocaleString();
  if (elAccess) elAccess.innerText = accessiblePct;
  if (elDisrupt) elDisrupt.innerText = criticalCount;
  if (elRisk) elRisk.innerText = highRiskCount;
  if (elEta) elEta.innerText = avgEta;
  if (elOpt) elOpt.innerText = optimizedCount;

  // 1. Render Incident Table (Disruption Page)
  const incTable = document.getElementById("incidents-table-body");
  if (incTable) {
    incTable.innerHTML = filteredIncidents.map(inc => `
      <tr id="incident-row-${inc.id}" onclick="window.viewIncidentDetails('${inc.id}')" class="border-b border-slate-800 hover:bg-slate-800/40 cursor-pointer transition">
        <td class="px-4 py-3 font-semibold text-white text-xs">${inc.type}</td>
        <td class="px-4 py-3 text-slate-300 text-xs">${inc.location}</td>
        <td class="px-4 py-3 text-slate-300 text-xs">${inc.state}</td>
        <td class="px-4 py-3 text-xs">
          <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${
            inc.severity === 'Critical' ? 'bg-red-950 text-red-400 border border-red-500/30' :
            inc.severity === 'High' ? 'bg-orange-950 text-orange-400 border border-orange-500/20' :
            'bg-yellow-950 text-yellow-400 border border-yellow-500/20'
          }">${inc.severity}</span>
        </td>
        <td class="px-4 py-3 text-slate-400 text-xs">${inc.detected}</td>
        <td class="px-4 py-3 text-slate-300 text-xs">${inc.affectedRoutes}</td>
        <td class="px-4 py-3 text-xs">
          <span class="px-1.5 py-0.5 rounded text-[10px] font-semibold ${
            inc.status === 'Active' ? 'bg-red-950/40 text-red-300' : 'bg-slate-800 text-slate-400'
          }">${inc.status}</span>
        </td>
      </tr>
    `).join("");
  }

  // 2. Render Shipment Table
  const shipTable = document.getElementById("shipments-table-body");
  if (shipTable) {
    shipTable.innerHTML = filteredShipments.map(ship => {
      const prog = Math.round((ship.telemetry ? ship.telemetry.progress : 0.45) * 100);
      const spd = ship.telemetry ? ship.telemetry.speedKmh : 52;
      return `
        <tr id="shipment-row-${ship.id}" class="border-b border-slate-800 hover:bg-slate-800/40 transition cursor-pointer">
          <td class="px-4 py-3 font-mono font-bold text-white text-xs" onclick="window.openVehicleTelemetryModal('${ship.id}')">
            <div class="flex items-center gap-1.5">
              <span class="text-blue-400">🚚</span>
              <span>${ship.id}</span>
            </div>
          </td>
          <td class="px-4 py-3 text-slate-300 text-xs" onclick="window.openVehicleTelemetryModal('${ship.id}')">${ship.origin} &rarr; ${ship.destination}</td>
          <td class="px-4 py-3 text-slate-300 text-xs" onclick="window.openVehicleTelemetryModal('${ship.id}')">${ship.cargo}</td>
          <td class="px-4 py-3 text-xs" onclick="window.openVehicleTelemetryModal('${ship.id}')">
            <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${
              ship.priority === 'Emergency' ? 'bg-red-950 text-red-400 border border-red-500/30' :
              ship.priority === 'High' ? 'bg-amber-950 text-amber-400 border border-amber-500/20' :
              'bg-slate-800 text-slate-300'
            }">${ship.priority}</span>
          </td>
          <td class="px-4 py-3 text-xs" onclick="window.openVehicleTelemetryModal('${ship.id}')">
            <span class="font-semibold ${
              ship.risk === 'High' ? 'text-red-400' :
              ship.risk === 'Medium' ? 'text-amber-400' : 'text-emerald-400'
            }">${ship.risk}</span>
          </td>
          <td class="px-4 py-3 text-xs">
            <div class="w-24">
              <div class="flex justify-between text-[9px] text-slate-400 mb-0.5">
                <span id="shipment-progress-pct-${ship.id}">${prog}%</span>
                <span>${spd} km/h</span>
              </div>
              <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div id="shipment-progress-bar-${ship.id}" class="bg-gradient-to-r from-blue-500 to-emerald-400 h-full rounded-full transition-all duration-300" style="width: ${prog}%"></div>
              </div>
            </div>
          </td>
          <td class="px-4 py-3 text-slate-300 text-xs font-mono font-medium">${ship.eta}</td>
          <td class="px-4 py-3 text-xs">
            <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${
              ship.status === 'Rerouted' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/30' :
              ship.status === 'Delayed' ? 'bg-red-950 text-red-400 border border-red-500/30' :
              'bg-blue-950 text-blue-400 border border-blue-500/20'
            }">${ship.status === 'Rerouted' ? '🤖 Rerouted' : ship.status}</span>
          </td>
          <td class="px-4 py-3 text-xs text-right">
            <button onclick="event.stopPropagation(); window.openVehicleTelemetryModal('${ship.id}')" class="bg-slate-800 hover:bg-slate-750 border border-slate-700 hover:border-blue-500 text-slate-200 text-[10px] font-bold py-1 px-2 rounded transition">
              Telemetry &rarr;
            </button>
          </td>
        </tr>
      `;
    }).join("");
  }

  // 3. Render Hubs Table
  const hubsTable = document.getElementById("hubs-table-body");
  if (hubsTable) {
    hubsTable.innerHTML = data.hubs.map(hub => `
      <tr onclick="window.viewHubDetails('${hub.id}')" class="border-b border-slate-800 hover:bg-slate-800/40 cursor-pointer transition">
        <td class="px-4 py-3 font-semibold text-white text-xs">${hub.name}</td>
        <td class="px-4 py-3 text-slate-300 text-xs">${hub.state}</td>
        <td class="px-4 py-3 text-slate-300 text-xs">${hub.inbound} units</td>
        <td class="px-4 py-3 text-slate-300 text-xs">${hub.outbound} units</td>
        <td class="px-4 py-3 text-slate-300 text-xs">${hub.capacity}</td>
        <td class="px-4 py-3 text-slate-300 text-xs">${hub.congestion}</td>
        <td class="px-4 py-3 text-slate-300 text-xs">${hub.avgProcessing}</td>
      </tr>
    `).join("");
  }

  // 4. Update Alerts Panel
  const alertsList = document.getElementById("alerts-list-container");
  if (alertsList) {
    alertsList.innerHTML = data.alerts.map(alert => `
      <div id="alert-card-${alert.id}" class="p-3 rounded-lg flex items-start justify-between gap-3 border ${
        alert.severity === 'critical' ? 'bg-red-950/20 border-red-500/30' :
        alert.severity === 'high' ? 'bg-orange-950/20 border-orange-500/20' :
        'bg-yellow-950/20 border-yellow-500/20'
      } ${alert.acknowledged ? 'opacity-50' : ''}">
        <div>
          <div class="flex items-center gap-1.5 mb-1">
            <span class="text-xs ${
              alert.severity === 'critical' ? 'text-red-400' :
              alert.severity === 'high' ? 'text-orange-400' : 'text-yellow-400'
            }">●</span>
            <span class="text-[9px] uppercase font-bold tracking-wider ${
              alert.severity === 'critical' ? 'text-red-400' :
              alert.severity === 'high' ? 'text-orange-400' : 'text-yellow-400'
            }">${alert.severity}</span>
            <span class="text-[9px] text-slate-400 ml-2">${alert.timestamp}</span>
          </div>
          <p class="text-slate-300 text-xs leading-relaxed font-medium">${alert.text}</p>
        </div>
        <div class="flex gap-1">
          <button onclick="window.acknowledgeAlert('${alert.id}')" class="text-slate-400 hover:text-white text-xs p-1" title="Acknowledge">✓</button>
          <button onclick="window.dismissAlert('${alert.id}')" class="text-slate-400 hover:text-red-400 text-xs p-1" title="Dismiss">&times;</button>
        </div>
      </div>
    `).join("");
  }

  // 5. Update Risk Category Cards (Risk Page)
  const riskGrid = document.getElementById("risk-categories-grid");
  if (riskGrid) {
    riskGrid.innerHTML = data.predictions.map(pred => `
      <div class="p-4 rounded-xl glass-card text-xs">
        <div class="flex justify-between items-start mb-2">
          <h3 class="font-bold text-white text-sm">${pred.category}</h3>
          <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${
            pred.trend === 'up' ? 'bg-red-950 text-red-400 border border-red-500/20' : 'bg-slate-800 text-slate-400'
          }">${pred.trend === 'up' ? '▲ RISING' : '■ STABLE'}</span>
        </div>
        <div class="grid grid-cols-3 gap-2 text-center py-2 bg-slate-900/60 rounded border border-slate-800 mb-3">
          <div><span class="text-slate-400 block text-[9px]">Current</span><b class="text-slate-200 text-sm">${pred.current}</b></div>
          <div><span class="text-slate-400 block text-[9px]">Forecast (6h)</span><b class="text-white text-sm">${pred.predicted}</b></div>
          <div><span class="text-slate-400 block text-[9px]">Confidence</span><b class="text-blue-400 text-sm">${pred.confidence}</b></div>
        </div>
        <div class="mb-2"><span class="text-slate-400 block text-[9px]">Affected Area:</span><b class="text-slate-300">${pred.affectedArea}</b></div>
        <div class="p-2 bg-slate-950/60 rounded text-[10px] leading-relaxed border border-slate-900">
          <span class="text-blue-400 font-bold block mb-0.5">AI Insights:</span>
          ${pred.explanation}
        </div>
      </div>
    `).join("");
  }

  // 6. Update Accessibility score list (Accessibility Page)
  const scoreContainer = document.getElementById("state-score-container");
  if (scoreContainer) {
    scoreContainer.innerHTML = data.states.map(st => `
      <div class="p-3 bg-slate-900/50 border border-slate-800 rounded-lg flex items-center justify-between">
        <div>
          <span class="text-white font-bold text-xs block">${st.name}</span>
          <span class="text-[10px] text-slate-400">Shipments: <b>${st.shipments}</b> | Disruptions: <b>${st.disruptions}</b></span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-24 bg-slate-800 h-1.5 rounded-full overflow-hidden">
            <div class="h-full rounded-full ${
              st.score >= 85 ? 'bg-emerald-500' :
              st.score >= 70 ? 'bg-yellow-500' : 'bg-red-500'
            }" style="width: ${st.score}%"></div>
          </div>
          <span class="font-bold text-xs ${
            st.score >= 85 ? 'text-emerald-400' :
            st.score >= 70 ? 'text-yellow-400' : 'text-red-400'
          }">${st.score}/100</span>
        </div>
      </div>
    `).join("");
  }

  // 7. Update Predictive Reroute Console Feed
  if (window.renderPredictiveConsoleFeed) {
    window.renderPredictiveConsoleFeed();
  }
};

window.renderPredictiveConsoleFeed = function() {
  const feed = document.getElementById("predictive-reroute-feed");
  if (!feed || !window.nerData || !window.nerData.predictiveEvents) return;

  feed.innerHTML = window.nerData.predictiveEvents.map(function(evt) {
    return `
      <div class="p-3 bg-slate-900/80 border border-slate-800 hover:border-cyan-500/40 rounded-xl transition space-y-1.5 animate-fade-in text-xs">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1.5 font-mono font-bold text-white">
            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>${evt.shipmentId}</span>
          </div>
          <span class="text-[10px] text-slate-400 font-mono">${evt.time}</span>
        </div>
        <div class="text-slate-300 text-[11px] leading-relaxed">
          <span class="text-amber-400 font-semibold">⚠️ ${evt.hazard}</span> &rarr;
          <span class="text-emerald-300 font-medium">${evt.action}</span>
        </div>
        <div class="flex justify-between items-center text-[10px] pt-1.5 border-t border-slate-800/60">
          <span class="text-slate-400">Risk: <b class="text-emerald-400">${evt.riskReduced}</b></span>
          <span class="text-teal-300 font-bold">⏱ Saved: +${evt.timeSaved}</span>
          <span class="bg-blue-950/80 text-blue-300 border border-blue-800/40 px-1.5 py-0.5 rounded text-[9px] font-semibold">${evt.status}</span>
        </div>
      </div>
    `;
  }).join("");
};

// Alert Actions
window.acknowledgeAlert = function(alertId) {
  const alert = window.nerData.alerts.find(a => a.id === alertId);
  if (alert) {
    alert.acknowledged = true;
    window.refreshDashboardUI();
  }
};

window.dismissAlert = function(alertId) {
  window.nerData.alerts = window.nerData.alerts.filter(a => a.id !== alertId);
  window.refreshDashboardUI();
};

// Detail Drawer Handlers
window.viewIncidentDetails = function(incId) {
  const inc = window.nerData.incidents.find(i => i.id === incId);
  if (!inc) return;

  const drawer = document.getElementById("detail-drawer");
  const body = document.getElementById("drawer-body");
  if (!drawer || !body) return;

  body.innerHTML = `
    <div class="space-y-4">
      <div class="flex justify-between items-start">
        <div>
          <h3 class="font-bold text-white text-base">${inc.type}</h3>
          <p class="text-xs text-slate-400">${inc.location}</p>
        </div>
        <span class="px-2 py-0.5 rounded text-xs font-bold bg-red-950 text-red-400 border border-red-500/30">${inc.severity}</span>
      </div>
      
      <div class="p-3 bg-slate-900/60 rounded border border-slate-800 text-xs">
        <span class="text-slate-400 block mb-1">Incident Report:</span>
        <p class="text-slate-200 leading-relaxed">${inc.description}</p>
      </div>

      <div class="grid grid-cols-2 gap-3 text-xs">
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-800">
          <span class="text-slate-400 block text-[10px]">Detected</span>
          <b class="text-white text-xs">${inc.detected}</b>
        </div>
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-800">
          <span class="text-slate-400 block text-[10px]">Primary Status</span>
          <b class="text-red-400 text-xs">${inc.status}</b>
        </div>
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-800">
          <span class="text-slate-400 block text-[10px]">Affected Corridor</span>
          <b class="text-white text-xs">${inc.affectedRoutes}</b>
        </div>
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-800">
          <span class="text-slate-400 block text-[10px]">Est Clearance Time</span>
          <b class="text-amber-400 text-xs">4h 15m</b>
        </div>
      </div>

      <div class="p-3 bg-emerald-950/20 border border-emerald-500/20 rounded text-xs">
        <span class="text-emerald-400 font-bold block mb-1">🤖 AI Operations Protocol</span>
        <p class="text-slate-300 mb-2">Automated re-routing is active. Intercepting shipments scheduled for ${inc.affectedRoutes}.</p>
        <button onclick="window.handleCopilotAction('reroute_units')" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-1 px-2.5 rounded text-xs transition">
          Authorize AI Rerouting Action
        </button>
      </div>
    </div>
  `;
  drawer.classList.remove("translate-x-full");
};

window.viewShipmentDetails = function(shipId) {
  const ship = window.nerData.shipments.find(s => s.id === shipId);
  if (!ship) return;

  const drawer = document.getElementById("detail-drawer");
  const body = document.getElementById("drawer-body");
  if (!drawer || !body) return;

  body.innerHTML = `
    <div class="space-y-4">
      <div class="flex justify-between items-start">
        <div>
          <h3 class="font-mono font-bold text-white text-base">${ship.id}</h3>
          <p class="text-xs text-slate-400">${ship.origin} &rarr; ${ship.destination}</p>
        </div>
        <span class="px-2 py-0.5 rounded text-xs font-bold bg-blue-950 text-blue-400 border border-blue-500/20">${ship.status}</span>
      </div>

      <div class="grid grid-cols-2 gap-3 text-xs">
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-800">
          <span class="text-slate-400 block text-[10px]">Cargo Classification</span>
          <b class="text-white text-xs">${ship.cargo}</b>
        </div>
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-800">
          <span class="text-slate-400 block text-[10px]">Cargo Net Weight</span>
          <b class="text-white text-xs">${ship.weight}</b>
        </div>
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-800">
          <span class="text-slate-400 block text-[10px]">ETA Projection</span>
          <b class="text-white text-xs">${ship.eta}</b>
        </div>
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-800">
          <span class="text-slate-400 block text-[10px]">Grid Risk Score</span>
          <b class="${ship.risk === 'High' ? 'text-red-400' : ship.risk === 'Medium' ? 'text-amber-400' : 'text-emerald-400'} text-xs">${ship.risk} Risk</b>
        </div>
      </div>

      <!-- Timeline tracker -->
      <div class="p-3 bg-slate-900/60 rounded border border-slate-800 text-xs">
        <span class="text-slate-400 font-bold block mb-2">Transit Timeline Tracking</span>
        <div class="space-y-3 relative before:absolute before:left-2 before:top-2 before:bottom-2 before:w-[1px] before:bg-slate-700">
          ${ship.timeline.map(t => `
            <div class="flex items-start gap-3 relative">
              <div class="w-4 h-4 rounded-full bg-slate-800 border-2 border-slate-500 flex items-center justify-center z-10">
                <div class="w-1.5 h-1.5 rounded-full bg-slate-200"></div>
              </div>
              <div>
                <span class="text-[10px] text-slate-400 block">${t.time}</span>
                <span class="text-slate-200 text-xs font-semibold">${t.act}</span>
              </div>
            </div>
          `).join("")}
        </div>
      </div>

      <div class="p-3 bg-blue-950/20 border border-blue-500/20 rounded text-xs flex justify-between items-center">
        <div>
          <span class="text-blue-400 font-bold block">Live Corridor Route Mapping</span>
          <p class="text-slate-300 text-[11px]">Render delivery path coords on dashboard map.</p>
        </div>
        <button onclick="window.confirmRouteSelection('${JSON.stringify(ship.currentPos ? [ship.currentPos] : [])}', '${ship.id}')" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-1 px-3 rounded text-[11px] transition">
          Plot Map
        </button>
      </div>
    </div>
  `;
  drawer.classList.remove("translate-x-full");
};

window.viewHubDetails = function(hubId) {
  const hub = window.nerData.hubs.find(h => h.id === hubId);
  if (!hub) return;

  const drawer = document.getElementById("detail-drawer");
  const body = document.getElementById("drawer-body");
  if (!drawer || !body) return;

  body.innerHTML = `
    <div class="space-y-4">
      <div>
        <h3 class="font-bold text-white text-base">${hub.name}</h3>
        <p class="text-xs text-slate-400">${hub.state} Logistics Hub</p>
      </div>

      <div class="grid grid-cols-2 gap-3 text-xs">
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-800">
          <span class="text-slate-400 block text-[10px]">Active Inbound</span>
          <b class="text-white text-xs">${hub.inbound} Cargo Units</b>
        </div>
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-800">
          <span class="text-slate-400 block text-[10px]">Active Outbound</span>
          <b class="text-white text-xs">${hub.outbound} Cargo Units</b>
        </div>
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-800">
          <span class="text-slate-400 block text-[10px]">Depot Load Capacity</span>
          <b class="text-white text-xs">${hub.capacity}</b>
        </div>
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-800">
          <span class="text-slate-400 block text-[10px]">Local Congestion Index</span>
          <b class="text-white text-xs">${hub.congestion}</b>
        </div>
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-800">
          <span class="text-slate-400 block text-[10px]">Accessibility Factor</span>
          <b class="text-white text-xs">${hub.accessibility}</b>
        </div>
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-800">
          <span class="text-slate-400 block text-[10px]">Processing Delay</span>
          <b class="text-white text-xs">${hub.avgProcessing}</b>
        </div>
      </div>

      <button onclick="window.switchTab('map'); if(window.nerMap) window.nerMap.setView([${hub.lat}, ${hub.lng}], 9);" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-1.5 px-3 rounded text-xs transition">
        Center Hub on Live Map
      </button>
    </div>
  `;
  drawer.classList.remove("translate-x-full");
};

window.showCorridorDetails = function(corrId) {
  const corr = window.nerData.corridors.find(c => c.id === corrId);
  if (!corr) return;

  const drawer = document.getElementById("detail-drawer");
  const body = document.getElementById("drawer-body");
  if (!drawer || !body) return;

  body.innerHTML = `
    <div class="space-y-4">
      <div>
        <h3 class="font-bold text-white text-base">${corr.name}</h3>
        <p class="text-xs text-slate-400">Logistics Corridor Segment</p>
      </div>

      <div class="grid grid-cols-2 gap-3 text-xs">
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-800">
          <span class="text-slate-400 block text-[10px]">Corridor Status</span>
          <b class="text-white text-xs capitalize">${corr.statusText}</b>
        </div>
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-800">
          <span class="text-slate-400 block text-[10px]">Active Delay</span>
          <b class="text-white text-xs">${corr.delay}</b>
        </div>
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-800">
          <span class="text-slate-400 block text-[10px]">Calculated Risk</span>
          <b class="text-white text-xs">${corr.riskScore}/100</b>
        </div>
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-800">
          <span class="text-slate-400 block text-[10px]">Segment Endpoints</span>
          <b class="text-white text-xs">${corr.from} &rarr; ${corr.to}</b>
        </div>
      </div>

      <button onclick="window.switchTab('routes'); document.getElementById('route-origin').value='${corr.from} Hub'; document.getElementById('route-destination').value='${corr.to} depot';" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-1.5 px-3 rounded text-xs transition">
        Optimize Cargo along Corridor
      </button>
    </div>
  `;
  drawer.classList.remove("translate-x-full");
};

window.closeDetailDrawer = function() {
  const drawer = document.getElementById("detail-drawer");
  if (drawer) drawer.classList.add("translate-x-full");
};

// Toast Notifications System
window.initToast = function() {
  let toastContainer = document.getElementById("toast-container");
  if (!toastContainer) {
    toastContainer = document.createElement("div");
    toastContainer.id = "toast-container";
    toastContainer.className = "fixed top-6 right-6 z-[10000] flex flex-col gap-2";
    document.body.appendChild(toastContainer);
  }
};

window.showToast = function(msg, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  let bg = "bg-slate-800 border-slate-700";
  let icon = "ℹ️";
  if (type === "success") { bg = "bg-emerald-950/90 border-emerald-500/30 text-emerald-300"; icon = "✓"; }
  else if (type === "warning") { bg = "bg-amber-950/90 border-amber-500/30 text-amber-300"; icon = "⚠️"; }
  else if (type === "critical") { bg = "bg-red-950/90 border-red-500/30 text-red-300"; icon = "🚨"; }

  toast.className = `flex items-center gap-2 px-4 py-3 rounded-lg border text-xs font-semibold shadow-2xl animate-fade-in ${bg}`;
  toast.innerHTML = `
    <span>${icon}</span>
    <span>${msg}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("opacity-0", "transition-opacity", "duration-500");
    setTimeout(() => toast.remove(), 500);
  }, 4000);
};

// Initialize Chart.js visual panels
window.charts = {};
window.initCharts = function() {
  // Chart 1: Shipments by State
  const c1Ctx = document.getElementById("chart-shipments-state");
  if (c1Ctx) {
    if (window.charts.shipmentsState) window.charts.shipmentsState.destroy();
    window.charts.shipmentsState = new Chart(c1Ctx, {
      type: 'bar',
      data: {
        labels: window.nerData.states.map(s => s.name),
        datasets: [{
          label: 'Active Shipments',
          data: window.nerData.states.map(s => s.shipments),
          backgroundColor: 'rgba(59, 130, 246, 0.65)',
          borderColor: '#3b82f6',
          borderWidth: 1.5,
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af', font: { size: 9 } } },
          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af', font: { size: 9 } } }
        }
      }
    });
  }

  // Chart 2: Disruption Type
  const c2Ctx = document.getElementById("chart-disruptions-type");
  if (c2Ctx) {
    if (window.charts.disruptionsType) window.charts.disruptionsType.destroy();
    window.charts.disruptionsType = new Chart(c2Ctx, {
      type: 'doughnut',
      data: {
        labels: ['Landslide', 'Flooding', 'Road Closure', 'Congestion', 'Weather'],
        datasets: [{
          data: [3, 2, 2, 4, 1],
          backgroundColor: [
            'rgba(239, 68, 68, 0.7)',
            'rgba(249, 115, 22, 0.7)',
            'rgba(245, 158, 11, 0.7)',
            'rgba(59, 130, 246, 0.7)',
            'rgba(16, 185, 129, 0.7)'
          ],
          borderColor: 'rgba(25, 35, 58, 1)',
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { 
          legend: { 
            position: 'right', 
            labels: { color: '#9ca3af', font: { size: 9 }, boxWidth: 8 } 
          } 
        }
      }
    });
  }

  // Chart 3: Expected Route Risk 24 Hours (Line Chart)
  const c3Ctx = document.getElementById("chart-expected-risk-line");
  if (c3Ctx) {
    if (window.charts.expectedRisk) window.charts.expectedRisk.destroy();
    window.charts.expectedRisk = new Chart(c3Ctx, {
      type: 'line',
      data: {
        labels: ['08:00', '12:00', '16:00', '20:00', '00:00', '04:00', '08:00'],
        datasets: [
          {
            label: 'Risk % Forecast',
            data: [35, 42, 58, 79, 72, 60, 45],
            borderColor: '#f97316',
            backgroundColor: 'rgba(249, 115, 22, 0.1)',
            fill: true,
            tension: 0.4,
            borderWidth: 2
          },
          {
            label: 'Confidence Interval (95%)',
            data: [45, 52, 68, 89, 82, 70, 55],
            borderColor: 'rgba(249, 115, 22, 0.2)',
            borderDash: [5, 5],
            fill: false,
            tension: 0.4,
            borderWidth: 1
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { 
          legend: { 
            position: 'top', 
            labels: { color: '#9ca3af', font: { size: 9 }, boxWidth: 8 } 
          } 
        },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af', font: { size: 9 } } },
          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af', font: { size: 9 } }, max: 100 }
        }
      }
    });
  }

  // Chart 4: Accessibility comparison by state
  const c4Ctx = document.getElementById("chart-accessibility-bars");
  if (c4Ctx) {
    if (window.charts.accessibilityBars) window.charts.accessibilityBars.destroy();
    window.charts.accessibilityBars = new Chart(c4Ctx, {
      type: 'bar',
      data: {
        labels: window.nerData.states.map(s => s.name),
        datasets: [{
          label: 'Accessibility Index',
          data: window.nerData.states.map(s => s.score),
          backgroundColor: window.nerData.states.map(s => {
            if (s.score >= 85) return 'rgba(16, 185, 129, 0.65)';
            if (s.score >= 70) return 'rgba(245, 158, 11, 0.65)';
            return 'rgba(239, 68, 68, 0.65)';
          }),
          borderColor: window.nerData.states.map(s => {
            if (s.score >= 85) return '#10b981';
            if (s.score >= 70) return '#f59e0b';
            return '#ef4444';
          }),
          borderWidth: 1.5,
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af', font: { size: 9 } }, max: 100 },
          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af', font: { size: 9 } } }
        }
      }
    });
  }
};

// SENTINEL Foundation Data Verification & Display Controller
window.fetchSentinelData = async function() {
  try {
    const apiBase = (window.backendSync && window.backendSync.apiBase) 
      ? window.backendSync.apiBase 
      : (window.location.protocol.startsWith("http") ? window.location.origin : "http://127.0.0.1:8001");

    const [basesRes, depotsRes, invRes] = await Promise.all([
      fetch(`${apiBase}/api/bases`),
      fetch(`${apiBase}/api/depots`),
      fetch(`${apiBase}/api/inventory`)
    ]);

    if (!basesRes.ok || !depotsRes.ok || !invRes.ok) return;

    const bases = await basesRes.json();
    const depots = await depotsRes.json();
    const items = await invRes.json();

    const depotMap = {};
    depots.forEach(d => depotMap[d.id] = d.name);

    // 1. Update Overview KPI Cards
    const kpiBases = document.getElementById("kpi-bases-count");
    if (kpiBases) kpiBases.innerText = `${bases.length} Bases`;

    const kpiInv = document.getElementById("kpi-inventory-status");
    if (kpiInv) kpiInv.innerText = `${items.length} Items`;

    // 2. Render Bases Containers (#sentinel-bases-container & #bases-grid-container)
    const baseCardsHtml = bases.map(b => `
      <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl glass-card">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-bold text-white">${b.name}</span>
          <span class="text-[9px] px-1.5 py-0.5 rounded font-mono font-bold ${b.status === 'OPERATIONAL' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/30' : 'bg-amber-950 text-amber-400 border border-amber-500/30'}">${b.status}</span>
        </div>
        <div class="text-[11px] text-slate-400">Type: <span class="text-slate-200 font-semibold">${b.base_type}</span></div>
        <div class="text-[11px] text-slate-400 mt-0.5">Capacity: <span class="text-slate-200 font-mono">${b.capacity} Tons</span></div>
        <div class="text-[10px] text-slate-500 mt-2 truncate">${b.description || ''}</div>
      </div>
    `).join("");

    const basesContainer = document.getElementById("sentinel-bases-container");
    if (basesContainer) basesContainer.innerHTML = baseCardsHtml;
    const basesGrid = document.getElementById("bases-grid-container");
    if (basesGrid) basesGrid.innerHTML = baseCardsHtml;

    // 3. Render Depots Table
    const depotsBody = document.getElementById("depots-table-body");
    if (depotsBody) {
      depotsBody.innerHTML = depots.map(d => `
        <tr class="hover:bg-slate-900/60 transition">
          <td class="p-3 pl-6 font-mono text-slate-400">${d.id}</td>
          <td class="p-3 font-semibold text-white">${d.name}</td>
          <td class="p-3 font-mono text-slate-300">${d.base_id}</td>
          <td class="p-3"><span class="bg-slate-800 text-slate-300 border border-slate-700 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold">${d.depot_type}</span></td>
          <td class="p-3 font-mono text-slate-200">${d.storage_capacity.toLocaleString()}</td>
          <td class="p-3 font-mono text-slate-400">${d.latitude.toFixed(4)}, ${d.longitude.toFixed(4)}</td>
          <td class="p-3 pr-6"><span class="text-[10px] font-bold ${d.status === 'OPERATIONAL' ? 'text-emerald-400' : 'text-amber-400'}">${d.status}</span></td>
        </tr>
      `).join("");
    }

    // 4. Calculate Health / Watch / Critical Summary Counts
    let healthyCount = 0;
    let watchCount = 0;
    let criticalCount = 0;

    items.forEach(item => {
      if (item.current_quantity < item.minimum_threshold) {
        criticalCount++;
      } else if (item.current_quantity < item.minimum_threshold * 1.2) {
        watchCount++;
      } else {
        healthyCount++;
      }
    });

    const hElem = document.getElementById("summary-healthy-count");
    if (hElem) hElem.innerText = `${healthyCount} Items`;
    const wElem = document.getElementById("summary-watch-count");
    if (wElem) wElem.innerText = `${watchCount} Items`;
    const cElem = document.getElementById("summary-critical-count");
    if (cElem) cElem.innerText = `${criticalCount} Items`;

    // 5. Render Inventory Table
    const tbody = document.getElementById("sentinel-inventory-table-body");
    if (tbody) {
      tbody.innerHTML = items.map(item => {
        let statusBadge = `<span class="bg-emerald-950 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded font-bold text-[10px]">HEALTHY STOCK</span>`;
        if (item.current_quantity < item.minimum_threshold) {
          statusBadge = `<span class="bg-red-950 text-red-400 border border-red-500/40 px-2 py-0.5 rounded font-bold text-[10px] animate-pulse">CRITICAL STOCK ALERT</span>`;
        } else if (item.current_quantity < item.minimum_threshold * 1.2) {
          statusBadge = `<span class="bg-amber-950 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded font-bold text-[10px]">WATCH THRESHOLD</span>`;
        }

        return `
          <tr class="hover:bg-slate-900/60 transition">
            <td class="p-3 pl-6 font-mono text-slate-400">${item.id}</td>
            <td class="p-3 font-semibold text-white">${item.item_name}</td>
            <td class="p-3 text-slate-300">${depotMap[item.depot_id] || item.depot_id}</td>
            <td class="p-3"><span class="bg-slate-800 text-slate-300 border border-slate-700 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold">${item.category}</span></td>
            <td class="p-3 font-mono font-bold text-white">${item.current_quantity.toLocaleString()} ${item.unit}</td>
            <td class="p-3 font-mono text-slate-400">${item.minimum_threshold.toLocaleString()} ${item.unit}</td>
            <td class="p-3 font-mono text-slate-400">${item.maximum_capacity.toLocaleString()} ${item.unit}</td>
            <td class="p-3 font-mono text-slate-300">${item.daily_consumption_rate} / day</td>
            <td class="p-3"><span class="text-[10px] font-bold ${item.criticality === 'CRITICAL' ? 'text-red-400' : item.criticality === 'HIGH' ? 'text-orange-400' : 'text-slate-300'}">${item.criticality}</span></td>
            <td class="p-3 pr-6">${statusBadge}</td>
          </tr>
        `;
      }).join("");
    }

    // 6. Overview Inventory Snapshot Cards
    const snapshotContainer = document.getElementById("overview-inventory-snapshot");
    if (snapshotContainer) {
      snapshotContainer.innerHTML = items.slice(0, 3).map(item => {
        const isCrit = item.current_quantity < item.minimum_threshold;
        const isWatch = item.current_quantity < item.minimum_threshold * 1.2;
        const borderCls = isCrit ? 'border-red-500/40 bg-red-950/20' : isWatch ? 'border-amber-500/40 bg-amber-950/20' : 'border-emerald-500/30 bg-emerald-950/20';
        const statusText = isCrit ? 'CRITICAL' : isWatch ? 'WATCH' : 'HEALTHY';
        const colorCls = isCrit ? 'text-red-400' : isWatch ? 'text-amber-400' : 'text-emerald-400';

        return `
          <div class="p-3 rounded-lg border ${borderCls} text-xs space-y-1">
            <div class="flex justify-between items-center">
              <span class="font-bold text-white truncate max-w-[130px]">${item.item_name}</span>
              <span class="text-[9px] font-mono font-bold ${colorCls}">${statusText}</span>
            </div>
            <div class="text-[11px] font-mono text-slate-300 font-bold">${item.current_quantity.toLocaleString()} / ${item.minimum_threshold.toLocaleString()} ${item.unit}</div>
            <div class="text-[9px] text-slate-400">Depot: ${item.depot_id}</div>
          </div>
        `;
      }).join("");
    }

  } catch (err) {
    console.error("Failed to fetch SENTINEL data:", err);
  }
};
