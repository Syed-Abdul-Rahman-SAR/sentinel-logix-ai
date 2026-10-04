// NER-LINK AI - Intelligent Operations Copilot chatbot

window.copilotReplies = {
  routes: {
    text: "There are 3 main routes available from <b>Guwahati to Imphal</b> today:<br><br>" +
          "1. <b>Route A (AI Recommended)</b>: Lowest combined risk (18/100), ETA 6h 42m. Bypasses NH-2 slide sectors.<br>" +
          "2. <b>Route B (Dimapur Bypass)</b>: 24 mins faster but has elevated rainfall indices.<br>" +
          "3. <b>Route C (NH-37 Jiribam)</b>: Safe flatland route, but adds 1h 15m to travel time.<br><br>" +
          "I recommend choosing Route A today due to high safety indices.",
    actions: [
      { label: "Plot Route A on Map", action: "plot_route_a" },
      { label: "Compare Scores", action: "switch_tab_routes" }
    ]
  },
  risk: {
    text: "<b>High-Risk Corridors:</b><br><br>" +
          "⚠️ <b>NH-10 (Siliguri - Gangtok)</b>: 78/100 Risk. Landslide threat elevated due to soil moisture saturation.<br>" +
          "⚠️ <b>NH-15 (Guwahati - Itanagar)</b>: 35/100 Risk. Construction delay near Banderdewa.<br><br>" +
          "All other major transit channels are operating within safe baseline parameters.",
    actions: [
      { label: "Focus NH-10 on Map", action: "zoom_nh10" },
      { label: "View Risk Analytics", action: "switch_tab_risk" }
    ]
  },
  delays: {
    text: "<b>Shipments showing elevated delay risk:</b><br><br>" +
          "• <b>NER-10319</b> (Electronics, Siliguri &rarr; Gangtok): High risk due to NH-10 blockage.<br>" +
          "• <b>NER-10752</b> (General, Guwahati &rarr; Itanagar): Moderate risk from construction congestions.<br><br>" +
          "Recommend initiating auto-rerouting for high-priority items.",
    actions: [
      { label: "Reroute High Risk Units", action: "reroute_units" },
      { label: "Open Shipment Table", action: "switch_tab_shipments" }
    ]
  },
  nh10: {
    text: "<b>NH-10 Corridor Analysis:</b><br><br>" +
          "Risk Score: <b>78/100</b><br>" +
          "Factor Breakdown:<br>" +
          "• Soil Saturation: <b>82% (Critical)</b><br>" +
          "• Rain forecast: <b>95mm (Heavy Rain Warning)</b><br>" +
          "• Slope Stability Indicator: <b>Poor (Active Slide Zone)</b><br><br>" +
          "Recommend shifting transport loads to regional backup channels.",
    actions: [
      { label: "Locate Slide Zone", action: "zoom_nh10_slide" }
    ]
  },
  emergency: {
    text: "For **emergency medical shipments** (e.g. Guwahati to Imphal):<br><br>" +
          "1. Use **Route A** (NH-2 corridor) which is currently clear (96% accessibility).<br>" +
          "2. If NH-2 experiences any active blockages, immediately divert via **NH-37 (Silchar-Jiribam)**. It adds 75 minutes but bypasses mountain slide zones.<br>" +
          "3. Request air-dispatch support if ground corridors drop below 50% accessibility.",
    actions: [
      { label: "Plot Emergency Backup", action: "plot_emergency_backup" },
      { label: "Pre-Clear NH-2 Lane", action: "pre_clear" }
    ]
  },
  default: {
    text: "I am the NER-LINK AI Operations Copilot. How can I assist you with logistics grid management today?<br><br>" +
          "You can ask me about:<br>" +
          "• <i>Guwahati to Imphal route safety</i><br>" +
          "• <i>High risk corridors</i><br>" +
          "• <i>Delayed shipments</i><br>" +
          "• <i>NH-10 status</i><br>" +
          "• <i>Emergency alternatives</i>",
    actions: []
  }
};

window.askAICopilot = function(query) {
  const chatMessages = document.getElementById("copilot-messages");
  if (!chatMessages) return;

  // Append user message
  const userMsgDiv = document.createElement("div");
  userMsgDiv.className = "flex justify-end mb-3 chat-message";
  userMsgDiv.innerHTML = `
    <div class="max-w-[80%] bg-blue-600/80 border border-blue-500/30 text-white rounded-lg rounded-tr-none px-3.5 py-2 text-xs">
      ${query}
    </div>
  `;
  chatMessages.appendChild(userMsgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  // Append thinking indicator
  const thinkingDiv = document.createElement("div");
  thinkingDiv.className = "flex justify-start mb-3 chat-message";
  thinkingDiv.innerHTML = `
    <div class="max-w-[80%] bg-slate-800/80 border border-slate-700/50 rounded-lg rounded-tl-none px-3.5 py-2 text-xs flex items-center gap-1.5">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>
  `;
  chatMessages.appendChild(thinkingDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  // Match reply
  let replyKey = "default";
  let dynamicReply = null;
  const q = query.toLowerCase();
  
  if (q.includes("predict") || q.includes("reroute") || q.includes("realtime") || q.includes("real-time")) {
    const isAuto = window.realtimeConfig ? window.realtimeConfig.autoReroute : true;
    const isRunning = window.realtimeConfig ? window.realtimeConfig.running : true;
    const evts = (window.nerData && window.nerData.predictiveEvents) ? window.nerData.predictiveEvents : [];
    
    let evtsSummary = evts.slice(0, 3).map(e => `• <b>${e.shipmentId}</b>: ${e.action} (Saved: <b>+${e.timeSaved}</b>, Risk: <b>${e.riskReduced}</b>)`).join("<br>");
    if (!evtsSummary) evtsSummary = "<i>No emergency reroutes triggered yet. All primary corridors operating normally.</i>";

    dynamicReply = {
      text: `<b>Real-Time Predictive Rerouting Status:</b><br><br>` +
            `• Engine State: <b class="text-emerald-400">${isRunning ? 'Active Telemetry (Looping)' : 'Paused'}</b><br>` +
            `• Autonomy Mode: <b class="text-blue-400">${isAuto ? 'Autonomous AI Dispatch' : 'Operator Supervised'}</b><br><br>` +
            `<b>Recent Predictive Decisions:</b><br>${evtsSummary}<br><br>` +
            `The engine continuously models rain saturation, slope stability, and checkpost queues, projecting disruption risk 30-90 minutes into the future to divert cargo before blockages occur.`,
      actions: [
        { label: "Open Predictive Console", action: "switch_tab_routes" },
        { label: "Trigger Test Hazard", action: "trigger_hazard_test" },
        { label: "Inspect Live Fleet", action: "switch_tab_shipments" }
      ]
    };
  } else if (q.includes("guwahati") && q.includes("imphal")) replyKey = "routes";
  else if (q.includes("risk") || q.includes("corridor")) replyKey = "risk";
  else if (q.includes("delay") || q.includes("delayed")) replyKey = "delays";
  else if (q.includes("nh-10") || q.includes("nh10")) replyKey = "nh10";
  else if (q.includes("emergency") || q.includes("medical")) replyKey = "emergency";

  const replyData = dynamicReply || window.copilotReplies[replyKey];

  setTimeout(() => {
    // Remove thinking indicator
    chatMessages.removeChild(thinkingDiv);

    // Append AI response
    const aiMsgDiv = document.createElement("div");
    aiMsgDiv.className = "flex justify-start mb-3 chat-message";
    
    let actionsHtml = "";
    if (replyData.actions && replyData.actions.length > 0) {
      actionsHtml = `
        <div class="mt-2 flex flex-wrap gap-1.5 pt-1.5 border-t border-slate-700/50">
          ${replyData.actions.map(act => `
            <button onclick="window.handleCopilotAction('${act.action}')" class="bg-slate-800 hover:bg-slate-700 border border-slate-600 text-blue-400 hover:text-white rounded py-1 px-2 text-[10px] font-semibold transition">
              ${act.label}
            </button>
          `).join("")}
        </div>
      `;
    }

    aiMsgDiv.innerHTML = `
      <div class="max-w-[85%] bg-slate-800/80 border border-slate-700/50 text-slate-200 rounded-lg rounded-tl-none px-3.5 py-2 text-xs">
        <div class="flex items-center gap-1.5 text-blue-400 font-bold mb-1">
          <span>🤖</span>
          <span>NER-LINK Copilot</span>
        </div>
        <div>${replyData.text}</div>
        ${actionsHtml}
      </div>
    `;
    chatMessages.appendChild(aiMsgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }, 800);
};

window.handleCopilotAction = function(action) {
  if (window.showToast) window.showToast(`Action Triggered: ${action}`, "info");

  if (action === "plot_route_a") {
    // Coordinates for NH-2 Route A
    const path = window.nerData.corridors.find(c => c.id === "nh2_dim").path;
    if (window.highlightRouteOnMap) window.highlightRouteOnMap(path);
  } else if (action === "zoom_nh10") {
    if (window.nerMap) {
      window.nerMap.setView([27.0, 88.5], 9);
      const nh10 = window.nerData.corridors.find(c => c.id === "nh10");
      if (nh10 && window.mapLayers.corridors["nh10"]) {
        window.mapLayers.corridors["nh10"].openTooltip();
      }
    }
  } else if (action === "zoom_nh10_slide") {
    if (window.nerMap) {
      window.nerMap.setView([27.1770, 88.5303], 10);
      window.showToast("Centering on landslide warning: Rangpo Segment NH-10", "warning");
    }
  } else if (action === "plot_emergency_backup") {
    // Plot alternative NH-37 Silchar-Jiribam route
    const nh37Coords = window.nerData.corridors.find(c => c.id === "nh37").path;
    const nh6Coords = window.nerData.corridors.find(c => c.id === "nh6").path;
    // Join NH-6 and NH-37 to show Guwahati -> Silchar -> Imphal
    const combinedPath = [...nh6Coords, ...nh37Coords];
    if (window.highlightRouteOnMap) window.highlightRouteOnMap(combinedPath);
  } else if (action === "reroute_units") {
    window.showToast("Initiated automated AI reroute for delayed units.", "success");
    // Trigger simulation of rerouting for NH-10 units
    window.nerData.shipments.forEach(s => {
      if (s.routeId === "nh10") {
        s.status = "Rerouted";
        s.routeId = "nh27";
      }
    });
    if (window.refreshDashboardUI) window.refreshDashboardUI();
    if (window.renderMapAssets) window.renderMapAssets();
  } else if (action === "switch_tab_routes") {
    window.switchTab("routes");
  } else if (action === "switch_tab_risk") {
    window.switchTab("risk");
  } else if (action === "switch_tab_shipments") {
    window.switchTab("shipments");
  } else if (action === "pre_clear") {
    window.showToast("Authority signal sent: Pre-clearing emergency transit lane on NH-2.", "success");
  } else if (action === "trigger_hazard_test") {
    if (window.triggerHazardScenario) {
      window.triggerHazardScenario("nh10_landslide");
    }
  }
};
