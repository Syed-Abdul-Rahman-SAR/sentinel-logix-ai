// NER-LINK AI - Automated Hackathon Demonstration Controller

window.demoRunning = false;
window.demoTimeoutIds = [];

window.startDemoScenario = function() {
  if (window.demoRunning) return;
  window.demoRunning = true;

  // Render floating demo status card
  let statusCard = document.getElementById("demo-status-card");
  if (!statusCard) {
    statusCard = document.createElement("div");
    statusCard.id = "demo-status-card";
    statusCard.className = "fixed bottom-6 left-6 z-[9999] bg-slate-900 border-2 border-blue-500 rounded-xl shadow-2xl p-4 w-[340px] text-slate-200 animate-fade-in";
    document.body.appendChild(statusCard);
  }
  statusCard.classList.remove("hidden");

  // Disable UI buttons to prevent interference
  const runDemoBtns = document.querySelectorAll(".run-demo-btn");
  runDemoBtns.forEach(btn => {
    btn.disabled = true;
    btn.classList.add("opacity-50");
  });

  const steps = [
    {
      title: "Step 1: Establishing Baseline Grid",
      desc: "Restoring NER logistics network to a normal operational state. Weather is clear, accessibility index is at 75%.",
      action: () => {
        window.switchTab("overview");
        window.resetSimulation("nh10", "high_risk", "High Landslide Risk", "1h 45m", 78, "sikkim");
        if (window.resetMapZoom) window.resetMapZoom();
      },
      delay: 0
    },
    {
      title: "Step 2: Monitoring Weather Hazards",
      desc: "AI sensors detect heavy monsoonal rainfall (95mm) in the Teesta Valley. Sikkim weather shifts to Heavy Rain.",
      action: () => {
        window.switchTab("risk");
        // Update weather mock data in UI
        const sikkimWeather = window.nerData.weather.find(w => w.location === "Gangtok");
        if (sikkimWeather) {
          sikkimWeather.rainProbability = "98%";
          sikkimWeather.condition = "Severe Rain Alert";
        }
        if (window.refreshDashboardUI) window.refreshDashboardUI();
        window.showToast("Heavy Rainfall Warning active in Sikkim sectors", "warning");
      },
      delay: 3500
    },
    {
      title: "Step 3: Incident Detected (Landslide)",
      desc: "NH-10 corridor is blocked by rockfall near Rangpo. Live map updates with warning markers; corridor turns red.",
      action: () => {
        window.switchTab("map");
        if (window.nerMap) window.nerMap.setView([27.1770, 88.5303], 9);
        
        // Inject block in corridor
        const nh10 = window.nerData.corridors.find(c => c.id === "nh10");
        if (nh10) {
          nh10.status = "blocked";
          nh10.statusText = "Landslide Blockage";
          nh10.delay = "Blocked";
          nh10.riskScore = 100;
        }

        // Add to incidents
        const newIncident = {
          id: "demo-landslide",
          type: "Landslide",
          location: "NH-10 Rangpo Segment",
          state: "Sikkim",
          severity: "Critical",
          detected: "Just now",
          affectedRoutes: "NH-10",
          status: "Active",
          description: "Monsoonal rockfall has blocked both lanes. Transport operations suspended."
        };
        window.nerData.incidents.unshift(newIncident);

        // Prepend critical alert
        window.nerData.alerts.unshift({
          id: "demo-alert-ls",
          severity: "critical",
          text: "NH-10 blocked by rockfall. State accessibility score dropped.",
          timestamp: "Just now",
          acknowledged: false
        });

        if (window.renderMapAssets) window.renderMapAssets();
        if (window.refreshDashboardUI) window.refreshDashboardUI();
        window.showToast("CRITICAL: NH-10 Corridor blocked!", "critical");
      },
      delay: 7500
    },
    {
      title: "Step 4: AI Predicts Network Cascades",
      desc: "Predictive engine increases local landslide risk projection to 95%. Accessibility index drops to 38%.",
      action: () => {
        window.switchTab("risk");
        // Drop Sikkim accessibility
        const sikkim = window.nerData.states.find(s => s.id === "sikkim");
        if (sikkim) {
          sikkim.score = 38;
          sikkim.disruptions += 1;
        }
        
        // Increase landslide prediction
        const landslidePred = window.nerData.predictions.find(p => p.category === "Landslide Risk");
        if (landslidePred) {
          landslidePred.current = "95%";
          landslidePred.predicted = "99%";
        }

        if (window.refreshDashboardUI) window.refreshDashboardUI();
      },
      delay: 11500
    },
    {
      title: "Step 5: Shipment Impact Assessment",
      desc: "Scanning active freight database. AI flags shipment NER-10319 (carrying electronics) trapped in the blockade.",
      action: () => {
        window.switchTab("shipments");
        const shipment = window.nerData.shipments.find(s => s.id === "NER-10319");
        if (shipment) {
          shipment.status = "Delayed";
          shipment.risk = "High";
          shipment.timeline.unshift({ time: "Demo Time", act: "⚠️ Alert: Vehicle halted due to NH-10 Landslide block." });
        }
        if (window.refreshDashboardUI) window.refreshDashboardUI();
        
        // Find and highlight row
        setTimeout(() => {
          const row = document.getElementById("shipment-row-NER-10319");
          if (row) {
            row.classList.add("bg-red-950/40", "border-red-500/50");
          }
        }, 300);
      },
      delay: 15500
    },
    {
      title: "Step 6: AI Reroute Optimization",
      desc: "NER-LINK AI runs alternate routing algorithms. Simulating network backup lanes via NH-27 plains gateway.",
      action: () => {
        window.switchTab("routes");
        
        // Auto-populate form
        document.getElementById("route-origin").value = "Siliguri Gateway";
        document.getElementById("route-destination").value = "Gangtok Transit";
        document.getElementById("route-cargo").value = "Electronics";
        document.getElementById("route-weight").value = "12";
        document.getElementById("route-priority").value = "Normal";

        // Click generate
        const genBtn = document.getElementById("generate-routes-btn");
        if (genBtn) genBtn.click();
      },
      delay: 19500
    },
    {
      title: "Step 7: Executing AI Dispatch Reroutes",
      desc: "AI reroutes shipment NER-10319 to a safer alternate corridor. New route and updated timeline are committed.",
      action: () => {
        const shipment = window.nerData.shipments.find(s => s.id === "NER-10319");
        if (shipment) {
          shipment.status = "Rerouted";
          shipment.risk = "Low";
          shipment.routeId = "nh27"; // Switch to NH-27
          shipment.timeline.unshift({ time: "Demo Time", act: "🤖 AI Automated Reroute: Dispatched via NH-27 corridor." });
        }
        
        window.switchTab("shipments");
        if (window.refreshDashboardUI) window.refreshDashboardUI();
        window.showToast("AI Auto-Rerouted 11 units around NH-10", "success");
      },
      delay: 24500
    },
    {
      title: "Step 8: AI Copilot Dashboard Briefing",
      desc: "Opening AI Copilot. Operations assistant provides natural language explanation of the grid rerouting decisions.",
      action: () => {
        // Toggle Copilot Panel
        const copPanel = document.getElementById("copilot-panel");
        if (copPanel && copPanel.classList.contains("translate-x-full")) {
          const copTrigger = document.getElementById("copilot-trigger-btn");
          if (copTrigger) copTrigger.click();
        }
        
        // Ask question
        setTimeout(() => {
          if (window.askAICopilot) {
            window.askAICopilot("Why is NH-10 high risk?");
          }
        }, 500);
      },
      delay: 28500
    },
    {
      title: "Step 9: Evaluating System Impact",
      desc: "Reviewing decision metrics. AI rerouting achieved a 42% expected delay reduction across 14 affected shipments.",
      action: () => {
        window.switchTab("impact");
        // Show impact result statistics
        const resultPanel = document.getElementById("simulation-results");
        if (resultPanel) {
          resultPanel.innerHTML = `
            <div class="mt-4 p-4 rounded-lg bg-red-950/40 border border-red-500/30 text-slate-200">
              <div class="flex items-center gap-2 text-red-400 font-bold mb-2">
                <span>⚡</span>
                <span>DEMO STATUS: MONSOON LANDSLIDE ACTIVE</span>
              </div>
              <p class="text-xs text-slate-300 mb-2">
                14 shipments affected | Sikkim Accessibility score: 38% | NH-10 Corridor status: Blocked.
              </p>
              <div class="p-2.5 bg-emerald-950/40 border border-emerald-500/30 rounded text-xs">
                <span class="text-emerald-400 font-bold block mb-1">🤖 AI Grid Mitigation Results</span>
                Average Delay Saved: <b>+1h 55m</b> per shipment. Delay reduction: <b>42%</b>.
              </div>
              <button onclick="window.stopDemoScenario()" class="mt-3 w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-1 px-2 rounded text-xs">
                Exit Demonstration Mode
              </button>
            </div>
          `;
          resultPanel.classList.remove("hidden");
        }
      },
      delay: 33500
    },
    {
      title: "Demonstration Complete!",
      desc: "The logistics network is operating dynamically. Click × to dismiss or reset the grid.",
      action: () => {
        window.demoRunning = false;
        document.querySelectorAll(".run-demo-btn").forEach(function(btn) { btn.disabled = false; btn.classList.remove("opacity-50"); });
        statusCard.innerHTML = `
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <span class="text-emerald-400 text-lg">✓</span>
              <h4 class="font-bold text-white text-sm">Demonstration Complete</h4>
            </div>
            <button onclick="document.getElementById('demo-status-card').classList.add('hidden')" class="text-slate-400 hover:text-white font-bold text-base leading-none">&times;</button>
          </div>
          <p class="text-xs text-slate-400 mb-4">
            The scenario showed how weather sensing, risk warnings, and incident simulations trigger instant, explainable AI reroutes.
          </p>
          <button onclick="window.stopDemoScenario()" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-1.5 px-3 rounded text-xs transition">
            Reset Grid &amp; Exit Demo
          </button>
        `;
      },
      delay: 37500
    }
  ];

  // Execute sequence
  steps.forEach(step => {
    const id = setTimeout(() => {
      // Update floating card content
      statusCard.innerHTML = `
        <div class="flex items-center justify-between mb-2">
          <h4 class="font-bold text-white text-sm">${step.title}</h4>
          <span class="text-[10px] bg-blue-900/60 text-blue-300 border border-blue-700/50 rounded px-1.5 font-bold uppercase">AUTOPLAY</span>
        </div>
        <p class="text-xs text-slate-300 leading-relaxed mb-4">${step.desc}</p>
        <div class="w-full bg-slate-800 rounded-full h-1.5 mb-2 overflow-hidden">
          <div class="bg-blue-500 h-full rounded-full transition-all duration-300" style="width: ${((steps.indexOf(step) + 1) / steps.length) * 100}%"></div>
        </div>
        <div class="flex justify-between items-center text-[10px] text-slate-400">
          <span>Step ${steps.indexOf(step) + 1} of ${steps.length}</span>
          <button onclick="window.stopDemoScenario()" class="text-red-400 hover:text-red-300 font-bold">Skip Demo</button>
        </div>
      `;
      step.action();
    }, step.delay);
    window.demoTimeoutIds.push(id);
  });
};

window.stopDemoScenario = function() {
  // Clear any pending timeouts
  window.demoTimeoutIds.forEach(id => clearTimeout(id));
  window.demoTimeoutIds = [];

  // Reset variables
  window.demoRunning = false;

  // Hide floating card
  const statusCard = document.getElementById("demo-status-card");
  if (statusCard) statusCard.classList.add("hidden");

  // Re-enable demo trigger buttons
  const runDemoBtns = document.querySelectorAll(".run-demo-btn");
  runDemoBtns.forEach(btn => {
    btn.disabled = false;
    btn.classList.remove("opacity-50");
  });

  // Reset simulation and return to overview
  window.resetSimulation("nh10", "high_risk", "High Landslide Risk", "1h 45m", 78, "sikkim");
  window.switchTab("overview");
  if (window.resetMapZoom) window.resetMapZoom();

  // Close Copilot Panel
  const copPanel = document.getElementById("copilot-panel");
  if (copPanel && !copPanel.classList.contains("translate-x-full")) {
    const copTrigger = document.getElementById("copilot-trigger-btn");
    if (copTrigger) copTrigger.click();
  }

  // Restore weather values
  const sikkimWeather = window.nerData.weather.find(w => w.location === "Gangtok");
  if (sikkimWeather) {
    sikkimWeather.rainProbability = "95%";
    sikkimWeather.condition = "Heavy Rain";
  }

  window.showToast("Demo reset completed. Logistics grid restored.", "info");
};
