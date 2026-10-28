"""
Route optimization router.
"""
from fastapi import APIRouter
from ..models import RouteRequest
from ..services.route_optimizer import optimize_route

router = APIRouter(prefix="/api/routes", tags=["Routes"])


@router.post("/optimize")
def optimize(req: RouteRequest):
    return optimize_route(
        origin_lat=req.origin_lat,
        origin_lng=req.origin_lng,
        dest_lat=req.dest_lat,
        dest_lng=req.dest_lng,
        vehicle_range_km=req.vehicle_range_km,
        current_soc=req.current_soc,
        min_soc=req.min_soc,
    )
