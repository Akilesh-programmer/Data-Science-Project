"""
Stations router — CRUD + filtering endpoints for EV charging stations.
"""
from fastapi import APIRouter, Query
from typing import Optional
import numpy as np
from ..services.data_loader import store

router = APIRouter(prefix="/api/stations", tags=["Stations"])


@router.get("")
def list_stations(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    country: Optional[str] = None,
    connector_type: Optional[str] = None,
    min_power: Optional[float] = None,
    max_power: Optional[float] = None,
    status: Optional[str] = None,
    year: Optional[int] = None,
    operator: Optional[str] = None,
    # Bounding box
    min_lat: Optional[float] = None,
    min_lng: Optional[float] = None,
    max_lat: Optional[float] = None,
    max_lng: Optional[float] = None,
):
    bbox = None
    if all(v is not None for v in [min_lat, min_lng, max_lat, max_lng]):
        bbox = (min_lat, min_lng, max_lat, max_lng)

    filtered = store.filter_stations(
        country=country,
        connector_type=connector_type,
        min_power=min_power,
        max_power=max_power,
        status=status,
        year=year,
        operator=operator,
        bbox=bbox,
    )

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    page_df = filtered.iloc[start:end]

    cols = [
        "StationID", "Operator", "UsageType", "UsageCost",
        "AddressTitle", "Town", "StateOrProvince", "Country",
        "Latitude", "Longitude", "MaxPowerKW", "FastChargeCount",
        "ConnectionTypes", "StatusType", "YearCreated",
    ]
    stations = page_df[cols].to_dict(orient="records")

    return {"total": total, "page": page, "page_size": page_size, "stations": stations}


@router.get("/geojson")
def stations_geojson(
    country: Optional[str] = None,
    limit: int = Query(5000, ge=1, le=20000),
):
    """Return stations as GeoJSON FeatureCollection for map rendering."""
    filtered = store.filter_stations(country=country)
    if len(filtered) > limit:
        filtered = filtered.sample(n=limit, random_state=42)

    features = []
    for _, row in filtered.iterrows():
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row["Longitude"]), float(row["Latitude"])],
                },
                "properties": {
                    "id": int(row["StationID"]),
                    "name": str(row["AddressTitle"]) if row["AddressTitle"] is not None else "",
                    "operator": str(row["Operator"]) if row["Operator"] is not None else "",
                    "power_kw": float(row["MaxPowerKW"]) if not np.isnan(row["MaxPowerKW"]) else 0.0,
                    "connector": str(row["ConnectionTypes"]) if row["ConnectionTypes"] is not None else "",
                    "status": str(row["StatusType"]) if row["StatusType"] is not None else "",
                    "country": str(row["Country"]) if row["Country"] is not None else "",
                    "year": int(row["YearCreated"]) if not np.isnan(row["YearCreated"]) else 2020,
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}


@router.get("/{station_id}")
def get_station(station_id: int):
    result = store.get_station_by_id(station_id)
    if result is None:
        return {"error": "Station not found"}
    # Convert numpy types to python native
    return {k: (int(v) if hasattr(v, 'item') and isinstance(v, (int,)) else
                float(v) if hasattr(v, 'item') else v)
            for k, v in result.items()
            if k in [
                "StationID", "Operator", "UsageType", "UsageCost",
                "AddressTitle", "Town", "StateOrProvince", "Country",
                "Latitude", "Longitude", "MaxPowerKW", "FastChargeCount",
                "ConnectionTypes", "StatusType", "YearCreated",
            ]}
