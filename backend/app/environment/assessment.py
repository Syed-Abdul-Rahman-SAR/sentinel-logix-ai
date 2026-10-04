"""
SENTINEL LOGIX AI - Environmental Risk Assessment Engine
Phase 10A: Weather & Terrain Intelligence Foundation

Computes a deterministic, explainable 0–100 Environmental Risk Score by combining
four weather sub-signals and four terrain sub-signals.

═══════════════════════════════════════════════════════════════════════════════
SCORE FORMULA
═══════════════════════════════════════════════════════════════════════════════

  weather_risk_score  ∈ [0, 50]  (4 sub-signals, each contributing up to max pts)
  terrain_risk_score  ∈ [0, 50]  (4 sub-signals, each contributing up to max pts)
  environmental_risk_score = weather_risk_score + terrain_risk_score  ∈ [0, 100]

WEATHER SUB-SIGNALS (total max = 50 pts)
─────────────────────────────────────────
  W1 – Precipitation intensity (rainfall_mm / snowfall proxy)    max 20 pts
  W2 – Visibility impairment (visibility_km)                      max 15 pts
  W3 – Wind speed disruption (wind_speed_kmh)                     max 10 pts
  W4 – Temperature extreme (temperature_celsius)                   max  5 pts

TERRAIN SUB-SIGNALS (total max = 50 pts)
─────────────────────────────────────────
  T1 – Elevation factor (normalised 0–1)                          max 20 pts
  T2 – Slope / gradient factor (normalised 0–1)                   max 15 pts
  T3 – Road condition quality                                      max 10 pts
  T4 – Hazard flags (flood_prone + landslide_prone)               max  5 pts

CLASSIFICATION THRESHOLDS
─────────────────────────
  CRITICAL  ≥ 75
  HIGH      ≥ 50
  MEDIUM    ≥ 25
  LOW       <  25

NOTES
─────
  * This engine is entirely separate from assess_logistics_risk() in risk/assessment.py.
    It measures environmental exposure, not operational logistics risk.
  * No machine learning is used; all thresholds are explicit named constants.
  * The function is pure / side-effect-free; it does not read from the database.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# WEATHER SUB-SIGNAL MAXIMUMS
# ─────────────────────────────────────────────────────────────────────────────
W1_MAX = 20.0   # Precipitation intensity
W2_MAX = 15.0   # Visibility impairment
W3_MAX = 10.0   # Wind speed disruption
W4_MAX = 5.0    # Temperature extreme
WEATHER_TOTAL_MAX = W1_MAX + W2_MAX + W3_MAX + W4_MAX   # = 50.0

# ─────────────────────────────────────────────────────────────────────────────
# TERRAIN SUB-SIGNAL MAXIMUMS
# ─────────────────────────────────────────────────────────────────────────────
T1_MAX = 20.0   # Elevation factor
T2_MAX = 15.0   # Slope factor
T3_MAX = 10.0   # Road condition
T4_MAX = 5.0    # Hazard flags
TERRAIN_TOTAL_MAX = T1_MAX + T2_MAX + T3_MAX + T4_MAX   # = 50.0

# ─────────────────────────────────────────────────────────────────────────────
# CLASSIFICATION THRESHOLDS
# ─────────────────────────────────────────────────────────────────────────────
THRESHOLD_CRITICAL = 75.0
THRESHOLD_HIGH = 50.0
THRESHOLD_MEDIUM = 25.0


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL SCORING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _score_precipitation(rainfall_mm: float, precip_type: str) -> Tuple[float, str, str, str]:
    """
    W1 – Precipitation Intensity (max 20 pts).
    Blizzard/heavy snow receives maximum regardless of mm value.
    Returns: (score, severity, description, impact)
    """
    pt = precip_type.upper()

    if pt == "BLIZZARD":
        return (20.0, "CRITICAL",
                f"Blizzard conditions reported (precipitation type: {pt})",
                "Near-zero trafficability; route likely impassable for wheeled logistics vehicles")

    if pt == "SNOW":
        return (16.0, "HIGH",
                f"Snow conditions reported (precipitation type: {pt})",
                "Significant reduction in traction and tyre grip; convoy speed severely limited")

    # For liquid precipitation, threshold by intensity
    if rainfall_mm >= 25.0:
        return (20.0, "CRITICAL",
                f"Extreme rainfall intensity: {rainfall_mm:.1f} mm/hr",
                "Flash flood risk; road surface expected to be flooded or washed out on vulnerable sections")
    elif rainfall_mm >= 15.0:
        return (15.0, "HIGH",
                f"Heavy rainfall: {rainfall_mm:.1f} mm/hr",
                "High flood exposure; movement speed severely reduced and road damage possible")
    elif rainfall_mm >= 5.0:
        return (8.0, "MEDIUM",
                f"Moderate rainfall: {rainfall_mm:.1f} mm/hr",
                "Reduced traction and slower movement; minor flooding possible on low-lying sections")
    elif rainfall_mm > 0.0:
        return (3.0, "LOW",
                f"Light precipitation: {rainfall_mm:.1f} mm/hr",
                "Minor slippery surface conditions; minimal impact on logistics movement")
    else:
        return (0.0, "NONE",
                "No precipitation detected",
                "No precipitation-related movement impediment")


def _score_visibility(visibility_km: float) -> Tuple[float, str, str, str]:
    """
    W2 – Visibility Impairment (max 15 pts).
    Returns: (score, severity, description, impact)
    """
    if visibility_km < 1.0:
        return (15.0, "CRITICAL",
                f"Severely restricted visibility: {visibility_km:.1f} km",
                "Convoy movement extremely hazardous; navigation and obstacle detection critically impaired")
    elif visibility_km < 3.0:
        return (11.0, "HIGH",
                f"Poor visibility: {visibility_km:.1f} km",
                "Significant increase in accident risk; convoy speed and spacing must be reduced")
    elif visibility_km < 6.0:
        return (6.0, "MEDIUM",
                f"Reduced visibility: {visibility_km:.1f} km",
                "Moderate movement difficulty; use of headlights and reduced speed required")
    elif visibility_km < 10.0:
        return (2.0, "LOW",
                f"Slightly reduced visibility: {visibility_km:.1f} km",
                "Minimal operational impact; standard precautions sufficient")
    else:
        return (0.0, "NONE",
                f"Good visibility: {visibility_km:.1f} km",
                "No visibility-related movement impediment")


def _score_wind(wind_speed_kmh: float) -> Tuple[float, str, str, str]:
    """
    W3 – Wind Speed Disruption (max 10 pts).
    Returns: (score, severity, description, impact)
    """
    if wind_speed_kmh >= 70.0:
        return (10.0, "CRITICAL",
                f"Gale-force winds: {wind_speed_kmh:.0f} km/h",
                "Serious risk of vehicle instability; high-sided convoy vehicles at risk of overturning")
    elif wind_speed_kmh >= 50.0:
        return (7.0, "HIGH",
                f"Strong winds: {wind_speed_kmh:.0f} km/h",
                "Vehicle handling significantly affected; heavy cargo vehicles require reduced speed")
    elif wind_speed_kmh >= 30.0:
        return (4.0, "MEDIUM",
                f"Moderate-strong winds: {wind_speed_kmh:.0f} km/h",
                "Some handling difficulty on exposed ridgeline and bridge sections")
    elif wind_speed_kmh >= 15.0:
        return (1.0, "LOW",
                f"Light wind: {wind_speed_kmh:.0f} km/h",
                "Negligible impact on logistics movement")
    else:
        return (0.0, "NONE",
                f"Calm: {wind_speed_kmh:.0f} km/h",
                "No wind-related impediment")


def _score_temperature(temp_c: float) -> Tuple[float, str, str, str]:
    """
    W4 – Temperature Extreme (max 5 pts).
    Returns: (score, severity, description, impact)
    """
    if temp_c <= -10.0:
        return (5.0, "CRITICAL",
                f"Extreme sub-zero temperature: {temp_c:.1f}°C",
                "Severe risk of fuel gelling, brake line freezing, and mechanical failure")
    elif temp_c <= 0.0:
        return (4.0, "HIGH",
                f"Freezing temperature: {temp_c:.1f}°C",
                "Ice formation on road surface; significant vehicle mechanical risk")
    elif temp_c <= 5.0:
        return (2.0, "MEDIUM",
                f"Near-freezing temperature: {temp_c:.1f}°C",
                "Risk of frost on road surface at night; cold-start issues for diesel engines")
    elif temp_c >= 42.0:
        return (3.0, "MEDIUM",
                f"Extreme heat: {temp_c:.1f}°C",
                "Vehicle overheating risk; fuel volatility and tyre blowout risk elevated")
    else:
        return (0.0, "NONE",
                f"Temperature within normal operating range: {temp_c:.1f}°C",
                "No temperature-related movement impediment")


def _score_elevation(elevation_factor: float) -> Tuple[float, str, str, str]:
    """
    T1 – Elevation Factor (max 20 pts).
    Returns: (score, severity, description, impact)
    """
    pts = round(elevation_factor * T1_MAX, 1)
    if elevation_factor >= 0.85:
        sev = "CRITICAL"
        desc = f"Extreme altitude terrain (elevation factor: {elevation_factor:.2f})"
        impact = "Thin air impairs engine performance; route traverses high-altitude passes with avalanche exposure"
    elif elevation_factor >= 0.60:
        sev = "HIGH"
        desc = f"High elevation terrain (elevation factor: {elevation_factor:.2f})"
        impact = "Significant altitude-related speed reduction and increased fuel consumption"
    elif elevation_factor >= 0.35:
        sev = "MEDIUM"
        desc = f"Moderate elevation terrain (elevation factor: {elevation_factor:.2f})"
        impact = "Moderate altitude effect on vehicle performance; extra time and fuel required"
    elif elevation_factor >= 0.10:
        sev = "LOW"
        desc = f"Low elevation change (elevation factor: {elevation_factor:.2f})"
        impact = "Minimal altitude-related impact"
    else:
        sev = "NONE"
        desc = f"Essentially flat terrain (elevation factor: {elevation_factor:.2f})"
        impact = "No altitude-related impediment"
    return (pts, sev, desc, impact)


def _score_slope(slope_factor: float) -> Tuple[float, str, str, str]:
    """
    T2 – Slope / Gradient Factor (max 15 pts).
    Returns: (score, severity, description, impact)
    """
    pts = round(slope_factor * T2_MAX, 1)
    if slope_factor >= 0.80:
        sev = "CRITICAL"
        desc = f"Extreme gradient / severe hairpin sections (slope factor: {slope_factor:.2f})"
        impact = "Heavy vehicles require engine braking assistance; runaway risk on descent sections"
    elif slope_factor >= 0.55:
        sev = "HIGH"
        desc = f"Steep gradient (slope factor: {slope_factor:.2f})"
        impact = "Heavily loaded vehicles require low gearing; tyre wear and brake heat risk"
    elif slope_factor >= 0.30:
        sev = "MEDIUM"
        desc = f"Moderate gradient (slope factor: {slope_factor:.2f})"
        impact = "Reduced convoy speed on uphill sections; extra fuel consumption"
    elif slope_factor >= 0.10:
        sev = "LOW"
        desc = f"Gentle slope (slope factor: {slope_factor:.2f})"
        impact = "Minimal gradient-related impact"
    else:
        sev = "NONE"
        desc = f"Level road (slope factor: {slope_factor:.2f})"
        impact = "No gradient-related impediment"
    return (pts, sev, desc, impact)


def _score_road_condition(road_condition: str) -> Tuple[float, str, str, str]:
    """
    T3 – Road Condition Quality (max 10 pts).
    Based on the road_quality field in SEGMENTS_SEED.
    Returns: (score, severity, description, impact)
    """
    rc = road_condition.upper()
    if rc == "CRITICAL":
        return (10.0, "CRITICAL",
                f"Road condition: CRITICAL (surface severely degraded)",
                "Convoy movement may be impossible; urgent route assessment required")
    elif rc == "POOR":
        return (8.0, "HIGH",
                f"Road condition: POOR",
                "High risk of vehicle damage; movement speed severely restricted and route may be impassable in adverse weather")
    elif rc == "FAIR":
        return (5.0, "MEDIUM",
                f"Road condition: FAIR",
                "Reduced movement speed; minor vehicle stress; avoid in extreme weather if possible")
    elif rc == "GOOD":
        return (2.0, "LOW",
                f"Road condition: GOOD",
                "Acceptable logistics surface; standard precautions apply")
    elif rc == "EXCELLENT":
        return (0.0, "NONE",
                f"Road condition: EXCELLENT",
                "No road-surface-related movement impediment")
    else:
        return (3.0, "LOW",
                f"Road condition: {road_condition} (unclassified)",
                "Road condition not formally graded; exercise caution")


def _score_hazard_flags(flood_prone: bool, landslide_prone: bool) -> Tuple[float, str, str, str]:
    """
    T4 – Hazard Flags (max 5 pts).
    Returns: (score, severity, description, impact)
    """
    if flood_prone and landslide_prone:
        return (5.0, "CRITICAL",
                "Route passes through both flood-prone and landslide-prone terrain",
                "Combined geohazard risk; route may become impassable with moderate-to-heavy rainfall")
    elif landslide_prone:
        return (3.5, "HIGH",
                "Route passes through landslide-prone terrain",
                "Landslide events can block route completely; monitor rainfall and pre-position recovery assets")
    elif flood_prone:
        return (2.5, "MEDIUM",
                "Route passes through flood-prone terrain",
                "Flooding can submerge road sections; route reconnaissance required after heavy rain")
    else:
        return (0.0, "NONE",
                "No significant geohazard flags on this route",
                "No flood or landslide risk identified")


# ─────────────────────────────────────────────────────────────────────────────
# PRIMARY ASSESSMENT FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def assess_environmental_risk(
    weather: Dict[str, Any],
    terrain: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Combines a weather snapshot and terrain record into a full environmental
    risk assessment.  Pure function — no I/O or database access.

    Parameters
    ----------
    weather : dict
        A record from SYNTHETIC_WEATHER_DATA (or matching schema).
    terrain : dict
        A record from SYNTHETIC_TERRAIN_DATA (or matching schema).

    Returns
    -------
    dict
        Full assessment dict compatible with EnvironmentalRiskAssessment schema.
    """
    route_id = weather["route_id"]
    route_name = weather["route_name"]

    contributing_factors: List[Dict[str, Any]] = []

    # ── WEATHER SUB-SIGNALS ──────────────────────────────────────────────────

    # W1 – Precipitation
    w1_pts, w1_sev, w1_desc, w1_impact = _score_precipitation(
        weather["rainfall_mm"], weather["precipitation_type"]
    )
    if w1_sev != "NONE":
        contributing_factors.append({
            "factor": "precipitation_intensity",
            "source": "weather",
            "severity": w1_sev,
            "score_contribution": w1_pts,
            "description": w1_desc,
            "impact": w1_impact,
        })

    # W2 – Visibility
    w2_pts, w2_sev, w2_desc, w2_impact = _score_visibility(weather["visibility_km"])
    if w2_sev != "NONE":
        contributing_factors.append({
            "factor": "visibility_impairment",
            "source": "weather",
            "severity": w2_sev,
            "score_contribution": w2_pts,
            "description": w2_desc,
            "impact": w2_impact,
        })

    # W3 – Wind
    w3_pts, w3_sev, w3_desc, w3_impact = _score_wind(weather["wind_speed_kmh"])
    if w3_sev != "NONE":
        contributing_factors.append({
            "factor": "wind_speed",
            "source": "weather",
            "severity": w3_sev,
            "score_contribution": w3_pts,
            "description": w3_desc,
            "impact": w3_impact,
        })

    # W4 – Temperature
    w4_pts, w4_sev, w4_desc, w4_impact = _score_temperature(weather["temperature_celsius"])
    if w4_sev != "NONE":
        contributing_factors.append({
            "factor": "temperature_extreme",
            "source": "weather",
            "severity": w4_sev,
            "score_contribution": w4_pts,
            "description": w4_desc,
            "impact": w4_impact,
        })

    weather_risk_score = min(WEATHER_TOTAL_MAX, round(w1_pts + w2_pts + w3_pts + w4_pts, 1))

    # ── TERRAIN SUB-SIGNALS ──────────────────────────────────────────────────

    # T1 – Elevation
    t1_pts, t1_sev, t1_desc, t1_impact = _score_elevation(terrain["elevation_factor"])
    if t1_sev != "NONE":
        contributing_factors.append({
            "factor": "elevation_factor",
            "source": "terrain",
            "severity": t1_sev,
            "score_contribution": t1_pts,
            "description": t1_desc,
            "impact": t1_impact,
        })

    # T2 – Slope
    t2_pts, t2_sev, t2_desc, t2_impact = _score_slope(terrain["slope_factor"])
    if t2_sev != "NONE":
        contributing_factors.append({
            "factor": "slope_gradient",
            "source": "terrain",
            "severity": t2_sev,
            "score_contribution": t2_pts,
            "description": t2_desc,
            "impact": t2_impact,
        })

    # T3 – Road condition
    t3_pts, t3_sev, t3_desc, t3_impact = _score_road_condition(terrain["road_condition"])
    if t3_sev != "NONE":
        contributing_factors.append({
            "factor": "road_condition",
            "source": "terrain",
            "severity": t3_sev,
            "score_contribution": t3_pts,
            "description": t3_desc,
            "impact": t3_impact,
        })

    # T4 – Hazard flags
    t4_pts, t4_sev, t4_desc, t4_impact = _score_hazard_flags(
        terrain.get("flood_prone", False), terrain.get("landslide_prone", False)
    )
    if t4_sev != "NONE":
        contributing_factors.append({
            "factor": "geohazard_flags",
            "source": "terrain",
            "severity": t4_sev,
            "score_contribution": t4_pts,
            "description": t4_desc,
            "impact": t4_impact,
        })

    terrain_risk_score = min(TERRAIN_TOTAL_MAX, round(t1_pts + t2_pts + t3_pts + t4_pts, 1))

    # ── COMPOSITE SCORE & CLASSIFICATION ────────────────────────────────────
    env_score = min(100.0, round(weather_risk_score + terrain_risk_score, 1))

    if env_score >= THRESHOLD_CRITICAL:
        classification = "CRITICAL"
    elif env_score >= THRESHOLD_HIGH:
        classification = "HIGH"
    elif env_score >= THRESHOLD_MEDIUM:
        classification = "MEDIUM"
    else:
        classification = "LOW"

    # ── HUMAN-READABLE EXPLANATION ───────────────────────────────────────────
    dominant = "weather" if weather_risk_score >= terrain_risk_score else "terrain"
    top_factors = sorted(contributing_factors, key=lambda f: f["score_contribution"], reverse=True)[:3]
    top_labels = "; ".join(f["description"] for f in top_factors)

    explanation = (
        f"Route '{route_name}' assessed at Environmental Risk Level {classification} "
        f"(Score: {env_score:.1f}/100). "
        f"Weather risk: {weather_risk_score:.1f}/50; Terrain risk: {terrain_risk_score:.1f}/50. "
        f"Dominant risk dimension: {dominant.upper()}. "
        f"Top contributing conditions: {top_labels}."
    )

    now_iso = datetime.now(timezone.utc).isoformat()

    return {
        "route_id": route_id,
        "route_name": route_name,
        "weather": weather,
        "terrain": terrain,
        "weather_risk_score": weather_risk_score,
        "terrain_risk_score": terrain_risk_score,
        "environmental_risk_score": env_score,
        "classification": classification,
        "contributing_factors": contributing_factors,
        "explanation": explanation,
        "data_source": "synthetic_demo",
        "environment": "demo",
        "generated_at": now_iso,
    }
