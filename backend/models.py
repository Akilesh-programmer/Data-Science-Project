"""
Pydantic models / schemas for the EV Infrastructure API.
"""
from pydantic import BaseModel
from typing import Optional, List


# ── Station Models ──────────────────────────────────────────────
class StationOut(BaseModel):
    StationID: int
    Operator: str
    UsageType: str
    UsageCost: Optional[str] = None
    AddressTitle: str
    Town: Optional[str] = None
    StateOrProvince: Optional[str] = None
    Country: str
    Latitude: float
    Longitude: float
    MaxPowerKW: float
    FastChargeCount: int
    ConnectionTypes: str
    StatusType: str
    YearCreated: int


class StationListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    stations: List[StationOut]


# ── Analytics Models ────────────────────────────────────────────
class SummaryStats(BaseModel):
    total_stations: int
    total_countries: int
    total_operators: int
    avg_power_kw: float
    median_power_kw: float
    operational_pct: float
    fast_charge_pct: float


class CountryCount(BaseModel):
    country: str
    count: int


class YearGrowth(BaseModel):
    year: int
    count: int
    cumulative: int


class ConnectorDistribution(BaseModel):
    connector_type: str
    count: int
    percentage: float


class PowerDistribution(BaseModel):
    range_label: str
    count: int
    percentage: float


class OperatorShare(BaseModel):
    operator: str
    count: int
    percentage: float


# ── Clustering Models ──────────────────────────────────────────
class ClusterCenter(BaseModel):
    cluster_id: int
    latitude: float
    longitude: float
    station_count: int
    avg_power_kw: float


class ClusterResult(BaseModel):
    n_clusters: int
    method: str
    centers: List[ClusterCenter]
    inertia: Optional[float] = None


# ── Route Optimization Models ─────────────────────────────────
class RouteRequest(BaseModel):
    origin_lat: float
    origin_lng: float
    dest_lat: float
    dest_lng: float
    vehicle_range_km: float = 300.0
    current_soc: float = 80.0  # percentage
    min_soc: float = 15.0       # don't go below this


class ChargingStop(BaseModel):
    station_id: int
    name: str
    latitude: float
    longitude: float
    power_kw: float
    distance_from_prev_km: float
    estimated_charge_time_min: float
    soc_on_arrival: float
    soc_on_departure: float


class RouteResponse(BaseModel):
    origin: dict
    destination: dict
    total_distance_km: float
    total_time_hours: float
    charging_stops: List[ChargingStop]
    waypoints: List[dict]
    energy_consumed_kwh: float
    feasible: bool
    message: str
