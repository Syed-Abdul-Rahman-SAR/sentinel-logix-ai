/**
 * SENTINEL LOGIX AI -- Intelligence Dashboard Integration
 * Phase 8B: Connects frontend to GET /api/intelligence/dashboard
 * Also integrates: /api/readiness, /api/digital-twin/simulate, /api/digital-twin/scenarios
 */

function getApiBase() {
  if (window.backendSync && window.backendSync.apiBase) return window.backendSync.apiBase;
  return "http://127.0.0.1:8001";
}

window.sentinelIntel = null;
window.sentinelDigitalTwinResult = null;
window.environmentalIntelligence = null;

// Primary Intelligence Dashboard Fetch
window.fetchIntelligenceDashboard = async function () {
  try {
    const res = await fetch(getApiBase() + "/api/intelligence/dashboard");
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    window.sentinelIntel = data;
    window.environmentalIntelligence = data.environmental_intelligence || null;
    applyIntelligenceToOverview(data);
    applyIntelligenceToForecastSection(data);
    updateSidebarBadges(data);
    // Phase 12B: Unified Intelligence renderers
    applyUnifiedIntelligence(data);
    applyCriticalSignals(data);
    applyIntelligenceModuleStatus(data);
    return data;
  } catch (err) {
    console.warn("[SENTINEL Intelligence] Dashboard API unavailable:", err.message);
    window.environmentalIntelligence = null;
    return null;
  }
};

/**
 * Accessor for Environmental Intelligence state.
 * Gracefully returns state or empty summary if API/data unavailable.
 */
window.getEnvironmentalIntelligence = function () {
  if (window.environmentalIntelligence) return window.environmentalIntelligence;
  if (window.sentinelIntel && window.sentinelIntel.environmental_intelligence) {
    window.environmentalIntelligence = window.sentinelIntel.environmental_intelligence;
    return window.environmentalIntelligence;
  }
  return {
    total_routes_assessed: 0,
    low_risk_routes: 0,
    medium_risk_routes: 0,
    high_risk_routes: 0,
    critical_risk_routes: 0,
    highest_risk_route: null,
    highest_risk_score: 0.0,
    weather_dominant_routes: 0,
    terrain_dominant_routes: 0,
    routes: [],
    data_source: "synthetic_demo",
    environment: "demo"
  };
};

/**
 * Accessor for a specific route's environmental risk summary from state.
 */
window.getEnvironmentalRouteRisk = function (routeId) {
  var env = window.getEnvironmentalIntelligence();
  if (!env || !env.routes || !routeId) return null;
  var target = routeId.toUpperCase().replace(/\s+/g, "-");
  for (var i = 0; i < env.routes.length; i++) {
    if (env.routes[i].route_id === target) {
      return env.routes[i];
    }
  }
  return null;
};


function applyIntelligenceToOverview(data) {
  var oo = data.operational_overview || {};
  var inv = data.inventory_intelligence || {};
  var risk = data.risk_intelligence || {};
  var readiness = data.readiness_intelligence || {};
  var supply = data.supply_movement || {};

  var kpiBases = document.getElementById("kpi-bases-count");
  if (kpiBases && oo.total_bases) kpiBases.innerText = oo.total_bases + " Bases";

  var kpiInv = document.getElementById("kpi-inventory-status");
  if (kpiInv && oo.total_depots) {
    kpiInv.innerText = oo.total_depots + " Depots";
    var sub = kpiInv.nextElementSibling;
    if (sub && inv.items_below_threshold_count !== undefined) {
      var crit = inv.items_below_threshold_count;
      sub.innerText = crit + " Item" + (crit !== 1 ? "s" : "") + " Below Threshold";
      sub.className = crit > 0 ? "text-[9px] text-red-400 font-semibold block mt-1" : "text-[9px] text-emerald-400 font-semibold block mt-1";
    }
  }

  var kpiReady = document.getElementById("kpi-mission-readiness");
  if (kpiReady) {
    var score = readiness.average_readiness_score || 0;
    var status = readiness.overall_readiness_status || "READY";
    var colorMap = { READY: "text-emerald-400", CAUTION: "text-amber-400", DEGRADED: "text-orange-400", CRITICAL: "text-red-400" };
    kpiReady.innerText = score.toFixed(0) + "%";
    kpiReady.className = "text-xl font-black block mt-1 " + (colorMap[status] || "text-slate-300");
    var sub2 = document.getElementById("kpi-mission-readiness-sub");
    if (sub2) {
      var critCount = readiness.readiness_status_counts && readiness.readiness_status_counts.CRITICAL ? readiness.readiness_status_counts.CRITICAL : 0;
      sub2.innerText = status + " -- " + critCount + " Depots Critical";
      sub2.className = status === "READY" ? "text-[9px] text-emerald-400 block mt-1" : "text-[9px] text-amber-400 block mt-1";
    }
  }

  var kpiRisk = document.getElementById("kpi-risk-level");
  if (kpiRisk) {
    var rLevel = risk.overall_risk_level || "LOW";
    var rColorMap = { CRITICAL: "text-red-400", HIGH: "text-orange-400", MEDIUM: "text-amber-400", LOW: "text-emerald-400" };
    kpiRisk.innerText = rLevel;
    kpiRisk.className = "text-xl font-black block mt-1 " + (rColorMap[rLevel] || "text-slate-300");
    var sub3 = document.getElementById("kpi-risk-level-sub");
    if (sub3 && risk.highest_risk_depot_name) sub3.innerText = "Highest: " + risk.highest_risk_depot_name + " (" + risk.highest_risk_score + ")";
  }

  var kpiInc = document.getElementById("kpi-critical-disruptions");
  if (kpiInc && oo.active_incidents_count !== undefined) {
    kpiInc.innerText = oo.active_incidents_count + " Incident" + (oo.active_incidents_count !== 1 ? "s" : "");
  }

  var supplyEl = document.getElementById("kpi-supply-movement");
  if (supplyEl) {
    var del = supply.delayed_shipments_count || 0;
    supplyEl.innerText = del > 0 ? del + " Delayed" : "On Schedule";
    supplyEl.className = del > 0 ? "text-xl font-black text-amber-400 block mt-1" : "text-xl font-black text-emerald-400 block mt-1";
  }
}

function applyIntelligenceToForecastSection(data) {
  var demand = data.demand_intelligence || {};
  var supply = data.supply_movement || {};
  var inv = data.inventory_intelligence || {};
  var highPressure = demand.high_pressure_items || [];

  var horizonEl = document.getElementById("intel-forecast-horizon");
  if (horizonEl) horizonEl.innerText = (demand.forecast_horizon_days || 14) + " days";

  var modelEl = document.getElementById("intel-forecast-model-status");
  if (modelEl) {
    modelEl.innerText = demand.forecast_model_status || "UNAVAILABLE";
    modelEl.className = demand.forecast_model_status === "ACTIVE" ? "text-[10px] font-bold text-emerald-400" : "text-[10px] font-bold text-amber-400";
  }

  var stockoutEl = document.getElementById("intel-stockout-count");
  if (stockoutEl) stockoutEl.innerText = inv.stockout_projected_count || 0;

  var shipmentsEl = document.getElementById("intel-shipments-count");
  if (shipmentsEl) shipmentsEl.innerText = supply.total_shipments_count || 0;

  var container = document.getElementById("intel-forecast-pressure-list");
  if (!container) return;

  if (highPressure.length === 0) {
    container.innerHTML = '<div class="text-xs text-slate-400 text-center py-8 border border-dashed border-slate-800 rounded-xl"><div class="text-2xl mb-2">&#10003;</div>No high-pressure inventory items detected. All depots within normal thresholds.</div>';
    return;
  }

  container.innerHTML = highPressure.map(function(item) {
    var dso = item.days_until_stockout;
    var dbr = item.days_until_threshold_breach;
    var urgency = dso !== null && dso !== undefined && dso <= 3 ? "CRITICAL" : dso !== null && dso !== undefined ? "HIGH" : dbr !== null && dbr !== undefined && dbr <= 3 ? "WATCH" : "MONITOR";
    var urgencyBg = urgency === "CRITICAL" ? "border-red-500/40 bg-red-950/20" : urgency === "HIGH" ? "border-orange-500/30 bg-orange-950/20" : urgency === "WATCH" ? "border-amber-500/30 bg-amber-950/20" : "border-slate-700 bg-slate-900/40";
    var urgencyColor = urgency === "CRITICAL" ? "text-red-400" : urgency === "HIGH" ? "text-orange-400" : urgency === "WATCH" ? "text-amber-400" : "text-slate-400";
    var dsoHtml = dso !== null && dso !== undefined ? '<div class="font-mono font-black text-red-300 text-xs">Stockout D+' + dso + '</div>' : '';
    var dbrHtml = dbr !== null && dbr !== undefined ? '<div class="font-mono text-amber-300 text-[10px]">Threshold D+' + dbr + '</div>' : '';
    return '<div class="flex items-center justify-between p-3.5 rounded-xl border ' + urgencyBg + ' text-xs gap-3 transition">' +
      '<div class="flex-1 min-w-0"><div class="font-bold text-white text-sm truncate">' + item.item_name + '</div><div class="text-[10px] text-slate-400 mt-0.5 font-mono">' + item.item_id + ' &middot; Depot: ' + item.depot_id + '</div></div>' +
      '<div class="text-right shrink-0 space-y-0.5">' + dsoHtml + dbrHtml + '<div class="text-[9px] font-black uppercase tracking-wider ' + urgencyColor + ' mt-1">' + urgency + '</div></div>' +
      '</div>';
  }).join("");
}

window.fetchReadinessSectionData = async function () {
  var container = document.getElementById("readiness-depots-grid");
  var overallEl = document.getElementById("readiness-overall-status");
  var avgEl = document.getElementById("readiness-avg-score");
  if (!container) return;

  container.innerHTML = '<div class="col-span-full flex justify-center items-center py-12 gap-3 text-slate-400 text-xs"><span class="w-4 h-4 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin"></span>Fetching mission readiness assessments&hellip;</div>';

  try {
    var res = await fetch(getApiBase() + "/api/readiness");
    if (!res.ok) throw new Error("HTTP " + res.status);
    var assessments = await res.json();

    if (window.sentinelIntel) {
      var ri = window.sentinelIntel.readiness_intelligence || {};
      var st = ri.overall_readiness_status || "READY";
      var cm = { READY: "text-emerald-400", CAUTION: "text-amber-400", DEGRADED: "text-orange-400", CRITICAL: "text-red-400" };
      if (overallEl) { overallEl.innerText = st; overallEl.className = "text-2xl font-black " + (cm[st] || "text-slate-300"); }
      if (avgEl) avgEl.innerText = (ri.average_readiness_score || 0).toFixed(1);
    }

    if (assessments.length === 0) {
      container.innerHTML = '<div class="col-span-full text-center text-xs text-slate-400 py-8">No readiness assessments available.</div>';
      return;
    }

    container.innerHTML = assessments.map(function(a) {
      var score = parseFloat(a.readiness_score || 0);
      var status = a.readiness_status || "READY";
      var borderColor = status === "CRITICAL" ? "border-red-500/50 bg-red-950/10" : status === "DEGRADED" ? "border-orange-500/40 bg-orange-950/10" : status === "CAUTION" ? "border-amber-500/30 bg-amber-950/10" : "border-emerald-500/20";
      var statusBadge = status === "CRITICAL" ? "bg-red-950 text-red-400 border border-red-500/40" : status === "DEGRADED" ? "bg-orange-950 text-orange-400 border border-orange-500/30" : status === "CAUTION" ? "bg-amber-950 text-amber-400 border border-amber-500/30" : "bg-emerald-950 text-emerald-400 border border-emerald-500/20";
      var scoreColor = status === "CRITICAL" ? "text-red-400" : status === "DEGRADED" ? "text-orange-400" : status === "CAUTION" ? "text-amber-400" : "text-emerald-400";
      var barColor = status === "CRITICAL" ? "bg-red-500" : status === "DEGRADED" ? "bg-orange-500" : status === "CAUTION" ? "bg-amber-400" : "bg-emerald-500";
      var factors = a.contributing_factors || [];
      var factorsHtml = factors.length > 0 ? '<div class="space-y-1.5 border-t border-slate-800/80 pt-2"><div class="text-[9px] uppercase tracking-wider text-slate-500 font-bold">Contributing Factors</div>' + factors.slice(0, 4).map(function(f) {
        var arrow = f.impact === "negative" ? "&#9660;" : f.impact === "positive" ? "&#9650;" : "&bull;";
        var fc = f.impact === "negative" ? "text-red-400" : f.impact === "positive" ? "text-emerald-400" : "text-slate-400";
        return '<div class="flex items-center gap-1.5 text-[10px]"><span class="' + fc + '">' + arrow + '</span><span class="text-slate-300 flex-1">' + f.factor + '</span>' + (f.value !== undefined ? '<span class="font-mono text-slate-400 text-[9px]">' + f.value + '</span>' : '') + '</div>';
      }).join("") + '</div>' : '';
      var narrativeHtml = a.narrative ? '<p class="text-[10px] text-slate-400 border-t border-slate-800 pt-2 leading-relaxed">' + a.narrative.substring(0, 200) + (a.narrative.length > 200 ? "&hellip;" : "") + '</p>' : '';
      var baseNameHtml = a.base_name ? '<div class="text-[10px] text-slate-500 mt-0.5">' + a.base_name + '</div>' : '';
      return '<div class="p-5 rounded-xl glass-card border ' + borderColor + ' space-y-3 transition hover:shadow-lg">' +
        '<div class="flex items-start justify-between gap-2"><div class="min-w-0"><div class="font-bold text-white text-sm truncate">' + (a.depot_name || a.depot_id) + '</div><div class="text-[10px] text-slate-400 font-mono mt-0.5">' + a.depot_id + '</div>' + baseNameHtml + '</div><span class="text-[10px] px-2 py-0.5 rounded font-mono font-bold shrink-0 ' + statusBadge + '">' + status + '</span></div>' +
        '<div class="flex items-end justify-between"><span class="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Readiness Score</span><span class="text-2xl font-black ' + scoreColor + '">' + score.toFixed(0) + '<span class="text-sm text-slate-400">/100</span></span></div>' +
        '<div class="w-full bg-slate-800 rounded-full h-1.5"><div class="' + barColor + ' h-1.5 rounded-full transition-all duration-700" style="width:' + Math.max(0, Math.min(100, score)) + '%"></div></div>' +
        factorsHtml + narrativeHtml + '</div>';
    }).join("");

  } catch (err) {
    console.warn("[SENTINEL Readiness] API unavailable:", err.message);
    container.innerHTML = '<div class="col-span-full text-center py-12 space-y-2"><div class="text-2xl">&#9888;</div><div class="text-xs text-red-400 font-bold">Readiness API Unavailable</div><div class="text-[10px] text-slate-500">Ensure the FastAPI backend is running on port 8001.</div></div>';
  }
};

window.initDigitalTwinSection = async function () {
  var selectEl = document.getElementById("dt-depot-select");
  if (!selectEl) return;
  try {
    var results = await Promise.all([fetch(getApiBase() + "/api/depots"), fetch(getApiBase() + "/api/digital-twin/scenarios")]);
    var depotsRes = results[0];
    var scenariosRes = results[1];
    if (depotsRes.ok) {
      var depots = await depotsRes.json();
      selectEl.innerHTML = depots.map(function(d) { return '<option value="' + d.id + '">' + d.name + ' (' + d.id + ')</option>'; }).join("");
    }
    if (scenariosRes.ok) {
      var scenarios = await scenariosRes.json();
      renderScenarioTemplates(scenarios);
    }
  } catch (err) {
    console.warn("[SENTINEL DigitalTwin] Load error:", err.message);
  }
};

function renderScenarioTemplates(scenarios) {
  var container = document.getElementById("dt-scenario-templates");
  if (!container || !scenarios || scenarios.length === 0) return;
  window._dtScenarioTemplates = scenarios;
  container.innerHTML = scenarios.map(function(s, i) {
    return '<button onclick="window.applyScenarioTemplate(' + i + ')" class="text-left p-3 rounded-lg border border-slate-700 bg-slate-900/60 hover:border-cyan-500/40 hover:bg-cyan-950/20 transition text-xs space-y-1 cursor-pointer w-full">' +
      '<div class="font-bold text-white">' + (s.scenario_type || "Scenario").replace(/_/g, " ") + '</div>' +
      '<div class="text-slate-400 text-[10px]">' + (s.description || "") + '</div>' +
      '<div class="flex items-center gap-2 flex-wrap mt-1"><span class="text-[9px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded font-mono">Severity: ' + (s.severity || "MEDIUM") + '</span><span class="text-[9px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded font-mono">Duration: ' + (s.disruption_duration_days || 5) + 'd</span></div>' +
      '</button>';
  }).join("");
}

window.applyScenarioTemplate = function (idx) {
  var scenarios = window._dtScenarioTemplates;
  if (!scenarios || !scenarios[idx]) return;
  var s = scenarios[idx];
  var typeEl = document.getElementById("dt-scenario-type");
  var durEl = document.getElementById("dt-duration");
  var delayEl = document.getElementById("dt-delay");
  var sevEl = document.getElementById("dt-severity");
  var routeEl = document.getElementById("dt-route-select");
  var descEl = document.getElementById("dt-description");
  if (typeEl) typeEl.value = s.scenario_type || "ROUTE_DISRUPTION";
  if (durEl) durEl.value = s.disruption_duration_days || 5;
  if (delayEl) delayEl.value = s.additional_delay_days || 2;
  if (sevEl) sevEl.value = s.severity || "MEDIUM";
  if (s.affected_depot_id) { var sel = document.getElementById("dt-depot-select"); if (sel) sel.value = s.affected_depot_id; }
  if (s.affected_route_id && routeEl) routeEl.value = s.affected_route_id;
  if (s.description && descEl) descEl.value = s.description;
  if (window.showToast) window.showToast("Template applied: " + (s.scenario_type || "").replace(/_/g, " "), "info");
};

window.runDigitalTwinSimulation = async function () {
  var btn = document.getElementById("dt-run-btn");
  var resultsEl = document.getElementById("dt-results-panel");
  var pillEl = document.getElementById("dt-status-pill");
  var formEl = document.getElementById("dt-simulation-form");
  if (!btn || !resultsEl) return;

  var depotId = document.getElementById("dt-depot-select") ? document.getElementById("dt-depot-select").value.trim() : "";
  var routeId = document.getElementById("dt-route-select") ? document.getElementById("dt-route-select").value.trim() : "";
  var scenarioType = document.getElementById("dt-scenario-type") ? document.getElementById("dt-scenario-type").value.trim() : "ROUTE_DISRUPTION";
  var duration = parseInt(document.getElementById("dt-duration") ? document.getElementById("dt-duration").value : "5");
  var delay = parseInt(document.getElementById("dt-delay") ? document.getElementById("dt-delay").value : "0");
  var severity = document.getElementById("dt-severity") ? document.getElementById("dt-severity").value : "HIGH";
  var description = document.getElementById("dt-description") ? document.getElementById("dt-description").value.trim() : "";

  // Frontend Validation
  if (!depotId) {
    if (window.showToast) window.showToast("Please select a target depot.", "warning");
    return;
  }
  if (isNaN(duration) || duration <= 0) {
    if (window.showToast) window.showToast("Disruption duration must be greater than 0 days.", "warning");
    return;
  }
  if (isNaN(delay) || delay < 0) {
    if (window.showToast) window.showToast("Additional delay must be greater than or equal to 0 days.", "warning");
    return;
  }

  // Lock Controls
  btn.disabled = true;
  btn.innerHTML = '<span class="inline-flex items-center gap-2"><span class="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></span> SIMULATING...</span>';
  if (pillEl) { pillEl.innerText = "SIMULATING"; pillEl.className = "text-[9px] bg-cyan-950 text-cyan-400 border border-cyan-500/40 px-2 py-0.5 rounded font-mono font-bold uppercase animate-pulse"; }
  if (formEl) {
    var inputs = formEl.querySelectorAll("input, select, button");
    inputs.forEach(function(el) { el.disabled = true; });
  }

  // Clear stale results and present simulation running state
  resultsEl.innerHTML = '<div class="p-6 space-y-4 bg-slate-950 border border-cyan-500/30 text-center"><div class="flex justify-center items-center gap-3 text-cyan-400 text-sm font-bold"><span class="w-4 h-4 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin"></span> Digital Twin Engine Executing What-If Simulation...</div><p class="text-xs text-slate-400">Evaluating inventory trajectory, delayed replenishment, risk deltas, and readiness scores in memory.</p></div>';
  resultsEl.classList.remove("hidden");

  try {
    var payload = {
      scenario_type: scenarioType,
      affected_depot_id: depotId,
      disruption_duration_days: duration,
      additional_delay_days: delay,
      severity: severity
    };
    if (routeId) payload.affected_route_id = routeId;
    if (description) payload.description = description;

    var res = await fetch(getApiBase() + "/api/digital-twin/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      var msg = "HTTP " + res.status;
      try {
        var errBody = await res.json();
        if (errBody.detail) {
          if (Array.isArray(errBody.detail)) {
            msg = errBody.detail.map(function(d) { return (d.loc ? d.loc.join(".") + ": " : "") + d.msg; }).join("; ");
          } else {
            msg = errBody.detail;
          }
        }
      } catch(x) {}
      throw new Error(msg);
    }

    var result = await res.json();
    window.sentinelDigitalTwinResult = result;
    
    // Render handoff confirmation & stored state panel
    renderDigitalTwinResults(result);

    // Update map overlays for active simulation
    if (window.updateDigitalTwinMapOverlay) {
      window.updateDigitalTwinMapOverlay(result);
    }

    if (pillEl) { pillEl.innerText = "SIMULATION COMPLETED"; pillEl.className = "text-[9px] bg-emerald-950 text-emerald-400 border border-emerald-500/40 px-2 py-0.5 rounded font-mono font-bold uppercase"; }
    var dtBadge = document.getElementById("sidebar-digital-twin-badge");
    if (dtBadge) { dtBadge.innerText = "ACTIVE"; dtBadge.className = "text-[8px] bg-cyan-950 text-cyan-400 border border-cyan-500/30 px-1.5 py-0.5 rounded font-mono"; }
    if (window.showToast) window.showToast("Digital Twin simulation completed successfully.", "success");

  } catch (err) {
    window.sentinelDigitalTwinResult = null;
    if (window.clearDigitalTwinMapOverlay) window.clearDigitalTwinMapOverlay();
    if (pillEl) { pillEl.innerText = "SIMULATION FAILED"; pillEl.className = "text-[9px] bg-red-950 text-red-400 border border-red-500/40 px-2 py-0.5 rounded font-mono font-bold uppercase"; }
    
    resultsEl.innerHTML = '<div class="p-6 bg-red-950/20 border border-red-500/30 rounded-xl space-y-2"><div class="flex items-center gap-2 text-red-400 font-bold text-sm"><span>⚠️</span> Simulation Error</div><p class="text-slate-300 text-xs">' + err.message + '</p><div class="text-[10px] text-slate-500 font-mono">Ensure parameters meet backend constraints and server is running on port 8001.</div></div>';
    if (window.showToast) window.showToast("Simulation error: " + err.message, "error");

  } finally {
    // Unlock Controls
    btn.disabled = false;
    btn.innerHTML = '<span>▶</span><span>RUN DIGITAL TWIN SIMULATION</span>';
    if (formEl) {
      var inputs = formEl.querySelectorAll("input, select, button");
      inputs.forEach(function(el) { el.disabled = false; });
    }
  }
};

function renderDigitalTwinResults(result) {
  var el = document.getElementById("dt-results-panel");
  if (!el) return;

  if (!result || typeof result !== "object") {
    el.innerHTML = '<div class="p-8 text-center text-slate-400 font-mono text-xs border border-dashed border-slate-800 rounded-xl">SIMULATION RESULT UNAVAILABLE</div>';
    el.classList.remove("hidden");
    return;
  }

  el.classList.remove("hidden");

  // Helper for metric delta formatting (delta = scenario - baseline)
  function formatMetricDelta(val, invertGoodBad) {
    if (val === undefined || val === null || isNaN(val)) return '<span class="text-slate-500 font-mono">--</span>';
    var isZero = Math.abs(val) < 0.01;
    if (isZero) return '<span class="text-slate-400 font-mono">&plusmn;0</span>';
    var isPositive = val > 0;
    var isGood = invertGoodBad ? !isPositive : isPositive;
    var color = isGood ? "text-emerald-400" : "text-amber-400";
    if (Math.abs(val) > 10 && !isGood) color = "text-red-400";
    var prefix = isPositive ? "+" : "";
    return '<span class="font-mono font-bold ' + color + '">' + prefix + (Number.isInteger(val) ? val : val.toFixed(1)) + '</span>';
  }

  // Helper for status badges
  function formatStatusBadge(statusStr) {
    var s = (statusStr || "READY").toUpperCase();
    var cls = s === "CRITICAL" ? "text-red-400 bg-red-950 border-red-500/40" : s === "DEGRADED" || s === "HIGH" ? "text-orange-400 bg-orange-950 border-orange-500/40" : s === "CAUTION" || s === "MEDIUM" ? "text-amber-400 bg-amber-950 border-amber-500/40" : "text-emerald-400 bg-emerald-950 border-emerald-500/40";
    return '<span class="px-2 py-0.5 text-[9px] font-mono font-bold rounded border ' + cls + '">' + s + '</span>';
  }

  // Extract Comparison Data
  var comp = result.comparison || {};
  
  var minInv = comp.minimum_inventory || { baseline: result.minimum_simulated_inventory || 0, scenario: result.minimum_simulated_inventory || 0, delta: 0 };
  var finalInv = comp.final_inventory || { baseline: 0, scenario: 0, delta: 0 };
  var shortfall = comp.inventory_shortfall || { baseline: 0, scenario: result.inventory_shortfall || 0, delta: result.inventory_shortfall || 0 };
  
  var stockoutOcc = comp.stockout_occurrence || { baseline: false, scenario: (result.stockout_day !== null), changed: (result.stockout_day !== null) };
  var stockoutDay = comp.stockout_day || { baseline: null, scenario: result.stockout_day, changed: (result.stockout_day !== null) };
  var breachDay = comp.threshold_breach_day || { baseline: null, scenario: result.threshold_breach_day, changed: (result.threshold_breach_day !== null) };
  
  var riskScore = comp.risk_score || { baseline: result.baseline_risk_score || 0, scenario: result.simulated_risk_score || 0, delta: result.risk_score_delta || 0 };
  var riskClass = comp.risk_classification || { baseline: result.baseline_risk_level || "LOW", scenario: result.simulated_risk_level || "HIGH", changed: true };
  
  var readyScore = comp.readiness_score || { baseline: result.baseline_readiness_score || 0, scenario: result.simulated_readiness_score || 0, delta: result.readiness_score_delta || 0 };
  var readyStatus = comp.readiness_status || { baseline: result.baseline_readiness_status || "READY", scenario: result.simulated_readiness_status || "DEGRADED", changed: true };

  var shipCount = comp.affected_shipment_count || { baseline: 0, scenario: (result.affected_shipments || []).length, delta: (result.affected_shipments || []).length };
  var delayedQty = comp.total_delayed_shipment_quantity || { baseline: 0, scenario: (result.affected_shipments || []).reduce(function(a, b) { return a + (b.quantity || 0); }, 0), delta: 0 };
  var maxDelay = comp.max_shipment_delay_days || { baseline: 0, scenario: Math.max.apply(Math, (result.affected_shipments || []).map(function(s) { return s.delay_days || 0; }).concat([0])), delta: 0 };

  // Human Summary & Baseline Breach Notices (Requirement #5, #8, #9)
  var summaryText = result.human_summary || result.explanation || "Simulation finished successfully.";
  
  var baselineBreachNote = "";
  if (breachDay.baseline !== null && breachDay.baseline !== undefined && breachDay.baseline === breachDay.scenario) {
    baselineBreachNote += '<div class="flex items-center gap-2 p-2.5 bg-amber-950/30 border border-amber-500/30 rounded-lg text-amber-300 text-[11px]"><span class="font-bold">⚠️ Notice:</span> Threshold breach (Day D+' + breachDay.baseline + ') was already present in baseline before this disruption.</div>';
  }
  if (stockoutDay.baseline !== null && stockoutDay.baseline !== undefined && stockoutDay.baseline === stockoutDay.scenario) {
    baselineBreachNote += '<div class="flex items-center gap-2 p-2.5 bg-red-950/30 border border-red-500/30 rounded-lg text-red-300 text-[11px]"><span class="font-bold">⚠️ Notice:</span> Stock-out (Day D+' + stockoutDay.baseline + ') was already present in baseline before this disruption.</div>';
  }

  // Format Helper for Day metrics
  function formatDayValue(dayVal, baselineVal, isChanged) {
    if (dayVal === null || dayVal === undefined) return '<span class="text-emerald-400 font-bold">None</span>';
    if (!isChanged && baselineVal === dayVal) {
      return '<span class="text-amber-300 font-mono font-bold">Day D+' + dayVal + '</span> <span class="text-[9px] text-slate-500 block">(Baseline Existing)</span>';
    }
    return '<span class="text-red-400 font-mono font-bold">Day D+' + dayVal + '</span>';
  }

  // Comparison Metrics Grid Items
  var metricsGridHtml = [
    { label: "Risk Score", base: riskScore.baseline.toFixed(1), scen: riskScore.scenario.toFixed(1), delta: formatMetricDelta(riskScore.delta, false) },
    { label: "Risk Classification", base: formatStatusBadge(riskClass.baseline), scen: formatStatusBadge(riskClass.scenario), delta: riskClass.changed ? '<span class="text-amber-400 font-bold text-[9px]">CHANGED</span>' : '<span class="text-slate-500 font-mono text-[9px]">UNCHANGED</span>' },
    { label: "Readiness Score", base: readyScore.baseline.toFixed(0) + "%", scen: readyScore.scenario.toFixed(0) + "%", delta: formatMetricDelta(readyScore.delta, true) },
    { label: "Readiness Status", base: formatStatusBadge(readyStatus.baseline), scen: formatStatusBadge(readyStatus.scenario), delta: readyStatus.changed ? '<span class="text-amber-400 font-bold text-[9px]">CHANGED</span>' : '<span class="text-slate-500 font-mono text-[9px]">UNCHANGED</span>' },
    { label: "Minimum Inventory", base: minInv.baseline.toFixed(0), scen: minInv.scenario.toFixed(0), delta: formatMetricDelta(minInv.delta, true) },
    { label: "Final Inventory", base: finalInv.baseline.toFixed(0), scen: finalInv.scenario.toFixed(0), delta: formatMetricDelta(finalInv.delta, true) },
    { label: "Inventory Shortfall", base: shortfall.baseline.toFixed(0), scen: shortfall.scenario.toFixed(0), delta: formatMetricDelta(shortfall.delta, false) },
    { label: "Stock-out Occurrence", base: stockoutOcc.baseline ? "YES" : "NO", scen: stockoutOcc.scenario ? '<span class="text-red-400 font-bold">YES</span>' : "NO", delta: stockoutOcc.changed ? '<span class="text-red-400 font-bold text-[9px]">NEW STOCKOUT</span>' : '<span class="text-slate-500 font-mono text-[9px]">UNCHANGED</span>' },
    { label: "Stock-out Day", base: stockoutDay.baseline ? "Day D+" + stockoutDay.baseline : "None", scen: formatDayValue(stockoutDay.scenario, stockoutDay.baseline, stockoutDay.changed), delta: stockoutDay.changed ? '<span class="text-red-400 font-bold text-[9px]">SHIFTED</span>' : '<span class="text-slate-500 font-mono text-[9px]">--</span>' },
    { label: "Threshold Breach Day", base: breachDay.baseline ? "Day D+" + breachDay.baseline : "None", scen: formatDayValue(breachDay.scenario, breachDay.baseline, breachDay.changed), delta: breachDay.changed ? '<span class="text-amber-400 font-bold text-[9px]">SHIFTED</span>' : '<span class="text-slate-500 font-mono text-[9px]">--</span>' },
    { label: "Affected Shipments", base: shipCount.baseline, scen: shipCount.scenario, delta: formatMetricDelta(shipCount.delta, false) },
    { label: "Total Delayed Quantity", base: delayedQty.baseline, scen: delayedQty.scenario, delta: formatMetricDelta(delayedQty.delta, false) },
    { label: "Max Shipment Delay", base: maxDelay.baseline + "d", scen: maxDelay.scenario + "d", delta: formatMetricDelta(maxDelay.delta, false) }
  ].map(function(m) {
    return '<div class="p-3 bg-slate-900/90 border border-slate-800 rounded-xl space-y-1">' +
      '<div class="text-[9px] uppercase font-bold tracking-wider text-slate-400 truncate" title="' + m.label + '">' + m.label + '</div>' +
      '<div class="flex items-center justify-between gap-1 text-xs">' +
        '<div class="font-mono text-slate-300 font-semibold">' + m.base + ' &rarr; <span class="text-white font-bold">' + m.scen + '</span></div>' +
        '<div class="shrink-0">' + m.delta + '</div>' +
      '</div>' +
      '</div>';
  }).join("");

  // Causal Chain Steps HTML (Requirement #2, #3)
  var causalChainList = result.causal_chain || [];
  var causalChainHtml = "";
  if (causalChainList.length > 0) {
    causalChainHtml = '<div class="space-y-3 pt-2">' +
      '<div class="flex items-center justify-between">' +
        '<div class="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2"><span>⛓️</span> Causal Propagation Chain</div>' +
        '<span class="text-[9px] text-slate-400 font-mono">Sequential Disruption Flow</span>' +
      '</div>' +
      '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">' +
      causalChainList.map(function(stepText, idx) {
        var num = (idx + 1 < 10 ? "0" : "") + (idx + 1);
        var icon = "🔗";
        var txtLower = stepText.toLowerCase();
        if (txtLower.indexOf("disruption") !== -1 || txtLower.indexOf("hazard") !== -1) icon = "🚨";
        else if (txtLower.indexOf("shipment") !== -1 || txtLower.indexOf("supply") !== -1 || txtLower.indexOf("postponed") !== -1 || txtLower.indexOf("delayed") !== -1) icon = "🚚";
        else if (txtLower.indexOf("consumption") !== -1 || txtLower.indexOf("rate") !== -1) icon = "⚡";
        else if (txtLower.indexOf("inventory") !== -1 || txtLower.indexOf("threshold") !== -1 || txtLower.indexOf("stock-out") !== -1) icon = "📦";
        else if (txtLower.indexOf("risk") !== -1) icon = "⚠️";
        else if (txtLower.indexOf("readiness") !== -1) icon = "🎯";

        return '<div class="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-2 relative group hover:border-cyan-500/40 transition">' +
          '<div class="flex items-center justify-between text-[10px]">' +
            '<span class="font-mono font-bold text-cyan-400 bg-cyan-950 border border-cyan-500/30 px-2 py-0.5 rounded">STEP ' + num + '</span>' +
            '<span class="text-base">' + icon + '</span>' +
          '</div>' +
          '<p class="text-xs text-slate-200 font-medium leading-relaxed">' + stepText + '</p>' +
          '</div>';
      }).join("") +
      '</div></div>';
  } else {
    causalChainHtml = '<div class="p-4 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-400 text-center font-mono">CAUSAL ANALYSIS UNAVAILABLE</div>';
  }

  // Scenario -> Consequence Summary Panel (Requirement #6)
  var triggerText = (result.scenario_type || "ROUTE_DISRUPTION").replace(/_/g, " ") + (result.affected_route_id ? " (" + result.affected_route_id + ")" : "");
  var propagationText = shipCount.scenario > 0 ? shipCount.scenario + " shipment(s) delayed (" + delayedQty.scenario.toFixed(0) + " units)" : "No shipment delays";
  var outcomeText = "Risk: " + (result.simulated_risk_level || "HIGH") + " (" + (riskScore.delta > 0 ? "+" : "") + riskScore.delta.toFixed(1) + ")";

  var consequenceSummaryHtml = '<div class="p-4 rounded-xl bg-slate-900/90 border border-brandBorder space-y-2">' +
    '<div class="text-[10px] uppercase font-bold tracking-wider text-slate-400 flex items-center gap-1.5"><span>🎯</span> Scenario Impact Flow</div>' +
    '<div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs pt-1">' +
      '<div class="p-2.5 rounded-lg bg-slate-950 border border-slate-800"><div class="text-[9px] uppercase font-bold text-cyan-400 mb-0.5">1. Trigger Scenario</div><div class="font-bold text-white truncate">' + triggerText + '</div><div class="text-[10px] text-slate-400 mt-0.5">Duration: ' + (result.disruption_duration_days || "--") + ' days &middot; Severity: ' + (result.severity || "HIGH") + '</div></div>' +
      '<div class="p-2.5 rounded-lg bg-slate-950 border border-slate-800"><div class="text-[9px] uppercase font-bold text-amber-400 mb-0.5">2. Supply Propagation</div><div class="font-bold text-slate-200 truncate">' + propagationText + '</div><div class="text-[10px] text-slate-400 mt-0.5">Max delay: +' + maxDelay.scenario + ' days</div></div>' +
      '<div class="p-2.5 rounded-lg bg-slate-950 border border-slate-800"><div class="text-[9px] uppercase font-bold text-red-400 mb-0.5">3. Operational Outcome</div><div class="font-bold text-slate-200 truncate">' + outcomeText + '</div><div class="text-[10px] text-slate-400 mt-0.5">Readiness score: ' + readyScore.scenario.toFixed(0) + '%</div></div>' +
    '</div></div>';

  // Contributing Factors Panel (Requirement #4)
  var factorsList = result.contributing_factors || [];
  var contributingFactorsHtml = "";
  if (factorsList.length > 0) {
    contributingFactorsHtml = '<div class="space-y-3 pt-2">' +
      '<div class="flex items-center justify-between">' +
        '<div class="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2"><span>🔍</span> Contributing Risk &amp; Disruption Factors (' + factorsList.length + ')</div>' +
        '<span class="text-[9px] text-slate-400 font-mono">Evidence &amp; Disruption Parameters</span>' +
      '</div>' +
      '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">' +
      factorsList.map(function(f) {
        var factorName = (f.factor || "FACTOR").replace(/_/g, " ");
        var sevBadge = formatStatusBadge(f.severity || "MEDIUM");
        return '<div tabindex="0" class="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2 hover:border-amber-500/40 focus:border-amber-500/60 focus:outline-none transition cursor-pointer group">' +
          '<div class="flex items-center justify-between gap-2"><div class="font-extrabold text-white text-xs truncate group-hover:text-amber-300 transition">' + factorName + '</div>' + sevBadge + '</div>' +
          '<p class="text-[11px] text-slate-300 leading-snug">' + (f.description || "") + '</p>' +
          (f.impact ? '<div class="text-[10px] text-slate-400 bg-slate-950 border border-slate-800/80 p-2 rounded-lg font-mono mt-1">' + f.impact + '</div>' : '') +
          '</div>';
      }).join("") +
      '</div></div>';
  } else {
    contributingFactorsHtml = '<div class="p-4 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-400 text-center font-mono">NO ADDITIONAL CONTRIBUTING FACTORS RETURNED</div>';
  }

  // Supply Movement Table
  var shipmentsList = result.affected_shipments || [];
  var shipmentsHtml = "";
  if (shipmentsList.length > 0) {
    shipmentsHtml = '<div class="space-y-3 pt-2"><div class="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2"><span>🚚</span> Supply Movement Impacts (' + shipmentsList.length + ' Shipments Affected)</div>' +
      '<div class="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950"><table class="w-full text-left text-[11px] border-collapse"><thead><tr class="bg-slate-900 text-slate-400 font-bold uppercase text-[9px] border-b border-slate-800"><th class="p-2.5 pl-4">Shipment ID</th><th class="p-2.5">Route</th><th class="p-2.5">Cargo Item</th><th class="p-2.5 text-right">Quantity</th><th class="p-2.5 text-center">Expected</th><th class="p-2.5 text-center">Simulated</th><th class="p-2.5 text-right pr-4">Delay</th></tr></thead><tbody class="divide-y divide-slate-800/60 text-slate-300">' +
      shipmentsList.map(function(s) {
        var delayColor = s.delay_days > 3 ? "text-red-400 font-extrabold" : s.delay_days > 0 ? "text-amber-400 font-bold" : "text-emerald-400";
        return '<tr><td class="p-2.5 pl-4 font-mono font-bold text-white">' + s.shipment_id + '</td><td class="p-2.5 font-mono text-slate-400">' + (s.route_id || "--") + '</td><td class="p-2.5 font-semibold text-slate-200">' + (s.cargo_item_id || "--") + '</td><td class="p-2.5 text-right font-mono">' + (s.quantity || 0) + '</td><td class="p-2.5 text-center font-mono text-slate-400">Day D+' + (s.expected_arrival_day !== undefined ? s.expected_arrival_day : "--") + '</td><td class="p-2.5 text-center font-mono text-amber-300">Day D+' + (s.simulated_arrival_day !== undefined ? s.simulated_arrival_day : "--") + '</td><td class="p-2.5 text-right pr-4 font-mono ' + delayColor + '">+' + (s.delay_days || 0) + 'd</td></tr>';
      }).join("") +
      '</tbody></table></div></div>';
  } else {
    shipmentsHtml = '<div class="p-4 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-400 text-center">No replenishment shipments were delayed in this scenario.</div>';
  }

  // Render Full Outcome Panel
  el.innerHTML = '<div class="p-6 space-y-6 border-t border-slate-800 bg-slate-950/90">' +
    '<div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">' +
      '<div>' +
        '<div class="text-xs font-black text-cyan-400 uppercase tracking-widest flex items-center gap-2">' +
          '<span class="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse"></span>' +
          'SIMULATION OUTCOME &amp; EXPLAINABILITY' +
        '</div>' +
        '<div class="text-sm font-bold text-white mt-1 font-display">' +
          (result.affected_depot_name || result.affected_depot_id || "Depot") + ' &middot; ' + (result.scenario_type || "ROUTE_DISRUPTION").replace(/_/g, " ") +
        '</div>' +
        '<div class="text-[10px] text-slate-400 font-mono mt-0.5 flex flex-wrap gap-2 items-center">' +
          '<span>Scenario ID: ' + (result.scenario_id || "--") + '</span>' +
          (result.base_name ? '<span>&bull; Base: ' + result.base_name + '</span>' : '') +
        '</div>' +
      '</div>' +
      '<div class="flex items-center gap-2 shrink-0 flex-wrap">' +
        '<span class="px-2.5 py-1 text-[10px] font-mono font-bold rounded bg-slate-900 text-slate-300 border border-slate-700">Duration: ' + (result.disruption_duration_days || "--") + 'd</span>' +
        formatStatusBadge(result.simulated_risk_level || result.severity) +
        '<span class="text-[9px] bg-cyan-950 border border-cyan-500/40 text-cyan-300 px-2.5 py-1 rounded font-mono font-bold">SYNTHETIC DEMO</span>' +
      '</div>' +
    '</div>' +

    '<div class="p-4 bg-cyan-950/20 border border-cyan-500/30 rounded-xl space-y-2">' +
      '<div class="text-[10px] font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5"><span>🧠</span> Operational Assessment &amp; Human Summary</div>' +
      '<p class="text-xs text-slate-200 leading-relaxed font-medium">' + summaryText + '</p>' +
      baselineBreachNote +
    '</div>' +

    consequenceSummaryHtml +

    causalChainHtml +

    '<div class="space-y-2">' +
      '<div class="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2"><span>📊</span> Key Metric Comparison</div>' +
      '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">' + metricsGridHtml + '</div>' +
    '</div>' +

    '<div class="space-y-2">' +
      '<div class="flex items-center justify-between">' +
        '<div class="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2"><span>📈</span> Inventory Trajectory Timeline</div>' +
        '<span class="text-[10px] text-slate-400 font-mono">Baseline vs Simulated Stock Level</span>' +
      '</div>' +
      '<div class="h-64 p-4 rounded-xl bg-slate-900 border border-slate-800 relative shadow-inner">' +
        '<canvas id="chart-dt-trajectory"></canvas>' +
      '</div>' +
    '</div>' +

    contributingFactorsHtml +

    shipmentsHtml +

  '</div>';

  // Render Trajectory Chart
  setTimeout(function() {
    renderTrajectoryChart(result.trajectory || []);
  }, 50);
}

function renderTrajectoryChart(trajectory) {
  var canvasCtx = document.getElementById("chart-dt-trajectory");
  if (!canvasCtx) return;

  if (window.charts && window.charts.dtTrajectory) {
    window.charts.dtTrajectory.destroy();
  }

  if (!trajectory || trajectory.length === 0) {
    var parent = canvasCtx.parentElement;
    if (parent) {
      parent.innerHTML = '<div class="h-full flex items-center justify-center text-slate-500 font-mono text-xs">TRAJECTORY DATA UNAVAILABLE</div>';
    }
    return;
  }

  var labels = trajectory.map(function(t) { return "D+" + t.day; });
  var baselineData = trajectory.map(function(t) { return t.baseline_inventory !== undefined ? t.baseline_inventory : 0; });
  var simulatedData = trajectory.map(function(t) { return t.simulated_inventory !== undefined ? t.simulated_inventory : 0; });
  var thresholdData = trajectory.map(function(t) { return t.threshold !== undefined ? t.threshold : 0; });

  if (!window.charts) window.charts = {};

  window.charts.dtTrajectory = new Chart(canvasCtx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Baseline Inventory',
          data: baselineData,
          borderColor: '#06b6d4',
          backgroundColor: 'transparent',
          borderDash: [4, 4],
          borderWidth: 2,
          pointRadius: 3,
          tension: 0.2
        },
        {
          label: 'Simulated Inventory',
          data: simulatedData,
          borderColor: '#f59e0b',
          backgroundColor: 'rgba(245, 158, 11, 0.08)',
          fill: true,
          borderWidth: 3,
          pointRadius: 4,
          pointBackgroundColor: '#f59e0b',
          tension: 0.2
        },
        {
          label: 'Safety Threshold',
          data: thresholdData,
          borderColor: '#ef4444',
          backgroundColor: 'transparent',
          borderDash: [3, 3],
          borderWidth: 1.5,
          pointRadius: 0,
          tension: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          position: 'top',
          labels: { color: '#cbd5e1', font: { size: 10, weight: 'bold' }, boxWidth: 10 }
        },
        tooltip: {
          backgroundColor: '#090d16',
          borderColor: 'rgba(255,255,255,0.15)',
          borderWidth: 1,
          titleFont: { size: 11, weight: 'bold' },
          bodyFont: { size: 10 },
          padding: 10
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8', font: { size: 10, family: 'monospace' } }
        },
        y: {
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8', font: { size: 10, family: 'monospace' } },
          title: { display: true, text: 'Inventory Stock Units', color: '#64748b', font: { size: 10 } }
        }
      }
    }
  });
}

// ============================================================
// Phase 12B: Intelligence Module Status Badges
// ============================================================
function applyIntelligenceModuleStatus(data) {
  var row = document.getElementById("unified-module-status-row");
  if (!row) return;
  var status = data.intelligence_status || {};
  var modules = [
    { key: "operational_data",       label: "Ops Data",       icon: "🗺️" },
    { key: "inventory",              label: "Inventory",      icon: "📦" },
    { key: "forecasting",            label: "Forecasting",    icon: "📈" },
    { key: "risk_engine",            label: "Risk Engine",    icon: "⚠️" },
    { key: "readiness_engine",       label: "Readiness",      icon: "🎯" },
    { key: "environmental_intelligence", label: "Env Intel", icon: "🌦️" },
    { key: "supply_movement",        label: "Supply Mvmt",    icon: "🚚" },
    { key: "digital_twin",           label: "Digital Twin",   icon: "📦" },
    { key: "advisor",                label: "Advisor",        icon: "🤖" }
  ];
  row.innerHTML = modules.map(function(m) {
    var s = (status[m.key] || "UNAVAILABLE").toUpperCase();
    var isOk = s === "AVAILABLE" || s === "ACTIVE" || s === "NO_ACTIVE_SCENARIO" || s === "READY";
    var isWarn = s === "NO_ACTIVE_SCENARIO";
    var cls = isWarn
      ? "bg-slate-900 border-slate-700 text-slate-300"
      : isOk
      ? "bg-emerald-950/50 border-emerald-500/30 text-emerald-400"
      : "bg-red-950/50 border-red-500/30 text-red-400";
    var dot = isWarn ? "text-slate-400" : isOk ? "text-emerald-400" : "text-red-400";
    var label = isWarn ? "STANDBY" : s;
    return '<div class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border ' + cls + ' text-[10px] font-mono font-bold">' +
      '<span class="' + dot + ' text-[8px]">●</span>' +
      '<span class="text-slate-300 text-[9px]">' + m.icon + '</span>' +
      '<span>' + m.label + '</span>' +
      '<span class="text-[8px] opacity-70">' + label + '</span>' +
      '</div>';
  }).join("");

  // Update sidebar unified-intel badge
  var badge = document.getElementById("sidebar-unified-intel-badge");
  if (badge) {
    var unavailableCount = modules.filter(function(m) {
      var s = (status[m.key] || "").toUpperCase();
      return s !== "AVAILABLE" && s !== "ACTIVE" && s !== "NO_ACTIVE_SCENARIO" && s !== "READY";
    }).length;
    if (unavailableCount === 0) {
      badge.innerText = "LIVE";
      badge.className = "text-[8px] bg-emerald-950 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 rounded font-mono";
    } else {
      badge.innerText = unavailableCount + " DOWN";
      badge.className = "text-[8px] bg-red-950 text-red-400 border border-red-500/30 px-1.5 py-0.5 rounded font-mono";
    }
  }
}

// ============================================================
// Phase 12B: Critical Signals — Overview Panel + Full Panel
// ============================================================
function applyCriticalSignals(data) {
  var signals = data.critical_signals || [];

  // Classification styling
  function signalStyle(classification) {
    var c = (classification || "").toUpperCase();
    if (c === "CRITICAL") return { border: "border-red-500/40 bg-red-950/20", badge: "bg-red-950 text-red-400 border-red-500/40", dot: "bg-red-500" };
    if (c === "HIGH")     return { border: "border-orange-500/30 bg-orange-950/20", badge: "bg-orange-950 text-orange-400 border-orange-500/30", dot: "bg-orange-500" };
    if (c === "MEDIUM")   return { border: "border-amber-500/30 bg-amber-950/20", badge: "bg-amber-950 text-amber-400 border-amber-500/30", dot: "bg-amber-400" };
    return { border: "border-slate-700 bg-slate-900/40", badge: "bg-slate-800 text-slate-300 border-slate-700", dot: "bg-slate-400" };
  }

  // Overview mini-card renderer (compact, max 5)
  var overviewEl = document.getElementById("unified-critical-signals-overview");
  if (overviewEl) {
    if (signals.length === 0) {
      overviewEl.innerHTML = '';
    } else {
      overviewEl.innerHTML = signals.slice(0, 5).map(function(s) {
        var st = signalStyle(s.classification);
        return '<div class="flex items-start gap-2 p-2 rounded-lg border ' + st.border + ' text-[10px]">' +
          '<span class="w-1.5 h-1.5 rounded-full mt-0.5 shrink-0 ' + st.dot + '"></span>' +
          '<div class="flex-1 min-w-0">' +
            '<span class="font-bold text-slate-200 block truncate">' + (s.explanation || "") + '</span>' +
            '<span class="text-[9px] text-slate-500 font-mono">' + s.source_module + ' · ' + s.entity_id + '</span>' +
          '</div>' +
          '<span class="shrink-0 px-1.5 py-0.5 rounded text-[8px] font-mono font-bold border ' + st.badge + '">' + s.classification + '</span>' +
        '</div>';
      }).join("");
    }
  }

  // Full signals panel
  var fullEl = document.getElementById("unified-critical-signals-panel");
  var countBadge = document.getElementById("unified-signals-count-badge");
  if (countBadge) {
    countBadge.innerText = signals.length > 0 ? signals.length + " Signal" + (signals.length !== 1 ? "s" : "") : "None";
    countBadge.className = signals.length > 0
      ? "text-[10px] bg-red-950 text-red-400 border border-red-500/30 px-2 py-0.5 rounded font-mono font-bold"
      : "text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded font-mono font-bold";
  }
  if (!fullEl) return;
  if (signals.length === 0) {
    fullEl.innerHTML = '<div class="text-xs text-slate-400 text-center py-8 border border-dashed border-slate-800 rounded-xl"><div class="text-2xl mb-2">&#10003;</div>No cross-module critical signals detected.</div>';
    return;
  }
  fullEl.innerHTML = signals.map(function(s) {
    var st = signalStyle(s.classification);
    var valStr = (s.relevant_value !== undefined && s.relevant_value !== null) ? String(s.relevant_value) : "";
    return '<div class="flex items-start gap-3 p-3.5 rounded-xl border ' + st.border + ' text-xs gap-3 transition">' +
      '<span class="w-2 h-2 rounded-full mt-1 shrink-0 ' + st.dot + ' animate-pulse"></span>' +
      '<div class="flex-1 min-w-0 space-y-0.5">' +
        '<div class="font-bold text-slate-100 text-sm leading-snug">' + (s.explanation || "") + '</div>' +
        '<div class="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[10px] text-slate-400 font-mono">' +
          '<span class="text-violet-400">' + (s.source_module || "").replace(/_/g, " ") + '</span>' +
          '<span>&#183; ' + (s.entity_type || "") + ': <span class="text-white font-bold">' + (s.entity_id || "") + '</span></span>' +
          (valStr ? '<span>&#183; Value: <span class="text-amber-300">' + valStr + '</span></span>' : '') +
          '<span>&#183; ID: <span class="text-slate-500">' + (s.signal_id || "") + '</span></span>' +
        '</div>' +
      '</div>' +
      '<span class="shrink-0 px-2 py-0.5 text-[9px] font-mono font-bold rounded border ' + st.badge + '">' + s.classification + '</span>' +
    '</div>';
  }).join("");
}

// ============================================================
// Phase 12B: Depot Unified Views Grid
// ============================================================
function applyUnifiedIntelligence(data) {
  var depotViews = data.depot_views || [];
  var grid = document.getElementById("unified-depot-views-grid");
  if (!grid) return;

  if (depotViews.length === 0) {
    grid.innerHTML = '<div class="col-span-full text-center text-xs text-slate-400 py-8 border border-dashed border-slate-800 rounded-xl">No depot unified views available.</div>';
    return;
  }

  function readinessCls(status) {
    var s = (status || "").toUpperCase();
    if (s === "CRITICAL") return "text-red-400";
    if (s === "DEGRADED") return "text-orange-400";
    if (s === "CAUTION")  return "text-amber-400";
    return "text-emerald-400";
  }
  function riskCls(level) {
    var s = (level || "").toUpperCase();
    if (s === "CRITICAL") return "text-red-400";
    if (s === "HIGH")     return "text-orange-400";
    if (s === "MEDIUM")   return "text-amber-400";
    return "text-emerald-400";
  }
  function borderCls(readinessStatus, riskLevel) {
    var rs = (readinessStatus || "").toUpperCase();
    var rl = (riskLevel || "").toUpperCase();
    if (rs === "CRITICAL" || rl === "CRITICAL") return "border-red-500/40 bg-red-950/10";
    if (rs === "DEGRADED" || rl === "HIGH")     return "border-orange-500/30 bg-orange-950/10";
    if (rs === "CAUTION"  || rl === "MEDIUM")   return "border-amber-500/20 bg-amber-950/10";
    return "border-slate-700";
  }

  grid.innerHTML = depotViews.map(function(dv) {
    var inv  = dv.inventory_health || {};
    var sor  = dv.stock_out_risk || {};
    var risk = dv.operational_risk || {};
    var mr   = dv.mission_readiness || {};
    var env  = dv.environmental_exposure || {};
    var sup  = dv.relevant_supply_movement || {};

    var bc = borderCls(mr.readiness_status, risk.risk_level);

    // Contributing factors pills
    var factorPills = (risk.top_contributing_factors || []).slice(0, 3).map(function(f) {
      return '<span class="text-[9px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded font-mono">' + f + '</span>';
    }).join("");

    // Readiness issues pills
    var issuePills = (mr.key_issues || []).slice(0, 3).map(function(i) {
      return '<span class="text-[9px] bg-red-950/50 text-red-400 border border-red-500/20 px-1.5 py-0.5 rounded font-mono">' + i + '</span>';
    }).join("");

    // Env exposure
    var envHtml = env.status === "UNAVAILABLE" || !env.route_id
      ? '<span class="text-[9px] text-slate-500 font-mono italic">' + (env.limitation || "No route data") + '</span>'
      : '<span class="text-[9px] font-mono">Route: <span class="text-slate-200 font-bold">' + env.route_id + '</span></span>' +
        '<span class="text-[9px] ml-2 font-mono">Env Risk: <span class="' + riskCls(env.classification) + ' font-bold">' + (env.environmental_risk_score !== undefined ? env.environmental_risk_score.toFixed(1) : "--") + '</span></span>';

    // High-pressure items
    var hpItems = (sor.high_pressure_items || []).slice(0, 2).map(function(it) {
      return '<div class="text-[9px] font-mono text-amber-300">▲ ' + (it.item_name || it.item_id || "") + (it.days_until_stockout !== null && it.days_until_stockout !== undefined ? ' — D+' + it.days_until_stockout + ' stockout' : '') + '</div>';
    }).join("");

    return '<div class="p-5 rounded-xl glass-card border ' + bc + ' space-y-4 transition hover:shadow-lg hover:shadow-violet-500/5">' +
      // Header
      '<div class="flex items-start justify-between gap-3">' +
        '<div class="min-w-0">' +
          '<div class="font-bold text-white text-sm truncate">' + (dv.depot_name || dv.depot_id) + '</div>' +
          '<div class="text-[10px] text-slate-400 font-mono mt-0.5">' + dv.depot_id + (dv.base_name ? ' · ' + dv.base_name : '') + '</div>' +
        '</div>' +
        '<div class="flex items-center gap-1.5 shrink-0">' +
          '<span class="text-[9px] px-2 py-0.5 rounded font-mono font-bold border bg-slate-800 border-slate-700 text-slate-300">' + (dv.data_source || "DEMO").toUpperCase() + '</span>' +
        '</div>' +
      '</div>' +
      // 4-metric summary grid
      '<div class="grid grid-cols-2 gap-2">' +
        // Readiness
        '<div class="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 space-y-0.5">' +
          '<div class="text-[9px] uppercase font-bold tracking-wider text-slate-400">Readiness</div>' +
          '<div class="text-lg font-black ' + readinessCls(mr.readiness_status) + '">' + (mr.readiness_score !== undefined ? mr.readiness_score.toFixed(0) : "--") + '%</div>' +
          '<div class="text-[9px] font-mono ' + readinessCls(mr.readiness_status) + ' font-bold">' + (mr.readiness_status || "--") + '</div>' +
        '</div>' +
        // Risk
        '<div class="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 space-y-0.5">' +
          '<div class="text-[9px] uppercase font-bold tracking-wider text-slate-400">Risk Score</div>' +
          '<div class="text-lg font-black ' + riskCls(risk.risk_level) + '">' + (risk.risk_score !== undefined ? risk.risk_score.toFixed(1) : "--") + '</div>' +
          '<div class="text-[9px] font-mono ' + riskCls(risk.risk_level) + ' font-bold">' + (risk.risk_level || "--") + '</div>' +
        '</div>' +
        // Inventory
        '<div class="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 space-y-0.5">' +
          '<div class="text-[9px] uppercase font-bold tracking-wider text-slate-400">Inventory</div>' +
          '<div class="text-sm font-black text-white">' + (inv.total_items !== undefined ? inv.total_items : "--") + ' items</div>' +
          '<div class="text-[9px] font-mono ' + (inv.items_below_threshold_count > 0 ? "text-red-400" : "text-emerald-400") + '">' + (inv.items_below_threshold_count || 0) + ' below threshold</div>' +
        '</div>' +
        // Supply Movement
        '<div class="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 space-y-0.5">' +
          '<div class="text-[9px] uppercase font-bold tracking-wider text-slate-400">Supply Mvmt</div>' +
          '<div class="text-sm font-black text-white">' + (sup.active_shipments_count || 0) + ' active</div>' +
          '<div class="text-[9px] font-mono ' + (sup.delayed_shipments_count > 0 ? "text-amber-400" : "text-emerald-400") + '">' + (sup.delayed_shipments_count || 0) + ' delayed</div>' +
        '</div>' +
      '</div>' +
      // Environmental exposure
      '<div class="border-t border-slate-800 pt-2 space-y-1">' +
        '<div class="text-[9px] uppercase font-bold tracking-wider text-slate-500">Environmental Exposure</div>' +
        '<div class="flex flex-wrap gap-2 items-center">' + envHtml + '</div>' +
      '</div>' +
      // Stockout risk
      (sor.projected_stockouts_count > 0 || hpItems ? '<div class="border-t border-slate-800 pt-2 space-y-1">' +
        '<div class="text-[9px] uppercase font-bold tracking-wider text-slate-500">Stockout Risk</div>' +
        '<div class="text-[10px] font-mono ' + (sor.projected_stockouts_count > 0 ? "text-red-400 font-bold" : "text-slate-400") + '">' + (sor.projected_stockouts_count || 0) + ' projected stockouts, ' + (sor.high_pressure_items_count || 0) + ' high-pressure</div>' +
        hpItems +
      '</div>' : '') +
      // Risk factors
      (factorPills ? '<div class="border-t border-slate-800 pt-2 space-y-1">' +
        '<div class="text-[9px] uppercase font-bold tracking-wider text-slate-500">Top Risk Factors</div>' +
        '<div class="flex flex-wrap gap-1">' + factorPills + '</div>' +
      '</div>' : '') +
      // Readiness issues
      (issuePills ? '<div class="border-t border-slate-800 pt-2 space-y-1">' +
        '<div class="text-[9px] uppercase font-bold tracking-wider text-slate-500">Readiness Issues</div>' +
        '<div class="flex flex-wrap gap-1">' + issuePills + '</div>' +
      '</div>' : '') +
    '</div>';
  }).join("");
}

function updateSidebarBadges(data) {
  var readiness = data.readiness_intelligence || {};
  var status = readiness.overall_readiness_status || "READY";

  var forecastBadge = document.getElementById("sidebar-forecast-badge");
  if (forecastBadge) { forecastBadge.innerText = "LIVE"; forecastBadge.className = "text-[8px] bg-emerald-950 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 rounded font-mono"; }

  var readinessBadge = document.getElementById("sidebar-readiness-badge");
  if (readinessBadge) {
    var label = status === "CRITICAL" ? "CRITICAL" : status === "DEGRADED" ? "DEGRADED" : status === "CAUTION" ? "CAUTION" : "LIVE";
    var cls = status === "CRITICAL" ? "bg-red-950 text-red-400 border-red-500/30" : status === "DEGRADED" ? "bg-orange-950 text-orange-400 border-orange-500/30" : status === "CAUTION" ? "bg-amber-950 text-amber-400 border-amber-500/30" : "bg-emerald-950 text-emerald-400 border-emerald-500/30";
    readinessBadge.innerText = label;
    readinessBadge.className = "text-[8px] " + cls + " border px-1.5 py-0.5 rounded font-mono";
  }

  var dtBadge = document.getElementById("sidebar-digital-twin-badge");
  if (dtBadge) {
    var dt = data.digital_twin || {};
    if (dt.scenario_available) { dtBadge.innerText = "ACTIVE"; dtBadge.className = "text-[8px] bg-cyan-950 text-cyan-400 border border-cyan-500/30 px-1.5 py-0.5 rounded font-mono"; }
    else { dtBadge.innerText = "READY"; dtBadge.className = "text-[8px] bg-slate-800 text-slate-300 border border-slate-700 px-1.5 py-0.5 rounded font-mono"; }
  }
}

// Intercept switchTab to lazy-load intelligence sections
var _origSwitchTab = window.switchTab;
window.switchTab = function (tabId) {
  if (_origSwitchTab) _origSwitchTab(tabId);
  if (tabId === "readiness") setTimeout(function() { window.fetchReadinessSectionData(); }, 100);
  if (tabId === "digital-twin") setTimeout(function() { window.initDigitalTwinSection(); }, 100);
  if (tabId === "forecast" && window.sentinelIntel) applyIntelligenceToForecastSection(window.sentinelIntel);
  if (tabId === "unified-intel" && window.sentinelIntel) {
    applyUnifiedIntelligence(window.sentinelIntel);
    applyCriticalSignals(window.sentinelIntel);
    applyIntelligenceModuleStatus(window.sentinelIntel);
  }
};

document.addEventListener("DOMContentLoaded", function () {
  setTimeout(function () { window.fetchIntelligenceDashboard(); }, 1200);
});
