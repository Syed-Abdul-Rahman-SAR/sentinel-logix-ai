// NER-LINK AI - Centralized Mock Data Store
// Exposes window.nerData to modular scripting components

window.nerData = {
  states: [
    { id: "assam", name: "Assam", score: 91, shipments: 524, disruptions: 2 },
    { id: "tripura", name: "Tripura", score: 87, shipments: 112, disruptions: 0 },
    { id: "meghalaya", name: "Meghalaya", score: 79, shipments: 184, disruptions: 1 },
    { id: "sikkim", name: "Sikkim", score: 72, shipments: 94, disruptions: 3 },
    { id: "nagaland", name: "Nagaland", score: 74, shipments: 142, disruptions: 2 },
    { id: "mizoram", name: "Mizoram", score: 69, shipments: 88, disruptions: 1 },
    { id: "manipur", name: "Manipur", score: 67, shipments: 98, disruptions: 3 },
    { id: "arunachal", name: "Arunachal Pradesh", score: 61, shipments: 42, disruptions: 2 }
  ],

  hubs: [
    { id: "ghy", name: "Guwahati Hub", state: "Assam", lat: 26.1445, lng: 91.7363, inbound: 412, outbound: 384, capacity: "84%", congestion: "Medium", accessibility: "92%", risk: "Low", avgProcessing: "1.2 hours" },
    { id: "slg", name: "Siliguri Gateway", state: "West Bengal", lat: 26.7271, lng: 88.3953, inbound: 610, outbound: 590, capacity: "91%", congestion: "High", accessibility: "95%", risk: "Low", avgProcessing: "2.1 hours" },
    { id: "imp", name: "Imphal Depot", state: "Manipur", lat: 24.8170, lng: 93.9368, inbound: 84, outbound: 62, capacity: "54%", congestion: "Low", accessibility: "67%", risk: "High", avgProcessing: "1.8 hours" },
    { id: "shl", name: "Shillong Transit", state: "Meghalaya", lat: 25.5788, lng: 91.8931, inbound: 132, outbound: 120, capacity: "72%", congestion: "Medium", accessibility: "79%", risk: "Medium", avgProcessing: "1.1 hours" },
    { id: "azl", name: "Aizawl Station", state: "Mizoram", lat: 23.7271, lng: 92.7176, inbound: 45, outbound: 38, capacity: "40%", congestion: "Low", accessibility: "69%", risk: "Medium", avgProcessing: "1.6 hours" },
    { id: "khm", name: "Kohima Terminal", state: "Nagaland", lat: 25.6751, lng: 94.1086, inbound: 72, outbound: 55, capacity: "48%", congestion: "Low", accessibility: "74%", risk: "High", avgProcessing: "1.5 hours" },
    { id: "agt", name: "Agartala Depot", state: "Tripura", lat: 23.8315, lng: 91.2868, inbound: 89, outbound: 82, capacity: "65%", congestion: "Low", accessibility: "87%", risk: "Low", avgProcessing: "1.0 hours" },
    { id: "gtkey", name: "Gangtok Transit", state: "Sikkim", lat: 27.3314, lng: 88.6138, inbound: 52, outbound: 48, capacity: "38%", congestion: "Medium", accessibility: "72%", risk: "High", avgProcessing: "1.4 hours" },
    { id: "itn", name: "Itanagar Hub", state: "Arunachal Pradesh", lat: 27.0844, lng: 93.6053, inbound: 38, outbound: 31, capacity: "32%", congestion: "Low", accessibility: "61%", risk: "High", avgProcessing: "1.9 hours" }
  ],

  corridors: [
    { 
      id: "nh10", 
      name: "NH-10 Corridor (Siliguri - Gangtok)", 
      from: "Siliguri", 
      to: "Gangtok", 
      status: "high_risk", 
      statusText: "High Landslide Risk",
      delay: "1h 45m",
      riskScore: 78,
      path: [
        [26.7271, 88.3953],
        [26.8967, 88.4682],
        [27.1770, 88.5303],
        [27.2348, 88.4986],
        [27.3314, 88.6138]
      ]
    },
    { 
      id: "nh27", 
      name: "NH-27 Main Arterial (Siliguri - Guwahati)", 
      from: "Siliguri", 
      to: "Guwahati", 
      status: "normal", 
      statusText: "Clear Route",
      delay: "0m",
      riskScore: 12,
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
      id: "nh6", 
      name: "NH-6 Corridor (Guwahati - Shillong - Silchar)", 
      from: "Guwahati", 
      to: "Silchar", 
      status: "normal", 
      statusText: "Normal Flow",
      delay: "15m",
      riskScore: 28,
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
      name: "NH-2 Corridor (Guwahati - Dimapur - Kohima - Imphal)", 
      from: "Guwahati", 
      to: "Imphal", 
      status: "normal", 
      statusText: "Clear Route",
      delay: "10m",
      riskScore: 22,
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
      name: "NH-37 Alternate (Silchar - Jiribam - Imphal)", 
      from: "Silchar", 
      to: "Imphal", 
      status: "minor", 
      statusText: "Minor Waterlogging",
      delay: "45m",
      riskScore: 46,
      path: [
        [24.8333, 92.7789],
        [24.8015, 93.1118],
        [24.8193, 93.5936],
        [24.8170, 93.9368]
      ]
    },
    { 
      id: "nh306", 
      name: "NH-306 Access (Silchar - Aizawl)", 
      from: "Silchar", 
      to: "Aizawl", 
      status: "normal", 
      statusText: "Clear",
      delay: "20m",
      riskScore: 31,
      path: [
        [24.8333, 92.7789],
        [24.2185, 92.6781],
        [23.7271, 92.7176]
      ]
    },
    { 
      id: "nh8", 
      name: "NH-8 Southern Arterial (Silchar - Agartala)", 
      from: "Silchar", 
      to: "Agartala", 
      status: "normal", 
      statusText: "Clear",
      delay: "5m",
      riskScore: 19,
      path: [
        [24.8333, 92.7789],
        [24.3648, 92.1643],
        [23.9161, 91.8496],
        [23.8315, 91.2868]
      ]
    },
    { 
      id: "nh15", 
      name: "NH-15 Northern Access (Guwahati - Itanagar)", 
      from: "Guwahati", 
      to: "Itanagar", 
      status: "minor", 
      statusText: "Road Repairs",
      delay: "30m",
      riskScore: 35,
      path: [
        [26.1445, 91.7363],
        [26.6528, 92.7926],
        [27.1009, 93.8118],
        [27.0844, 93.6053]
      ]
    }
  ],

  shipments: [
    { id: "NER-10428", origin: "Guwahati Hub", destination: "Imphal Depot", cargo: "Medical Supplies", weight: "4.5 Tons", priority: "Emergency", risk: "Low", eta: "6h 42m", status: "In Transit", routeId: "nh2_dim", currentPos: [25.6751, 94.1086], timeline: [{ time: "10:30 AM", act: "Dispatched from Guwahati Hub" }, { time: "02:15 PM", act: "Cleared Dimapur Checkpost" }, { time: "05:00 PM", act: "Arrived Kohima Terminal (In Transit)" }] },
    { id: "NER-10319", origin: "Siliguri Gateway", destination: "Gangtok Transit", cargo: "Electronics", weight: "12 Tons", priority: "Normal", risk: "High", eta: "3h 15m", status: "In Transit", routeId: "nh10", currentPos: [26.8967, 88.4682], timeline: [{ time: "01:00 PM", act: "Dispatched from Siliguri Gateway" }, { time: "03:30 PM", act: "Approaching Sevoke Slide Zone" }] },
    { id: "NER-10511", origin: "Guwahati Hub", destination: "Aizawl Station", cargo: "Food & Grain", weight: "15 Tons", priority: "High", risk: "Medium", eta: "8h 10m", status: "In Transit", routeId: "nh6", currentPos: [25.4522, 92.2045], timeline: [{ time: "08:15 AM", act: "Dispatched from Guwahati Hub" }, { time: "11:45 AM", act: "Passed Shillong Transit" }] },
    { id: "NER-10604", origin: "Siliguri Gateway", destination: "Agartala Depot", cargo: "Agriculture Supplies", weight: "8 Tons", priority: "Normal", risk: "Low", eta: "14h 30m", status: "In Transit", routeId: "nh8", currentPos: [24.8961, 92.5954], timeline: [{ time: "05:00 AM", act: "Dispatched from Siliguri Gateway" }, { time: "12:00 PM", act: "Cleared Guwahati Hub Bypass" }] },
    { id: "NER-10752", origin: "Guwahati Hub", destination: "Itanagar Hub", cargo: "General Cargo", weight: "6.2 Tons", priority: "Normal", risk: "Medium", eta: "5h 20m", status: "In Transit", routeId: "nh15", currentPos: [26.6528, 92.7926], timeline: [{ time: "03:00 PM", act: "Dispatched from Guwahati Hub" }] },
    { id: "NER-10112", origin: "Imphal Depot", destination: "Agartala Depot", cargo: "Medicine", weight: "1.5 Tons", priority: "Emergency", risk: "Low", eta: "7h 12m", status: "In Transit", routeId: "nh37", currentPos: [24.8015, 93.1118], timeline: [{ time: "07:30 PM", act: "Dispatched from Imphal Depot" }] }
  ],

  incidents: [
    { id: "inc-1", type: "Landslide", location: "NH-10 Slide Zone", state: "Sikkim", severity: "High", detected: "12 min ago", affectedRoutes: "NH-10", status: "Active", description: "Fresh rockfall near Rangpo has blocked the NH-10 dual lane. Heavy border traffic is backed up." },
    { id: "inc-2", type: "Flooding", location: "Dhemaji Bypass", state: "Assam", severity: "High", detected: "31 min ago", affectedRoutes: "State Highway 14", status: "Monitoring", description: "Brahmaputra tributary overflow has waterlogged the bypass. Light vehicles restricted." },
    { id: "inc-3", type: "Road Closure", location: "Churachandpur Highway", state: "Manipur", severity: "Medium", detected: "1h ago", affectedRoutes: "NH-150", status: "Active", description: "Bridge repairs at Leimatak river crossing. Heavy trucks diverted to local alternate bypasses." }
  ],

  weather: [
    { location: "Guwahati", state: "Assam", temp: "28°C", rainProbability: "30%", condition: "Partly Cloudy" },
    { location: "Gangtok", state: "Sikkim", temp: "16°C", rainProbability: "95%", condition: "Heavy Rain" },
    { location: "Shillong", state: "Meghalaya", temp: "19°C", rainProbability: "80%", condition: "Thundershowers" },
    { location: "Imphal", state: "Manipur", temp: "24°C", rainProbability: "45%", condition: "Cloudy" },
    { location: "Kohima", state: "Nagaland", temp: "21°C", rainProbability: "55%", condition: "Light Rain" }
  ],

  predictions: [
    { category: "Landslide Risk", current: "42%", predicted: "68%", trend: "up", affectedArea: "East Sikkim Corridor (NH-10)", confidence: "87%", explanation: "Rainfall intensity has increased by 34% over the previous 6-hour period while soil saturation indicators remain elevated." },
    { category: "Flood Risk", current: "25%", predicted: "58%", trend: "up", affectedArea: "Brahmaputra Valley (Guwahati / Tezpur)", confidence: "82%", explanation: "Upstream dam discharges coupled with forecasted 120mm rainfall over next 12 hours indicate localized spillover risk." },
    { category: "Road Closure Risk", current: "15%", predicted: "20%", trend: "stable", affectedArea: "Jowai-Badarpur Road (NH-6)", confidence: "90%", explanation: "Scheduled maintenance operations are postponed. Slope stability measures are holding despite wet conditions." },
    { category: "Weather Risk", current: "60%", predicted: "75%", trend: "up", affectedArea: "Meghalaya Highlands", confidence: "95%", explanation: "Extreme monsoon precipitation alert active. Visibility expected to drop below 50 meters in mountain passes." },
    { category: "Congestion Risk", current: "30%", predicted: "45%", trend: "up", affectedArea: "Siliguri Corridor Entry Point", confidence: "85%", explanation: "Increased inbound freight volume due to festival season shipments creating checking queue clearance lag." },
    { category: "Delivery Delay Risk", current: "18%", predicted: "35%", trend: "up", affectedArea: "Guwahati-Imphal Route", confidence: "89%", explanation: "Anticipated checkpost queue build-up at Dimapur due to landslide checks on heavy commercial units." }
  ],

  alerts: [
    { id: "alert-1", severity: "critical", text: "NH-10 accessibility dropped to 38% due to simulated landslide risk.", timestamp: "5 min ago", acknowledged: false },
    { id: "alert-2", severity: "high", text: "4 shipments are likely to exceed ETA by more than 90 minutes.", timestamp: "15 min ago", acknowledged: false },
    { id: "alert-3", severity: "warning", text: "Rainfall forecast indicates increased disruption probability in Meghalaya.", timestamp: "1h ago", acknowledged: false }
  ],

  aiImpactMetrics: {
    before: { delay: "2h 18m", reliability: "71%", response: "48 min" },
    after: { delay: "1h 26m", reliability: "89%", response: "12 min" }
  }
};
console.log("NER-LINK AI: Data store initialized successfully.", window.nerData);
