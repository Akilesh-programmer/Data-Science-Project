"""
Route optimization service — finds optimal EV route with charging stops.
Uses a greedy A*-inspired algorithm with State-of-Charge (SoC) constraints.
"""
import math
import heapq
import numpy as np
from geopy.distance import geodesic
from .data_loader import store


# ── Constants ───────────────────────────────────────────────────
AVG_SPEED_KMH = 80.0            # average travel speed
ENERGY_PER_KM_KWH = 0.18        # ~18 kWh/100 km (typical EV)
CHARGING_EFFICIENCY = 0.90       # 90 % efficiency from grid to battery
TYPICAL_BATTERY_KWH = 60.0      # 60 kWh battery assumed


def _haversine_km(lat1, lon1, lat2, lon2):
    """Fast haversine distance in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _soc_after_travel(current_soc_pct, distance_km, vehicle_range_km):
    """Return SoC % after travelling `distance_km`."""
    consumed_pct = (distance_km / vehicle_range_km) * 100
    return current_soc_pct - consumed_pct


def _charge_time_minutes(soc_from, soc_to, power_kw):
    """Estimate minutes to charge from soc_from% → soc_to% at given power."""
    if power_kw <= 0:
        return 999.0
    kwh_needed = (soc_to - soc_from) / 100 * TYPICAL_BATTERY_KWH
    hours = kwh_needed / (power_kw * CHARGING_EFFICIENCY)
    return max(0, hours * 60)


def optimize_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    vehicle_range_km: float = 300.0,
    current_soc: float = 80.0,
    min_soc: float = 15.0,
) -> dict:
    """
    Greedy route optimizer:
    1.  Compute direct distance.
    2.  If reachable with current SoC, return direct route.
    3.  Otherwise, find nearby operational stations along the corridor,
        pick the best charging stop (maximises progress toward dest while
        keeping SoC above min_soc), repeat.
    """
    total_direct_km = _haversine_km(origin_lat, origin_lng, dest_lat, dest_lng)

    # Can we make it directly?
    reachable_km = (current_soc - min_soc) / 100 * vehicle_range_km
    if reachable_km >= total_direct_km:
        arrival_soc = _soc_after_travel(current_soc, total_direct_km, vehicle_range_km)
        return _build_response(
            origin_lat, origin_lng, dest_lat, dest_lng,
            total_direct_km, [], current_soc, arrival_soc, vehicle_range_km
        )

    # ── Get candidate stations along the corridor ──────────────
    corridor_stations = _get_corridor_stations(
        origin_lat, origin_lng, dest_lat, dest_lng, corridor_width_km=80
    )

    if corridor_stations.empty:
        return {
            "origin": {"lat": origin_lat, "lng": origin_lng},
            "destination": {"lat": dest_lat, "lng": dest_lng},
            "total_distance_km": round(total_direct_km, 2),
            "total_time_hours": 0,
            "charging_stops": [],
            "waypoints": [],
            "energy_consumed_kwh": 0,
            "feasible": False,
            "message": "No charging stations found along the route corridor.",
        }

    # ── Greedy forward search ──────────────────────────────────
    stops = []
    cur_lat, cur_lng = origin_lat, origin_lng
    soc = current_soc
    total_dist = 0.0
    total_charge_time = 0.0
    visited_ids = set()
    max_iterations = 20  # safety cap

    for _ in range(max_iterations):
        remaining_km = _haversine_km(cur_lat, cur_lng, dest_lat, dest_lng)
        reachable_km = (soc - min_soc) / 100 * vehicle_range_km

        if reachable_km >= remaining_km:
            total_dist += remaining_km
            break

        # Find the best next station: furthest along the route we can reach
        max_range_km = reachable_km * 0.95  # small safety margin
        candidates = []
        for _, st in corridor_stations.iterrows():
            if st["StationID"] in visited_ids:
                continue
            dist_to_st = _haversine_km(cur_lat, cur_lng, st["Latitude"], st["Longitude"])
            dist_st_to_dest = _haversine_km(st["Latitude"], st["Longitude"], dest_lat, dest_lng)
            # Must be reachable AND closer to destination
            if dist_to_st <= max_range_km and dist_st_to_dest < remaining_km:
                progress = remaining_km - dist_st_to_dest  # how much closer to dest
                candidates.append((progress, dist_to_st, st))

        if not candidates:
            # Can't reach any station — route infeasible
            return {
                "origin": {"lat": origin_lat, "lng": origin_lng},
                "destination": {"lat": dest_lat, "lng": dest_lng},
                "total_distance_km": round(total_dist, 2),
                "total_time_hours": 0,
                "charging_stops": [s for s in stops],
                "waypoints": [],
                "energy_consumed_kwh": 0,
                "feasible": False,
                "message": f"Route infeasible — cannot reach next station from current position with {soc:.0f}% SoC.",
            }

        # Pick the station that gives most progress toward destination
        candidates.sort(key=lambda x: x[0], reverse=True)
        _, dist_to_station, best = candidates[0]

        # Travel to station
        arrival_soc = _soc_after_travel(soc, dist_to_station, vehicle_range_km)
        total_dist += dist_to_station

        # Charge to 90%
        charge_to = 90.0
        ct_min = _charge_time_minutes(arrival_soc, charge_to, best["MaxPowerKW"])
        total_charge_time += ct_min

        stops.append({
            "station_id": int(best["StationID"]),
            "name": str(best["AddressTitle"]),
            "latitude": float(best["Latitude"]),
            "longitude": float(best["Longitude"]),
            "power_kw": float(best["MaxPowerKW"]),
            "distance_from_prev_km": round(dist_to_station, 2),
            "estimated_charge_time_min": round(ct_min, 1),
            "soc_on_arrival": round(arrival_soc, 1),
            "soc_on_departure": round(charge_to, 1),
        })

        visited_ids.add(best["StationID"])
        cur_lat, cur_lng = best["Latitude"], best["Longitude"]
        soc = charge_to

    # Final leg distance
    final_arrival_soc = _soc_after_travel(soc, _haversine_km(cur_lat, cur_lng, dest_lat, dest_lng), vehicle_range_km)

    # Build waypoints list for map
    waypoints = [{"lat": origin_lat, "lng": origin_lng, "type": "origin"}]
    for s in stops:
        waypoints.append({"lat": s["latitude"], "lng": s["longitude"], "type": "charging_stop"})
    waypoints.append({"lat": dest_lat, "lng": dest_lng, "type": "destination"})

    drive_hours = total_dist / AVG_SPEED_KMH
    total_hours = drive_hours + total_charge_time / 60
    energy = total_dist * ENERGY_PER_KM_KWH

    return {
        "origin": {"lat": origin_lat, "lng": origin_lng},
        "destination": {"lat": dest_lat, "lng": dest_lng},
        "total_distance_km": round(total_dist, 2),
        "total_time_hours": round(total_hours, 2),
        "charging_stops": stops,
        "waypoints": waypoints,
        "energy_consumed_kwh": round(energy, 2),
        "feasible": True,
        "message": f"Route found with {len(stops)} charging stop(s). "
                   f"Total distance: {total_dist:.0f} km, "
                   f"Est. time: {total_hours:.1f} h (incl. charging).",
    }


def _get_corridor_stations(
    lat1, lng1, lat2, lng2, corridor_width_km=80
) -> "pd.DataFrame":
    """Return operational stations within a corridor between two points."""
    df = store.df
    # Only operational stations
    df = df[df["StatusType"] == "Operational"]

    # Bounding box with padding
    pad = corridor_width_km / 111  # rough degrees
    min_lat = min(lat1, lat2) - pad
    max_lat = max(lat1, lat2) + pad
    min_lng = min(lng1, lng2) - pad
    max_lng = max(lng1, lng2) + pad

    mask = (
        (df["Latitude"] >= min_lat)
        & (df["Latitude"] <= max_lat)
        & (df["Longitude"] >= min_lng)
        & (df["Longitude"] <= max_lng)
    )
    corridor = df[mask].copy()

    if corridor.empty:
        return corridor

    # Filter to stations actually near the line (not just in bounding box)
    # Use perpendicular distance from the route line
    def _point_line_dist_km(row):
        # Approximate using cross-track distance
        p = (row["Latitude"], row["Longitude"])
        a = (lat1, lng1)
        b = (lat2, lng2)
        # Vector math on lat/lng (rough but fast)
        ab = (b[0] - a[0], b[1] - a[1])
        ap = (p[0] - a[0], p[1] - a[1])
        ab_len = math.sqrt(ab[0] ** 2 + ab[1] ** 2)
        if ab_len == 0:
            return _haversine_km(p[0], p[1], a[0], a[1])
        cross = abs(ab[0] * ap[1] - ab[1] * ap[0])
        return (cross / ab_len) * 111  # rough km

    corridor["corridor_dist"] = corridor.apply(_point_line_dist_km, axis=1)
    return corridor[corridor["corridor_dist"] <= corridor_width_km]


def _build_response(
    olat, olng, dlat, dlng, dist, stops, start_soc, end_soc, vrange
):
    return {
        "origin": {"lat": olat, "lng": olng},
        "destination": {"lat": dlat, "lng": dlng},
        "total_distance_km": round(dist, 2),
        "total_time_hours": round(dist / AVG_SPEED_KMH, 2),
        "charging_stops": stops,
        "waypoints": [
            {"lat": olat, "lng": olng, "type": "origin"},
            {"lat": dlat, "lng": dlng, "type": "destination"},
        ],
        "energy_consumed_kwh": round(dist * ENERGY_PER_KM_KWH, 2),
        "feasible": True,
        "message": f"Direct route — no charging needed. Arrival SoC: {end_soc:.0f}%",
    }
