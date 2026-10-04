// NER-LINK AI - Global Natural Language Command Search

window.executeGlobalSearch = function(query) {
  const q = query.toLowerCase().trim();
  const searchResults = document.getElementById("search-results-overlay");
  if (!searchResults) return;

  if (!q) {
    searchResults.classList.add("hidden");
    searchResults.innerHTML = "";
    return;
  }

  let resultHtml = "";
  let interpretation = "";
  let actionBtn = "";

  // 1. Parse query
  if (q.includes("sikkim") || q.includes("critical routes")) {
    interpretation = "Sikkim Corridors & Road Closures";
    resultHtml = `
      <div class="p-2 border-b border-slate-700/50">
        <div class="text-white font-semibold text-xs">NH-10 (Siliguri - Gangtok)</div>
        <div class="text-[11px] text-red-400 font-medium">Status: HIGH RISK (Score 78) - Active Slide Warning</div>
      </div>
      <div class="p-2">
        <div class="text-white font-semibold text-xs">Gangtok Depot Transit</div>
        <div class="text-[11px] text-slate-400">Inbound volume: 52 | Outbound: 48</div>
      </div>
    `;
    actionBtn = `<button onclick="window.triggerSearchAction('focus_sikkim')" class="mt-2 w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-1.5 px-3 rounded text-[11px] transition">Map Sikkim Corridors</button>`;
  }
  else if (q.includes("delay") || q.includes("delayed")) {
    interpretation = "Delayed Shipment Tracker";
    resultHtml = `
      <div class="p-2 border-b border-slate-700/50">
        <div class="text-white font-semibold text-xs">NER-10319 (Electronics)</div>
        <div class="text-[11px] text-red-400">Delayed on NH-10 - ETA exceeded by 105 mins</div>
      </div>
      <div class="p-2">
        <div class="text-white font-semibold text-xs">NER-10752 (General Cargo)</div>
        <div class="text-[11px] text-yellow-400">At Risk - Heavy congestion on NH-15 Bypass</div>
      </div>
    `;
    actionBtn = `<button onclick="window.triggerSearchAction('view_delayed_shipments')" class="mt-2 w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-1.5 px-3 rounded text-[11px] transition">View in Shipments Panel</button>`;
  }
  else if (q.includes("lowest accessibility") || q.includes("accessibility")) {
    interpretation = "Regional Accessibility Index Summary";
    resultHtml = `
      <div class="p-2 border-b border-slate-700/50">
        <div class="text-white font-semibold text-xs">Arunachal Pradesh - 61/100</div>
        <div class="text-[11px] text-red-400">Lowest Score: Poor mountainous pavement quality & landslide closures</div>
      </div>
      <div class="p-2">
        <div class="text-white font-semibold text-xs">Manipur - 67/100</div>
        <div class="text-[11px] text-slate-400">Secondary Lowest: Bridge repair delays on NH-150</div>
      </div>
    `;
    actionBtn = `<button onclick="window.triggerSearchAction('view_accessibility')" class="mt-2 w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-1.5 px-3 rounded text-[11px] transition">Open Accessibility Index</button>`;
  }
  else if (q.includes("flood") || q.includes("flooding")) {
    interpretation = "Active Flooding Incidents";
    resultHtml = `
      <div class="p-2">
        <div class="text-white font-semibold text-xs">Dhemaji Bypass Flooding (Assam)</div>
        <div class="text-[11px] text-red-400">Critical - Brahmaputra waterlogging restricts NH-14 access</div>
      </div>
    `;
    actionBtn = `<button onclick="window.triggerSearchAction('view_disruptions')" class="mt-2 w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-1.5 px-3 rounded text-[11px] transition">Open Disruption Center</button>`;
  }
  else if (q.includes("optimize") || (q.includes("guwahati") && q.includes("imphal"))) {
    interpretation = "Route Intelligence Setup";
    resultHtml = `
      <div class="p-2">
        <div class="text-white font-semibold text-xs">Guwahati Hub &rarr; Imphal Depot</div>
        <div class="text-[11px] text-emerald-400">AI Optimization Engine online. Ready to plot 3 alternate lanes.</div>
      </div>
    `;
    actionBtn = `<button onclick="window.triggerSearchAction('optimize_medical')" class="mt-2 w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-1.5 px-3 rounded text-[11px] transition">Run AI Route Optimization</button>`;
  }
  else {
    interpretation = "General Logistics Knowledge Base";
    resultHtml = `
      <div class="p-2 text-slate-400 text-xs">
        No specific data matches found. Click below to consult the AI Copilot assistant for natural language reasoning.
      </div>
    `;
    actionBtn = `<button onclick="window.triggerSearchAction('open_copilot')" class="mt-2 w-full bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 font-bold py-1.5 px-3 rounded text-[11px] transition">Ask AI Copilot Assistant</button>`;
  }

  // 2. Render container
  searchResults.innerHTML = `
    <div class="p-3 bg-slate-900 border border-slate-700 rounded-lg shadow-2xl text-slate-200 max-w-sm absolute right-0 mt-2 z-[9999] w-[320px] animate-fade-in">
      <div class="flex items-center justify-between border-b border-slate-700/50 pb-2 mb-2">
        <div class="flex items-center gap-1.5">
          <span class="text-xs text-blue-400">🧠</span>
          <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400">AI Intent Interpretation</span>
        </div>
        <button onclick="document.getElementById('search-results-overlay').classList.add('hidden')" class="text-slate-400 hover:text-white text-xs font-bold">&times;</button>
      </div>
      <div class="text-xs font-bold text-white mb-1.5">${interpretation}</div>
      <div class="space-y-1 text-slate-300 max-h-[200px] overflow-y-auto">
        ${resultHtml}
      </div>
      ${actionBtn}
    </div>
  `;
  searchResults.classList.remove("hidden");
};

window.triggerSearchAction = function(action) {
  // Hide search overlay
  document.getElementById("search-results-overlay").classList.add("hidden");
  // Reset input
  document.getElementById("global-search-input").value = "";

  if (action === "focus_sikkim") {
    window.switchTab("map");
    if (window.nerMap) {
      window.nerMap.setView([27.1770, 88.5303], 9);
      // Open NH-10 polyline tooltip
      setTimeout(() => {
        if (window.mapLayers.corridors["nh10"]) {
          window.mapLayers.corridors["nh10"].openTooltip();
        }
      }, 500);
    }
    window.showToast("Filtered view: Sikkim logistics network highlighted.", "info");
  }
  else if (action === "view_delayed_shipments") {
    window.switchTab("shipments");
    const searchField = document.querySelector("#shipments input[placeholder*='Search']");
    if (searchField) {
      searchField.value = "Delayed";
      searchField.dispatchEvent(new Event('input'));
    }
  }
  else if (action === "view_accessibility") {
    window.switchTab("accessibility");
  }
  else if (action === "view_disruptions") {
    window.switchTab("disruptions");
  }
  else if (action === "optimize_medical") {
    window.switchTab("routes");
    // Pre-fill Route planner form
    document.getElementById("route-origin").value = "Guwahati Hub";
    document.getElementById("route-destination").value = "Imphal Depot";
    document.getElementById("route-cargo").value = "Medicine";
    document.getElementById("route-priority").value = "Emergency";
    document.getElementById("route-weight").value = "3.2";
    
    window.showToast("Route Planner pre-filled. Triggering AI Optimization.", "info");
    // Trigger route generation
    setTimeout(() => {
      const genBtn = document.getElementById("generate-routes-btn");
      if (genBtn) genBtn.click();
    }, 400);
  }
  else if (action === "open_copilot") {
    const chatBtn = document.getElementById("copilot-trigger-btn");
    if (chatBtn) chatBtn.click();
  }
};
