"""
Analytics router — stats, distributions, trends, heatmap data, clustering.
"""
from fastapi import APIRouter, Query
from typing import Optional
from ..services import analytics as analytics_svc
from ..services import clustering as clustering_svc

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/summary")
def summary():
    return analytics_svc.summary_stats()


@router.get("/top-countries")
def top_countries(n: int = Query(15, ge=1, le=50)):
    return analytics_svc.top_countries(n)


@router.get("/growth")
def growth():
    return analytics_svc.year_growth()


@router.get("/connectors")
def connectors():
    return analytics_svc.connector_distribution()


@router.get("/power-distribution")
def power_distribution():
    return analytics_svc.power_distribution()


@router.get("/operators")
def operators(n: int = Query(10, ge=1, le=30)):
    return analytics_svc.operator_share(n)


@router.get("/status")
def status_breakdown():
    return analytics_svc.status_breakdown()


@router.get("/heatmap")
def heatmap(sample_size: int = Query(10000, ge=100, le=50000)):
    return analytics_svc.heatmap_data(sample_size)


@router.get("/country-growth")
def country_growth(top_n: int = Query(5, ge=1, le=10)):
    return analytics_svc.country_growth_timeseries(top_n)


# ── Clustering endpoints ───────────────────────────────────────
@router.get("/clusters")
def clusters(
    country: Optional[str] = None,
    n_clusters: int = Query(8, ge=2, le=20),
):
    return clustering_svc.kmeans_clustering(country=country, n_clusters=n_clusters)


@router.get("/coverage-gaps")
def coverage_gaps(
    country: Optional[str] = None,
    top_n: int = Query(10, ge=1, le=30),
):
    return clustering_svc.find_coverage_gaps(country=country, top_n=top_n)


@router.get("/elbow")
def elbow(
    country: Optional[str] = None,
    max_k: int = Query(12, ge=2, le=20),
):
    return clustering_svc.elbow_data(country=country, max_k=max_k)
