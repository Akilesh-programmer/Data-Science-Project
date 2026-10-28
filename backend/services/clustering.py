"""
Clustering service — K-Means and DBSCAN on station coordinates.
Identifies coverage gaps and suggests optimal new station locations.
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from .data_loader import store


def kmeans_clustering(
    country: str | None = None,
    n_clusters: int = 8,
    sample_size: int = 20000,
) -> dict:
    """
    Run K-Means on station lat/lng for a given country (or globally).
    Returns cluster centres with metadata.
    """
    df = store.df if country is None else store.filter_stations(country=country)

    if len(df) < n_clusters:
        return {
            "n_clusters": 0,
            "method": "kmeans",
            "centers": [],
            "inertia": None,
        }

    # Sample if too large
    if len(df) > sample_size:
        df = df.sample(n=sample_size, random_state=42)

    coords = df[["Latitude", "Longitude"]].values
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(coords)
    df = df.copy()
    df["cluster"] = labels

    centres = []
    for i in range(n_clusters):
        cluster_df = df[df["cluster"] == i]
        centres.append(
            {
                "cluster_id": i,
                "latitude": round(float(km.cluster_centers_[i][0]), 6),
                "longitude": round(float(km.cluster_centers_[i][1]), 6),
                "station_count": int(len(cluster_df)),
                "avg_power_kw": round(float(cluster_df["MaxPowerKW"].mean()), 2),
            }
        )

    return {
        "n_clusters": n_clusters,
        "method": "kmeans",
        "centers": centres,
        "inertia": round(float(km.inertia_), 2),
    }


def find_coverage_gaps(
    country: str | None = None,
    grid_resolution: float = 1.0,
    top_n: int = 10,
) -> list[dict]:
    """
    Find geographic areas with low station density — potential sites
    for new charging stations.  Works by overlaying a grid and finding
    cells with the fewest stations near populated cluster centres.
    """
    df = store.df if country is None else store.filter_stations(country=country)
    if len(df) < 50:
        return []

    # Create a grid over the bounding box
    lat_min, lat_max = df["Latitude"].min(), df["Latitude"].max()
    lng_min, lng_max = df["Longitude"].min(), df["Longitude"].max()

    lat_bins = np.arange(lat_min, lat_max + grid_resolution, grid_resolution)
    lng_bins = np.arange(lng_min, lng_max + grid_resolution, grid_resolution)

    df = df.copy()
    df["lat_bin"] = pd.cut(df["Latitude"], bins=lat_bins, labels=False)
    df["lng_bin"] = pd.cut(df["Longitude"], bins=lng_bins, labels=False)

    # Drop any rows with NaN lat_bin or lng_bin (e.g. out of range)
    df_valid = df.dropna(subset=["lat_bin", "lng_bin"])
    if len(df_valid) == 0:
        return []

    # Count stations per grid cell
    grid_counts = (
        df_valid.groupby(["lat_bin", "lng_bin"], observed=False)
        .agg(count=("StationID", "size"), avg_lat=("Latitude", "mean"), avg_lng=("Longitude", "mean"))
        .reset_index()
    )

    if len(grid_counts) == 0:
        return []

    # We want cells that have *some* stations (so they're in a relevant area)
    # but fewer than the median — indicating underserved zones.
    median_count = grid_counts["count"].median()
    underserved = grid_counts[grid_counts["count"] <= median_count].nsmallest(
        top_n, "count"
    )

    return [
        {
            "latitude": round(float(row["avg_lat"]), 4),
            "longitude": round(float(row["avg_lng"]), 4),
            "current_station_count": int(row["count"]),
            "recommendation": "High priority" if row["count"] <= 2 else "Medium priority",
        }
        for _, row in underserved.iterrows()
    ]


def elbow_data(country: str | None = None, max_k: int = 12, sample_size: int = 10000) -> list[dict]:
    """Return inertia values for K=2..max_k for elbow method visualization."""
    df = store.df if country is None else store.filter_stations(country=country)
    if len(df) < 2:
        return []
    if len(df) > sample_size:
        df = df.sample(n=sample_size, random_state=42)

    coords = df[["Latitude", "Longitude"]].values
    results = []
    limit_k = min(max_k, len(coords) - 1)
    for k in range(2, limit_k + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(coords)
        results.append({"k": k, "inertia": round(float(km.inertia_), 2)})
    return results
