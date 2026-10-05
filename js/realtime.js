// NER-LINK AI - Real-Time Telemetry & Predictive Rerouting Engine
// Implements continuous multi-sensor telemetry, dynamic graph routing (Dijkstra),
// real-time vehicle movement, and autonomous/operator predictive rerouting.

(function() {
  "use strict";

  // 1. GLOBAL REAL-TIME CONFIGURATION
  window.realtimeConfig = {
    running: true,
    speed: 1, // 1x, 2x, 5x
    tickIntervalMs: 2000,
    autoReroute: true, // true: autonomous AI execution, false: operator approval
    soundEnabled: true,
    simTime: new Date(2026, 7, 26, 14, 25, 0), // Base IST time
    activeTimerId: null,
    pendingProposal: null,
    proposalCountdown: 15,
    proposalTimerId: null
  };

  // 2. AUDIO SYNTHESIS ENGINE (Web Audio API - Zero External Dependencies)
  window.playAlertSound = function(type) {
    if (!window.realtimeConfig.soundEnabled) return;
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();

      if (type === "reroute") {
        // Futuristic dual-tone notification: E5 (659Hz) -> A5 (880Hz)
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.connect(gain);
        gain.connect(ctx.destination);
        
        osc.frequency.setValueAtTime(659.25, ctx.currentTime);
        osc.frequency.setValueAtTime(880.00, ctx.currentTime + 0.12);
        gain.gain.setValueAtTime(0.18, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.45);
        
        osc.start(ctx.currentTime);
        osc.stop(ctx.currentTime + 0.45);
      } else if (type === "hazard") {
        // Warning alert: 440Hz -> 311Hz
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "triangle";
        osc.connect(gain);
        gain.connect(ctx.destination);
        
        osc.frequency.setValueAtTime(440, ctx.currentTime);
        osc.frequency.setValueAtTime(311.13, ctx.currentTime + 0.15);
        gain.gain.setValueAtTime(0.22, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.55);
        
        osc.start(ctx.currentTime);
        osc.stop(ctx.currentTime + 0.55);
      }
    } catch (e) {
      // Audio context blocked until first user interaction
    }
  };

  // 3. TOPOLOGICAL GRAPH DATA MODEL (NER Hubs & Connectors)
  const NER_GRAPH = {
    nodes: {
      "slg": { id: "slg", name: "Siliguri Gateway", state: "West Bengal", lat: 26.7271, lng: 88.3953 },
      "gtkey": { id: "gtkey", name: "Gangtok Transit", state: "Sikkim", lat: 27.3314, lng: 88.6138 },
      "klp": { id: "klp", name: "Kalimpong Alternate Pass", state: "West Bengal", lat: 27.0667, lng: 88.4667 },
      "ghy": { id: "ghy", name: "Guwahati Hub", state: "Assam", lat: 26.1445, lng: 91.7363 },
      "tez": { id: "tez", name: "Tezpur Junction", state: "Assam", lat: 26.6528, lng: 92.7926 },
      "itn": { id: "itn", name: "Itanagar Hub", state: "Arunachal Pradesh", lat: 27.0844, lng: 93.6053 },
      "shl": { id: "shl", name: "Shillong Transit", state: "Meghalaya", lat: 25.5788, lng: 91.8931 },
      "slc": { id: "slc", name: "Silchar Hub", state: "Assam", lat: 24.8333, lng: 92.7789 },
      "dmp": { id: "dmp", name: "Dimapur Junction", state: "Nagaland", lat: 25.9064, lng: 93.7273 },
      "khm": { id: "khm", name: "Kohima Terminal", state: "Nagaland", lat: 25.6751, lng: 94.1086 },
      "jrb": { id: "jrb", name: "Jiribam Gateway", state: "Manipur", lat: 24.8015, lng: 93.1118 },
      "imp": { id: "imp", name: "Imphal Depot", state: "Manipur", lat: 24.8170, lng: 93.9368 },
      "azl": { id: "azl", name: "Aizawl Station", state: "Mizoram", lat: 23.7271, lng: 92.7176 },
      "agt": { id: "agt", name: "Agartala Depot", state: "Tripura", lat: 23.8315, lng: 91.2868 }
    },

    edges: [
      {
        id: "nh10",
        name: "NH-10 Sevoke-Rangpo (Siliguri - Gangtok)",
        u: "slg", v: "gtkey",
        distanceKm: 114,
        baseMins: 210,
        riskScore: 78,
        status: "high_risk", // normal, minor, high_risk, blocked
        path: [
          [26.7271, 88.3953],
          [26.8967, 88.4682],
          [27.1770, 88.5303],
          [27.2348, 88.4986],
          [27.3314, 88.6138]
        ]
      },
      {
        id: "nh10_alt",
        name: "NH-717A Kalimpong Bypass (Siliguri - Kalimpong - Gangtok)",
        u: "slg", v: "gtkey",
        via: "klp",
        distanceKm: 142,
        baseMins: 260,
        riskScore: 24,
        status: "normal",
        path: [
          [26.7271, 88.3953],
          [26.9012, 88.5211],
          [27.0667, 88.4667],
          [27.1950, 88.6120],
          [27.3314, 88.6138]
        ]
      },
      {
        id: "nh27",
        name: "NH-27 East-West Arterial (Siliguri - Guwahati)",
        u: "slg", v: "ghy",
        distanceKm: 485,
        baseMins: 520,
        riskScore: 12,
        status: "normal",
        path: [
          [26.7271, 88.3953],
          [26.5222, 88.7247],
          [26.4919, 89.5273],
          [26.4950, 90.5583],
          [26.5050, 90.9632],
          [26.1445, 91.7363]
        ]
      },
      {
        id: "nh15",
        name: "NH-15 Northern Access (Guwahati - Tezpur - Itanagar)",
        u: "ghy", v: "itn",
        via: "tez",
        distanceKm: 330,
        baseMins: 380,
        riskScore: 35,
        status: "minor",
        path: [
          [26.1445, 91.7363],
          [26.6528, 92.7926],
          [27.1009, 93.8118],
          [27.0844, 93.6053]
        ]
      },
      {
        id: "nh6",
        name: "NH-6 Highland Corridor (Guwahati - Shillong - Silchar)",
        u: "ghy", v: "slc",
        via: "shl",
        distanceKm: 310,
        baseMins: 460,
        riskScore: 28,
        status: "normal",
        path: [
          [26.1445, 91.7363],
          [26.1154, 91.8675],
          [25.9011, 91.8817],
          [25.6481, 91.8906],
          [25.5788, 91.8931],
          [25.4522, 92.2045],
          [25.3524, 92.3687],
          [24.8961, 92.5954],
          [24.8333, 92.7789]
        ]
      },
      {
        id: "nh2_dim",
        name: "NH-2 Mountain Trunk (Guwahati - Dimapur - Kohima - Imphal)",
        u: "ghy", v: "imp",
        via: "khm",
        distanceKm: 480,
        baseMins: 550,
        riskScore: 22,
        status: "normal",
        path: [
          [26.1445, 91.7363],
          [26.3477, 92.6841],
          [25.9064, 93.7273],
          [25.6751, 94.1086],
          [25.2652, 94.0152],
          [24.8170, 93.9368]
        ]
      },
      {
        id: "nh37",
        name: "NH-37 Valley Alternate (Silchar - Jiribam - Imphal)",
        u: "slc", v: "imp",
        via: "jrb",
        distanceKm: 215,
        baseMins: 320,
        riskScore: 46,
        status: "minor",
        path: [
          [24.8333, 92.7789],
          [24.8015, 93.1118],
          [24.8193, 93.5936],
          [24.8170, 93.9368]
        ]
      },
      {
        id: "nh306",
        name: "NH-306 South Ridge (Silchar - Aizawl)",
        u: "slc", v: "azl",
        distanceKm: 175,
        baseMins: 310,
        riskScore: 31,
        status: "normal",
        path: [
          [24.8333, 92.7789],
          [24.2185, 92.6781],
          [23.7271, 92.7176]
        ]
      },
      {
        id: "nh8",
        name: "NH-8 Tripura Arterial (Silchar - Agartala)",
        u: "slc", v: "agt",
        distanceKm: 285,
        baseMins: 420,
        riskScore: 19,
        status: "normal",
        path: [
          [24.8333, 92.7789],
          [24.3648, 92.1643],
          [23.9161, 91.8496],
          [23.8315, 91.2868]
        ]
      }
    ]
  };

  window.nerGraph = NER_GRAPH;

  // 4. DYNAMIC GRAPH PATHFINDING (Dijkstra with Multi-Factor Cost Function)
  // Cost = Distance * (1 + riskPenalty + statusPenalty + weatherPenalty)
  window.calculateDynamicRoute = function(fromNodeId, toNodeId, options) {
    options = options || {};
    const avoidCorridorIds = options.avoidCorridorIds || [];
    const avoidNodeIds = options.avoidNodeIds || [];
    const priority = options.priority || "Normal"; // Emergency, High, Normal

    // Build adjacency list
    const adj = {};
    Object.keys(NER_GRAPH.nodes).forEach(function(n) { adj[n] = []; });

    NER_GRAPH.edges.forEach(function(edge) {
      if (avoidCorridorIds.includes(edge.id)) return;

      // Calculate dynamic edge weight
      let weight = edge.distanceKm;
      let riskFactor = edge.riskScore / 100;
      
      if (edge.status === "blocked") {
        weight = 999999; // Near infinite
      } else if (edge.status === "high_risk") {
        weight *= (1 + riskFactor * 2.8);
      } else if (edge.status === "minor") {
        weight *= (1 + riskFactor * 1.2);
      } else {
        weight *= (1 + riskFactor * 0.4);
      }

      // Priority adjustments
      if (priority === "Emergency" && edge.riskScore > 50) {
        weight *= 2.0; // Emergency avoids risky routes more aggressively
      }

      adj[edge.u].push({ to: edge.v, edge: edge, weight: weight });
      adj[edge.v].push({ to: edge.u, edge: edge, weight: weight });
    });

    // Dijkstra algorithm
    const dist = {};
    const prev = {};
    const unvisited = new Set(Object.keys(NER_GRAPH.nodes));

    Object.keys(NER_GRAPH.nodes).forEach(function(n) {
      dist[n] = Infinity;
      prev[n] = null;
    });

    dist[fromNodeId] = 0;

    while (unvisited.size > 0) {
      let curr = null;
      let minDist = Infinity;
      for (let n of unvisited) {
        if (dist[n] < minDist) {
          minDist = dist[n];
          curr = n;
        }
      }

      if (curr === null || minDist === Infinity) break;
      if (curr === toNodeId) break;

      unvisited.delete(curr);

      if (avoidNodeIds.includes(curr) && curr !== fromNodeId && curr !== toNodeId) {
        continue;
      }

      for (let neighbor of (adj[curr] || [])) {
        if (!unvisited.has(neighbor.to)) continue;
        const alt = dist[curr] + neighbor.weight;
        if (alt < dist[neighbor.to]) {
          dist[neighbor.to] = alt;
          prev[neighbor.to] = { node: curr, edge: neighbor.edge };
        }
      }
    }

    // Reconstruct path
    if (dist[toNodeId] === Infinity) {
      return null; // No path found
    }

    const pathEdges = [];
    let curr = toNodeId;
    while (prev[curr]) {
      pathEdges.unshift(prev[curr].edge);
      curr = prev[curr].node;
    }

    // Stitch coordinate polylines
    let combinedCoords = [];
    let totalKm = 0;
    let totalMins = 0;
    let sumRisk = 0;

    pathEdges.forEach(function(e, idx) {
      totalKm += e.distanceKm;
      let delayPenalty = e.status === "blocked" ? 240 : e.status === "high_risk" ? 90 : e.status === "minor" ? 25 : 0;
      totalMins += (e.baseMins + delayPenalty);
      sumRisk += e.riskScore;

      if (idx === 0) {
        combinedCoords = [].concat(e.path);
      } else {
        combinedCoords = combinedCoords.concat(e.path.slice(1));
      }
    });

    const avgRisk = pathEdges.length > 0 ? Math.round(sumRisk / pathEdges.length) : 20;
    const accessibilityScore = Math.max(20, Math.min(98, Math.round(100 - (avgRisk * 0.7))));

    const hours = Math.floor(totalMins / 60);
    const mins = totalMins % 60;

    return {
      success: true,
      edges: pathEdges,
      corridorIds: pathEdges.map(function(e) { return e.id; }),
      coordinates: combinedCoords,
      distanceKm: totalKm,
      durationMins: totalMins,
      etaString: hours + "h " + (mins < 10 ? "0" + mins : mins) + "m",
      avgRiskScore: avgRisk,
      accessibilityScore: accessibilityScore,
      primaryCorridor: pathEdges[0] ? pathEdges[0].name : "NER Transit Highway"
    };
  };

  // Helper to map city string to graph node ID
  window.cityToNodeId = function(cityName) {
    if (!cityName) return "ghy";
    const c = cityName.toLowerCase();
    if (c.includes("siliguri")) return "slg";
    if (c.includes("gangtok") || c.includes("sikkim")) return "gtkey";
    if (c.includes("guwahati") || c.includes("assam")) return "ghy";
    if (c.includes("imphal") || c.includes("manipur")) return "imp";
    if (c.includes("shillong") || c.includes("meghalaya")) return "shl";
    if (c.includes("aizawl") || c.includes("mizoram")) return "azl";
    if (c.includes("kohima") || c.includes("dimapur") || c.includes("nagaland")) return "khm";
    if (c.includes("agartala") || c.includes("tripura")) return "agt";
    if (c.includes("itanagar") || c.includes("arunachal")) return "itn";
    if (c.includes("silchar")) return "slc";
    return "ghy";
  };

  // 5. VEHICLE TELEMETRY & SMOOTH INTERPOLATION
  window.initFleetTelemetry = function() {
    if (!window.nerData || !window.nerData.shipments) return;

    window.nerData.shipments.forEach(function(ship, idx) {
      const corr = window.nerData.corridors.find(function(c) { return c.id === ship.routeId; }) || window.nerData.corridors[0];
      
      if (!ship.telemetry) {
        const initialProgress = ((idx * 23 + 17) % 75 + 10) / 100;
        ship.telemetry = {
          progress: initialProgress,
          speedKmh: Math.floor(Math.random() * 15) + 48,
          heading: 65,
          activePath: [].concat(corr.path),
          totalDistanceKm: 340,
          remainingKm: Math.round(340 * (1 - initialProgress)),
          originalRouteId: ship.routeId,
          reroutedCount: 0,
          vehicleNumber: "AS-01-" + String.fromCharCode(65 + idx) + String.fromCharCode(66 + idx) + "-" + (1000 + idx * 43),
          fuelLevel: (88 - idx * 7) + "%",
          temperature: "22°C (Dry Box)",
          lastPing: "Just now"
        };
      }

      const pos = getPointAlongPath(ship.telemetry.activePath, ship.telemetry.progress);
      ship.currentPos = pos;
    });

    if (!window.nerData.predictiveEvents) {
      window.nerData.predictiveEvents = [
        {
          id: "pred-init-1",
          time: "14:10 IST",
          shipmentId: "NER-10604",
          hazard: "Predicted waterlogging near Badarpur Pass (NH-6)",
          action: "Pre-emptively routed via Southern Arterial (NH-8)",
          timeSaved: "45 mins",
          riskReduced: "68% → 19%",
          status: "Executed Autonomous"
        }
      ];
    }
  };

  function getPointAlongPath(coords, fraction) {
    if (!coords || coords.length === 0) return [26.1445, 91.7363];
    if (coords.length === 1 || fraction <= 0) return coords[0];
    if (fraction >= 1) return coords[coords.length - 1];

    const segLengths = [];
    let totalLength = 0;
    for (let i = 0; i < coords.length - 1; i++) {
      const p1 = coords[i];
      const p2 = coords[i + 1];
      const d = Math.hypot(p2[0] - p1[0], p2[1] - p1[1]);
      segLengths.push(d);
      totalLength += d;
    }

    const targetDist = totalLength * fraction;
    let accumulated = 0;

    for (let i = 0; i < segLengths.length; i++) {
      if (accumulated + segLengths[i] >= targetDist) {
        const segFrac = (targetDist - accumulated) / (segLengths[i] || 0.00001);
        const p1 = coords[i];
        const p2 = coords[i + 1];
        return [
          p1[0] + (p2[0] - p1[0]) * segFrac,
          p1[1] + (p2[1] - p1[1]) * segFrac
        ];
      }
      accumulated += segLengths[i];
    }
    return coords[coords.length - 1];
  }

  // 6. REAL-TIME TELEMETRY LOOP TICK
  window.realtimeTick = function() {
    if (!window.realtimeConfig.running) return;

    const simTime = window.realtimeConfig.simTime;
    simTime.setSeconds(simTime.getSeconds() + (30 * window.realtimeConfig.speed));
    
    const timeStr = simTime.toLocaleTimeString("en-IN", { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }) + " IST";
    const clockEl = document.getElementById("realtime-clock");
    if (clockEl) clockEl.innerText = timeStr;

    if (window.nerData && window.nerData.shipments) {
      window.nerData.shipments.forEach(function(ship) {
        if (!ship.telemetry) return;

        const step = (0.0035 * window.realtimeConfig.speed);
        ship.telemetry.progress += step;

        if (ship.telemetry.progress >= 1.0) {
          ship.telemetry.progress = 0.02;
          ship.timeline.unshift({
            time: timeStr.slice(0, 5),
            act: "Delivered to destination node. Reloaded and dispatched on return schedule."
          });
        }

        ship.currentPos = getPointAlongPath(ship.telemetry.activePath, ship.telemetry.progress);
        ship.telemetry.lastPing = "1s ago";
        ship.telemetry.speedKmh = Math.max(35, Math.min(75, ship.telemetry.speedKmh + (Math.random() > 0.5 ? 1 : -1)));
      });
    }

    fluctuateSensors();
    scanAndPredictReroutes();

    if (window.updateMapFleetPositions) {
      window.updateMapFleetPositions();
    }

    if (window.currentTab === "shipments") {
      updateShipmentProgressUI();
    }
  };

  function fluctuateSensors() {
    if (!window.nerData || !window.nerData.weather) return;
    if (Math.random() < 0.2) {
      const w = window.nerData.weather[Math.floor(Math.random() * window.nerData.weather.length)];
      if (w) {
        let prob = parseInt(w.rainProbability);
        prob = Math.max(10, Math.min(99, prob + (Math.random() > 0.5 ? 2 : -2)));
        w.rainProbability = prob + "%";
      }
    }
  }

  // 7. PREDICTIVE REROUTING ENGINE
  function scanAndPredictReroutes() {
    if (!window.nerData || !window.nerData.shipments) return;

    window.nerData.shipments.forEach(function(shipment) {
      if (shipment.status === "Rerouted" && shipment.telemetry && shipment.telemetry.reroutedCount > 0) return;

      const activeCorrId = shipment.routeId;
      const corridorObj = window.nerData.corridors.find(function(c) { return c.id === activeCorrId; });
      if (!corridorObj) return;

      const hasSevereRisk = corridorObj.riskScore >= 75 || corridorObj.status === "blocked";
      const hasActiveIncident = window.nerData.incidents.some(function(inc) {
        return inc.status === "Active" && 
          (inc.location.includes(corridorObj.name.split(" ")[0]) || inc.affectedRoutes.includes(corridorObj.name.split(" ")[0]));
      });

      if (hasSevereRisk || hasActiveIncident) {
        const now = Date.now();
        if (now - (window.realtimeConfig.lastPredictedRerouteTime || 0) < 6000) return;

        triggerPredictiveRerouteForShipment(shipment, corridorObj, hasSevereRisk ? "High Landslide / Flooding Risk" : "Active Incident Ahead");
        window.realtimeConfig.lastPredictedRerouteTime = now;
      }
    });
  }

  function triggerPredictiveRerouteForShipment(shipment, blockedCorridor, reason) {
    const originNode = window.cityToNodeId(shipment.origin);
    const destNode = window.cityToNodeId(shipment.destination);

    const altRoute = window.calculateDynamicRoute(originNode, destNode, {
      avoidCorridorIds: [blockedCorridor.id],
      priority: shipment.priority
    });

    if (!altRoute || !altRoute.success) {
      return;
    }

    const originalDelayMins = blockedCorridor.status === "blocked" ? 240 : 135;
    const timeSavedMins = Math.max(35, Math.round(originalDelayMins * 0.65));
    const savedHours = Math.floor(timeSavedMins / 60);
    const savedRemainingMins = timeSavedMins % 60;
    const timeSavedStr = savedHours > 0 ? savedHours + "h " + savedRemainingMins + "m" : savedRemainingMins + "m";

    const oldRisk = blockedCorridor.riskScore;
    const newRisk = altRoute.avgRiskScore;

    const proposal = {
      shipmentId: shipment.id,
      cargo: shipment.cargo,
      origin: shipment.origin,
      destination: shipment.destination,
      hazardLocation: blockedCorridor.name,
      hazardReason: reason,
      avoidedCorridorId: blockedCorridor.id,
      newCorridorIds: altRoute.corridorIds,
      newPath: altRoute.coordinates,
      newEta: altRoute.etaString,
      timeSaved: timeSavedStr,
      riskBefore: oldRisk,
      riskAfter: newRisk,
      primaryAlternate: altRoute.primaryCorridor,
      summary: "Proactive reroute around " + blockedCorridor.name.split(" ")[0] + " avoids " + reason.toLowerCase() + ". Expected time saved: " + timeSavedStr + "."
    };

    if (window.realtimeConfig.autoReroute) {
      executePredictiveReroute(proposal);
    } else {
      window.presentRerouteApprovalModal(proposal);
    }
  }

  window.executePredictiveReroute = function(proposal) {
    const shipment = window.nerData.shipments.find(function(s) { return s.id === proposal.shipmentId; });
    if (!shipment) return;

    shipment.status = "Rerouted";
    shipment.risk = proposal.riskAfter < 35 ? "Low" : "Medium";
    shipment.eta = proposal.newEta;
    shipment.routeId = proposal.newCorridorIds[0] || shipment.routeId;

    if (shipment.telemetry) {
      shipment.telemetry.activePath = proposal.newPath;
      shipment.telemetry.reroutedCount += 1;
      shipment.telemetry.progress = Math.max(0.15, shipment.telemetry.progress * 0.7);
      shipment.currentPos = getPointAlongPath(shipment.telemetry.activePath, shipment.telemetry.progress);
    }

    const timeStr = window.realtimeConfig.simTime.toLocaleTimeString("en-IN", { hour: '2-digit', minute: '2-digit', hour12: false }) + " IST";

    shipment.timeline.unshift({
      time: timeStr,
      act: "🤖 AI PREDICTIVE REROUTE: Diverted via " + proposal.primaryAlternate + ". Avoided " + proposal.hazardReason + ". ETA: " + proposal.newEta + " (" + proposal.timeSaved + " saved)."
    });

    const newEvent = {
      id: "pred-evt-" + Date.now(),
      time: timeStr,
      shipmentId: proposal.shipmentId,
      hazard: proposal.hazardReason + " on " + proposal.hazardLocation.split(" ")[0],
      action: "Diverted via " + proposal.primaryAlternate,
      timeSaved: proposal.timeSaved,
      riskReduced: proposal.riskBefore + "% → " + proposal.riskAfter + "%",
      status: window.realtimeConfig.autoReroute ? "Autonomous Executed" : "Operator Approved"
    };
    window.nerData.predictiveEvents.unshift(newEvent);

    window.nerData.alerts.unshift({
      id: "alert-pred-" + Date.now(),
      severity: "high",
      text: "PREDICTIVE REROUTE: Shipment " + proposal.shipmentId + " automatically rerouted via " + proposal.primaryAlternate + ". Saved " + proposal.timeSaved + ".",
      timestamp: "Just now",
      acknowledged: false
    });

    window.playAlertSound("reroute");

    if (window.showToast) {
      window.showToast("🤖 Predictive Reroute: " + proposal.shipmentId + " diverted (+" + proposal.timeSaved + " saved)", "success");
    }

    if (window.drawPredictiveDetourOnMap) {
      window.drawPredictiveDetourOnMap(proposal);
    }

    if (window.refreshDashboardUI) window.refreshDashboardUI();
    if (window.renderPredictiveConsoleFeed) window.renderPredictiveConsoleFeed();

    const optKPI = document.getElementById("kpi-ai-optimized");
    if (optKPI) {
      let cur = parseInt(optKPI.innerText.replace(/,/g, "")) || 436;
      optKPI.innerText = (cur + 1).toLocaleString();
    }
  };

  // 8. OPERATOR APPROVAL MODAL
  window.presentRerouteApprovalModal = function(proposal) {
    window.realtimeConfig.pendingProposal = proposal;
    window.realtimeConfig.proposalCountdown = 15;

    window.playAlertSound("hazard");

    let modal = document.getElementById("predictive-reroute-modal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "predictive-reroute-modal";
      modal.className = "fixed inset-0 z-[10000] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4";
      document.body.appendChild(modal);
    }

    modal.innerHTML = `
      <div class="bg-slate-900 border-2 border-amber-500/80 rounded-2xl p-6 max-w-lg w-full text-slate-100 shadow-2xl relative animate-scale-up">
        <div class="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
          <div class="flex items-center gap-2 text-amber-400 font-extrabold text-sm">
            <span class="text-xl animate-pulse">⚡</span>
            <span>PREDICTIVE REROUTE PROPOSAL</span>
          </div>
          <span class="text-xs bg-amber-950 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded font-mono font-bold" id="modal-countdown-timer">
            Auto-executing in 15s
          </span>
        </div>

        <p class="text-xs text-slate-300 leading-relaxed mb-4">
          NER-LINK AI telemetry detected an imminent disruption: <b class="text-white">${proposal.hazardReason}</b> along <b class="text-amber-300">${proposal.hazardLocation}</b>. 
          To prevent vehicle halt, an alternate bypass corridor has been calculated.
        </p>

        <div class="grid grid-cols-3 gap-2 text-center text-xs mb-4">
          <div class="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
            <span class="text-[10px] text-slate-400 block">Affected Unit</span>
            <b class="text-white font-mono text-sm">${proposal.shipmentId}</b>
            <span class="text-[9px] text-slate-400 block mt-0.5">${proposal.cargo}</span>
          </div>
          <div class="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
            <span class="text-[10px] text-slate-400 block">Risk Reduction</span>
            <b class="text-emerald-400 text-sm">${proposal.riskBefore}% &rarr; ${proposal.riskAfter}%</b>
            <span class="text-[9px] text-emerald-400 block mt-0.5">▼ Safety Secured</span>
          </div>
          <div class="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
            <span class="text-[10px] text-slate-400 block">Delay Avoided</span>
            <b class="text-teal-300 text-sm">+${proposal.timeSaved}</b>
            <span class="text-[9px] text-slate-400 block mt-0.5">ETA: ${proposal.newEta}</span>
          </div>
        </div>

        <div class="p-3 bg-blue-950/30 border border-blue-500/30 rounded-lg text-xs mb-4">
          <div class="text-[10px] uppercase font-bold text-blue-400 tracking-wider mb-1">Recommended Bypass Pathway:</div>
          <div class="font-semibold text-white">${proposal.primaryAlternate}</div>
          <div class="text-[11px] text-slate-400 mt-1">${proposal.origin} &rarr; ${proposal.destination}</div>
        </div>

        <div class="flex gap-3 pt-2">
          <button onclick="window.confirmOperatorApproval()" class="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold py-2.5 px-4 rounded-lg text-xs transition duration-150 shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-1.5">
            <span>✓</span>
            <span>APPROVE & DISPATCH DETOUR</span>
          </button>
          <button onclick="window.dismissOperatorApproval()" class="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 font-bold py-2.5 px-4 rounded-lg text-xs transition">
            Dismiss (Hold Route)
          </button>
        </div>
      </div>
    `;
    modal.classList.remove("hidden");

    if (window.realtimeConfig.proposalTimerId) {
      clearInterval(window.realtimeConfig.proposalTimerId);
    }

    window.realtimeConfig.proposalTimerId = setInterval(function() {
      window.realtimeConfig.proposalCountdown--;
      const timerEl = document.getElementById("modal-countdown-timer");
      if (timerEl) {
        timerEl.innerText = "Auto-executing in " + window.realtimeConfig.proposalCountdown + "s";
      }
      if (window.realtimeConfig.proposalCountdown <= 0) {
        clearInterval(window.realtimeConfig.proposalTimerId);
        window.confirmOperatorApproval();
      }
    }, 1000);
  };

  window.confirmOperatorApproval = function() {
    if (window.realtimeConfig.proposalTimerId) {
      clearInterval(window.realtimeConfig.proposalTimerId);
    }
    const modal = document.getElementById("predictive-reroute-modal");
    if (modal) modal.classList.add("hidden");

    if (window.realtimeConfig.pendingProposal) {
      window.executePredictiveReroute(window.realtimeConfig.pendingProposal);
      window.realtimeConfig.pendingProposal = null;
    }
  };

  window.dismissOperatorApproval = function() {
    if (window.realtimeConfig.proposalTimerId) {
      clearInterval(window.realtimeConfig.proposalTimerId);
    }
    const modal = document.getElementById("predictive-reroute-modal");
    if (modal) modal.classList.add("hidden");
    window.realtimeConfig.pendingProposal = null;
    if (window.showToast) window.showToast("Predictive reroute deferred by operator.", "info");
  };

  // 9. INSTANT HAZARD TEST SCENARIOS
  window.triggerHazardScenario = function(scenarioType) {
    let corridorId = "nh10";
    let type = "Landslide";
    let locationName = "NH-10 Sevoke Rockfall";
    let desc = "Geotechnical acoustic sensors detect slope movement near Rangpo. Imminent rockfall predicted within 25 minutes.";

    if (scenarioType === "nh10_landslide") {
      corridorId = "nh10";
      type = "Landslide";
      locationName = "NH-10 Teesta Valley";
      desc = "Monsoon soil saturation reached 94%. Active landslide warning issued for Rangpo-Sevoke corridor.";
    } else if (scenarioType === "nh6_flood") {
      corridorId = "nh6";
      type = "Flooding";
      locationName = "NH-6 Jowai Pass Waterlogging";
      desc = "Barak valley tributary flash flood has submerged highway culvert. Heavy trucks halted.";
    } else if (scenarioType === "nh2_rockfall") {
      corridorId = "nh2_dim";
      type = "Rockfall Blockage";
      locationName = "NH-2 Kohima Mountain Ridge";
      desc = "Massive boulders obstructing dual carriage way near Kohima. Critical medical shipments at risk.";
    } else {
      const choices = ["nh10_landslide", "nh6_flood", "nh2_rockfall"];
      return window.triggerHazardScenario(choices[Math.floor(Math.random() * choices.length)]);
    }

    const corr = window.nerData.corridors.find(function(c) { return c.id === corridorId; });
    if (corr) {
      corr.status = "blocked";
      corr.statusText = "Simulated " + type;
      corr.delay = "4h 15m";
      corr.riskScore = 98;
    }

    const incId = "hazard-inc-" + Date.now();
    window.nerData.incidents.unshift({
      id: incId,
      type: type,
      location: locationName,
      state: corridorId === "nh10" ? "Sikkim" : corridorId === "nh6" ? "Meghalaya" : "Nagaland",
      severity: "Critical",
      detected: "Just now",
      affectedRoutes: corr ? corr.name.split(" ")[0] : "National Highway",
      status: "Active",
      description: desc
    });

    window.playAlertSound("hazard");
    if (window.showToast) {
      window.showToast("🚨 TELEMETRY HAZARD: " + type + " injected on " + locationName + "!", "critical");
    }

    window.realtimeConfig.lastPredictedRerouteTime = 0;
    scanAndPredictReroutes();

    if (window.renderMapAssets) window.renderMapAssets();
    if (window.refreshDashboardUI) window.refreshDashboardUI();
  };

  // 10. ENGINE RUNTIME CONTROLS
  window.startRealtimeEngine = function() {
    if (window.realtimeConfig.activeTimerId) return;
    window.realtimeConfig.running = true;
    window.initFleetTelemetry();
    window.realtimeConfig.activeTimerId = setInterval(window.realtimeTick, window.realtimeConfig.tickIntervalMs);
    console.log("NER-LINK AI: Real-Time Telemetry & Predictive Engine started.");
  };

  window.stopRealtimeEngine = function() {
    if (window.realtimeConfig.activeTimerId) {
      clearInterval(window.realtimeConfig.activeTimerId);
      window.realtimeConfig.activeTimerId = null;
    }
    window.realtimeConfig.running = false;
  };

  window.toggleEnginePause = function() {
    window.realtimeConfig.running = !window.realtimeConfig.running;
    const btn = document.getElementById("realtime-pause-btn");
    const indicator = document.getElementById("realtime-live-indicator");
    
    if (btn) {
      btn.innerHTML = window.realtimeConfig.running ? '<span>⏸</span><span class="hidden sm:inline">Pause</span>' : '<span>▶</span><span class="hidden sm:inline">Resume</span>';
    }
    if (indicator) {
      if (window.realtimeConfig.running) {
        indicator.classList.remove("bg-yellow-500");
        indicator.classList.add("bg-emerald-500");
      } else {
        indicator.classList.remove("bg-emerald-500");
        indicator.classList.add("bg-yellow-500");
      }
    }

    if (window.showToast) {
      window.showToast(window.realtimeConfig.running ? "Real-time engine resumed." : "Real-time engine paused.", "info");
    }
  };

  window.setEngineSpeed = function(multiplier) {
    window.realtimeConfig.speed = multiplier;
    const buttons = document.querySelectorAll(".speed-control-btn");
    buttons.forEach(function(b) {
      if (parseInt(b.getAttribute("data-speed")) === multiplier) {
        b.classList.add("bg-blue-600", "text-white");
        b.classList.remove("bg-slate-800", "text-slate-300");
      } else {
        b.classList.remove("bg-blue-600", "text-white");
        b.classList.add("bg-slate-800", "text-slate-300");
      }
    });

    if (window.showToast) {
      window.showToast("Simulation speed set to " + multiplier + "x", "info");
    }
  };

  window.toggleAutoReroute = function(enabled) {
    window.realtimeConfig.autoReroute = enabled;
    const label = document.getElementById("auto-reroute-toggle-label");
    if (label) {
      label.innerText = enabled ? "Auto-Reroute: ON" : "Auto-Reroute: OFF (Manual)";
    }
    if (window.showToast) {
      window.showToast(enabled ? "AI Autonomous Rerouting enabled." : "Operator Approval required for reroutes.", "info");
    }
  };

  function updateShipmentProgressUI() {
    if (!window.nerData || !window.nerData.shipments) return;
    window.nerData.shipments.forEach(function(ship) {
      if (!ship.telemetry) return;
      const pct = Math.round(ship.telemetry.progress * 100);
      const bar = document.getElementById("shipment-progress-bar-" + ship.id);
      if (bar) bar.style.width = pct + "%";
      const pctTxt = document.getElementById("shipment-progress-pct-" + ship.id);
      if (pctTxt) pctTxt.innerText = pct + "%";
    });
  }

  // 11. LIVE BACKEND WEBSOCKET & REST INTEGRATION
  window.backendSync = {
    ws: null,
    connected: false,
    retryTimer: null,
    apiBase: "http://127.0.0.1:8001",
    
    init: function() {
      this.connectWebSocket();
    },

    connectWebSocket: function() {
      const self = this;
      const wsUrl = self.apiBase.replace(/^http/, "ws") + "/ws/dashboard";
      
      try {
        if (self.ws) {
          self.ws.onclose = null;
          self.ws.close();
        }
        
        self.ws = new WebSocket(wsUrl);
        
        self.ws.onopen = function() {
          self.connected = true;
          self.updateStatusBadge("connected");
          console.log("[NER-LINK] Connected to FastAPI WebSocket Engine:", wsUrl);
          if (window.showToast) {
            window.showToast("🟢 Live Telemetry Stream Connected (FastAPI WebSocket)", "success");
          }
        };

        self.ws.onmessage = function(event) {
          try {
            const msg = JSON.parse(event.data);
            self.handleMessage(msg);
          } catch (e) {
            console.warn("WebSocket parse error:", e);
          }
        };

        self.ws.onclose = function() {
          self.connected = false;
          self.updateStatusBadge("disconnected");
          clearTimeout(self.retryTimer);
          self.retryTimer = setTimeout(function() {
            self.connectWebSocket();
          }, 4000);
        };

        self.ws.onerror = function() {
          self.connected = false;
          self.updateStatusBadge("disconnected");
        };
      } catch (err) {
        self.connected = false;
        self.updateStatusBadge("disconnected");
      }
    },

    updateStatusBadge: function(state) {
      const badge = document.getElementById("backend-status-badge");
      const dot = document.getElementById("backend-dot");
      const text = document.getElementById("backend-status-text");
      if (!badge || !dot || !text) return;

      if (state === "connected") {
        badge.className = "bg-emerald-950/80 border border-emerald-500/50 text-emerald-300 font-bold text-[10px] px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition";
        dot.className = "w-2 h-2 rounded-full bg-emerald-400 animate-pulse";
        text.innerText = "FASTAPI BACKEND: ONLINE";
      } else {
        badge.className = "bg-slate-900 border border-slate-700 text-slate-400 font-bold text-[10px] px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition";
        dot.className = "w-2 h-2 rounded-full bg-amber-500";
        text.innerText = "LOCAL ENGINE (STANDALONE)";
      }
    },

    handleMessage: function(msg) {
      const self = this;
      if (!msg || !msg.type) return;

      if (msg.type === "FLEET_SNAPSHOT") {
        if (msg.vehicles && Array.isArray(msg.vehicles)) {
          msg.vehicles.forEach(function(v) {
            self.applyVehicleTelemetry(v);
          });
        }
      } else if (msg.type === "TELEMETRY_UPDATE") {
        if (msg.data) {
          self.applyVehicleTelemetry(msg.data);
        }
      } else if (msg.type === "BATCH_SYNCED") {
        if (window.showToast) {
          window.showToast("📡 Offline Telemetry Sync: " + msg.points_synced + " pings processed for " + msg.vehicle_id, "info");
        }
        if (msg.latest_point) {
          self.applyVehicleTelemetry({
            vehicle_id: msg.vehicle_id,
            latitude: msg.latest_point.latitude,
            longitude: msg.latest_point.longitude,
            recorded_at: msg.latest_point.recorded_at,
            received_at: msg.latest_point.received_at
          });
        }
      } else if (msg.type === "VEHICLE_STALE") {
        self.markVehicleStale(msg.vehicle_id, msg.age_seconds);
      } else if (msg.type === "INCIDENT_REPORTED") {
        self.handleLiveIncident(msg.incident);
      }
    },

    applyVehicleTelemetry: function(t) {
      if (!t || !t.vehicle_id) return;
      if (!window.nerData || !window.nerData.shipments) return;

      const vidMap = {
        "V-01": "NER-10428",
        "V-02": "NER-10319",
        "V-03": "NER-10511",
        "V-04": "NER-10604",
        "V-05": "NER-10752"
      };
      const targetId = vidMap[t.vehicle_id] || t.vehicle_id;
      let ship = window.nerData.shipments.find(function(s) { return s.id === targetId || s.id === t.vehicle_id; });

      if (!ship) {
        ship = {
          id: t.vehicle_id,
          origin: "Field Origin",
          destination: "Field Destination",
          cargo: "Telemetry Test Unit",
          weight: "5.0 Tons",
          priority: "Normal",
          risk: "Low",
          eta: "In Transit",
          status: "In Transit",
          routeId: "nh6",
          currentPos: [t.latitude, t.longitude]
        };
        window.nerData.shipments.push(ship);
      }

      ship.currentPos = [t.latitude, t.longitude];
      ship.isStale = t.is_stale || (t.status === "STALE");
      
      if (!ship.telemetry) {
        ship.telemetry = {};
      }
      ship.telemetry.speedKmh = Math.round(t.speed_kmh || 0);
      ship.telemetry.heading = Math.round(t.heading || 0);
      ship.telemetry.lastPing = "Just now";
      ship.telemetry.batteryPct = t.battery_pct;
      ship.telemetry.networkStatus = t.network_status || "ONLINE";

      if (ship.isStale) {
        ship.status = "Delayed";
        ship.risk = "High";
      }

      if (window.updateMapFleetPositions) {
        window.updateMapFleetPositions();
      }
      if (window.refreshDashboardUI) {
        window.refreshDashboardUI();
      }
    },

    markVehicleStale: function(vehicle_id, age_seconds) {
      const vidMap = {
        "V-01": "NER-10428",
        "V-02": "NER-10319",
        "V-03": "NER-10511",
        "V-04": "NER-10604",
        "V-05": "NER-10752"
      };
      const targetId = vidMap[vehicle_id] || vehicle_id;
      const ship = window.nerData && window.nerData.shipments
        ? window.nerData.shipments.find(function(s) { return s.id === targetId || s.id === vehicle_id; })
        : null;

      if (ship) {
        ship.isStale = true;
        ship.status = "Delayed";
        ship.risk = "High";
        if (window.updateMapFleetPositions) window.updateMapFleetPositions();
        if (window.refreshDashboardUI) window.refreshDashboardUI();
      }

      if (window.showToast) {
        window.showToast("⚠️ DEAD-ZONE WARNING: Vehicle " + vehicle_id + " silent for " + Math.round(age_seconds) + "s!", "critical");
      }
    },

    handleLiveIncident: function(inc) {
      if (!inc || !window.nerData) return;
      window.nerData.incidents.unshift({
        id: inc.id,
        type: inc.type,
        location: inc.road_name || (inc.title + " (GPS: " + inc.latitude.toFixed(2) + ", " + inc.longitude.toFixed(2) + ")"),
        state: "North East Region",
        severity: inc.severity === "CRITICAL" ? "Critical" : "High",
        detected: "Just now (Live)",
        affectedRoutes: inc.road_name || "Regional Corridor",
        status: "Active",
        description: inc.description || inc.title
      });

      window.playAlertSound("hazard");
      if (window.showToast) {
        window.showToast("🚨 LIVE HAZARD REPORTED: " + inc.type + " - " + inc.title, "critical");
      }

      if (window.scanAndPredictReroutes) {
        window.scanAndPredictReroutes();
      }
      if (window.renderMapAssets) window.renderMapAssets();
      if (window.refreshDashboardUI) window.refreshDashboardUI();
    }
  };

  // Auto-connect when loaded
  if (typeof window !== "undefined") {
    setTimeout(function() {
      if (window.backendSync) window.backendSync.init();
    }, 1500);
  }

})();
