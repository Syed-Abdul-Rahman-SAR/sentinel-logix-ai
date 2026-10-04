// NER-LINK AI - Dynamic Incident Simulator & Network Impact Engine

window.simulating = false;

window.runImpactSimulation = function(type, corridorId) {
  if (window.simulating) return;
  window.simulating = true;

  // 1. Show spinner or processing state in UI
  const simBtn = document.getElementById("run-simulation-btn");
  const simResults = document.getElementById("simulation-results");
  if (simBtn) {
    simBtn.disabled = true;
    simBtn.innerHTML = `
      <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      Analyzing Grid Cascades...
    `;
  }

  // 2. Lookup the target corridor
  const corr = window.nerData.corridors.find(c => c.id === corridorId);
  if (!corr) {
    window.simulating = false;
    return;
  }

  // 3. Perform Simulation Logic (Simulated delay of 1.2s for hackathon aesthetic)
  setTimeout(() => {
    // Save backup state for reset if needed
    const oldStatus = corr.status;
    const oldStatusText = corr.statusText;
    const oldDelay = corr.delay;
    const oldRisk = corr.riskScore;

    // Set blocked state
    corr.status = "blocked";
    corr.statusText = `Simulated ${type}`;
    corr.delay = "4h 25m";
    corr.riskScore = 99;

    // Determine affected state and hubs
    let stateId = "";
    let stateName = "";
    let delayIncrease = "+2h 14m";
    let shipmentsCount = 23;
    let reroutedCount = 18;
    let savingsPct = 37;

    if (corridorId === "nh10") {
      stateId = "sikkim";
      stateName = "Sikkim";
      // Update Sikkim score from 72 to 38
      const stateObj = window.nerData.states.find(s => s.id === "sikkim");
      if (stateObj) {
        stateObj.score = 38;
        stateObj.disruptions += 1;
      }
      shipmentsCount = 14;
      reroutedCount = 11;
      delayIncrease = "+1h 55m";
      savingsPct = 42;
    } else if (corridorId === "nh2_dim") {
      stateId = "manipur";
      stateName = "Manipur";
      // Update Manipur score from 67 to 39
      const stateObj = window.nerData.states.find(s => s.id === "manipur");
      const nagalandObj = window.nerData.states.find(s => s.id === "nagaland");
      if (stateObj) {
        stateObj.score = 39;
        stateObj.disruptions += 1;
      }
      if (nagalandObj) {
        nagalandObj.score = 48;
        nagalandObj.disruptions += 1;
      }
      shipmentsCount = 31;
      reroutedCount = 26;
      delayIncrease = "+3h 10m";
      savingsPct = 35;
    } else {
      // General defaults
      stateId = "assam";
      stateName = "Assam";
      const stateObj = window.nerData.states.find(s => s.id === "assam");
      if (stateObj) {
        stateObj.score = 58;
        stateObj.disruptions += 1;
      }
    }

    // Insert active incident
    const newIncId = `sim-inc-${Date.now()}`;
    const newIncident = {
      id: newIncId,
      type: type,
      location: `${corr.name} (Ch. Point)`,
      state: stateName,
      severity: "Critical",
      detected: "Just now",
      affectedRoutes: corr.name.split(" ")[0],
      status: "Active",
      description: `A simulated ${type.toLowerCase()} has completely blocked transportation nodes along this highway. Rerouting algorithms engaged.`
    };
    window.nerData.incidents.unshift(newIncident);

    // Update shipments
    let countAffected = 0;
    window.nerData.shipments.forEach(shipment => {
      if (shipment.routeId === corridorId) {
        countAffected++;
        // Simulating AI Rerouting
        if (countAffected % 3 === 0) {
          shipment.status = "Delayed";
          shipment.risk = "High";
          shipment.eta = "11h 55m";
          shipment.timeline.unshift({ time: "Simulated Time", act: `⚠️ Delay warning: Route blocked by ${type}.` });
        } else {
          shipment.status = "Rerouted";
          shipment.risk = "Medium";
          shipment.eta = "9h 15m";
          // Change routeId to alternative route
          if (corridorId === "nh2_dim") shipment.routeId = "nh37"; // Switch to NH-37 Jiribam
          else if (corridorId === "nh10") shipment.routeId = "nh27"; // Reroute back to Assam plains gateway
          
          shipment.timeline.unshift({ time: "Simulated Time", act: `🤖 AI Rerouted shipment to avoid ${type} on ${corr.name.split(" ")[0]}.` });
        }
      }
    });

    // Create a Critical Alert
    const newAlert = {
      id: `sim-alert-${Date.now()}`,
      severity: "critical",
      text: `CRITICAL ALERT: ${type} simulated on ${corr.name.split(" ")[0]}! Accessibility Index dropped.`,
      timestamp: "Just now",
      acknowledged: false
    };
    window.nerData.alerts.unshift(newAlert);

    // Update global dashboard items
    const accessibilityOverview = document.getElementById("ner-accessibility-index");
    if (accessibilityOverview) {
      accessibilityOverview.innerText = "61/100"; // Overall drop
    }

    // Redraw and trigger toast
    if (window.renderMapAssets) window.renderMapAssets();
    if (window.refreshDashboardUI) window.refreshDashboardUI();
    if (window.showToast) {
      window.showToast(`Simulated ${type} successfully injected!`, "critical");
    }

    // 4. Render results visually in simulation panel
    if (simResults) {
      simResults.innerHTML = `
        <div class="mt-4 p-4 rounded-lg bg-red-950/40 border border-red-500/30 text-slate-200 animate-fade-in">
          <div class="flex items-center gap-2 text-red-400 font-bold mb-2">
            <span class="text-lg">⚡</span>
            <span>SIMULATION IMPACT: ${type} on ${corr.name.split(" ")[0]}</span>
          </div>
          <div class="grid grid-cols-2 gap-3 text-xs mb-3">
            <div class="bg-slate-900/60 p-2.5 rounded border border-slate-700/40">
              <span class="text-slate-400 block">Corridors Blocked</span>
              <span class="text-white text-base font-bold">1 Primary Corridor</span>
            </div>
            <div class="bg-slate-900/60 p-2.5 rounded border border-slate-700/40">
              <span class="text-slate-400 block">Impacted Shipments</span>
              <span class="text-white text-base font-bold">${shipmentsCount} Active Units</span>
            </div>
            <div class="bg-slate-900/60 p-2.5 rounded border border-slate-700/40">
              <span class="text-slate-400 block">Avg Incident Delay</span>
              <span class="text-red-400 text-base font-bold">${delayIncrease}</span>
            </div>
            <div class="bg-slate-900/60 p-2.5 rounded border border-slate-700/40">
              <span class="text-slate-400 block">AI Automated Reroutes</span>
              <span class="text-emerald-400 text-base font-bold">${reroutedCount} Shipments</span>
            </div>
          </div>
          <div class="p-3 bg-emerald-950/30 border border-emerald-500/20 rounded text-xs">
            <div class="flex items-center gap-1.5 text-emerald-400 font-bold mb-1">
              <span>🤖</span>
              <span>NER-LINK AI Reroute Optimization</span>
            </div>
            <p class="text-slate-300">
              AI successfully rerouted <b>${reroutedCount}</b> out of <b>${shipmentsCount}</b> shipments. 
              Average grid delays reduced by <b class="text-emerald-400">${savingsPct}%</b> compared to manual dispatch.
            </p>
          </div>
          <button onclick="window.resetSimulation('${corridorId}', '${oldStatus}', '${oldStatusText}', '${oldDelay}', ${oldRisk}, '${stateId}')" class="mt-3 w-full bg-slate-800 hover:bg-slate-700 border border-slate-600 text-white font-medium py-1.5 px-3 rounded text-xs transition duration-150">
            Clear Active Simulation
          </button>
        </div>
      `;
      simResults.classList.remove("hidden");
    }

    // Reset button
    if (simBtn) {
      simBtn.disabled = false;
      simBtn.innerHTML = "RUN IMPACT SIMULATION";
    }
    window.simulating = false;
  }, 1200);
};

window.resetSimulation = function(corridorId, oldStatus, oldStatusText, oldDelay, oldRisk, stateId) {
  const corr = window.nerData.corridors.find(c => c.id === corridorId);
  if (corr) {
    corr.status = oldStatus;
    corr.statusText = oldStatusText;
    corr.delay = oldDelay;
    corr.riskScore = oldRisk;
  }

  // Restore State score
  const stateObj = window.nerData.states.find(s => s.id === stateId);
  if (stateObj) {
    if (stateId === "sikkim") stateObj.score = 72;
    else if (stateId === "manipur") {
      stateObj.score = 67;
      const nagalandObj = window.nerData.states.find(s => s.id === "nagaland");
      if (nagalandObj) nagalandObj.score = 74;
    }
  }

  // Filter out simulated incidents and alerts
  window.nerData.incidents = window.nerData.incidents.filter(inc => !inc.id.startsWith("sim-inc"));
  window.nerData.alerts = window.nerData.alerts.filter(alert => !alert.id.startsWith("sim-alert"));

  // Re-link shipments route back to standard
  window.nerData.shipments.forEach(shipment => {
    if (shipment.status === "Rerouted" || shipment.status === "Delayed") {
      shipment.status = "In Transit";
      shipment.risk = "Low";
      if (corridorId === "nh2_dim") shipment.routeId = "nh2_dim";
      shipment.timeline = shipment.timeline.filter(t => !t.act.includes("simulated") && !t.act.includes("AI Rerouted"));
    }
  });

  // Reset UI elements
  const simResults = document.getElementById("simulation-results");
  if (simResults) {
    simResults.innerHTML = "";
    simResults.classList.add("hidden");
  }

  const accessibilityOverview = document.getElementById("ner-accessibility-index");
  if (accessibilityOverview) {
    accessibilityOverview.innerText = "75/100"; // Default
  }

  if (window.renderMapAssets) window.renderMapAssets();
  if (window.refreshDashboardUI) window.refreshDashboardUI();
  if (window.showToast) {
    window.showToast("Simulation cleared. Grid restored to baseline state.", "info");
  }
};
